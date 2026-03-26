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

import hashlib
import json
import os
import re
import sys
import time as _time
import urllib.request
import urllib.error
from datetime import datetime, date
from pathlib import Path
from typing import Any, Optional
from bs4 import BeautifulSoup

# ─── Debug 模式 ───

_DEBUG: bool = os.environ.get('BASKETBALL_DEBUG', '').lower() in ('1', 'true', 'yes')


def _debug_log(msg: str) -> None:
    """若 BASKETBALL_DEBUG=1 則輸出 debug 訊息至 stderr"""
    if _DEBUG:
        print(f'[DEBUG] {msg}', file=sys.stderr)


# ─── TTL 快取 ───

_CACHE_DIR = Path.home() / '.cache' / 'taiwan-basketball'
_CACHE_TTL_DEFAULT = 300  # 5 分鐘

# 依資料類型設定 TTL（秒）
CACHE_TTL = {
    'schedule': 300,    # 賽程：5 分鐘
    'games': 600,       # 比賽結果：10 分鐘
    'standings': 600,   # 戰績：10 分鐘
    'player': 3600,     # 球員數據：1 小時
    'leaders': 600,     # 排行榜：10 分鐘
    'default': 300,
}

_cache_enabled: bool = True


def _cache_key(url: str) -> str:
    return hashlib.md5(url.encode()).hexdigest()


def _cache_get(key: str) -> Optional[Any]:
    """從磁碟快取讀取，若過期則回傳 None"""
    if not _cache_enabled:
        return None
    cache_file = _CACHE_DIR / f'{key}.json'
    if not cache_file.exists():
        return None
    try:
        data = json.loads(cache_file.read_text(encoding='utf-8'))
        ttl = data.get('ttl', _CACHE_TTL_DEFAULT)
        if _time.time() - data.get('timestamp', 0) < ttl:
            _debug_log(f'Cache hit: {key}')
            return data['value']
        _debug_log(f'Cache expired: {key}')
    except (json.JSONDecodeError, KeyError, OSError):
        pass
    return None


def _cache_set(key: str, value: Any, ttl: int = _CACHE_TTL_DEFAULT) -> None:
    """將資料寫入磁碟快取"""
    if not _cache_enabled:
        return
    try:
        _CACHE_DIR.mkdir(parents=True, exist_ok=True)
        cache_file = _CACHE_DIR / f'{key}.json'
        cache_file.write_text(
            json.dumps({'timestamp': _time.time(), 'ttl': ttl, 'value': value}, ensure_ascii=False),
            encoding='utf-8',
        )
        _debug_log(f'Cache set: {key} (TTL={ttl}s)')
    except OSError as e:
        _debug_log(f'Cache write failed: {e}')


def disable_cache() -> None:
    """停用快取（CLI --no-cache 旗標使用）"""
    global _cache_enabled
    _cache_enabled = False


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
_FETCH_RETRIES = 3          # 最多重試次數
_FETCH_BACKOFF_BASE = 1.5   # 退避基數（秒）


def _fetch_html(url: str, ttl: int = _CACHE_TTL_DEFAULT) -> str:
    """用 urllib 抓 HTML，支援快取與指數退避重試"""
    key = _cache_key(url)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    _debug_log(f'GET {url}')
    last_err: Exception = RuntimeError('No attempts made')
    for attempt in range(_FETCH_RETRIES):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': _UA})
            with urllib.request.urlopen(req, timeout=15) as resp:
                html = resp.read().decode('utf-8', errors='replace')
            _cache_set(key, html, ttl)
            return html
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            last_err = e
            if attempt < _FETCH_RETRIES - 1:
                wait = _FETCH_BACKOFF_BASE ** attempt
                _debug_log(f'Request failed ({e}), retrying in {wait:.1f}s… (attempt {attempt + 1}/{_FETCH_RETRIES})')
                _time.sleep(wait)
    raise urllib.error.URLError(f'Failed after {_FETCH_RETRIES} attempts: {last_err}')


