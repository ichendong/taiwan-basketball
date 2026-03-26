#!/usr/bin/env python3
# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "beautifulsoup4",
#     "lxml",
# ]
# ///
"""
台灣職籃 API 共用模組
支援 PLG、TPBL 兩大聯盟的賽程與戰績查詢
"""

import json
import re
import urllib.request
import urllib.error
from datetime import datetime, date
from typing import Optional
from bs4 import BeautifulSoup

# ─── 球隊別名對照表 ───

TEAM_ALIASES = {
    # PLG
    '富邦': '臺北富邦勇士', '勇士': '臺北富邦勇士', '臺北富邦勇士': '臺北富邦勇士', '台北富邦勇士': '臺北富邦勇士',
    '璞園': '桃園璞園領航猿', '領航猿': '桃園璞園領航猿', '桃園璞園領航猿': '桃園璞園領航猿', '桃園領航猿': '桃園璞園領航猿',
    '台鋼獵鷹': '台鋼獵鷹', '獵鷹': '台鋼獵鷹', '台鋼': '台鋼獵鷹', 'tsg': '台鋼獵鷹',
    '洋基': '洋基工程', '洋基工程': '洋基工程', 'yankey': '洋基工程', 'ark': '洋基工程',
    # TPBL
    '台新': '臺北台新戰神', '戰神': '臺北台新戰神', '臺北台新戰神': '臺北台新戰神', '台北台新戰神': '臺北台新戰神',
    '中信特攻': '新北中信特攻', '特攻': '新北中信特攻', '新北中信特攻': '新北中信特攻',
    '新北國王': '新北國王', '國王': '新北國王',
    '台啤': '桃園台啤永豐雲豹', '雲豹': '桃園台啤永豐雲豹', '桃園台啤永豐雲豹': '桃園台啤永豐雲豹',
    '台南台鋼': '台南台鋼獵鷹', '台南獵鷹': '台南台鋼獵鷹', '台南台鋼獵鷹': '台南台鋼獵鷹',
    '鋼鐵人': '高雄全家海神', '高雄鋼鐵人': '高雄全家海神', '高雄全家海神': '高雄全家海神', '海神': '高雄全家海神',
    '夢想家': '福爾摩沙夢想家', '福爾摩沙': '福爾摩沙夢想家', '福爾摩沙夢想家': '福爾摩沙夢想家',
    '攻城獅': '新竹御嵿攻城獅', '新竹攻城獅': '新竹御嵿攻城獅', '新竹御嵿攻城獅': '新竹御嵿攻城獅', '御嵿': '新竹御嵿攻城獅',
}

# 簡稱 → 正式名稱（用於 standings 簡稱還原）
PLG_SHORT_NAMES = {
    '領航猿': '桃園璞園領航猿',
    '獵鷹': '台鋼獵鷹',
    '勇士': '臺北富邦勇士',
    '洋基工程': '洋基工程',
}

LEAGUE_NAMES = {
    'plg': 'P. LEAGUE+',
    'tpbl': '台灣職業籃球大聯盟',
}

def _sec_to_mmss(seconds: float) -> str:
    """秒數轉 MM:SS 格式"""
    s = round(seconds)
    return f'{s // 60}:{s % 60:02d}'

_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'


def _fetch_html(url: str) -> str:
    """用 urllib 直接抓 HTML（不依賴 headless browser）"""
    req = urllib.request.Request(url, headers={'User-Agent': _UA})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode('utf-8', errors='replace')


def resolve_team(team_input: str) -> Optional[str]:
    """模糊匹配球隊名稱"""
    if team_input in TEAM_ALIASES.values():
        return team_input
    low = team_input.lower()
    for alias, full_name in TEAM_ALIASES.items():
        if low in alias.lower() or alias.lower() in low:
            return full_name
    return None


def normalize_league(league: str) -> str:
    return league.lower().strip()


# ─── TPBL API (REST) ───

