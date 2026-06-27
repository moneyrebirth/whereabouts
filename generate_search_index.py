#!/usr/bin/env python3
"""
Whereabouts 検索インデックス生成
summary/*.json からキーワード・地名・コメントのインデックスを生成
"""
import json
import glob
import os

from config import SUMMARY_DIR, WEB_DIR
import os
OUTPUT = os.path.join(WEB_DIR, 'search_index.json')

def main():
    index = []
    for path in sorted(glob.glob(f'{SUMMARY_DIR}/*.json')):
        try:
            with open(path) as f:
                d = json.load(f)
        except:
            continue

        date = d.get('date', '')
        summary_text = d.get('summary', '')
        visits = d.get('visits', [])

        keywords = ''
        comment = ''
        for line in summary_text.split('\n'):
            if line.startswith('キーワード:'):
                keywords = line.replace('キーワード:', '').strip()
            elif line.startswith('コメント:'):
                comment = line.replace('コメント:', '').strip()

        places = [v.get('name', '') for v in visits if v.get('name')]

        index.append({
            'date': date,
            'keywords': keywords,
            'comment': comment,
            'places': places,
            'search_text': f'{date} {keywords} {comment} {" ".join(places)}'.lower()
        })

    with open(OUTPUT, 'w') as f:
        json.dump(index, f, ensure_ascii=False, indent=2)

    print(f'インデックス生成: {len(index)}日分 → {OUTPUT}')

if __name__ == '__main__':
    main()
