# taiwan-basketball 🏀

OpenClaw Agent Skill — Taiwan professional basketball (PLG + TPBL) stats, scores, schedules, and player data.

## Version

v0.9

## Usage

See [SKILL.md](SKILL.md) for full documentation.

## Quick Start

```bash
# PLG & TPBL today's schedule
uv run scripts/basketball_schedule.py --league all

# Standings
uv run scripts/basketball_standings.py --league plg
uv run scripts/basketball_standings.py --league tpbl

# Recent results
uv run scripts/basketball_games.py --league all --last 5

# Player stats (fuzzy search)
uv run scripts/basketball_player.py --league all --player 林書豪
```
