#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "beautifulsoup4",
#     "lxml",
# ]
# ///
"""
台灣職籃單場比賽球員數據（Boxscore）
支援 PLG、TPBL 兩大聯盟
"""

import argparse
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from _basketball_api import (
    get_league_api, LEAGUE_NAMES, normalize_league,
    disable_cache, format_table, _str_display_width,
)


_BOX_COLUMNS = ['number', 'name', 'mins', 'pts', 'fg2', 'fg3', 'ft', 'reb', 'ast', 'stl', 'blk', 'tov', 'pf', 'eff', 'pm']
_BOX_HEADERS_PLG = {
    'number': '背號', 'name': '球員', 'mins': '時間', 'pts': '得分',
    'fg2': '二分', 'fg3': '三分', 'ft': '罰球', 'reb': '籃板',
    'ast': '助攻', 'stl': '抄截', 'blk': '阻攻', 'tov': '失誤', 'pf': '犯規',
    'eff': 'EFF', 'pm': '+/-',
}
_BOX_HEADERS_TPBL = {
    'number': '背號', 'name': '球員', 'mins': '時間', 'pts': '得分',
    'fg2': '二分', 'fg3': '三分', 'ft': '罰球', 'reb': '籃板',
    'ast': '助攻', 'stl': '抄截', 'blk': '阻攻', 'tov': '失誤', 'pf': '犯規',
    'eff': 'EFF', 'pm': '+/-',
}


def _normalize_player(p: dict, league: str) -> dict:
    """統一球員數據格式"""
    if league == 'plg':
        return {
            'number': p.get('jersey', ''),
            'name': p.get('name', ''),
            'mins': p.get('mins', ''),
            'pts': p.get('pts') if p.get('pts') is not None else '',
            'fg2': p.get('fg2', ''),
            'fg3': p.get('fg3', ''),
            'ft': p.get('ft', ''),
            'reb': p.get('reb') if p.get('reb') is not None else '',
            'ast': p.get('ast') if p.get('ast') is not None else '',
            'stl': p.get('stl') if p.get('stl') is not None else '',
            'blk': p.get('blk') if p.get('blk') is not None else '',
            'tov': p.get('tov') if p.get('tov') is not None else '',
            'pf': p.get('pf') if p.get('pf') is not None else '',
            'eff': p.get('eff') if p.get('eff') is not None else '',
            'pm': p.get('plus_minus') if p.get('plus_minus') is not None else '',
        }
    else:  # tpbl
        fg2 = f"{p.get('fg2m', '')}/{p.get('fg2a', '')}" if p.get('fg2m') else ''
        fg3 = f"{p.get('fg3m', '')}/{p.get('fg3a', '')}" if p.get('fg3m') else ''
        ft = f"{p.get('ftm', '')}/{p.get('fta', '')}" if p.get('ftm') else ''
        reb = p.get('reb', '')
        if p.get('orb') and p.get('drb'):
            reb = f"{reb}({p.get('orb')}/{p.get('drb')})"
        return {
            'number': p.get('number', ''),
            'name': p.get('name', ''),
            'mins': p.get('mins', ''),
            'pts': p.get('pts') if p.get('pts') else '',
            'fg2': fg2,
            'fg3': fg3,
            'ft': ft,
            'reb': reb,
            'ast': p.get('ast') if p.get('ast') else '',
            'stl': p.get('stl') if p.get('stl') else '',
            'blk': p.get('blk') if p.get('blk') else '',
            'tov': p.get('tov') if p.get('tov') else '',
            'pf': p.get('pf') if p.get('pf') else '',
            'eff': p.get('eff') if p.get('eff') else '',
            'pm': '',
        }


def _filter_dnp(players: list[dict], league: str) -> list[dict]:
    """過濾掉 DNP（未上場）球員"""
    if league == 'plg':
        return [p for p in players if not p.get('dnp')]
    return players