class TPBLAPI:
    """TPBL 官方 REST API 封裝"""
    BASE_URL = 'https://api.tpbl.basketball/api'

    def __init__(self):
        self._season_id: Optional[int] = None

    def _fetch_json(self, path: str) -> dict | list:
        req = urllib.request.Request(f'{self.BASE_URL}{path}')
        req.add_header('User-Agent', _UA)
        req.add_header('Referer', 'https://tpbl.basketball/')
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())

    def _get_current_season_id(self) -> int:
        if self._season_id is not None:
            return self._season_id
        seasons = self._fetch_json('/seasons')
        for s in seasons:
            if s.get('status') == 'IN_PROGRESS':
                self._season_id = s['id']
                return self._season_id
        self._season_id = seasons[-1]['id'] if seasons else 2
        return self._season_id

    def get_schedule(self, season_id: Optional[int] = None) -> list[dict]:
        games = self.get_games(season_id)
        schedule = []
        today = date.today().isoformat()
        for g in games:
            if g.get('status') == 'NOT_STARTED' and g.get('game_date', '') >= today:
                schedule.append({
                    'date': g['game_date'],
                    'weekday': g.get('game_day_of_week', ''),
                    'time': g.get('game_time', '')[:5],
                    'away_team': g['away_team']['name'],
                    'home_team': g['home_team']['name'],
                    'venue': g.get('venue', ''),
                    'status': 'upcoming',
                    'round': g.get('round'),
                })
        return schedule

    def get_standings(self, season_id: Optional[int] = None) -> list[dict]:
        # TPBL 官方 API 無 /standings endpoint（已確認 404），故從 games 計算戰績
        games = self.get_games(season_id)
        teams = {}
        for g in games:
            if g.get('status') != 'COMPLETED':
                continue
            home = g['home_team']['name']
            away = g['away_team']['name']
            home_score = g['home_team'].get('won_score', 0)
            away_score = g['away_team'].get('won_score', 0)
            for name in (home, away):
                if name not in teams:
                    teams[name] = {'team': name, 'wins': 0, 'losses': 0}
            if home_score > away_score:
                teams[home]['wins'] += 1
                teams[away]['losses'] += 1
            else:
                teams[away]['wins'] += 1
                teams[home]['losses'] += 1
        standings = sorted(teams.values(), key=lambda x: (-x['wins'], x['losses']))
        for i, t in enumerate(standings, 1):
            total = t['wins'] + t['losses']
            t['rank'] = i
            t['win_rate'] = round(t['wins'] / total, 3) if total else 0
        return standings

    def get_games(self, season_id: Optional[int] = None) -> list[dict]:
        """取得所有比賽原始資料"""
        sid = season_id or self._get_current_season_id()
        return self._fetch_json(f'/seasons/{sid}/games')

    def get_player_stats(self, name: str, season: str | None = None) -> dict:
        """從 TPBL 官方 API 查詢球員數據（/games/stats/players）"""
        import time
        # 取得所有賽季的 division_ids（搜尋全部賽季以支援歷史球員）
        try:
            seasons = self._fetch_json('/seasons')
        except Exception:
            seasons = []

        all_stats = {}  # keyed by player name, store per-season data
        for s in seasons:
            sid = s['id']
            try:
                games = self._fetch_json(f'/seasons/{sid}/games')
            except Exception:
                continue
            division_ids = sorted(set(g.get('division_id') for g in games if g.get('division_id')))
            for div_id in division_ids:
                try:
                    time.sleep(0.3)
                    data = self._fetch_json(f'/games/stats/players?division_id={div_id}')
                except Exception:
                    continue
                season_label = s.get('year', s.get('name', str(sid)))
                # e.g. "2024-2025 賽季" -> "24/25"
                season_short = season_label.replace(' 賽季', '').replace('-', '/')[2:]
                for entry in data:
                    player = entry.get('player', {})
                    pname = player.get('name', '')
                    if not pname:
                        continue
                    if pname not in all_stats:
                        all_stats[pname] = {
                            'name': pname,
                            'number': player.get('number', ''),
                            'team': entry.get('team', {}).get('name', ''),
                            'meta': player.get('meta', {}),
                            'seasons_data': {},
                        }
                    sd = all_stats[pname]['seasons_data']
                    if season_short not in sd:
                        sd[season_short] = {
                            'game_count': entry.get('game_count', 0),
                            'accumulated_stats': entry.get('accumulated_stats', {}),
                            'average_stats': entry.get('average_stats', {}),
                            'percentage_stats': entry.get('percentage_stats', {}),
                            'team': entry.get('team', {}).get('name', ''),
                        }
                    else:
                        prev = sd[season_short]
                        prev['game_count'] += entry.get('game_count', 0)
                        new_acc = entry.get('accumulated_stats', {})
                        for k, v in new_acc.items():
                            if k in prev['accumulated_stats'] and isinstance(v, (int, float)):
                                prev['accumulated_stats'][k] += v
                        if entry.get('game_count', 0) >= prev.get('_best_div_gp', 0):
                            prev['percentage_stats'] = entry.get('percentage_stats', {})
                            prev['team'] = entry.get('team', {}).get('name', prev['team'])
                            prev['_best_div_gp'] = entry.get('game_count', 0)

        for v in all_stats.values():
            for sd in v.get('seasons_data', {}).values():
                sd.pop('_best_div_gp', None)

        # 模糊搜尋
        name_lower = name.lower().strip()
        matches = [v for k, v in all_stats.items() if name_lower in k.lower() or k.lower() in name_lower]
        if not matches:
            for v in all_stats.values():
                if name in v.get('team', ''):
                    matches.append(v)
        if not matches:
            return {'error': f'找不到 TPBL 球員: {name}', 'league': 'tpbl', 'player_name': name}

        if len(matches) > 1:
            return {
                'league': 'tpbl',
                'player_name': name,
                'matches': [
                    {'name': m['name'], 'team': m['team']}
                    for m in matches
                ],
                'message': f'找到 {len(matches)} 位球員，請輸入更精確的名稱',
            }

        p = matches[0]
        meta = p['meta']
        seasons_data = p.get('seasons_data', {})

        seasons_list = []
        career_acc = {}
        for slabel in sorted(seasons_data.keys()):
            sd = seasons_data[slabel]
            gp = sd['game_count']
            acc = sd['accumulated_stats']
            pct = sd['percentage_stats']
            # 用累加的 accumulated_stats 重算場均（跨 division 準確）
            avg = {}
            if gp > 0:
                for k, v in acc.items():
                    if isinstance(v, (int, float)):
                        avg[k] = round(v / gp, 1)
            seasons_list.append({
                'season': slabel,
                'gp': gp,
                'avg_minutes': _sec_to_mmss(avg.get('time_on_court', 0)) if avg.get('time_on_court') else None,
                'avg_pts': avg.get('score'),
                'avg_reb': avg.get('rebounds'),
                'avg_ast': avg.get('assists'),
                'avg_stl': avg.get('steals'),
                'avg_blk': avg.get('blocks'),
                'fg2a': acc.get('two_pointers_attempted'),
                'fg2m': acc.get('two_pointers_made'),
                'fg2_pct': float(pct.get('two_pointers_percentage', 0)) / 100 if pct.get('two_pointers_percentage') else None,
                'fg3a': acc.get('three_pointers_attempted'),
                'fg3m': acc.get('three_pointers_made'),
                'fg3_pct': float(pct.get('three_pointers_percentage', 0)) / 100 if pct.get('three_pointers_percentage') else None,
                'fta': acc.get('free_throws_attempted'),
                'ftm': acc.get('free_throws_made'),
                'ft_pct': round(float(pct.get('free_throws_percentage', 0)) / 100, 3) if pct.get('free_throws_percentage') else None,
                'avg_tov': avg.get('turnovers'),
                'avg_pf': avg.get('fouls'),
                'eff': avg.get('efficiency'),
                'orb': acc.get('offensive_rebounds'),
                'drb': acc.get('defensive_rebounds'),
                'plus_minus': acc.get('plus_minus'),
                'pir': acc.get('performance_index_rating'),
            })
            # Career totals
            for k, v in acc.items():
                if isinstance(v, (int, float)):
                    career_acc[k] = career_acc.get(k, 0) + v
            career_acc['game_count'] = career_acc.get('game_count', 0) + gp

        career_gp = career_acc.pop('game_count', 0)
        career_avg = {}
        if career_gp > 0:
            for k, v in career_acc.items():
                if isinstance(v, (int, float)):
                    career_avg[k] = round(v / career_gp, 1)

        info = {
            'name': p['name'],
            'team': p['team'],
            'number': p.get('number', ''),
            'position': meta.get('position', ''),
            'height_cm': meta.get('height'),
            'weight': meta.get('weight'),
            'nationality': meta.get('nationality', ''),
            'league': 'tpbl',
            'seasons': seasons_list,
            'career': {
                'gp': career_gp,
                'avg_pts': career_avg.get('score'),
                'avg_reb': career_avg.get('rebounds'),
                'avg_ast': career_avg.get('assists'),
                'total_pts': career_acc.get('score'),
                'total_reb': career_acc.get('rebounds'),
                'total_ast': career_acc.get('assists'),
            } if career_gp > 0 else None,
        }
        return info

    def get_results(self, season_id: Optional[int] = None, team: Optional[str] = None) -> list[dict]:
        games = self.get_games(season_id)
        results = []
        for g in games:
            if g.get('status') != 'COMPLETED':
                continue
            if team and team not in g['home_team']['name'] and team not in g['away_team']['name']:
                continue
            results.append({
                'date': g['game_date'],
                'weekday': g.get('game_day_of_week', ''),
                'time': g.get('game_time', '')[:5],
                'away_team': g['away_team']['name'],
                'home_team': g['home_team']['name'],
                'away_score': g['away_team'].get('won_score', 0),
                'home_score': g['home_team'].get('won_score', 0),
                'venue': g.get('venue', ''),
                'round': g.get('round'),
            })
        return results


