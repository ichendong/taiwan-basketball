---
name: taiwan-basketball
description: "Taiwan professional basketball stats, scores, schedules for PLG and TPBL."
tags: ["plg", "tpbl", "basketball", "taiwan", "sports", "scores", "standings"]
---

# Taiwan Basketball Skill - 台灣職籃資訊查詢 🏀

Query PLG (P. LEAGUE+) and TPBL (台灣職業籃球大聯盟) game results, schedules, standings, player stats, league leaders, and head-to-head records.

## Data Sources

| Source | Description |
|--------|-------------|
| PLG official website | HTML scraping (server-side rendered) |
| TPBL official REST API | `api.tpbl.basketball` |

## Features

| Feature | Script | Source |
|---------|--------|--------|
| Schedule (with countdown) | `basketball_schedule.py` | PLG website / TPBL API |
| Standings | `basketball_standings.py` | PLG website / TPBL API |
| Game results | `basketball_games.py` | PLG website / TPBL API |
| Player stats | `basketball_player.py` | PLG website / TPBL API |
| League leaders | `basketball_leaders.py` | PLG website / TPBL API |
| Player comparison | `basketball_compare.py` | PLG website / TPBL API |
| Boxscore (per-game) | `basketball_boxscore.py` | PLG API / TPBL API |

## Quick Start

All scripts use `uv run` for dependency management.

### Schedule

```bash
uv run scripts/basketball_schedule.py --league plg
uv run scripts/basketball_schedule.py --league tpbl
uv run scripts/basketball_schedule.py --league all       # PLG + TPBL 合併查詢
uv run scripts/basketball_schedule.py -l plg --team 勇士
uv run scripts/basketball_schedule.py -l all --next      # 只顯示下一場比賽及倒數
uv run scripts/basketball_schedule.py -l all --format table
```

### Standings

```bash
uv run scripts/basketball_standings.py --league plg
uv run scripts/basketball_standings.py --league tpbl
uv run scripts/basketball_standings.py --league plg --format table
```

### Game Results

```bash
uv run scripts/basketball_games.py --league plg
uv run scripts/basketball_games.py --league tpbl
uv run scripts/basketball_games.py --league all            # PLG + TPBL 合併查詢
uv run scripts/basketball_games.py --league all --last 5   # 最近 5 場結果
uv run scripts/basketball_games.py -l tpbl --team 戰神
uv run scripts/basketball_games.py -l all --last 10 --format table
```

### Player Stats

```bash
uv run scripts/basketball_player.py --league plg --player 林書豪
uv run scripts/basketball_player.py --league tpbl --player 林書豪
uv run scripts/basketball_player.py --league all --player 林書豪
uv run scripts/basketball_player.py -l plg -p 林書豪 --season 2023-24
uv run scripts/basketball_player.py -l tpbl -p 夢想家           # 球隊搜尋
```

### League Leaders（排行榜）

```bash
uv run scripts/basketball_leaders.py --league plg --stat pts          # PLG 得分王
uv run scripts/basketball_leaders.py --league tpbl --stat reb --top 5 # TPBL 籃板前5名
uv run scripts/basketball_leaders.py -l tpbl -s ast --format table    # 表格輸出
uv run scripts/basketball_leaders.py -l all -s pts --top 10           # 雙聯盟得分榜
```

Supported `--stat` values: `pts`（得分）、`reb`（籃板）、`ast`（助攻）、`stl`（抄截）、`blk`（阻攻）、`tov`（失誤）、`pf`（犯規）、`eff`（效率值，TPBL 限定）

### Player Comparison（球員比較）

```bash
uv run scripts/basketball_compare.py --league plg --player1 林書豪 --player2 戴維斯
uv run scripts/basketball_compare.py -l tpbl -p1 林志傑 -p2 陳盈駿
uv run scripts/basketball_compare.py -l plg -p1 林書豪 -p2 戴維斯 --season 2023-24
uv run scripts/basketball_compare.py -l plg -p1 林書豪 -p2 戴維斯 --format table
```

### Boxscore（單場球員數據）