def main():
    parser = argparse.ArgumentParser(
        description='台灣職籃單場比賽球員數據（Boxscore）',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
範例:
  uv run scripts/basketball_boxscore.py --league plg --game 693
  uv run scripts/basketball_boxscore.py --league tpbl --game 1371
  uv run scripts/basketball_boxscore.py -l plg -g 693 -f table
  uv run scripts/basketball_boxscore.py -l plg -g 693 --all
        '''
    )

    parser.add_argument('--league', '-l', type=str, required=True,
                        choices=['plg', 'tpbl'],
                        help='聯盟代碼')
    parser.add_argument('--game', '-g', type=str, required=True,
                        help='比賽 ID（PLG 用 gohoops ID 如 693，TPBL 用 API ID 如 1371）')
    parser.add_argument('--format', '-f', type=str, default='json',
                        choices=['json', 'table'], help='輸出格式（預設 json）')
    parser.add_argument('--no-cache', action='store_true', help='停用快取')
    parser.add_argument('--all', action='store_true', help='包含未上場球員（DNP）')
    parser.add_argument('--tab', type=str, default='TOTAL',
                        help='PLG 統計區間：Q1/Q2/Q3/Q4/1st_half/2nd_half/TOTAL（預設 TOTAL）')

    args = parser.parse_args()

    if args.no_cache:
        disable_cache()

    league = normalize_league(args.league)
    api = get_league_api(league)

    try:
        if league == 'plg':
            boxscore = api.get_boxscore(args.game, tab=args.tab)
            home_team_name = ''
            away_team_name = ''
            # Try to find team names from game schedule
            games = api.get_games()
            # PLG schedule uses G-prefixed IDs, boxscore uses gohoops numeric ID
            # Match by looking at all games - the gohoops ID is embedded in trackGame() onclick
            # Fallback: try to get team names from first non-DNP player's name context
            for g in games:
                gid = g.get('game_id', '')
                # The G-number doesn't map to gohoops ID, use date/venue matching
                if g.get('status') == 'completed':
                    # Simple: use boxscore API's home/away score to match
                    if (str(g.get('away_score')) == str(boxscore.get('score_away')) and
                        str(g.get('home_score')) == str(boxscore.get('score_home'))):
                        home_team_name = g.get('home_team', '')
                        away_team_name = g.get('away_team', '')
                        break
        else:
            boxscore = api.get_boxscore(args.game)
            home_team_name = boxscore.get('home_team', '')
            away_team_name = boxscore.get('away_team', '')

        if boxscore.get('error'):
            print(json.dumps({'error': boxscore['error']}, ensure_ascii=False), file=sys.stderr)
            sys.exit(1)

        if args.format == 'table':
            headers = _BOX_HEADERS_PLG if league == 'plg' else _BOX_HEADERS_TPBL
            cols = _BOX_COLUMNS

            # Get players
            home_players = boxscore.get('home_players', [])
            away_players = boxscore.get('away_players', [])

            if not args.all:
                home_players = _filter_dnp(home_players, league)
                away_players = _filter_dnp(away_players, league)

            home_rows = [_normalize_player(p, league) for p in home_players]
            away_rows = [_normalize_player(p, league) for p in away_players]

            # Quarter scores header
            quarters = boxscore.get('quarters', {})
            home_quarters = boxscore.get('home_quarters', [])
            away_quarters = boxscore.get('away_quarters', [])

            if quarters:
                q_scores = []
                for qk in ('q1', 'q2', 'q3', 'q4'):
                    q = quarters.get(qk, {})
                    if q.get('home') and q.get('home') != '-':
                        q_scores.append(f"{q.get('away')}-{q.get('home')}")
                if q_scores:
                    print(f'  節分：({" / ".join(q_scores)})')
            elif home_quarters:
                q_scores = []
                for i, hq in enumerate(home_quarters):
                    aq = away_quarters[i] if i < len(away_quarters) else {}
                    q_scores.append(f"{aq.get('score', '?')}-{hq.get('score', '?')}")
                if q_scores:
                    print(f'  節分：({" / ".join(q_scores)})')

            # Scores
            if league == 'plg':
                sh, sa = boxscore.get('score_home'), boxscore.get('score_away')
            else:
                ht, at = boxscore.get('home_total'), boxscore.get('away_total')
                sh = ht.get('won_score') if ht else None
                sa = at.get('won_score') if at else None

            print(f'  總分：{sa}:{sh}')
            print()

            # TPBL: team-level stats only
            if league == 'tpbl' and not boxscore.get('home_players'):
                note = boxscore.get('note', '')
                if note:
                    print(f'  ⚠️ {note}')
                print()
                for key, q_list in [('away', away_quarters), ('home', home_quarters)]:
                    team_name = boxscore.get(f'{key}_team', key)
                    print(f'  🏀 {team_name}')
                    if q_list:
                        _QTBL_COLS = ['quarter', 'score', 'fg', 'reb', 'ast', 'stl', 'blk', 'tov', 'pf']
                        _QTBL_HDRS = {'quarter': '節次', 'score': '得分', 'fg': 'FG', 'reb': '籃板',
                                      'ast': '助攻', 'stl': '抄截', 'blk': '阻攻', 'tov': '失誤', 'pf': '犯規'}
                        rows = [{k: v for k, v in q.items() if k in _QTBL_COLS} for q in q_list]
                        print(format_table(rows, _QTBL_COLS, _QTBL_HDRS))
                    print()
            else:
                home_players = boxscore.get('home_players', [])
                away_players = boxscore.get('away_players', [])
                if not args.all:
                    home_players = _filter_dnp(home_players, league)
                    away_players = _filter_dnp(away_players, league)
                home_rows = [_normalize_player(p, league) for p in home_players]
                away_rows = [_normalize_player(p, league) for p in away_players]

                print(f'  🏀 {away_team_name or "客隊"}')
                if away_rows:
                    print(format_table(away_rows, cols, headers))
                else:
                    print('    （無數據）')
                print()
                print(f'  🏀 {home_team_name or "主隊"}')
                if home_rows:
                    print(format_table(home_rows, cols, headers))
                else:
                    print('    （無數據）')
        else:
            print(json.dumps(boxscore, ensure_ascii=False, indent=2))
    except Exception as e:
        print(json.dumps({'error': str(e)}, ensure_ascii=False), file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