def _fetch_json_url(url: str, headers: Optional[dict] = None, ttl: int = _CACHE_TTL_DEFAULT) -> Any:
    """用 urllib 抓 JSON，支援快取與指數退避重試"""
    key = _cache_key(url)
    cached = _cache_get(key)
    if cached is not None:
        return cached

    _debug_log(f'GET (JSON) {url}')
    req = urllib.request.Request(url)
    req.add_header('User-Agent', _UA)
    if headers:
        for k, v in headers.items():
            req.add_header(k, v)

    last_err: Exception = RuntimeError('No attempts made')
    for attempt in range(_FETCH_RETRIES):
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read())
            _cache_set(key, data, ttl)
            return data
        except (urllib.error.URLError, urllib.error.HTTPError, OSError) as e:
            last_err = e
            if attempt < _FETCH_RETRIES - 1:
                wait = _FETCH_BACKOFF_BASE ** attempt
                _debug_log(f'Request failed ({e}), retrying in {wait:.1f}s… (attempt {attempt + 1}/{_FETCH_RETRIES})')
                _time.sleep(wait)
        except json.JSONDecodeError as e:
            raise ValueError(f'Invalid JSON from {url}: {e}') from e
    raise urllib.error.URLError(f'Failed after {_FETCH_RETRIES} attempts: {last_err}')


def _safe_int(value: Any, default: int = 0) -> int:
    """安全轉換整數，失敗時回傳預設值"""
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _safe_float(value: Any, default: float = 0.0) -> float:
    """安全轉換浮點數，失敗時回傳預設值"""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default

# ─── 表格格式化工具 ───

import unicodedata as _unicodedata


def _str_display_width(s: str) -> int:
    """計算字串顯示寬度（East Asian Wide/Fullwidth 字元佔 2 格，其餘佔 1 格）"""
    return sum(
        2 if _unicodedata.east_asian_width(c) in ('W', 'F') else 1
        for c in s
    )


