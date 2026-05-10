"""
台灣籃球維基館 (wikibasketball) API 模組
使用 Camoufox 繞過 Anubis 防護機制
"""

import json
import re
import urllib.parse
from typing import Any

WIKI_BASE = 'https://wikibasketball.dils.tku.edu.tw/wiki/index.php'

# Camoufox venv 路徑（共用 CPBL skill 的 venv）
CAMOUFOX_VENV = '/home/ichen/.openclaw/workspace/skills/cpbl/.venv'


def _get_camoufox():
    """取得 Camoufox 模組（需要 CPBL skill 的 venv）"""
    import sys
    venv_lib = f'{CAMOUFOX_VENV}/lib'
    # 找到正確的 site-packages
    import os
    for d in os.listdir(venv_lib):
        if d.startswith('python3.'):
            site_packages = f'{venv_lib}/{d}/site-packages'
            if os.path.isdir(site_packages) and site_packages not in sys.path:
                sys.path.insert(0, site_packages)
            break
    from camoufox.sync_api import Camoufox
    return Camoufox


def _wiki_url(title: str) -> str:
    """建構維基館 URL"""
    encoded = urllib.parse.quote(title)
    return f'{WIKI_BASE}?title={encoded}'


def _wiki_search_url(query: str) -> str:
    """建構搜尋 URL"""
    encoded = urllib.parse.quote(query)
    return f'{WIKI_BASE}?title=特殊:搜尋&search={encoded}'


def search_player_wiki(name: str) -> list[dict]:
    """搜尋台灣籃球維基館的球員頁面

    Returns:
        list of [{title, url, snippet}]
    """
    Camoufox = _get_camoufox()
    results = []

    with Camoufox(headless=True) as browser:
        page = browser.new_page()
        page.goto(_wiki_search_url(name), timeout=60000)
        page.wait_for_timeout(10000)

        text = page.inner_text('#mw-content-text')
        # 解析搜尋結果
        # 格式：每行一個結果，包含標題和摘要
        lines = text.split('\n')
        current_title = None
        current_snippet = []

        for line in lines:
            line = line.strip()
            if not line:
                continue
            # 搜尋結果通常有 KB 大小標記
            kb_match = re.search(r'\(\d+.*?個字\)', line)
            if kb_match and current_title:
                results.append({
                    'title': current_title,
                    'url': _wiki_url(current_title),
                    'snippet': ' '.join(current_snippet)[:200],
                })
                current_title = None
                current_snippet = []
                continue
            # 第一行通常是標題
            if current_title is None:
                current_title = line
            else:
                current_snippet.append(line)

        # 最後一個結果
        if current_title:
            results.append({
                'title': current_title,
                'url': _wiki_url(current_title),
                'snippet': ' '.join(current_snippet)[:200],
            })

    return results


def get_player_wiki(name: str) -> dict[str, Any]:
    """從台灣籃球維基館抓取球員資料

    Returns:
        dict with keys: name, experience, career_stats, awards, wiki_url
    """
    Camoufox = _get_camoufox()
    result: dict[str, Any] = {
        'name': name,
        'league': 'wiki',
        'experience': [],
        'awards': [],
        'career_stats': {},
        'wiki_url': _wiki_url(name),
    }

    with Camoufox(headless=True) as browser:
        # 先嘗試直接訪問球員頁面
        page = browser.new_page()
        page.goto(_wiki_url(name), timeout=60000)
        page.wait_for_timeout(10000)

        text = page.inner_text('#mw-content-text')

        # 如果頁面不存在，嘗試搜尋
        if '沒有內容' in text or '此頁目前沒有內容' in text:
            page.goto(_wiki_search_url(name), timeout=60000)
            page.wait_for_timeout(10000)
            text = page.inner_text('#mw-content-text')

            # 嘗試找到第一個匹配的結果並訪問
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                if name in line and '個字' not in line:
                    # 嘗試訪問這個頁面
                    try:
                        page.goto(_wiki_url(line), timeout=60000)
                        page.wait_for_timeout(10000)
                        text = page.inner_text('#mw-content-text')
                        result['wiki_url'] = _wiki_url(line)
                        result['name'] = line
                        break
                    except Exception:
                        continue
                    break

        # 解析經歷
        lines = text.split('\n')
        in_experience = False
        for line in lines:
            line = line.strip()
            if line.startswith('經歷') or line == '經歷':
                in_experience = True
                continue
            if in_experience:
                if line.startswith('生涯') or line.startswith('獲') or line.startswith('特殊'):
                    in_experience = False
                    continue
                # 格式：YYYY年 -- 描述 或 YYYY-YYYY -- 描述
                m = re.match(r'(\d{4})(?:-(\d{4}))?\s*年?\s*--\s*(.+)', line)
                if m:
                    start = m.group(1)
                    end = m.group(2) or m.group(1)
                    desc = m.group(3).strip()
                    result['experience'].append({
                        'period': f'{start}-{end}' if end != start else start,
                        'description': desc,
                    })

        # 解析獎項
        in_awards = False
        for line in lines:
            line = line.strip()
            if '年度' in line and ('最有價值' in line or '最佳' in line or '王' in line or '獎' in line):
                in_awards = True
            if in_awards:
                if '——' in line or '--' in line:
                    result['awards'].append(line)
                elif re.match(r'\d{4}年', line):
                    result['awards'].append(line)

        # 解析生涯成績表格
        in_stats = False
        current_league = ''
        for line in lines:
            line = line.strip()
            if '例行賽' in line and ('P. LEAGUE' in line or 'TPBL' in line or 'SBL' in line or 'T1' in line):
                current_league = line.strip('：:').strip()
                in_stats = True
                result['career_stats'][current_league] = []
                continue
            if in_stats and line.startswith('年度'):
                continue  # header
            if in_stats and line.startswith('總計'):
                in_stats = False
                continue
            if in_stats and '\t' in line:
                # 資料行
                parts = line.split('\t')
                if len(parts) >= 5:
                    result['career_stats'][current_league].append({
                        'season': parts[0],
                        'team': parts[1] if len(parts) > 1 else '',
                        'number': parts[2] if len(parts) > 2 else '',
                        'gp': parts[3] if len(parts) > 3 else '',
                    })
            if in_stats and line == '' or '編輯' in line:
                in_stats = False

    return result


if __name__ == '__main__':
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else '高柏鎧'
    data = get_player_wiki(name)
    print(json.dumps(data, ensure_ascii=False, indent=2))