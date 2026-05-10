"""
台灣籃球維基館 (wikibasketball) API 模組
使用 Camoufox 繞過 Anubis 防護機制

主要用途：
1. 球員經歷（跨聯盟球隊歷史）
2. 球員獎項紀錄
3. T1 聯盟歷史數據（已消失聯盟）
4. 本土球員詳細資料

洋將可能不在維基館，以本土球員為主。
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
    import os
    venv_lib = f'{CAMOUFOX_VENV}/lib'
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


def _parse_experience(dl_element) -> list[dict]:
    """解析經歷區塊的 <dl><dd><ul><li> 結構

    格式：聯盟球隊（年份～年份）或 聯盟球隊A→球隊B（年份～）
    """
    results = []
    if not dl_element:
        return results

    for li in dl_element.find_all('li'):
        text = li.get_text(strip=True)
        if not text:
            continue

        org_team = ''
        start_year = 0
        end_year = 0

        # 格式1：聯盟+球隊（YYYY年～YYYY年）
        m = re.match(r'(.+?)（(\d{4})年～(\d{4})年）', text)
        if m:
            org_team = m.group(1).strip()
            start_year = int(m.group(2))
            end_year = int(m.group(3))
        else:
            # 格式2：聯盟+球隊（YYYY年）只有一年
            m = re.match(r'(.+?)（(\d{4})年）', text)
            if m:
                org_team = m.group(1).strip()
                start_year = int(m.group(2))
                end_year = start_year
            else:
                # 格式3：聯盟+球隊（YYYY年～）無結束年份，代表仍在效力
                m = re.match(r'(.+?)（(\d{4})年～）', text)
                if m:
                    org_team = m.group(1).strip()
                    start_year = int(m.group(2))
                    end_year = start_year  # 仍在效力
                else:
                    continue

        # 分離聯盟和球隊
        league_prefixes = [
            'P. LEAGUE+', '台灣職業籃球大聯盟', 'T1聯盟',
            '超級籃球聯賽', 'NBA', 'NCAA', 'CBA',
            '東亞超級聯賽', '丹麥籃球聯賽', '義大利籃球乙級聯賽',
            '加拿大精英籃球聯賽', '美國職籃發展聯盟', '美國職籃',
            '亞洲俱樂部冠軍聯賽',
        ]

        league = ''
        team = org_team
        for prefix in sorted(league_prefixes, key=len, reverse=True):
            if org_team.startswith(prefix):
                league = prefix
                team = org_team[len(prefix):].strip()
                break

        # 處理球隊更名：A→B
        teams = [t.strip() for t in team.split('→')] if '→' in team else [team]

        results.append({
            'league': league,
            'team': team,
            'teams': teams,
            'start_year': start_year,
            'end_year': end_year,
            'raw': text,
        })

    return results


def _parse_awards(content_div) -> list[str]:
    """解析特殊事蹟/獎項"""
    awards = []

    # 找「特殊事蹟」h2
    for heading in content_div.find_all('h2'):
        span = heading.find('span', class_='mw-headline')
        if span and ('特殊事蹟' in span.get_text() or '獎項' in span.get_text()):
            dl = heading.find_next_sibling('dl')
            if dl:
                for dd in dl.find_all('dd'):
                    text = dd.get_text(strip=True)
                    if text and ('年度' in text or '王' in text or '獎' in text or '最佳' in text or '入選' in text):
                        awards.append(text)
            break

    return awards


def get_player_wiki(name: str) -> dict[str, Any]:
    """從台灣籃球維基館抓取球員資料

    Returns:
        dict with keys: name, found, experience, awards, wiki_url
    """
    Camoufox = _get_camoufox()
    result: dict[str, Any] = {
        'name': name,
        'found': False,
        'experience': [],
        'awards': [],
        'wiki_url': _wiki_url(name),
        'league': 'wiki',
    }

    with Camoufox(headless=True) as browser:
        page = browser.new_page()

        # 嘗試直接訪問球員頁面
        page.goto(_wiki_url(name), timeout=60000)
        page.wait_for_timeout(10000)

        content_div = page.query_selector('#mw-content-text')
        if not content_div:
            browser.close()
            return result

        text = content_div.inner_text()

        # 如果頁面不存在，嘗試搜尋
        if '沒有內容' in text or '此頁目前沒有內容' in text:
            page.goto(
                f'{WIKI_BASE}?title=特殊:搜尋&search={urllib.parse.quote(name)}',
                timeout=60000,
            )
            page.wait_for_timeout(10000)
            text = content_div.inner_text()

            # 嘗試找到匹配的結果
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(page.content(), 'lxml')

            # 搜尋結果中的連結
            for link in soup.find_all('a', href=True):
                href = link['href']
                title_text = link.get_text(strip=True)
                if name in title_text and '/wiki/' in href:
                    # 找到匹配的頁面，重新訪問
                    full_url = f'https://wikibasketball.dils.tku.edu.tw{href}' if href.startswith('/') else href
                    page.goto(full_url, timeout=60000)
                    page.wait_for_timeout(10000)
                    content_div = page.query_selector('#mw-content-text')
                    text = content_div.inner_text()
                    result['wiki_url'] = full_url
                    result['name'] = title_text
                    break
            else:
                browser.close()
                return result

        result['found'] = True

        # 用 BeautifulSoup 解析 HTML
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(page.content(), 'lxml')
        content = soup.find('div', id='mw-content-text')

        # 1. 解析經歷
        for heading in content.find_all('h2'):
            span = heading.find('span', class_='mw-headline')
            if span and '經歷' in span.get_text() and '籃球' not in span.get_text():
                dl = heading.find_next_sibling('dl')
                if dl:
                    result['experience'] = _parse_experience(dl)
                break

        # 2. 解析獎項
        result['awards'] = _parse_awards(content)

        browser.close()

    return result


def search_player_wiki(name: str, limit: int = 10) -> list[dict]:
    """搜尋台灣籃球維基館的球員頁面

    Returns:
        list of [{title, url, snippet}]
    """
    Camoufox = _get_camoufox()
    results = []

    with Camoufox(headless=True) as browser:
        page = browser.new_page()
        page.goto(
            f'{WIKI_BASE}?title=特殊:搜尋&search={urllib.parse.quote(name)}',
            timeout=60000,
        )
        page.wait_for_timeout(10000)

        from bs4 import BeautifulSoup
        soup = BeautifulSoup(page.content(), 'lxml')
        content = soup.find('div', class_='searchresults')

        if not content:
            # 嘗試另一種結構
            content = soup.find('div', id='mw-content-text')

        if content:
            for link in content.find_all('a', href=True):
                href = link['href']
                title = link.get_text(strip=True)
                if '/wiki/' in href and title and name in title:
                    full_url = f'https://wikibasketball.dils.tku.edu.tw{href}' if href.startswith('/') else href
                    snippet = ''
                    # 找摘要
                    parent = link.find_parent('div')
                    if parent:
                        snippet = parent.get_text(strip=True)[:200]
                    results.append({
                        'title': title,
                        'url': full_url,
                        'snippet': snippet,
                    })
                    if len(results) >= limit:
                        break

        browser.close()

    return results


if __name__ == '__main__':
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else '高柏鎧'
    data = get_player_wiki(name)
    print(json.dumps(data, ensure_ascii=False, indent=2))