#!/usr/bin/env python3
"""
Whereabouts 日次サマリーHTML生成
summary/{date}.json を読み込み、地図+訪問地+キーワードのHTMLを生成
"""
import json
import sys
import datetime
import math

import os
from config import LOG_FILE, SUMMARY_DIR, WEB_DIR
JST = datetime.timezone(datetime.timedelta(hours=9))
NOISE_THRESHOLD_M = 50000


def haversine(p1, p2):
    R = 6371000
    dlat = math.radians(p2['lat'] - p1['lat'])
    dlng = math.radians(p2['lng'] - p1['lng'])
    a = (math.sin(dlat/2)**2 +
         math.cos(math.radians(p1['lat'])) * math.cos(math.radians(p2['lat'])) *
         math.sin(dlng/2)**2)
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))


def load_track_points(date_str):
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
                acc = props.get('horizontal_accuracy', 9999)
                if acc and acc > 100:
                    continue
                points.append({'lat': coords[1], 'lng': coords[0], 'timestamp': ts})
    points.sort(key=lambda p: p['timestamp'])

    # ノイズ除去
    if not points:
        return points
    filtered = [points[0]]
    for p in points[1:]:
        if haversine(filtered[-1], p) < NOISE_THRESHOLD_M:
            filtered.append(p)
    return filtered


def build_html(date_str, summary_data, track_points):
    visits = summary_data.get('visits', [])
    summary_text = summary_data.get('summary', '')

    # キーワード/コメントをパース
    keywords = ''
    comment = ''
    for line in summary_text.split('\n'):
        if line.startswith('キーワード:'):
            keywords = line.replace('キーワード:', '').strip()
        elif line.startswith('コメント:'):
            comment = line.replace('コメント:', '').strip()

    track_json = json.dumps(track_points, ensure_ascii=False)
    visits_json = json.dumps(visits, ensure_ascii=False)

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Whereabouts - {date_str}</title>
<link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
<script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #0f1117; color: #e0e0e0; }}
  #header {{ padding: 16px 20px; background: #181c27; border-bottom: 1px solid #2a2f3f; }}
  #header h1 {{ font-size: 14px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: #7c9cff; }}
  #header .date {{ font-size: 22px; font-weight: 700; margin-top: 4px; }}
  #summary {{ padding: 14px 20px; background: #161a24; border-bottom: 1px solid #2a2f3f; }}
  #keywords {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 8px; }}
  .tag {{ background: #2a3060; color: #9ab0ff; padding: 4px 12px; border-radius: 14px; font-size: 12px; }}
  #comment {{ font-size: 14px; color: #c0c8e0; line-height: 1.6; }}
  #map {{ height: 70vh; width: 100%; position: relative; }}
  #legend {{ position: absolute; bottom: 30px; left: 10px; z-index: 1000; background: rgba(15,17,23,0.85); border: 1px solid #2a2f3f; border-radius: 8px; padding: 8px 12px; font-size: 11px; color: #8890aa; }}
  #legend .grad {{ width: 160px; height: 8px; border-radius: 4px; background: linear-gradient(to right, hsl(0,95%,55%), hsl(60,95%,50%), hsl(120,95%,45%), hsl(180,95%,50%), hsl(240,95%,60%), hsl(300,95%,55%), hsl(360,95%,55%)); margin: 4px 0; }}
  #legend .grad-labels {{ display: flex; justify-content: space-between; font-size: 10px; color: #6070a0; }}
  #visits {{ padding: 16px 20px; }}
  #visits h2 {{ font-size: 13px; color: #8890aa; text-transform: uppercase; letter-spacing: 0.08em; margin-bottom: 10px; }}
  .visit-row {{ display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px solid #20242f; font-size: 13px; }}
  .visit-time {{ color: #7c9cff; min-width: 110px; }}
  .visit-name {{ color: #e0e0e0; }}
  .visit-dur {{ color: #6070a0; margin-left: auto; }}
</style>
</head>
<body>

<div id="header">
  <h1>Whereabouts</h1>
  <div class="date">{date_str}</div>
</div>

<div id="summary">
  <div id="keywords">
    {''.join(f'<span class="tag">{k.strip()}</span>' for k in keywords.split(',') if k.strip())}
  </div>
  <div id="comment">{comment}</div>
</div>

<div id="map">
  <div id="legend">
    <div class="grad"></div>
    <div class="grad-labels"><span>深夜</span><span>昼</span><span>深夜</span></div>
  </div>
</div>

<div id="visits">
  <h2>訪問地</h2>
  <div id="visit-list"></div>
</div>

<script>
  const track = {track_json};
  const visits = {visits_json};

  const map = L.map('map').setView([35.68, 139.69], 11);
  L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
    attribution: '© OpenStreetMap contributors', maxZoom: 19
  }}).addTo(map);

  function timeToColor(ts) {{
    const dt = new Date(new Date(ts).getTime() + 9*60*60*1000);
    const h = dt.getUTCHours() + dt.getUTCMinutes()/60 + dt.getUTCSeconds()/3600;
    return `hsl(${{(h/24)*360}}, 95%, 55%)`;
  }}

  if (track.length > 1) {{
    for (let i = 0; i < track.length - 1; i++) {{
      L.polyline(
        [[track[i].lat, track[i].lng],[track[i+1].lat, track[i+1].lng]],
        {{color: timeToColor(track[i].timestamp), weight: 3, opacity: 0.85}}
      ).addTo(map);
    }}
    const bounds = L.latLngBounds(track.map(p => [p.lat, p.lng]));
    map.fitBounds(bounds, {{padding: [30,30]}});
  }}

  visits.forEach(v => {{
    L.circleMarker([v.lat, v.lng], {{
      radius: 9, color: '#fff', fillColor: '#ff9944', fillOpacity: 1, weight: 2
    }}).bindPopup(`<b>${{v.name}}</b><br>${{v.arrival}} - ${{v.departure}} (${{v.duration_min}}分)`).addTo(map);
  }});

  const listEl = document.getElementById('visit-list');
  visits.forEach(v => {{
    const row = document.createElement('div');
    row.className = 'visit-row';
    row.innerHTML = `<span class="visit-time">${{v.arrival}} - ${{v.departure}}</span><span class="visit-name">${{v.name}}</span><span class="visit-dur">${{v.duration_min}}分</span>`;
    listEl.appendChild(row);
  }});
</script>
</body>
</html>
"""
    return html


def main(date_str=None):
    if date_str is None:
        date_str = datetime.datetime.now(JST).strftime('%Y-%m-%d')

    summary_path = os.path.join(SUMMARY_DIR, f'{date_str}.json')
    try:
        with open(summary_path, 'r') as f:
            summary_data = json.load(f)
    except FileNotFoundError:
        print(f'summary not found: {summary_path}', file=sys.stderr)
        sys.exit(1)

    track_points = load_track_points(date_str)
    html = build_html(date_str, summary_data, track_points)

    out_path = os.path.join(WEB_DIR, f'summary-{date_str}.html')
    with open(out_path, 'w') as f:
        f.write(html)
    print(f'生成: {out_path}')


if __name__ == '__main__':
    target_date = sys.argv[1] if len(sys.argv) > 1 else None
    main(target_date)
