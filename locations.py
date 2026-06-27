from flask import Flask, request, jsonify, abort
import json, datetime

app = Flask(__name__)
import os
API_TOKEN = os.environ.get("WHEREABOUTS_TOKEN", "changeme")
from config import LOG_FILE
JST = datetime.timezone(datetime.timedelta(hours=9))

@app.route('/api/locations', methods=['POST'])
def log_location():
    auth = request.headers.get('Authorization', '')
    if auth != f'Bearer {API_TOKEN}':
        abort(401)
    data = request.json
    with open(LOG_FILE, 'a') as f:
        f.write(json.dumps(data) + '\n')
    return {"result": "ok"}

@app.route('/api/today', methods=['GET'])
def today():
    auth = request.headers.get('Authorization', '')
    if auth != f'Bearer {API_TOKEN}':
        abort(401)

    date_str = request.args.get('date')
    if not date_str:
        date_str = datetime.datetime.now(JST).strftime('%Y-%m-%d')

    jst_start = datetime.datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=JST)
    jst_end = jst_start + datetime.timedelta(days=1)
    utc_start = jst_start.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    utc_end = jst_end.astimezone(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')

    try:
        import duckdb
        conn = duckdb.connect()
        sql = f"SELECT locations.geometry.coordinates[2] as lat, locations.geometry.coordinates[1] as lng, locations.properties.timestamp as ts, locations.properties.speed as speed, locations.properties.horizontal_accuracy as accuracy, locations.properties.altitude as altitude FROM (SELECT unnest(locations) as locations FROM read_ndjson('{LOG_FILE}')) WHERE locations.properties.timestamp >= '{utc_start}' AND locations.properties.timestamp < '{utc_end}' AND locations.geometry.coordinates[1] != 0 ORDER BY ts"
        rows = conn.execute(sql).fetchall()
        conn.close()
        points = [{'lat': r[0], 'lng': r[1], 'timestamp': r[2], 'speed': r[3] if r[3] is not None else -1, 'accuracy': r[4] if r[4] is not None else 9999, 'altitude': r[5] if r[5] is not None else 0} for r in rows if r[0] and r[1]]
    except Exception as e:
        return jsonify({'error': str(e)}), 500

    total = len(points)
    if total > 2000:
        indices = [int(i * total / 2000) for i in range(2000)]
        points = [points[i] for i in indices]
    return jsonify({'points': points, 'count': len(points), 'total': total})

@app.route('/api/status', methods=['GET'])
def status():
    import os
    try:
        stat = os.stat(LOG_FILE)
        size_mb = round(stat.st_size / 1024 / 1024, 2)
        # 最終受信時刻と今日の件数
        today_str = datetime.datetime.now(JST).strftime('%Y-%m-%d')
        last_ts = None
        today_count = 0
        with open(LOG_FILE, 'r') as f:
            for line in f:
                try:
                    batch = json.loads(line)
                    for loc in batch.get('locations', []):
                        ts = loc.get('properties', {}).get('timestamp', '')
                        if not ts:
                            continue
                        if last_ts is None or ts > last_ts:
                            last_ts = ts
                        dt = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        if dt.astimezone(JST).strftime('%Y-%m-%d') == today_str:
                            today_count += 1
                except:
                    continue
        last_jst = ''
        if last_ts:
            dt = datetime.datetime.fromisoformat(last_ts.replace('Z', '+00:00'))
            last_jst = dt.astimezone(JST).strftime('%Y-%m-%d %H:%M:%S')
        return jsonify({
            'status': 'ok',
            'last_received': last_ts,
            'last_received_jst': last_jst,
            'today_count': today_count,
            'log_size_mb': size_mb,
            'server_time_jst': datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
