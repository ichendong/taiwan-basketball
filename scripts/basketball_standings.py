#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "beautifulsoup4",
#     "lxml",
# ]
# ///
"""
台灣職籃戰績查詢
支援 PLG、TPBL 兩大聯盟
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _basketball_api import get_league_api, LEAGUE_NAMES, disable_cache, format_table

_STANDINGS_COLUMNS = ['rank', 'team', 'gp', 'wins', 'losses', 'win_rate']
_STANDINGS_HEADERS = {
    'rank': '排名', 'team': '球隊', 'gp': '出賽', 'wins': '勝', 'losses': '敗', 'win_rate': '勝率',
}


def main():
    parser = argparse.ArgumentParser(
        description='台灣職籃戰績查詢',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
範例:
  uv run scripts/basketball_standings.py --league tpbl
  uv run scripts/basketball_standings.py --league plg
  uv run scripts/basketball_standings.py --league plg --format table
        '''
    )

    parser.add_argument('--league', '-l', type=str, required=True,
                        choices=['plg', 'tpbl'],
                        help='聯盟代碼')
    parser.add_argument('--format', '-f', type=str, default='json',
                        choices=['json', 'table'], help='輸出格式（預設 json）')
    parser.add_argument('--no-cache', action='store_true', help='停用快取')
    parser.add_argument('--debug', action='store_true', help='開啟 debug 輸出')

    args = parser.parse_args()

    if args.debug:
        os.environ['BASKETBALL_DEBUG'] = '1'
    if args.no_cache:
        disable_cache()

    league_name = LEAGUE_NAMES.get(args.league, args.league)
    print(f'✅ 聯盟：{league_name}', file=sys.stderr)

    try:
        api = get_league_api(args.league)
        standings = api.get_standings()

        if args.format == 'table':
            print(format_table(standings, _STANDINGS_COLUMNS, _STANDINGS_HEADERS))
        else:
            print(json.dumps(standings, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()

