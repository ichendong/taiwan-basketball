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
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _basketball_api import (
    get_league_api, LEAGUE_NAMES, resolve_team, normalize_league,
    disable_cache, get_next_game, format_table,
)

_SCHEDULE_COLUMNS = ['league', 'date', 'weekday', 'time', 'away_team', 'home_team', 'venue', 'countdown']
_SCHEDULE_HEADERS = {
    'league': '聯盟', 'date': '日期', 'weekday': '星期', 'time': '時間',
    'away_team': '客隊', 'home_team': '主隊', 'venue': '場館', 'countdown': '倒數',
}


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
  uv run scripts/basketball_schedule.py -l all --format table
        '''
    )

    parser.add_argument('--league', '-l', type=str, required=True,
                        choices=['plg', 'tpbl', 'all'],
                        help='聯盟代碼（all = PLG + TPBL）')
    parser.add_argument('--team', '-t', type=str, help='球隊名過濾（支援簡稱）')
    parser.add_argument('--format', '-f', type=str, default='json',
                        choices=['json', 'table'], help='輸出格式（預設 json）')
    parser.add_argument('--next', action='store_true',
                        help='只顯示最近一場比賽及倒數計時')
    parser.add_argument('--no-cache', action='store_true', help='停用快取')
    parser.add_argument('--debug', action='store_true', help='開啟 debug 輸出')

    args = parser.parse_args()

    if args.debug:
        os.environ['BASKETBALL_DEBUG'] = '1'
    if args.no_cache:
        disable_cache()

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

        if args.next:
            next_game = get_next_game(all_schedule)
            if next_game:
                output = [next_game]
                print(f'🏀 下一場比賽：{next_game.get("date")} {next_game.get("time")} '
                      f'{next_game.get("away_team")} vs {next_game.get("home_team")} '
                      f'（{next_game.get("countdown", "")}）', file=sys.stderr)
            else:
                output = []
        else:
            # 加入倒數資訊（所有場次）
            for g in all_schedule:
                ng = get_next_game([g])
                if ng and 'countdown' in ng:
                    g['countdown'] = ng['countdown']
            output = all_schedule

        if not output:
            print('⚠️ 目前沒有符合條件的未來賽程', file=sys.stderr)

        if args.format == 'table':
            cols = [c for c in _SCHEDULE_COLUMNS if any(c in g for g in output)]
            print(format_table(output, cols, _SCHEDULE_HEADERS))
        else:
            print(json.dumps(output, ensure_ascii=False, indent=2))

    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