# ─── PLG API (HTML Scraping) ───

class PLGAPI:
    """PLG 官網 HTML 抓取解析（server-side rendered）"""
    BASE_URL = 'https://pleagueofficial.com'

    def get_standings(self) -> list[dict]:
        """解析戰績頁面（/standings）"""
        html = _fetch_html(f'{self.BASE_URL}/standings')
        soup = BeautifulSoup(html, 'lxml')

        standings = []
        # 第一個 table 是例行賽戰績
        table = soup.find('table')
        if not table:
            return standings

        for row in table.find_all('tr')[1:]:  # skip header
            cells = row.find_all(['th', 'td'])
            if len(cells) < 5:
                continue

            # 排名和球隊名用 <th>，數據用 <td>
            # cells: [rank(th), team(th), gp(td), W(td), L(td), PCT(td), GB(td), ...]
            a_tag = cells[1].find('a')
            team_short = a_tag.get_text(strip=True) if a_tag else cells[1].get_text(strip=True)
            team_name = PLG_SHORT_NAMES.get(team_short, team_short)

            try:
                gp = int(cells[2].get_text(strip=True))
                wins = int(cells[3].get_text(strip=True))
                losses = int(cells[4].get_text(strip=True))
                pct_str = cells[5].get_text(strip=True).replace('%', '')
                win_rate = int(pct_str) / 100 if pct_str.isdigit() else round(wins / (wins + losses), 3)
            except (ValueError, IndexError):
                continue

            standings.append({
                'rank': len(standings) + 1,
                'team': team_name,
                'gp': gp,
                'wins': wins,
                'losses': losses,
                'win_rate': win_rate,
            })

        return standings

    def _derive_season_year(self, soup: BeautifulSoup) -> tuple[int, int]:
        """從頁面標題推導賽季年份（如 '2025-26' → (2025, 2026)）"""
        title = soup.find('title')
        if title:
            text = title.get_text(strip=True)
            m = re.search(r'(\d{4})-(\d{2})', text)
            if m:
                return int(m.group(1)), 2000 + int(m.group(2))
        # fallback: 當前跨年邏輯
        today = date.today()
        if today.month >= 10:
            return today.year, today.year + 1
        return today.year - 1, today.year

    def get_games(self) -> list[dict]:
        """解析賽程頁面（/schedule），回傳所有比賽"""
        html = _fetch_html(f'{self.BASE_URL}/schedule')
        soup = BeautifulSoup(html, 'lxml')
        season_start, season_end = self._derive_season_year(soup)
        games = []

        for row in soup.find_all('div', class_='match_row'):
            try:
                # 日期時間區塊
                dt_div = row.find('div', class_='match_row_datetime')
                if not dt_div:
                    continue
                h5s = dt_div.find_all('h5')
                h6s = dt_div.find_all('h6')
                game_date = h5s[0].get_text(strip=True) if len(h5s) > 0 else ''
                weekday = h5s[1].get_text(strip=True) if len(h5s) > 1 else ''
                game_time = h6s[0].get_text(strip=True) if h6s else ''

                # 處理日期格式：10/26 → 依月份推導年份
                parts = game_date.split('/')
                if len(parts) == 2:
                    month = int(parts[0])
                    # 跨年賽季：10-12月用 season_start，其餘用 season_end
                    year = season_start if month >= 10 else season_end
                    date_str = f'{year}-{parts[0].zfill(2)}-{parts[1].zfill(2)}'
                else:
                    date_str = game_date

                # 客隊/主隊/比分都在 row.mx-0 裡
                col_lg_12 = row.find('div', class_='col-lg-12')
                if not col_lg_12:
                    continue
                inner_row = col_lg_12.find('div', class_='row')
                if not inner_row:
                    continue
                col_divs = inner_row.find_all('div', recursive=False)
                away_div = None
                home_div = None
                for cd in col_divs:
                    cls = ' '.join(cd.get('class', []))
                    if 'col-lg-3' in cls and 'text-right' in cls:
                        away_div = cd
                    elif 'col-lg-3' in cls and ('text-md-left' in cls or 'text-left' in cls):
                        home_div = cd

                if not away_div or not home_div:
                    continue

                # 客隊名稱：取 PC_only span 或一般文字
                away_name = self._extract_team_name(away_div)
                home_name = self._extract_team_name(home_div)

                # 比分（col-lg-4 區塊內的 h6.ff8bit）
                score_div = inner_row.find('div', class_='col-lg-4')
                away_score = None
                home_score = None
                game_id = ''
                venue = ''

                if score_div:
                    score_h6s = score_div.find_all('h6', class_='ff8bit')
                    if len(score_h6s) >= 2:
                        try:
                            away_score = int(score_h6s[0].get_text(strip=True))
                            home_score = int(score_h6s[1].get_text(strip=True))
                        except ValueError:
                            pass

                    # Game ID 和場館
                    info_h5s = score_div.find_all('h5')
                    for ih in info_h5s:
                        txt = ih.get_text(strip=True)
                        if txt.startswith('G') and len(txt) <= 5:
                            game_id = txt
                        elif '體育' in txt or '籃球' in txt or '大學' in txt:
                            venue = txt

                game = {
                    'date': date_str,
                    'weekday': weekday,
                    'time': game_time,
                    'away_team': away_name,
                    'home_team': home_name,
                    'venue': venue,
                    'game_id': game_id,
                }

                if away_score is not None and home_score is not None:
                    if away_score == 0 and home_score == 0:
                        game['status'] = 'postponed'
                    else:
                        game['away_score'] = away_score
                        game['home_score'] = home_score
                        game['status'] = 'completed'
                else:
                    game['status'] = 'upcoming'

                games.append(game)
            except Exception:
                continue

        return games

    def get_schedule(self) -> list[dict]:
        """未來賽程"""
        games = self.get_games()
        return [g for g in games if g.get('status') == 'upcoming']

    def get_results(self, team: Optional[str] = None) -> list[dict]:
        """已完成比賽結果"""
        games = self.get_games()
        results = [g for g in games if g.get('status') == 'completed']
        if team:
            resolved = resolve_team(team)
            if resolved:
                results = [g for g in results if resolved in g.get('away_team', '') or resolved in g.get('home_team', '')]
        return results

    def search_player(self, name: str) -> list[dict]:
        """搜尋球員，回傳匹配的球員列表 [{name, player_id, url}]"""
        name = name.strip()
        # 從 /stat-player 和 /all-players 收集球員
        players = {}
        for path in ('/stat-player', '/all-players'):
            try:
                html = _fetch_html(f'{self.BASE_URL}{path}')
                soup = BeautifulSoup(html, 'lxml')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if href.startswith('/player/'):
                        pid = href.split('/player/')[1].split('?')[0]
                        pname = a.get_text(strip=True)
                        if pname and pid not in players:
                            players[pid] = {'name': pname, 'player_id': pid, 'url': f'{self.BASE_URL}{href}'}
            except Exception:
                continue

        # 模糊匹配
        results = []
        for p in players.values():
            if name in p['name'] or p['name'] in name:
                results.append(p)
        # 也試試英文匹配
        name_lower = name.lower()
        for p in players.values():
            if name_lower in p['name'].lower() and p not in results:
                results.append(p)
        return results

    def get_player_stats_by_id(self, player_id: str, season: str | None = None) -> dict:
        """從球員頁面抓取各賽季統計數據"""
        html = _fetch_html(f'{self.BASE_URL}/player/{player_id}')
        soup = BeautifulSoup(html, 'lxml')
        tables = soup.find_all('table')

        # Table 0: 基本資料
        info = {'player_id': player_id, 'name': '', 'team': '', 'number': '', 'position': '',
                'height': '', 'weight': '', 'birthday': '', 'birthplace': ''}
        if tables:
            for row in tables[0].find_all('tr'):
                cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
                if len(cells) >= 2:
                    key = cells[0]
                    val = cells[1]
                    if key == '球隊':
                        info['team'] = val.split('\n')[0].strip()
                    elif key == '背號':
                        info['number'] = val
                    elif key == '位置':
                        info['position'] = val
                    elif key == '身高':
                        info['height'] = val
                    elif key == '體重':
                        info['weight'] = val
                    elif key == '生日':
                        info['birthday'] = val
                    elif key == '出生地':
                        info['birthplace'] = val

        # 從 title 抓球員名稱
        title = soup.find('title')
        if title:
            t = title.get_text(strip=True)
            if '|' in t:
                info['name'] = t.split('|')[0].strip()

        # Table 2: 累計數據 per season
        # Table 3: 平均數據 per season
        season_stats = []
        if len(tables) >= 3:
            cum_rows = tables[2].find_all('tr')[1:]  # skip header
            avg_rows = tables[3].find_all('tr')[1:] if len(tables) >= 4 else []

            for i, row in enumerate(cum_rows):
                cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
                if len(cells) < 16 or not cells[0]:
                    continue
                s = cells[0]  # season or 'career'

                if season and s != season and s != 'career':
                    continue

                stat = {
                    'season': s,
                    'gp': int(cells[1]) if cells[1].isdigit() else None,
                    'minutes': cells[2],
                    'pts': int(cells[3]) if cells[3].isdigit() else None,
                    'reb': int(cells[4]) if cells[4].isdigit() else None,
                    'ast': int(cells[5]) if cells[5].isdigit() else None,
                    'stl': int(cells[6]) if cells[6].isdigit() else None,
                    'blk': int(cells[7]) if cells[7].isdigit() else None,
                    'fg': cells[8],
                    'fg_pct': cells[9],
                    '3p': cells[10],
                    '3p_pct': cells[11],
                    'ft': cells[12],
                    'ft_pct': cells[13],
                    'tov': int(cells[14]) if cells[14].isdigit() else None,
                    'pf': int(cells[15]) if cells[15].isdigit() else None,
                }

                # 加入平均數據
                if i < len(avg_rows):
                    ac = [c.get_text(strip=True) for c in avg_rows[i].find_all(['td', 'th'])]
                    if len(ac) >= 6:
                        # 統一 avg_minutes 為浮點分鐘數
                        mins_raw = ac[2]
                        if ':' in mins_raw:
                            stat['avg_minutes'] = mins_raw
                        else:
                            try:
                                total_sec = round(float(mins_raw) * 60)
                                stat['avg_minutes'] = f'{total_sec // 60}:{total_sec % 60:02d}'
                            except (ValueError, TypeError):
                                stat['avg_minutes'] = mins_raw
                        stat['avg_pts'] = ac[3]
                        stat['avg_reb'] = ac[4]
                        stat['avg_ast'] = ac[5]

                season_stats.append(stat)

        career = None
        regular = [s for s in season_stats if s['season'] != 'career']
        for s in season_stats:
            if s['season'] == 'career':
                career = s
                break

        info['seasons'] = regular
        info['career'] = career
        return info

    def get_player_stats(self, name: str, season: str | None = None) -> dict:
        """搜尋球員並回傳統計數據"""
        matches = self.search_player(name)
        if not matches:
            return {'error': f'找不到球員: {name}', 'league': 'plg'}
        if len(matches) > 1:
            return {
                'league': 'plg',
                'matches': [{'name': m['name'], 'player_id': m['player_id']} for m in matches],
                'message': f'找到 {len(matches)} 位球員，請指定 player_id',
            }
        return self.get_player_stats_by_id(matches[0]['player_id'], season)

    @staticmethod
    def _extract_team_name(div) -> str:
        """從球隊 div 提取正式名稱"""
        # 嘗試 PC_only span（中文名）
        pc_span = div.find('span', class_='PC_only')
        if pc_span:
            name = pc_span.get_text(strip=True)
            if name and name not in ('客隊', '主隊', 'VS'):
                return PLG_SHORT_NAMES.get(name, name)

        # fallback: 用所有文字找匹配
        text = div.get_text(strip=True)
        for short, full in PLG_SHORT_NAMES.items():
            if short in text:
                return full
        return text[:20]  # truncate


# ─── 統一介面 ───

def get_league_api(league: str):
    league = normalize_league(league)
    if league == 'plg':
        return PLGAPI()
    elif league == 'tpbl':
        return TPBLAPI()
    else:
        raise ValueError(f'不支援的聯盟: {league}（支援: plg, tpbl）')
