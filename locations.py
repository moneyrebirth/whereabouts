from flask import Flask, request, jsonify, abort
import json, datetime

app = Flask(__name__)
import os
API_TOKEN = os.environ.get("WHEREABOUTS_TOKEN", "changeme")
LOG_FILE = '/var/log/locations.jsonl'
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

    points = []
    try:
        with open(LOG_FILE, 'r') as f:
            for line in f:
                try:
                    batch = json.loads(line)
                    for loc in batch.get('locations', []):
                        props = loc.get('properties', {})
                        ts = props.get('timestamp', '')
                        if not ts:
                            continue
                        dt = datetime.datetime.fromisoformat(ts.replace('Z', '+00:00'))
                        dt_jst = dt.astimezone(JST)
                        if dt_jst.strftime('%Y-%m-%d') == date_str:
                            coords = loc['geometry']['coordinates']
                            if coords != [0, 0]:
                                points.append({
                                    'lat': coords[1],
                                    'lng': coords[0],
                                    'timestamp': ts,
                                    'speed': props.get('speed', -1),
                                    'accuracy': props.get('horizontal_accuracy', 9999)
                                })
                except:
                    continue
    except FileNotFoundError:
        pass
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
