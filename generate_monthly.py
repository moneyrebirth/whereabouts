#!/usr/bin/env python3
"""
Whereabouts 月次サマリーHTML生成
その月の全track pointsを日付別の色で1枚の地図に集約
"""
import json
import sys
import os
import glob
import datetime
import math
import calendar

LOG_FILE = '/var/log/locations.jsonl'
JST = datetime.timezone(datetime.timedelta(hours=9))
from config import LOG_FILE, SUMMARY_DIR, WEB_DIR
NOISE_THRESHOLD_M = 50000


def haversine(p1, p2):
    R = 6371000
    dlat = math.radians(p2['lat'] - p1['lat'])
    dlng = math.radians(p2['lng'] - p1['lng'])
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(p1['lat'])) * math.cos(math.radians(p2['lat'])) *
         math.sin(dlng/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def load_month_points(year, month):
    """その月の全ポイントを日付ごとに分けて返す"""
    days_in_month = calendar.monthrange(year, month)[1]
    by_day = {d: [] for d in range(1, days_in_month + 1)}

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
                if dt_jst.year != year or dt_jst.month != month:
                    continue
                coords = loc.get('geometry', {}).get('coordinates')
                if not coords or coords == [0, 0]:
                    continue
                acc = props.get('horizontal_accuracy', 9999)
                if acc and acc > 100:
                    continue
                by_day[dt_jst.day].append({
                    'lat': coords[1], 'lng': coords[0], 'timestamp': ts
                })

    # 各日付内でソート＆ノイズ除去
    for day, pts in by_day.items():
        pts.sort(key=lambda p: p['timestamp'])
        if not pts:
            continue
        filtered = [pts[0]]
        for p in pts[1:]:
            if haversine(filtered[-1], p) < NOISE_THRESHOLD_M:
                filtered.append(p)
        by_day[day] = filtered

    return by_day


def load_daily_summaries(year, month):
    """既存の日次サマリーJSONから訪問地・キーワードを集約"""
    pattern = f'{SUMMARY_DIR}/{year}-{month:02d}-*.json'
    summaries = []
    for path in sorted(glob.glob(pattern)):
        try:
            with open(path) as f:
                summaries.append(json.load(f))
        except (json.JSONDecodeError, FileNotFoundError):
            continue
    return summaries


def build_html(year, month, by_day, summaries, days_in_month):
    month_str = f'{year}-{month:02d}'

    # 全訪問地点を集約
    all_visits = []
    all_keywords = []
    for s in summaries:
        for v in s.get('visits', []):
            v2 = dict(v)
            v2['date'] = s['date']
            all_visits.append(v2)
        for line in s.get('summary', '').split('\n'):
            if line.startswith('キーワード:'):
                kws = line.replace('キーワード:', '').strip()
                all_keywords.extend([k.strip() for k in kws.split(',') if k.strip()])

    # 頻出キーワード上位
    from collections import Counter
    top_keywords = [k for k, _ in Counter(all_keywords).most_common(8)]

    by_day_json = json.dumps(by_day, ensure_ascii=False, default=str)
    visits_json = json.dumps(all_visits, ensure_ascii=False, default=str)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Whereabouts - {month_str}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #0f1117; color: #e0e0e0; }}
  #header {{ padding: 16px 20px; background: #181c27; border-bottom: 1px solid #2a2f3f; display:flex; align-items:baseline; gap:16px; }}
  #header h1 {{ font-size: 14px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: #7c9cff; }}
  #header .month {{ font-size: 22px; font-weight: 700; }}
  #keywords {{ padding: 12px 20px; background:#161a24; border-bottom:1px solid #2a2f3f; display:flex; gap:8px; flex-wrap:wrap; }}
  .tag {{ background: #2a3060; color: #9ab0ff; padding: 4px 12px; border-radius: 14px; font-size: 12px; }}
  #map {{ height: 78vh; width: 100%; }}
  #legend {{ position:absolute; bottom:20px; left:10px; z-index:1000; background:rgba(15,17,23,0.85); border:1px solid #2a2f3f; border-radius:8px; padding:8px 12px; font-size:11px; color:#8890aa; }}
  #legend .grad {{ width:180px; height:8px; border-radius:4px; margin:4px 0;
     background: linear-gradient(to right, hsl(0,80%,55%), hsl(120,80%,45%), hsl(240,80%,55%), hsl(330,80%,55%)); }}
  #legend .grad-labels {{ display:flex; justify-content:space-between; font-size:10px; color:#6070a0; }}
</style>
</head>
<body>

<div id="header">
  <h1>Whereabouts</h1>
  <div class="month">{month_str}</div>
</div>

<div id="keywords">
  {''.join(f'<span class="tag">{k}</span>' for k in top_keywords)}
</div>

<div id="map"></div>
<div id="legend">
  <div class="grad"></div>
  <div class="grad-labels"><span>1日</span><span>{days_in_month}日</span></div>
</div>

<script>
  const byDay = {by_day_json};
  const visits = {visits_json};
  const daysInMonth = {days_in_month};

  const map = L.map('map').setView([35.68, 139.69], 10);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '© OpenStreetMap contributors', maxZoom: 19
  }}).addTo(map);

  function dayToColor(day) {{
    const hue = ((day - 1) / daysInMonth) * 330;
    return `hsl(${{hue}}, 80%, 55%)`;
  }}

  let allBounds = [];
  Object.keys(byDay).forEach(day => {{
    const pts = byDay[day];
    if (pts.length < 2) return;
    const color = dayToColor(parseInt(day));
    const latlngs = pts.map(p => [p.lat, p.lng]);
    L.polyline(latlngs, {{color: color, weight: 2, opacity: 0.7}}).addTo(map);
    allBounds = allBounds.concat(latlngs);
  }});

  visits.forEach(v => {{
    L.circleMarker([v.lat, v.lng], {{
      radius: 5, color: '#fff', fillColor: '#ffffff', fillOpacity: 0.6, weight: 1
    }}).bindPopup(`<b>${{v.name}}</b><br>${{v.date}} ${{v.arrival}}-${{v.departure}}`).addTo(map);
  }});

  if (allBounds.length > 0) {{
    map.fitBounds(L.latLngBounds(allBounds), {{padding: [30,30]}});
  }}
</script>
</body>
</html>
"""
    return html


def main(year=None, month=None):
    now = datetime.datetime.now(JST)
    year = year or now.year
    month = month or now.month
    days_in_month = calendar.monthrange(year, month)[1]

    print(f'{year}-{month:02d} のデータ集計中...')
    by_day = load_month_points(year, month)
    summaries = load_daily_summaries(year, month)
    print(f'  {len(summaries)} 日分のサマリー, {sum(len(v) for v in by_day.values())} 点')

    html = build_html(year, month, by_day, summaries, days_in_month)

    out_path = os.path.join(WEB_DIR, f'{year}-{month:02d}.html')
    with open(out_path, 'w') as f:
        f.write(html)
    print(f'生成: {out_path}')


if __name__ == '__main__':
    if len(sys.argv) >= 3:
        main(int(sys.argv[1]), int(sys.argv[2]))
    else:
        main()