def format_table(data: list[dict], columns: Optional[list[str]] = None,
                 headers: Optional[dict[str, str]] = None) -> str:
    """將 list[dict] 格式化為 ASCII 表格（正確處理中文寬度）

    Args:
        data: 資料列表
        columns: 要顯示的欄位（預設全部）
        headers: 欄位顯示名稱對照（key → display name）
    """
    if not data:
        return '（無資料）'

    cols = columns or list(data[0].keys())
    hdrs = headers or {}

    def cell(val: Any) -> str:
        if val is None:
            return '-'
        return str(val)

    # 計算各欄寬度
    col_widths: dict[str, int] = {}
    for c in cols:
        display_name = hdrs.get(c, c)
        col_widths[c] = _str_display_width(display_name)
    for row in data:
        for c in cols:
            col_widths[c] = max(col_widths[c], _str_display_width(cell(row.get(c))))

    def pad_cell(val: str, width: int) -> str:
        return val + ' ' * (width - _str_display_width(val))

    sep = '+' + '+'.join('-' * (col_widths[c] + 2) for c in cols) + '+'
    header_row = '|' + '|'.join(f' {pad_cell(hdrs.get(c, c), col_widths[c])} ' for c in cols) + '|'
    lines = [sep, header_row, sep]
    for row in data:
        lines.append('|' + '|'.join(f' {pad_cell(cell(row.get(c)), col_widths[c])} ' for c in cols) + '|')
    lines.append(sep)
    return '\n'.join(lines)


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

    def _fetch_json(self, path: str, ttl: int = _CACHE_TTL_DEFAULT) -> Any:
        return _fetch_json_url(
            f'{self.BASE_URL}{path}',
            headers={'Referer': 'https://tpbl.basketball/'},
            ttl=ttl,
        )

    def _get_current_season_id(self) -> int:
        if self._season_id is not None:
            return self._season_id
        seasons = self._fetch_json('/seasons', ttl=CACHE_TTL['standings'])
        for s in seasons:
            if s.get('status') == 'IN_PROGRESS':
                self._season_id = s.get('id', 2)
                return self._season_id
        self._season_id = seasons[-1].get('id', 2) if seasons else 2
        return self._season_id

    def get_schedule(self, season_id: Optional[int] = None) -> list[dict]:
        games = self.get_games(season_id)
        schedule = []
        today = date.today().isoformat()
        for g in games:
            if g.get('status') == 'NOT_STARTED' and g.get('game_date', '') >= today:
                home = g.get('home_team') or {}
                away = g.get('away_team') or {}
                schedule.append({
                    'date': g.get('game_date', ''),
                    'weekday': g.get('game_day_of_week', ''),
                    'time': (g.get('game_time') or '')[:5],
                    'away_team': away.get('name', ''),
                    'home_team': home.get('name', ''),
                    'venue': g.get('venue', ''),
                    'status': 'upcoming',
                    'round': g.get('round'),
                })
        return schedule

    def get_standings(self, season_id: Optional[int] = None) -> list[dict]:
        # TPBL 官方 API 無 /standings endpoint（已確認 404），故從 games 計算戰績
        games = self.get_games(season_id)
        teams: dict[str, dict] = {}
        for g in games:
            if g.get('status') != 'COMPLETED':
                continue
            home_info = g.get('home_team') or {}
            away_info = g.get('away_team') or {}
            home = home_info.get('name', '')
            away = away_info.get('name', '')
            if not home or not away:
                continue
            home_score = _safe_int(home_info.get('won_score', 0))
            away_score = _safe_int(away_info.get('won_score', 0))
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
        return self._fetch_json(f'/seasons/{sid}/games', ttl=CACHE_TTL['games'])

    def _get_division_ids(self, season_id: int) -> list[int]:
        """取得賽季中所有 division_id"""
        try:
            games = self._fetch_json(f'/seasons/{season_id}/games', ttl=CACHE_TTL['games'])
            return sorted(set(g.get('division_id') for g in games if g.get('division_id')))
        except (urllib.error.URLError, ValueError):
            return []

    def _fetch_player_stats_for_division(self, div_id: int) -> list[dict]:
        """抓取單一 division 的所有球員統計"""
        try:
            return self._fetch_json(f'/games/stats/players?division_id={div_id}', ttl=CACHE_TTL['player'])
        except (urllib.error.URLError, ValueError):
            return []

    @staticmethod
    def _season_label_to_short(label: str) -> str:
        """'2024-2025 賽季' → '24/25'"""
        clean = label.replace(' 賽季', '').strip()
        m = re.search(r'(\d{4})-(\d{4})', clean)
        if m:
            return f'{m.group(1)[-2:]}/{m.group(2)[-2:]}'
        return clean


    def get_player_stats(self, name: str, season: str | None = None) -> dict:
        """從 TPBL 官方 API 查詢球員數據"""
        try:
            seasons = self._fetch_json('/seasons', ttl=CACHE_TTL['standings'])
        except (urllib.error.URLError, ValueError):
            seasons = []

        all_stats: dict[str, dict] = {}

        for s in seasons:
            sid = s.get('id')
            if not sid:
                continue
            season_short = self._season_label_to_short(s.get('year', s.get('name', str(sid))))

            # 若已指定賽季則跳過不匹配的
            if season and season_short != season:
                continue

            for div_id in self._get_division_ids(sid):
                for entry in self._fetch_player_stats_for_division(div_id):
                    player = entry.get('player') or {}
                    pname = player.get('name', '')
                    if not pname:
                        continue
                    if pname not in all_stats:
                        all_stats[pname] = {
                            'name': pname,
                            'number': player.get('number', ''),
                            'team': (entry.get('team') or {}).get('name', ''),
                            'meta': player.get('meta') or {},
                            'seasons_data': {},
                        }
                    sd = all_stats[pname]['seasons_data']
                    if season_short not in sd:
                        sd[season_short] = {
                            'game_count': entry.get('game_count', 0),
                            'accumulated_stats': dict(entry.get('accumulated_stats') or {}),
                            'team': (entry.get('team') or {}).get('name', ''),
                        }
                    else:
                        prev = sd[season_short]
                        prev['game_count'] += entry.get('game_count', 0)
                        new_acc = entry.get('accumulated_stats') or {}
                        for k, v in new_acc.items():
                            if isinstance(v, (int, float)):
                                prev['accumulated_stats'][k] = prev['accumulated_stats'].get(k, 0) + v
                        # 更新球隊名（優先出場數多的分區）
                        if entry.get('game_count', 0) > prev.get('_best_div_gp', 0):
                            prev['team'] = (entry.get('team') or {}).get('name', prev['team'])
                            prev['_best_div_gp'] = entry.get('game_count', 0)

        for v in all_stats.values():
            for sd in v.get('seasons_data', {}).values():
                sd.pop('_best_div_gp', None)

        # 模糊搜尋
        name_lower = name.lower().strip()
        matches = [v for k, v in all_stats.items() if name_lower in k.lower() or k.lower() in name_lower]
        if not matches:
            matches = [v for v in all_stats.values() if name in v.get('team', '')]
        if not matches:
            return {'error': f'找不到 TPBL 球員: {name}', 'league': 'tpbl', 'player_name': name}

        if len(matches) > 1:
            return {
                'league': 'tpbl',
                'player_name': name,
                'matches': [{'name': m['name'], 'team': m['team']} for m in matches],
                'message': f'找到 {len(matches)} 位球員，請輸入更精確的名稱',
            }

        p = matches[0]
        meta = p.get('meta') or {}
        seasons_data = p.get('seasons_data', {})

        seasons_list = []
        career_acc: dict[str, float] = {}
        career_gp = 0

        for slabel in sorted(seasons_data.keys()):
            sd = seasons_data[slabel]
            gp = sd.get('game_count', 0)
            acc = sd.get('accumulated_stats', {})

            # 從累計 makes/attempts 計算命中率（跨 division 準確）
            fg2m = _safe_float(acc.get('two_pointers_made'))
            fg2a = _safe_float(acc.get('two_pointers_attempted'))
            fg3m = _safe_float(acc.get('three_pointers_made'))
            fg3a = _safe_float(acc.get('three_pointers_attempted'))
            ftm = _safe_float(acc.get('free_throws_made'))
            fta = _safe_float(acc.get('free_throws_attempted'))

            avg: dict[str, float] = {}
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
                'fg2a': int(fg2a) if fg2a else None,
                'fg2m': int(fg2m) if fg2m else None,
                'fg2_pct': round(fg2m / fg2a, 3) if fg2a else None,
                'fg3a': int(fg3a) if fg3a else None,
                'fg3m': int(fg3m) if fg3m else None,
                'fg3_pct': round(fg3m / fg3a, 3) if fg3a else None,
                'fta': int(fta) if fta else None,
                'ftm': int(ftm) if ftm else None,
                'ft_pct': round(ftm / fta, 3) if fta else None,
                'avg_tov': avg.get('turnovers'),
                'avg_pf': avg.get('fouls'),
                'eff': avg.get('efficiency'),
                'orb': acc.get('offensive_rebounds'),
                'drb': acc.get('defensive_rebounds'),
                'plus_minus': acc.get('plus_minus'),
                'pir': acc.get('performance_index_rating'),
            })
            for k, v in acc.items():
                if isinstance(v, (int, float)):
                    career_acc[k] = career_acc.get(k, 0) + v
            career_gp += gp

        career_avg: dict[str, float] = {}
        if career_gp > 0:
            for k, v in career_acc.items():
                if isinstance(v, (int, float)):
                    career_avg[k] = round(v / career_gp, 1)

        return {
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
                'total_pts': int(career_acc.get('score', 0)),
                'total_reb': int(career_acc.get('rebounds', 0)),
                'total_ast': int(career_acc.get('assists', 0)),
            } if career_gp > 0 else None,
        }

    def get_boxscore(self, game_id: str) -> dict:
        """取得單場比賽統計（TPBL 僅提供球隊級別數據，無個別球員數據）

        Args:
            game_id: TPBL 比賽 ID（數字）
        """
        data = self._fetch_json(f'/games/{game_id}/stats', ttl=CACHE_TTL['games'])
        home_team = data.get('home_team') or {}
        away_team = data.get('away_team') or {}
        home_teams = home_team.get('teams', {})
        away_teams = away_team.get('teams', {})

        def _round_stats(teams_data: dict) -> list[dict]:
            rounds = []
            for rnd_key in sorted(teams_data.get('rounds', {}).keys(), key=int):
                rnd = teams_data['rounds'][rnd_key]
                rounds.append({
                    'quarter': int(rnd_key),
                    'score': rnd.get('won_score'),
                    'opponent_score': rnd.get('lost_score'),
                    'fg': rnd.get('field_goals'),
                    'fg_pct': rnd.get('field_goals_percentage'),
                    'fg2': rnd.get('two_pointers'),
                    'fg3': rnd.get('three_pointers'),
                    'ft': rnd.get('free_throws'),
                    'reb': rnd.get('rebounds'),
                    'ast': rnd.get('assists'),
                    'stl': rnd.get('steals'),
                    'blk': rnd.get('blocks'),
                    'tov': rnd.get('turnovers'),
                    'pf': rnd.get('fouls'),
                })
            return rounds

        return {
            'game_id': game_id,
            'home_team': home_team.get('name', ''),
            'away_team': away_team.get('name', ''),
            'home_quarters': _round_stats(home_teams),
            'away_quarters': _round_stats(away_teams),
            'home_total': home_teams.get('total'),
            'away_total': away_teams.get('total'),
            'note': 'TPBL API 僅提供球隊級別統計，無個別球員數據',
        }

    def get_results(self, season_id: Optional[int] = None, team: Optional[str] = None) -> list[dict]:
        games = self.get_games(season_id)
        results = []
        for g in games:
            if g.get('status') != 'COMPLETED':
                continue
            home = g.get('home_team') or {}
            away = g.get('away_team') or {}
            home_name = home.get('name', '')
            away_name = away.get('name', '')
            if team and team not in home_name and team not in away_name:
                continue
            results.append({
                'date': g.get('game_date', ''),
                'weekday': g.get('game_day_of_week', ''),
                'time': (g.get('game_time') or '')[:5],
                'away_team': away_name,
                'home_team': home_name,
                'away_score': _safe_int(away.get('won_score', 0)),
                'home_score': _safe_int(home.get('won_score', 0)),
                'venue': g.get('venue', ''),
                'round': g.get('round'),
                'game_id': str(g.get('id', '')),
            })
        return results

    def get_league_leaders(self, stat: str = 'pts', top_n: int = 10,
                           season_id: Optional[int] = None) -> list[dict]:
        """取得聯盟排行榜（依指定數據欄位排序）

        stat 支援: pts, reb, ast, stl, blk, tov, pf, eff
        """
        # 統計欄位對應 accumulated_stats 鍵名
        stat_key_map = {
            'pts': 'score', 'reb': 'rebounds', 'ast': 'assists',
            'stl': 'steals', 'blk': 'blocks', 'tov': 'turnovers',
            'pf': 'fouls', 'eff': 'efficiency',
        }
        acc_key = stat_key_map.get(stat, stat)
        sid = season_id or self._get_current_season_id()
        players: dict[str, dict] = {}

        for div_id in self._get_division_ids(sid):
            for entry in self._fetch_player_stats_for_division(div_id):
                player = entry.get('player') or {}
                pname = player.get('name', '')
                if not pname:
                    continue
                gp = entry.get('game_count', 0)
                acc = entry.get('accumulated_stats') or {}
                val = _safe_float(acc.get(acc_key, 0))
                avg_val = round(val / gp, 1) if gp > 0 else 0.0

                if pname not in players or gp > players[pname].get('gp', 0):
                    players[pname] = {
                        'name': pname,
                        'team': (entry.get('team') or {}).get('name', ''),
                        'gp': gp,
                        'value': avg_val,
                    }

        result = sorted(players.values(), key=lambda x: x.get('value', 0), reverse=True)
        for i, p in enumerate(result[:top_n], 1):
            p['rank'] = i
        return result[:top_n]


