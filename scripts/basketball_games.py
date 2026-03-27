#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "beautifulsoup4",
#     "lxml",
# ]
# ///
"""
台灣職籃比賽結果查詢
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
    disable_cache, format_table, fetch_leagues_parallel,
)

_GAMES_COLUMNS = ['league', 'date', 'weekday', 'away_team', 'away_score', 'home_score', 'home_team', 'venue']
_GAMES_HEADERS = {
    'league': '聯盟', 'date': '日期', 'weekday': '星期',
    'away_team': '客隊', 'away_score': '客分', 'home_score': '主分', 'home_team': '主隊', 'venue': '場館',
}


def fetch_results(league: str, team=None):
    api = get_league_api(league)
    results = api.get_results(team=team)
    for r in results:
        r['league'] = league
    return results


def main():
    parser = argparse.ArgumentParser(
        description='台灣職籃比賽結果查詢',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
範例:
  uv run scripts/basketball_games.py --league plg
  uv run scripts/basketball_games.py --league tpbl
  uv run scripts/basketball_games.py --league all
  uv run scripts/basketball_games.py --league all --last 5
  uv run scripts/basketball_games.py -l tpbl --team 戰神
  uv run scripts/basketball_games.py -l all --last 10 --format table
        '''
    )

    parser.add_argument('--league', '-l', type=str, required=True,
                        choices=['plg', 'tpbl', 'all'],
                        help='聯盟代碼（all = PLG + TPBL）')
    parser.add_argument('--team', '-t', type=str, help='球隊名過濾（支援簡稱）')
    parser.add_argument('--last', '-n', type=int, default=0,
                        help='只顯示最近 N 場比賽結果（預設全部）')
    parser.add_argument('--format', '-f', type=str, default='json',
                        choices=['json', 'table'], help='輸出格式（預設 json）')
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
            print(f'✅ 「{args.team}」→「{team}」', file=sys.stderr)

    try:
        leagues = ['plg', 'tpbl'] if args.league == 'all' else [normalize_league(args.league)]

        def _fetch_results(league: str) -> list:
            return fetch_results(league, team)

        all_results = []
        for league, results in fetch_leagues_parallel(leagues, _fetch_results):
            print(f'✅ 聯盟：{LEAGUE_NAMES.get(league, league)}', file=sys.stderr)
            all_results.extend(results)

        # 按日期排序（最新在前）
        all_results.sort(key=lambda x: x.get('date', ''), reverse=True)

        if args.last > 0:
            all_results = all_results[:args.last]

        if not all_results:
            print('⚠️ 目前沒有符合條件的比賽結果', file=sys.stderr)

        if args.format == 'table':
            print(format_table(all_results, _GAMES_COLUMNS, _GAMES_HEADERS))
        else:
            print(json.dumps(all_results, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

