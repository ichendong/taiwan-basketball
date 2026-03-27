# taiwan-basketball 🏀

OpenClaw Agent Skill — Taiwan professional basketball (PLG + TPBL) stats, scores, schedules, player data, live scores, box scores, notifications, and transactions.

## Version

v2.0.0

## Usage

See [SKILL.md](SKILL.md) for full documentation.

## Quick Start

```bash
# PLG & TPBL today's schedule（並行查詢）
uv run scripts/basketball_schedule.py --league all

# Standings
uv run scripts/basketball_standings.py --league plg
uv run scripts/basketball_standings.py --league tpbl

# Recent results
uv run scripts/basketball_games.py --league all --last 5

# Player stats (fuzzy search)
uv run scripts/basketball_player.py --league all --player 林書豪

# Live scores ✨
uv run scripts/basketball_live.py --league all

# Box Score ✨
uv run scripts/basketball_boxscore.py --league tpbl --game-id 123

# Notifications ✨
uv run scripts/basketball_notify.py add --team 戰神 --league tpbl
uv run scripts/basketball_notify.py check --hours 24

# Transactions ✨
uv run scripts/basketball_transactions.py --league all
```