```bash
uv run scripts/basketball_boxscore.py -l plg -g 693            # PLG 用 gohoops game ID
uv run scripts/basketball_boxscore.py -l tpbl -g 1371          # TPBL 用 API game ID
uv run scripts/basketball_boxscore.py -l plg -g 693 -f table   # 表格輸出
uv run scripts/basketball_boxscore.py -l plg -g 693 --tab Q1   # 單節數據
uv run scripts/basketball_boxscore.py -l plg -g 693 --all      # 包含 DNP 球員
```

- **PLG**: 個別球員完整數據（得分、籃板、助攻、EFF、+/- 等），透過 `/api/boxscore.preciser.php` 取得。
- **TPBL**: 僅提供球隊級別每節統計（得分、FG、籃板、助攻等），無個別球員數據。

Supports fuzzy search by player name or team name. Returns per-season stats (GP, avg minutes/pts/reb/ast/stl/blk, FG/3P/FT splits, efficiency, PIR) plus career totals.

- **PLG**: Scrapes `/stat-player` + `/all-players` for player index, then `/player/{ID}` for detailed per-season stats.
- **TPBL**: Queries `/games/stats/players?division_id={id}` for all divisions across all seasons. Recalculates FG%/3P%/FT% from accumulated makes/attempts for cross-division accuracy.

## CLI Parameters

| Script | Param | Description |
|--------|-------|-------------|
| All | `--league`, `-l` | `plg`, `tpbl`, or `all` |
| All | `--format`, `-f` | `json` (預設) or `table` (ASCII 表格) |
| All | `--no-cache` | 停用磁碟快取 |
| All | `--debug` | 輸出 debug 訊息（或設 `BASKETBALL_DEBUG=1`）|
| schedule, games | `--team`, `-t` | Team name filter (supports aliases) |
| `basketball_schedule.py` | `--next` | 只顯示下一場比賽及倒數計時 |
| `basketball_games.py` | `--last`, `-n` | Show only last N results (default: all) |
| `basketball_player.py` | `--player`, `-p` | Player name to search |
| `basketball_player.py` | `--season`, `-s` | Filter by season (e.g., `2023-24`) |
| `basketball_leaders.py` | `--stat`, `-s` | Stat category (pts/reb/ast/stl/blk/tov/pf/eff) |
| `basketball_leaders.py` | `--top`, `-n` | Show top N players (default: 10) |
| `basketball_compare.py` | `--player1`, `-p1` | First player name |
| `basketball_compare.py` | `--player2`, `-p2` | Second player name |
| `basketball_compare.py` | `--season`, `-s` | Compare a specific season (default: career) |
| `basketball_boxscore.py` | `--game`, `-g` | Game ID (PLG: gohoops ID, TPBL: API ID) |
| `basketball_boxscore.py` | `--tab` | Stats period: Q1/Q2/Q3/Q4/1st_half/2nd_half/TOTAL (default: TOTAL) |
| `basketball_boxscore.py` | `--all` | Include DNP (did not play) players |

Output JSON includes a `league` field per game when using `--league all`.

## Caching

Results are cached on disk at `~/.cache/taiwan-basketball/` with the following TTLs:

| Data type | TTL |
|-----------|-----|
| Schedule | 5 minutes |
| Game results | 10 minutes |
| Standings | 10 minutes |
| Player stats | 1 hour |
| League leaders | 10 minutes |

Use `--no-cache` to bypass cache, or set `BASKETBALL_DEBUG=1` to see cache hits/misses.

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
- **Retry**: All HTTP requests retry up to 3 times with exponential backoff on network errors.
- **FG% accuracy**: TPBL percentage stats (FG%/3P%/FT%) are recalculated from cumulative makes/attempts for cross-division accuracy.
- **Season format**: TPBL seasons display as `YY/YY` (e.g., `24/25`); PLG seasons as `YYYY-YY` (e.g., `2023-24`).
- SBL (超級籃球聯賽) is not supported — official site (sleague.tw) is a Vue SPA with authenticated GraphQL API.
- `avg_minutes` output is unified to `MM:SS` format for both leagues.

