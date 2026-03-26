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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _basketball_api import get_league_api, LEAGUE_NAMES


def main():
    parser = argparse.ArgumentParser(
        description='台灣職籃戰績查詢',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
範例:
  uv run scripts/basketball_standings.py --league tpbl
  uv run scripts/basketball_standings.py --league plg
        '''
    )

    parser.add_argument('--league', '-l', type=str, required=True,
                        choices=['plg', 'tpbl'],
                        help='聯盟代碼')

    args = parser.parse_args()

    league_name = LEAGUE_NAMES.get(args.league, args.league)
    print(f'✅ 聯盟：{league_name}', file=sys.stderr)

    try:
        api = get_league_api(args.league)
        standings = api.get_standings()
        print(json.dumps(standings, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
