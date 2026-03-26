#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "beautifulsoup4",
#     "lxml",
# ]
# ///
"""
台灣職籃賽程查詢
支援 PLG、TPBL 兩大聯盟
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _basketball_api import get_league_api, LEAGUE_NAMES, resolve_team, normalize_league


def main():
    parser = argparse.ArgumentParser(
        description='台灣職籃賽程查詢',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
範例:
  uv run scripts/basketball_schedule.py --league plg
  uv run scripts/basketball_schedule.py --league tpbl
  uv run scripts/basketball_schedule.py --league all
  uv run scripts/basketball_schedule.py -l tpbl --team 戰神
        '''
    )

    parser.add_argument('--league', '-l', type=str, required=True,
                        choices=['plg', 'tpbl', 'all'],
                        help='聯盟代碼（all = PLG + TPBL）')
    parser.add_argument('--team', '-t', type=str, help='球隊名過濾（支援簡稱）')

    args = parser.parse_args()

    team = None
    if args.team:
        team = resolve_team(args.team)
        if team:
            if team != args.team:
                print(f'✅ 「{args.team}」→「{team}」', file=sys.stderr)
        else:
            print(f'⚠️ 找不到球隊「{args.team}」，將直接比對', file=sys.stderr)

    try:
        leagues = ['plg', 'tpbl'] if args.league == 'all' else [normalize_league(args.league)]

        all_schedule = []
        for league in leagues:
            print(f'✅ 聯盟：{LEAGUE_NAMES.get(league, league)}', file=sys.stderr)
            api = get_league_api(league)
            schedule = api.get_schedule()
            for s in schedule:
                s['league'] = league

            if team:
                schedule = [g for g in schedule
                           if team in g.get('away_team', '') or team in g.get('home_team', '')]
            all_schedule.extend(schedule)

        all_schedule.sort(key=lambda x: (x.get('date', ''), x.get('time', '')))

        if not all_schedule:
            print(f'⚠️ 目前沒有符合條件的未來賽程', file=sys.stderr)

        print(json.dumps(all_schedule, ensure_ascii=False, indent=2))

    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
