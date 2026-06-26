#!/usr/bin/env python3
"""
Whereabouts GPX Importer
Geographica等からエクスポートしたGPXファイルをlocations.jsonlにインポート
重複チェック付き
"""
import xml.etree.ElementTree as ET
import json
import sys

LOG_FILE = '/var/log/locations.jsonl'

def load_existing_timestamps():
    existing = set()
    try:
        with open(LOG_FILE, 'r') as f:
            for line in f:
                try:
                    batch = json.loads(line)
                    for loc in batch.get('locations', []):
                        ts = loc.get('properties', {}).get('timestamp', '')
                        if ts:
                            existing.add(ts)
                except:
                    continue
    except FileNotFoundError:
        pass
    return existing

def gpx_to_jsonl(gpx_file, existing_timestamps):
    tree = ET.parse(gpx_file)
    root = tree.getroot()

    tag = root.tag
    if 'GPX/1/0' in tag:
        ns = {'gpx': 'http://www.topografix.com/GPX/1/0'}
    else:
        ns = {'gpx': 'http://www.topografix.com/GPX/1/1'}

    locations = []
    skipped = 0
    for trkpt in root.findall('.//gpx:trkpt', ns):
        lat = float(trkpt.get('lat'))
        lon = float(trkpt.get('lon'))
        ele   = trkpt.find('gpx:ele', ns)
        time  = trkpt.find('gpx:time', ns)
        speed = trkpt.find('gpx:speed', ns)
        hacc  = trkpt.find('gpx:haccuracy', ns)

        if time is None:
            continue

        ts = time.text
        if ts in existing_timestamps:
            skipped += 1
            continue

        existing_timestamps.add(ts)
        locations.append({
            'type': 'Feature',
            'geometry': {'type': 'Point', 'coordinates': [lon, lat]},
            'properties': {
                'timestamp': ts,
                'altitude': float(ele.text) if ele is not None else 0,
                'speed': float(speed.text) if speed is not None else -1,
                'horizontal_accuracy': float(hacc.text) if hacc is not None else 9999,
            }
        })

    if locations:
        with open(LOG_FILE, 'a') as f:
            f.write(json.dumps({'locations': locations}) + '\n')

    print(f'{gpx_file}: {len(locations)}件インポート、{skipped}件スキップ（重複）')
    return existing_timestamps

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: python3 gpx_import.py file1.gpx file2.gpx ...')
        sys.exit(1)

    print('既存タイムスタンプを読み込み中...')
    existing = load_existing_timestamps()
    print(f'  {len(existing)}件の既存データ')

    for f in sys.argv[1:]:
        existing = gpx_to_jsonl(f, existing)
