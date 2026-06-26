#!/usr/bin/env python3
"""
Whereabouts 日次サマリー生成
- jsonlから指定日の座標を抽出
- 滞在クラスタを検出
- 逆ジオコーディングで地名取得
- Claude APIでキーワード/コメント生成
"""
import json
import sys
import time
import math
import datetime
import requests
import anthropic

import os
from config import LOG_FILE, SUMMARY_DIR, ANTHROPIC_KEY_FILE
JST = datetime.timezone(datetime.timedelta(hours=9))

NOMINATIM_URL = 'https://nominatim.openstreetmap.org/reverse'
USER_AGENT = 'whereabouts-app (personal lifelog)'

CLUSTER_RADIUS_M = 150
MIN_STAY_MINUTES = 8


def haversine(p1, p2):
    R = 6371000
    lat1, lng1 = p1['lat'], p1['lng']
    lat2, lng2 = p2['lat'], p2['lng']
    dlat = math.radians(lat2 - lat1)
    dlng = math.radians(lng2 - lng1)
    a = (math.sin(dlat / 2) ** 2 +
         math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) *
         math.sin(dlng / 2) ** 2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def load_points_for_date(date_str):
    points = []
    with open(LOG_FILE, 'r') as f:
        for line in f:
            try:
                batch = json.loads(line)
            except json.JSONDecodeError:
                continue
            for loc in batch.get('locations', []):
                props = loc.get('properties', {})
                ts = props.get('timestamp', '')
                if not ts:
                    continue
                try:
                    dt = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
                except ValueError:
                    continue
                dt_jst = dt.astimezone(JST)
                if dt_jst.strftime('%Y-%m-%d') != date_str:
                    continue
                coords = loc.get('geometry', {}).get('coordinates')
                if not coords or coords == [0, 0]:
                    continue
                points.append({
                    'lat': coords[1],
                    'lng': coords[0],
                    'timestamp': ts,
                    'dt_jst': dt_jst,
                    'accuracy': props.get('horizontal_accuracy', 9999),
                })
    points.sort(key=lambda p: p['dt_jst'])
    return points


def filter_accuracy(points, max_accuracy=100):
    return [p for p in points if p['accuracy'] is None or p['accuracy'] <= max_accuracy]


def detect_stays(points, radius_m=CLUSTER_RADIUS_M, min_minutes=MIN_STAY_MINUTES):
    if not points:
        return []

    stays = []
    cluster = [points[0]]

    for p in points[1:]:
        center = cluster[len(cluster) // 2]
        if haversine(center, p) <= radius_m:
            cluster.append(p)
        else:
            stays.append(cluster)
            cluster = [p]
    stays.append(cluster)

    visits = []
    for cluster in stays:
        if len(cluster) < 2:
            continue
        duration = (cluster[-1]['dt_jst'] - cluster[0]['dt_jst']).total_seconds() / 60
        if duration >= min_minutes:
            avg_lat = sum(p['lat'] for p in cluster) / len(cluster)
            avg_lng = sum(p['lng'] for p in cluster) / len(cluster)
            visits.append({
                'lat': avg_lat,
                'lng': avg_lng,
                'arrival': cluster[0]['dt_jst'].strftime('%H:%M'),
                'departure': cluster[-1]['dt_jst'].strftime('%H:%M'),
                'duration_min': round(duration),
            })
    return visits


def reverse_geocode(lat, lng):
    try:
        r = requests.get(NOMINATIM_URL, params={
            'lat': lat, 'lon': lng, 'format': 'json', 'zoom': 16,
            'accept-language': 'ja'
        }, headers={'User-Agent': USER_AGENT}, timeout=10)
        data = r.json()
        addr = data.get('address', {})
        name = (addr.get('amenity') or addr.get('shop') or addr.get('building')
                or addr.get('railway') or addr.get('neighbourhood')
                or addr.get('suburb') or addr.get('city')
                or data.get('display_name', '不明').split(',')[0])
        return name
    except Exception as e:
        print(f'  geocode error: {e}', file=sys.stderr)
        return '不明'


def generate_keywords(visits, date_str):
    if not visits:
        return "この日の移動データはありません。"

    place_list = "\n".join(
        f"- {v['arrival']}〜{v['departure']} ({v['duration_min']}分): {v['name']}"
        for v in visits
    )

    with open(ANTHROPIC_KEY_FILE) as f:
        api_key = f.read().strip()
    client = anthropic.Anthropic(api_key=api_key)
    prompt = f"""以下は{date_str}に訪れた場所のリストです。

{place_list}

この訪問履歴から、その日の行動を表すキーワードを3〜5個と、1行の短いコメント（その日どんな日だったか）を日本語で生成してください。
出力フォーマット:
キーワード: xxx, xxx, xxx
コメント: ここに1行コメント
"""
    message = client.messages.create(
        model='claude-sonnet-4-6',
        max_tokens=200,
        messages=[{'role': 'user', 'content': prompt}]
    )
    return message.content[0].text


def main(date_str=None):
    if date_str is None:
        date_str = datetime.datetime.now(JST).strftime('%Y-%m-%d')

    print(f'[{date_str}] 座標読み込み中...')
    points = load_points_for_date(date_str)
    points = filter_accuracy(points)
    print(f'  {len(points)} 件の座標')

    print('滞在地検出中...')
    visits = detect_stays(points)
    print(f'  {len(visits)} 箇所の訪問地')

    print('逆ジオコーディング中...')
    for v in visits:
        v['name'] = reverse_geocode(v['lat'], v['lng'])
        print(f"  {v['arrival']}〜{v['departure']} ({v['duration_min']}分): {v['name']}")
        time.sleep(1.1)

    print('キーワード生成中...')
    summary_text = generate_keywords(visits, date_str)
    print(summary_text)

    result = {
        'date': date_str,
        'point_count': len(points),
        'visits': visits,
        'summary': summary_text,
    }

    out_path = os.path.join(SUMMARY_DIR, f'{date_str}.json')
    with open(out_path, 'w') as f:
        json.dump(result, f, ensure_ascii=False, indent=2, default=str)
    print(f'保存先: {out_path}')


if __name__ == '__main__':
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    main(target_date)
