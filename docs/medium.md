# Whereabouts — Own Your Location Data: A Self-Hosted GPS Life-Log

> "Where was I that day?" — I wanted to answer this question without asking Google.

Following [MoneyRebirth](https://github.com/moneyrebirth/moneyrebirth), my personal finance tracker, this is the second entry in my "ore-log" series — a Japanese concept of self-tracking your own life data. "Ore" (俺) means "I/me" in Japanese, so "ore-log" literally means "my log."

## The Problem

Google Timeline is convenient. But the idea of my entire location history sitting on Google's servers bothered me. I wanted to own my own data.

It started with a single question to Claude:

> "I want to log my location. Any way to do it without Google Maps?"

Two weeks and a few hours of work later, Whereabouts was born.

## What It Does

### Real-time Map

[Overland](https://github.com/aaronpk/Overland-iOS) (free, OSS iOS/Android app) sends GPS tracks to my own server every 60 seconds. The map updates in real-time with a beautiful color gradient:

- **Time mode**: midnight=blue → noon=green → night=red
- **Speed mode**: stopped=blue → walking=green → train=red

![Whereabouts Demo](https://raw.githubusercontent.com/moneyrebirth/whereabouts/main/screenshots/whereabouts_demo.png)

### Daily Summaries

Every night at 00:30, a cron job automatically:

1. Detects stay clusters (visited places)
2. Reverse geocodes coordinates to place names (Nominatim)
3. Generates keywords and comments via Claude API

```
Keywords: Shinjuku, outing, commute, evening
Comment: A well-balanced day with an afternoon trip to Ikebukuro and evening return.
```

### Monthly Aggregation

One month of tracks on a single map, with colors changing by date.

### Keyword Search

Search "Matsumoto" and find all days I visited in 2018. Search "2021-05" and find my hiking trip records.

### GPX Import

Import tracks from Geographica, YAMAP and other apps — with duplicate detection. My 2018 hike up Mt. Sulfur (Iōdake) came back to life.

The trail rises from the trailhead (1,718m) to the summit (2,654m), painted in a rainbow gradient that follows the altitude — and the memory of that climb comes rushing back.

![Trek Map](https://raw.githubusercontent.com/moneyrebirth/whereabouts/main/screenshots/treck.png)

## The Stack

| Component | Tech |
|---|---|
| GPS Collection | Overland (iOS/Android, OSS) |
| Server | Flask |
| Data | JSONL (no database!) |
| Query | DuckDB |
| Map | Leaflet.js |
| AI | Claude API |
| Infrastructure | VPS / fly.io |

**No database required.** Data accumulates in a single JSONL file. DuckDB queries it directly with SQL — fast enough for years of data.

## Deploy in 5 Minutes (fly.io)

```bash
git clone https://github.com/moneyrebirth/whereabouts
cd whereabouts
fly auth login
fly apps create your-whereabouts
fly volumes create whereabouts_data --app your-whereabouts --region nrt --size 1
fly secrets set WHEREABOUTS_TOKEN=your-secret-token
fly deploy
```

Set Overland's Server URL to `https://your-whereabouts.fly.dev/api/locations` and you're done.

## Phone Setup in 5 Minutes Too

Just two fields in Overland:

- **Server URL**: your server endpoint
- **Access Token**: your secret token

That's it. Overland handles the rest in the background.

## Lessons Learned

### cron and % character

```bash
# This breaks in cron
DATE=$(date +%Y-%m-%d)

# Escape % in crontab
DATE=$(date +\%Y-\%m-\%d)
```

### Noise filtering threshold

Train journeys jump 15km+ between GPS readings. Increasing the noise threshold from 5km to 50km fixed disappearing tracks.

### DuckDB migration

As the JSONL grew, reading all lines in Python became slow. Switching to DuckDB SQL filtering made `/api/today` respond in under 1 second regardless of file size.

```python
sql = f"""
SELECT locations.geometry.coordinates[2] as lat, ...
FROM (SELECT unnest(locations) as locations FROM read_ndjson('{LOG_FILE}'))
WHERE locations.properties.timestamp >= '{utc_start}'
"""
```

## Why Simple Wins

The core is just "receive location data and display it on a map." That simplicity makes it incredibly versatile:

- 📍 Personal life-log
- 🚴 Cycling route visualization
- 🏔️ Hiking track logging (altitude gradient!)
- 👨‍👩‍👧 Family location sharing
- 🚗 Vehicle tracking

Same system, endless applications.

## Your Data, Your Rules

- Location data never leaves your own server
- Fully open source — see exactly what runs
- JSONL format — readable by any tool

The past came alive when I imported old GPX files. Mountains climbed in 2018, cities visited in 2021 — all searchable, all mine.

---

**GitHub**: https://github.com/moneyrebirth/whereabouts

**Japanese article**: https://zenn.dev/dai610/articles/1f3e7add7dc08b
