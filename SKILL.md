---
name: taiwan-basketball
description: "Taiwan professional basketball stats, scores, schedules for PLG and TPBL."
tags: ["plg", "tpbl", "basketball", "taiwan", "sports", "scores", "standings"]
---

# Taiwan Basketball Skill - 台灣職籃資訊查詢 🏀

Query PLG (P. LEAGUE+) and TPBL (台灣職業籃球大聯盟) game results, schedules, and standings.

## Data Sources

| Source | Description |
|--------|-------------|
| PLG official website | HTML scraping (server-side rendered) |
| TPBL official REST API | `api.tpbl.basketball` |

## Features

| Feature | Script | Source |
|---------|--------|--------|
| Schedule | `basketball_schedule.py` | PLG website / TPBL API |
| Standings | `basketball_standings.py` | PLG website / TPBL API |
| Game results | `basketball_games.py` | PLG website / TPBL API |
| Player stats | `basketball_player.py` | PLG website / TPBL API |

## Quick Start

All scripts use `uv run` for dependency management.

### Schedule

```bash
uv run scripts/basketball_schedule.py --league plg
uv run scripts/basketball_schedule.py --league tpbl
uv run scripts/basketball_schedule.py --league all       # PLG + TPBL 合併查詢
uv run scripts/basketball_schedule.py -l plg --team 勇士
```

### Standings

```bash
uv run scripts/basketball_standings.py --league plg
uv run scripts/basketball_standings.py --league tpbl
```

### Game Results

```bash
uv run scripts/basketball_games.py --league plg
uv run scripts/basketball_games.py --league tpbl
uv run scripts/basketball_games.py --league all            # PLG + TPBL 合併查詢
uv run scripts/basketball_games.py --league all --last 5   # 最近 5 場結果
uv run scripts/basketball_games.py -l tpbl --team 戰神
```

### Player Stats

```bash
uv run scripts/basketball_player.py --league plg --player 林書豪
uv run scripts/basketball_player.py --league tpbl --player 林書豪
uv run scripts/basketball_player.py --league all --player 林書豪
uv run scripts/basketball_player.py -l plg -p 林書豪 --season 2023-24
uv run scripts/basketball_player.py -l tpbl -p 夢想家           # 球隊搜尋
```

Supports fuzzy search by player name or team name. Returns per-season stats (GP, avg minutes/pts/reb/ast/stl/blk, FG/3P/FT splits, efficiency, PIR) plus career totals.

- **PLG**: Scrapes `/stat-player` + `/all-players` for player index, then `/player/{ID}` for detailed per-season stats.
- **TPBL**: Queries `/games/stats/players?division_id={id}` for all divisions across all seasons. Falls back to `/players/{id}` for historical data. Returns accumulated + average + percentage stats.

## CLI Parameters

| Script | Param | Description |
|--------|-------|-------------|
| All | `--league`, `-l` | `plg`, `tpbl`, or `all` |
| All | `--team`, `-t` | Team name filter (supports aliases) |
| `basketball_games.py` | `--last`, `-n` | Show only last N results (default: all) |
| `basketball_player.py` | `--player`, `-p` | Player name to search |
| `basketball_player.py` | `--season`, `-s` | Filter by season (e.g., `2023-24`) |

Output JSON includes a `league` field per game when using `--league all`.

## League Codes

| Code | League |
|------|--------|
| `plg` | P. LEAGUE+ (4 teams) |
| `tpbl` | 台灣職業籃球大聯盟 (7 teams) |

## Team Aliases

### PLG
| Alias | Full Name |
|-------|-----------|
| 富邦, 勇士 | 臺北富邦勇士 |
| 璞園, 領航猿 | 桃園璞園領航猿 |
| 台鋼, 獵鷹 | 台鋼獵鷹 |
| 洋基, 洋基工程 | 洋基工程 |
| 國王 | 新北國王 (已轉至 TPBL) |
| 攻城獅 | 新竹街口攻城獅 (已轉至 TPBL) |
| 夢想家 | 福爾摩沙台新夢想家 (已轉至 TPBL) |
| 鋼鐵人 | 高雄鋼鐵人 (已解散) |

### TPBL
| Alias | Full Name |
|-------|-----------|
| 台新, 戰神 | 臺北台新戰神 |
| 中信, 特攻 | 新北中信特攻 |
| 國王 | 新北國王 |
| 雲豹 | 桃園台啤永豐雲豹 |
| 夢想家 | 福爾摩沙夢想家 |
| 攻城獅 | 新竹御嵿攻城獅 |
| 海神 | 高雄全家海神 |

## Dependencies

Auto-installed via `uv`:
- `beautifulsoup4` — HTML parsing
- `lxml` — Fast parser

## Notes

- **PLG**: Server-side rendered HTML, no JS needed. Standings page has full table.
- **TPBL**: Official REST API at `api.tpbl.basketball`. Player stats via `/games/stats/players?division_id={id}` across all seasons.
- SBL (超級籃球聯賽) is not supported — official site (sleague.tw) is a Vue SPA with authenticated GraphQL API.
- `avg_minutes` output is unified to `MM:SS` format for both leagues.
