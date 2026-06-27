---
title: "Whereabouts — 自分の位置情報は自分で管理する【俺ログ第2弾】"
emoji: "📍"
type: "tech"
topics: ["python", "flask", "leaflet", "lifelog", "DuckDB", "oss"]
published: true
---

## はじめに

[MoneyRebirth](https://github.com/moneyrebirth/moneyrebirth) ([Zenn紹介記事](https://zenn.dev/articles/7c03c57176a90f/edit))に続く、俺ログシリーズ第2弾です。
家計は自分で管理できた。次は**位置情報**だ。

Googleのタイムラインは便利だけど、自分の行動履歴がGoogleのサーバーに蓄積されていくのが気になっていた。そして何より、「あの日俺はどこにいたか」を**自分のサーバーで記録・可視化したかった**。

きっかけはClaudeへのこんな一言だった。

> 「自分の位置情報をログに残したい。Google Mapsとか使わないで、何か方法ある？」

この曖昧な質問から約2週間、実働2〜3時間で**Whereabouts**が生まれた。

## できたもの

### リアルタイム地図

iPhoneアプリ [Overland](https://github.com/aaronpk/Overland-iOS)（OSS・無料）が60秒ごとに自前サーバーに位置情報を送信。ブラウザで軌跡をリアルタイムに確認できる。

時間帯と速度で色が変わるグラデーションが見ていて楽しい。

- **時間モード**: 深夜=青 → 昼=緑 → 夜=赤
- **速度モード**: 停止=青 → 徒歩=緑 → 電車=赤

![リアルタイム地図](https://raw.githubusercontent.com/moneyrebirth/whereabouts/main/screenshots/whereabouts_demo.png)

### 日次サマリー

毎日深夜0:30にcronが自動実行。

1. 滞在クラスタを検出（訪問地の特定）
2. Nominatimで逆ジオコーディング（座標→地名）
3. Claude APIでキーワードとコメントを自動生成

```
キーワード: 池袋, 外出, 帰宅, 滞在, 夜
コメント: 午後から池袋エリアへ外出し、夜に帰宅したメリハリのある一日。
```

### 月次集約地図

1ヶ月分の軌跡を1枚の地図に。日付で色が変わる虹色グラデーション。

### キーワード検索

「松本」で検索したら2018年の旅行が出てくる。「茅野市」で検索したら登山した日が全部出てくる。

### GPXインポート

GeographicaやYAMAPからエクスポートしたGPXファイルをインポートできる。重複チェック付き。

過去の登山記録も取り込んで、2018年の硫黄岳登山が蘇った。

標高グラデーションで登山ルートを可視化する `map_trek.html` も作った。
美濃戸山荘から硫黄岳までの登山の記録、高度が上るにつれて虹色に変化する山行軌跡、かっこよいね!l
![山行記録](https://raw.github.com/moneyrebirth/whereabouts/main/screenshots/trek.png)

## 技術スタック

| 要素 | 技術 |
|---|---|
| GPS収集 | Overland (iOS/Android, OSS) |
| サーバー | Flask |
| データ | JSONL（DBなし） |
| クエリ | DuckDB |
| 地図 | Leaflet.js |
| AI | Claude API (Anthropic) |
| インフラ | さくらVPS / fly.io |

**DBは使っていない。** データはJSONLファイルに溜まっていくだけ。それでも十分動く。

## セットアップは5分

### スマホの設定も5分

Android, iPhoneでの設定はたった2項目だけ。

1. Google Play, App StoreでOverlandをインストール（無料）
2. 設定画面で、"Server URL" を選択し以下を入力：
   - **Server URL**: `https://your-server.com/api/locations`
   - **Access Token**: 設定した`WHEREABOUTS_TOKEN`の値

<img src="https://raw.github.com/moneyrebirth/whereabouts/main/screenshots/overland.png" width="450">

これだけ。あとはバックグラウンドで自動的に位置情報を送り続ける。

### fly.ioなら最速

```bash
git clone https://github.com/moneyrebirth/whereabouts
cd whereabouts
fly auth login
fly apps create your-whereabouts
fly volumes create whereabouts_data --app your-whereabouts --region nrt --size 1
fly secrets set WHEREABOUTS_TOKEN=your-secret-token
fly deploy
```

OverlandのServer URLに `https://your-whereabouts.fly.dev/api/locations` を設定するだけ。

### VPSならフル機能

cronで日次サマリー、Claude APIでキーワード生成まで動く。

## 詰まったところ

### cronの%エスケープ

```bash
# これはダメ
DATE=$(date +%Y-%m-%d)

# cronでは%をエスケープ
DATE=$(date +\%Y-\%m-\%d)
```

### ノイズ除去の閾値

電車移動で15km以上ジャンプする点が「ノイズ」として除外されていた。閾値を5kmから50kmに広げて解決。

### DuckDB移行

JSONLファイルが大きくなるにつれて全行Pythonで読む処理が重くなった。DuckDBに移行してSQLで直接フィルタリング。レスポンスが劇的に改善。

```python
sql = f"""
SELECT locations.geometry.coordinates[2] as lat, ...
FROM (SELECT unnest(locations) as locations FROM read_ndjson('{LOG_FILE}'))
WHERE locations.properties.timestamp >= '{utc_start}'
"""
```

## データは自分のもの

Whereaboutsのコアコンセプトは**データの自己所有**。

- 位置情報はGoogleにもAppleにも送らない
- 自前サーバーのJSONLファイルに蓄積
- OSSなので中身が全部見える

2018年の涸沢カール、硫黄岳、松本...過去の記録も取り込んで、「あの日、俺はそこにいた」が蘇った。

## シンプルだからこその圧倒的汎用性

Whereaboutsのコアは「位置情報を受け取って地図に表示する」だけ。シンプルな構成だからこそ、用途が広い。

- 📍 **俺ログ** — 「あの日どこにいたか」を自分のサーバーで
- 🚴 **自転車ログ** — 速度グラデーションでルートを可視化
- 🏔️ **登山記録** — 標高グラデーション、GPXインポートで過去の記録も
- 👨‍👩‍👧 **家族の見守り** — 複数デバイスを色分けで表示
- 🚗 **運行管理** — 車両の移動履歴を簡単に把握

同じ仕組みで全部できる。大げさなシステムは不要。

Overlandアプリ（OSS）を入れてServer URLを設定するだけで、AndroidでもiOSでも動く。デバイスを増やすのも設定1つ。

## おわりに

「自分の位置情報をログに残したい」という一言から始まって、約2週間で完成した。

MoneyRebirth（家計）、Whereabouts（位置情報）と続いた俺ログシリーズ。次は何を自分で管理しようか。

---

- GitHub: https://github.com/moneyrebirth/whereabouts
- 日本語README: [README.ja.md](https://github.com/moneyrebirth/whereabouts/blob/main/README.ja.md)