# ─── PLG API (HTML Scraping) ───

class PLGAPI:
    """PLG 官網 HTML 抓取解析（server-side rendered）"""
    BASE_URL = 'https://pleagueofficial.com'

    def get_standings(self) -> list[dict]:
        """解析戰績頁面（/standings）"""
        html = _fetch_html(f'{self.BASE_URL}/standings', ttl=CACHE_TTL['standings'])
        soup = BeautifulSoup(html, 'lxml')

        standings = []
        # 第一個 table 是例行賽戰績
        table = soup.find('table')
        if not table:
            _debug_log('PLG standings: no <table> found in /standings')
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
                pct_str = cells[5].get_text(strip=True).replace('%', '') if len(cells) > 5 else ''
                win_rate = int(pct_str) / 100 if pct_str.isdigit() else round(wins / (wins + losses), 3)
            except (ValueError, IndexError, ZeroDivisionError):
                _debug_log(f'PLG standings: skipping row with parse error')
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
                start = int(m.group(1))
                end = 2000 + int(m.group(2))
                # 驗證合理性：end 必須是 start+1，且不超過當前年±2
                current_year = date.today().year
                if end == start + 1 and current_year - 2 <= start <= current_year + 1:
                    return start, end
        # fallback: 當前跨年邏輯
        today = date.today()
        if today.month >= 10:
            return today.year, today.year + 1
        return today.year - 1, today.year


    def get_games(self) -> list[dict]:
        """解析賽程頁面（/schedule），回傳所有比賽"""
        html = _fetch_html(f'{self.BASE_URL}/schedule', ttl=CACHE_TTL['schedule'])
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
                    month = _safe_int(parts[0])
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
                    score_h6s = [h for h in score_div.find_all('h6', class_='ff8bit') if 'MOBILE_only' not in (h.get('class') or [])]
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
            except (ValueError, IndexError, AttributeError) as e:
                _debug_log(f'PLG get_games: skipping row due to {e}')
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
        players: dict[str, dict] = {}
        for path in ('/stat-player', '/all-players'):
            try:
                html = _fetch_html(f'{self.BASE_URL}{path}', ttl=CACHE_TTL['player'])
                soup = BeautifulSoup(html, 'lxml')
                for a in soup.find_all('a', href=True):
                    href = a['href']
                    if href.startswith('/player/'):
                        pid = href.split('/player/')[1].split('?')[0]
                        pname = a.get_text(strip=True)
                        if pname and pid not in players:
                            players[pid] = {'name': pname, 'player_id': pid, 'url': f'{self.BASE_URL}{href}'}
            except (urllib.error.URLError, urllib.error.HTTPError) as e:
                _debug_log(f'PLG search_player: {path} failed: {e}')
                continue

        # 模糊匹配
        results = []
        name_lower = name.lower()
        for p in players.values():
            if name in p['name'] or p['name'] in name or name_lower in p['name'].lower():
                results.append(p)
        return results

    def get_player_stats_by_id(self, player_id: str, season: str | None = None) -> dict:
        """從球員頁面抓取各賽季統計數據"""
        html = _fetch_html(f'{self.BASE_URL}/player/{player_id}', ttl=CACHE_TTL['player'])
        soup = BeautifulSoup(html, 'lxml')
        tables = soup.find_all('table')

        # Table 0: 基本資料
        info: dict[str, Any] = {
            'player_id': player_id, 'name': '', 'team': '', 'number': '', 'position': '',
            'height': '', 'weight': '', 'birthday': '', 'birthplace': '',
        }
        if tables:
            for row in tables[0].find_all('tr'):
                cells = [c.get_text(strip=True) for c in row.find_all(['td', 'th'])]
                if len(cells) >= 2:
                    key, val = cells[0], cells[1]
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

                stat: dict[str, Any] = {
                    'season': s,
                    'gp': _safe_int(cells[1]) if cells[1].isdigit() else None,
                    'minutes': cells[2],
                    'pts': _safe_int(cells[3]) if cells[3].isdigit() else None,
                    'reb': _safe_int(cells[4]) if cells[4].isdigit() else None,
                    'ast': _safe_int(cells[5]) if cells[5].isdigit() else None,
                    'stl': _safe_int(cells[6]) if cells[6].isdigit() else None,
                    'blk': _safe_int(cells[7]) if cells[7].isdigit() else None,
                    'fg': cells[8],
                    'fg_pct': cells[9],
                    '3p': cells[10],
                    '3p_pct': cells[11],
                    'ft': cells[12],
                    'ft_pct': cells[13],
                    'tov': _safe_int(cells[14]) if cells[14].isdigit() else None,
                    'pf': _safe_int(cells[15]) if cells[15].isdigit() else None,
                }

                # 加入平均數據
                if i < len(avg_rows):
                    ac = [c.get_text(strip=True) for c in avg_rows[i].find_all(['td', 'th'])]
                    if len(ac) >= 6:
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

    def get_boxscore(self, game_id: str, tab: str = 'TOTAL') -> dict:
        """取得單場比賽 boxscore 數據

        Args:
            game_id: PLG 比賽 ID（如 '693'）
            tab: 統計區間，支援 Q1/Q2/Q3/Q4/1st_half/2nd_half/TOTAL
        """
        api_tab = tab.lower()  # API requires lowercase
        url = f'{self.BASE_URL}/api/boxscore.preciser.php?id={game_id}&away_tab={api_tab}&home_tab={api_tab}'
        resp = _fetch_json_url(url, ttl=CACHE_TTL['games'])
        if resp.get('error'):
            return {'error': resp['error'], 'game_id': game_id}
        data = resp['data']
        return {
            'game_id': game_id,
            'score_home': data.get('score_home'),
            'score_away': data.get('score_away'),
            'quarters': {
                'q1': {'home': data.get('q1_home'), 'away': data.get('q1_away')},
                'q2': {'home': data.get('q2_home'), 'away': data.get('q2_away')},
                'q3': {'home': data.get('q3_home'), 'away': data.get('q3_away')},
                'q4': {'home': data.get('q4_home'), 'away': data.get('q4_away')},
            },
            'home_players': self._parse_boxscore_players(data.get('home', [])),
            'away_players': self._parse_boxscore_players(data.get('away', [])),
            'home_total': data.get('home_total'),
            'away_total': data.get('away_total'),
        }

    @staticmethod
    def _parse_boxscore_players(players: list[dict]) -> list[dict]:
        """解析 PLG boxscore 球員數據"""
        result = []
        for p in players:
            entry = {
                'player_id': p.get('player_id'),
                'name': p.get('name_alt') or p.get('name', ''),
                'jersey': p.get('jersey', ''),
                'starter': p.get('starter'),
                'mins': p.get('mins'),
                'dnp': p.get('mins') == 'DNP',
                'pts': _safe_int(p.get('points')) if p.get('points') not in ('', None) else None,
                'fg2': p.get('two_m_two'),
                'fg2_pct': p.get('twop'),
                'fg3': p.get('trey_m_trey'),
                'fg3_pct': p.get('treyp'),
                'ft': p.get('ft_m_ft'),
                'ft_pct': p.get('ftp'),
                'reb': _safe_int(p.get('reb')) if p.get('reb') not in ('', None) else None,
                'orb': _safe_int(p.get('reb_o')) if p.get('reb_o') not in ('', None) else None,
                'drb': _safe_int(p.get('reb_d')) if p.get('reb_d') not in ('', None) else None,
                'ast': _safe_int(p.get('ast')) if p.get('ast') not in ('', None) else None,
                'stl': _safe_int(p.get('stl')) if p.get('stl') not in ('', None) else None,
                'blk': _safe_int(p.get('blk')) if p.get('blk') not in ('', None) else None,
                'tov': _safe_int(p.get('turnover')) if p.get('turnover') not in ('', None) else None,
                'pf': _safe_int(p.get('pfoul')) if p.get('pfoul') not in ('', None) else None,
                'eff': _safe_int(p.get('eff')) if p.get('eff') not in ('', None) else None,
                'plus_minus': _safe_int(p.get('positive')) if p.get('positive') not in ('', None) else None,
            }
            result.append(entry)
        return result

    def get_league_leaders(self, stat: str = 'pts', top_n: int = 10) -> list[dict]:
        """取得 PLG 聯盟排行榜（依指定數據欄位排序）

        stat 支援: pts, reb, ast, stl, blk, tov, pf
        """
        stat_col_map = {
            'pts': 'avg_pts', 'reb': 'avg_reb', 'ast': 'avg_ast',
            'stl': 'avg_stl', 'blk': 'avg_blk',
        }
        col_key = stat_col_map.get(stat, f'avg_{stat}')

        try:
            html = _fetch_html(f'{self.BASE_URL}/stat-player', ttl=CACHE_TTL['leaders'])
        except (urllib.error.URLError, urllib.error.HTTPError) as e:
            _debug_log(f'PLG get_league_leaders: fetch failed: {e}')
            return []

        soup = BeautifulSoup(html, 'lxml')
        table = soup.find('table')
        if not table:
            return []

        # 解析表頭
        header_row = table.find('tr')
        if not header_row:
            return []
        headers = [th.get_text(strip=True).lower() for th in header_row.find_all(['th', 'td'])]

        # 嘗試找到對應欄位索引
        stat_header_map = {
            'pts': ['pts', 'points', '得分', 'avg_pts'],
            'reb': ['reb', 'rebounds', '籃板', 'avg_reb'],
            'ast': ['ast', 'assists', '助攻', 'avg_ast'],
            'stl': ['stl', 'steals', '抄截', 'avg_stl'],
            'blk': ['blk', 'blocks', '阻攻', 'avg_blk'],
        }
        target_names = stat_header_map.get(stat, [stat])
        stat_idx = None
        for name_candidate in target_names:
            for i, h in enumerate(headers):
                if name_candidate in h:
                    stat_idx = i
                    break
            if stat_idx is not None:
                break

        players = []
        for row in table.find_all('tr')[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 3:
                continue
            try:
                # 抓球員名稱連結
                player_cell = cells[1] if len(cells) > 1 else cells[0]
                a_tag = player_cell.find('a')
                pname = a_tag.get_text(strip=True) if a_tag else player_cell.get_text(strip=True)
                if not pname:
                    continue

                # 抓球隊
                team = cells[2].get_text(strip=True) if len(cells) > 2 else ''

                # 抓目標統計值
                stat_val = None
                if stat_idx is not None and stat_idx < len(cells):
                    try:
                        stat_val = float(cells[stat_idx].get_text(strip=True))
                    except ValueError:
                        pass

                players.append({
                    'name': pname,
                    'team': team,
                    'value': stat_val,
                })
            except (IndexError, AttributeError):
                continue

        # 排序
        players = [p for p in players if p['value'] is not None]
        players.sort(key=lambda x: x.get('value', 0), reverse=True)
        for i, p in enumerate(players[:top_n], 1):
            p['rank'] = i
        return players[:top_n]

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
        # 截取最多 20 個字元（避免回傳垃圾）
        clean = re.sub(r'\s+', ' ', text).strip()
        return clean[:20] if clean else ''


# ─── 統一介面 ───

def get_next_game(schedule: list[dict]) -> Optional[dict]:
    """從賽程列表中找出最近一場未來比賽，並加上距今倒數"""
    today_iso = date.today().isoformat()
    upcoming = sorted(
        [g for g in schedule if g.get('date', '') >= today_iso],
        key=lambda x: (x.get('date', ''), x.get('time', '')),
    )
    if not upcoming:
        return None
    next_g = dict(upcoming[0])
    try:
        game_dt = datetime.fromisoformat(f"{next_g['date']}T{next_g.get('time', '00:00') or '00:00'}:00")
        now = datetime.now()
        delta = game_dt - now
        total_seconds = int(delta.total_seconds())
        if total_seconds > 0:
            days = total_seconds // 86400
            hours = (total_seconds % 86400) // 3600
            minutes = (total_seconds % 3600) // 60
            if days > 0:
                next_g['countdown'] = f'{days} 天 {hours} 小時後'
            elif hours > 0:
                next_g['countdown'] = f'{hours} 小時 {minutes} 分鐘後'
            else:
                next_g['countdown'] = f'{minutes} 分鐘後'
        else:
            next_g['countdown'] = '即將開始'
    except (ValueError, KeyError):
        pass
    return next_g


def get_head_to_head(games: list[dict], team_a: str, team_b: str) -> dict:
    """計算兩隊歷史對戰紀錄"""
    h2h_games = []
    for g in games:
        home = g.get('home_team', '')
        away = g.get('away_team', '')
        involves_a = team_a in home or team_a in away
        involves_b = team_b in home or team_b in away
        if involves_a and involves_b and g.get('status') == 'completed':
            h2h_games.append(g)

    wins_a = 0
    wins_b = 0
    for g in h2h_games:
        home = g.get('home_team', '')
        away = g.get('away_team', '')
        home_score = _safe_int(g.get('home_score', 0))
        away_score = _safe_int(g.get('away_score', 0))
        if home_score == away_score:
            continue
        winner = home if home_score > away_score else away
        if team_a in winner:
            wins_a += 1
        elif team_b in winner:
            wins_b += 1

    return {
        'team_a': team_a,
        'team_b': team_b,
        'games': len(h2h_games),
        'wins_a': wins_a,
        'wins_b': wins_b,
        'results': h2h_games,
    }


def get_league_api(league: str):
    league = normalize_league(league)
    if league == 'plg':
        return PLGAPI()
    elif league == 'tpbl':
        return TPBLAPI()
    else:
        raise ValueError(f'不支援的聯盟: {league}（支援: plg, tpbl）')
