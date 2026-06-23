#!/usr/bin/env python3
"""
Whereabouts カレンダーHTML生成
月ごとにデータがある日をリンク付きで表示
"""
import os
import sys
import datetime
import calendar
import glob

WHEREABOUTS_DIR = '/var/www/html_dai/whereabouts'
JST = datetime.timezone(datetime.timedelta(hours=9))


def build_calendar(year, month):
    days_in_month = calendar.monthrange(year, month)[1]
    month_str = f'{year}-{month:02d}'

    # データがある日を確認
    available = set()
    for day in range(1, days_in_month + 1):
        path = f'{WHEREABOUTS_DIR}/summary-{year}-{month:02d}-{day:02d}.html'
        if os.path.exists(path):
            available.add(day)

    # 月次サマリーがあるか
    monthly_exists = os.path.exists(f'{WHEREABOUTS_DIR}/{month_str}.html')

    # カレンダーのグリッドを生成
    cal = calendar.monthcalendar(year, month)

    rows = ''
    for week in cal:
        row = ''
        for day in week:
            if day == 0:
                row += '<td class="empty"></td>'
            elif day in available:
                row += f'<td class="has-data"><a href="summary-{year}-{month:02d}-{day:02d}.html">{day}</a></td>'
            else:
                row += f'<td class="no-data">{day}</td>'
        rows += f'<tr>{row}</tr>'

    monthly_link = ''
    if monthly_exists:
        monthly_link = f'<a href="{month_str}.html" class="monthly-btn">📍 {month_str} 月次サマリー</a>'

    html = f"""<!DOCTYPE html>
<html lang="ja">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Whereabouts - {month_str}</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: 'Helvetica Neue', Arial, sans-serif; background: #0f1117; color: #e0e0e0; padding: 24px; }}
  h1 {{ font-size: 13px; font-weight: 600; letter-spacing: 0.12em; text-transform: uppercase; color: #7c9cff; margin-bottom: 8px; }}
  h2 {{ font-size: 24px; font-weight: 700; margin-bottom: 20px; }}
  .monthly-btn {{ display: inline-block; background: #2a3060; border: 1px solid #4a5090; color: #9ab0ff; padding: 8px 16px; border-radius: 8px; text-decoration: none; font-size: 13px; margin-bottom: 20px; }}
  .monthly-btn:hover {{ background: #3a4080; }}
  table {{ width: 100%; border-collapse: collapse; max-width: 400px; }}
  th {{ padding: 8px; font-size: 11px; color: #6070a0; text-align: center; }}
  td {{ padding: 10px; text-align: center; border-radius: 8px; font-size: 16px; }}
  td.empty {{ }}
  td.no-data {{ color: #4a5070; }}
  td.has-data {{ background: #1a2040; }}
  td.has-data a {{ color: #9ab0ff; text-decoration: none; font-weight: 600; }}
  td.has-data a:hover {{ color: #fff; }}
  .nav {{ display: flex; gap: 12px; margin-top: 24px; }}
  .nav a {{ color: #6070a0; text-decoration: none; font-size: 13px; }}
  .nav a:hover {{ color: #9ab0ff; }}
</style>
</head>
<body>
<h1>Whereabouts</h1>
<h2>{month_str}</h2>

{monthly_link}

<table>
  <thead>
    <tr>
      <th>月</th><th>火</th><th>水</th><th>木</th><th>金</th><th>土</th><th>日</th>
    </tr>
  </thead>
  <tbody>
    {rows}
  </tbody>
</table>

<div class="nav">
  <a href="map.html">🗺️ リアルタイム地図</a>
  <a href="status.html">📡 ステータス</a>
</div>

</body>
</html>
"""
    return html


def main(year=None, month=None):
    now = datetime.datetime.now(JST)
    year = year or now.year
    month = month or now.month
    month_str = f'{year}-{month:02d}'

    html = build_calendar(year, month)
    out_path = f'{WHEREABOUTS_DIR}/{month_str}-calendar.html'
    with open(out_path, 'w') as f:
        f.write(html)
    print(f'生成: {out_path}')


if __name__ == '__main__':
    if len(sys.argv) >= 3:
        main(int(sys.argv[1]), int(sys.argv[2]))
    else:
        main()
