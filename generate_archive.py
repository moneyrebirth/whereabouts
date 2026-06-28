#!/usr/bin/env python3
"""
Whereabouts アーカイブページ生成
月次サマリーHTMLが存在する月のリンク一覧を生成
"""
import os
import glob
import datetime
from config import WEB_DIR

def main():
    # 存在する月次HTMLを収集
    months = []
    for path in sorted(glob.glob(os.path.join(WEB_DIR, '????-??.html')), reverse=True):
        basename = os.path.basename(path)
        month = basename.replace('.html', '')
        months.append(month)

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Whereabouts - Archive</title>
  <style>
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #0f1117; color: #e0e0e0; padding: 24px; }}
    h1 {{ font-size: 13px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: #7c9cff; margin-bottom: 20px; }}
    .nav {{ display: flex; gap: 12px; margin-bottom: 24px; }}
    .nav a {{ color: #6070a0; text-decoration: none; font-size: 13px; }}
    .nav a:hover {{ color: #9ab0ff; }}
    .grid {{ display: flex; flex-wrap: wrap; gap: 10px; }}
    .month-link {{ background: #181c27; border: 1px solid #2a2f3f; border-radius: 8px; padding: 10px 20px; text-decoration: none; color: #9ab0ff; font-size: 15px; font-weight: 600; transition: background 0.2s; }}
    .month-link:hover {{ background: #2a3060; border-color: #4a5090; }}
    .count {{ font-size: 11px; color: #4a5070; margin-top: 16px; }}
  </style>
</head>
<body>
  <h1>Whereabouts / Archive</h1>
  <div class="nav">
    <a href="map.html">🗺️ Map</a>
    <a href="status.html">📡 Status</a>
    <a href="search.html">🔍 Search</a>
  </div>
  <div class="grid">
    {''.join(f'<a class="month-link" href="{m}.html">📅 {m}</a>' for m in months)}
  </div>
  <div class="count">{len(months)} months</div>
</body>
</html>
"""
    out_path = os.path.join(WEB_DIR, 'archive.html')
    with open(out_path, 'w') as f:
        f.write(html)
    print(f'生成: {out_path} ({len(months)}ヶ月)')

if __name__ == '__main__':
    main()
