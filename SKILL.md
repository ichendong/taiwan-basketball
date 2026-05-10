# 台灣職籃資訊查詢 🏀

查詢 PLG（P. LEAGUE+）和 TPBL（台灣職業籃球大聯盟）的賽程、戰績、球員數據、排行榜、即時比分、Box Score、比賽提醒、球員異動，以及台灣籃球維基館的歷史資料。

## 資料來源

| 來源 | 說明 |
|------|------|
| PLG 官網 | HTML 爬蟲（伺服器端渲染） |
| TPBL 官方 API | `api.tpbl.basketball` REST API |
| 台灣籃球維基館 | Camoufox 繞過 Anubis 防護 |
| 本地 SQLite | `~/.local/share/taiwan-basketball/basketball.db` |

## 功能一覽

| 功能 | 腳本 | 來源 |
|------|------|------|
| 賽程（含倒數） | `basketball_schedule.py` | PLG / TPBL |
| 戰績排行 | `basketball_standings.py` | PLG / TPBL |
| 比賽結果 | `basketball_games.py` | PLG / TPBL |
| 球員數據 | `basketball_player.py` | PLG / TPBL |
| 排行榜 | `basketball_leaders.py` | PLG / TPBL |
| 球員比較 | `basketball_compare.py` | PLG / TPBL |
| 即時比分 ✨ | `basketball_live.py` | TPBL API / PLG 估算 |
| Box Score ✨ | `basketball_boxscore.py` | TPBL API / PLG 爬蟲 |
| 比賽提醒 ✨ | `basketball_notify.py` | PLG / TPBL |
| 球員異動 ✨ | `basketball_transactions.py` | PLG 新聞 / TPBL API |
| 維基館查詢 ✨ | `_wiki_api.py` | 台灣籃球維基館 |

## 快速開始

所有腳本使用 `uv run` 執行。

### 賽程

```bash
uv run scripts/basketball_schedule.py --league plg          # PLG 賽程
uv run scripts/basketball_schedule.py --league all           # 雙聯盟合併查詢
uv run scripts/basketball_schedule.py -l plg --team 勇士     # 球隊篩選
uv run scripts/basketball_schedule.py -l all --next          # 下一場比賽倒數
uv run scripts/basketball_schedule.py -l all --stage playoffs # 只看季後賽
```

### 比賽結果

```bash
uv run scripts/basketball_games.py --league all              # 雙聯盟結果
uv run scripts/basketball_games.py --league all --last 5     # 最近 5 場
uv run scripts/basketball_games.py -l tpbl --team 戰神       # 球隊篩選
uv run scripts/basketball_games.py -l tpbl --stage play-in   # 季後挑戰賽
```

### 球員數據

```bash
uv run scripts/basketball_player.py --league plg --player 林書豪
uv run scripts/basketball_player.py --league tpbl --player 高柏鎧   # 支援別名搜尋
uv run scripts/basketball_player.py --league all --player 吉爾貝克   # 別名：高柏鎧
uv run scripts/basketball_player.py -l plg -p 林書豪 --season 2023-24
```

**球員別名**：歸化改名、跨聯盟不同譯名都支援。例如「高柏鎧」在 PLG 叫「吉爾貝克」，搜任一個都能找到。

### 排行榜

```bash
uv run scripts/basketball_leaders.py --league plg --stat pts     # PLG 得分王
uv run scripts/basketball_leaders.py --league tpbl --stat reb    # TPBL 籃板王
uv run scripts/basketball_leaders.py -l all -s blk --top 5       # 雙聯盟阻攻前5
```

支援 `pts`（得分）、`reb`（籃板）、`ast`（助攻）、`stl`（抄截）、`blk`（阻攻）、`tov`（失誤）、`pf`（犯規）、`eff`（效率值，TPBL 限定）

### 即時比分

```bash
uv run scripts/basketball_live.py --league all              # 所有進行中比賽
uv run scripts/basketball_live.py --league tpbl --format table
```

- **TPBL**：API 直接回傳 `IN_PROGRESS` 狀態
- **PLG**：依賽程時間 ±3 小時估算，建議前往 `pleagueofficial.com` 查看即時比分

### Box Score（單場詳情）

```bash
uv run scripts/basketball_games.py --league tpbl --last 5 --format table  # 先取 game_id
uv run scripts/basketball_boxscore.py --league tpbl --game-id 123
uv run scripts/basketball_boxscore.py --league plg --game-id G101
```

### 比賽提醒

```bash
uv run scripts/basketball_notify.py add --team 戰神 --league tpbl
uv run scripts/basketball_notify.py list
uv run scripts/basketball_notify.py check                    # 未來 24 小時
uv run scripts/basketball_notify.py check --hours 48         # 未來 48 小時
uv run scripts/basketball_notify.py remove --team 戰神 --league tpbl
```

### 球員異動

```bash
uv run scripts/basketball_transactions.py --league all
uv run scripts/basketball_transactions.py --league tpbl --format table
uv run scripts/basketball_transactions.py --league all --from-db  # 從本地 DB 讀取
```

## 球員每季效力球隊

PLG 官方頁面只顯示「現役球隊」，我們用三層機制正確判斷每季效力球隊：

1. **Preciser API**（主來源）— 從球員頁面的逐場數據 API 抓「效力球隊」欄位
2. **經歷區塊**（fallback）— 解析球員頁面的「經歷」區塊，用期間推算每季球隊
3. **頁面基本資料**（最後手段）— 永遠顯示現役球隊，最不準

**範例**：飛米 2022-23 在鋼鐵人，2025-26 在富邦勇士，三層機制都能正確顯示。

**球隊名正規化**：統一移除「籃球隊」後綴和英文名，確保不同來源的球隊名一致（如「高雄17直播鋼鐵人」而非「高雄17直播鋼鐵人籃球隊」）。

## 賽制（Stage）過濾

| Stage | 說明 |
|-------|------|
| `regular` | 例行賽 |
| `play-in` | 季後挑戰賽（TPBL）|
| `playoffs` | 季後賽（TPBL 此階段即總冠軍賽）|
| `finals` | 總冠軍賽（PLG 專有）|
| `preseason` | 熱身賽 |

TPBL 的 `playoffs` 就是總冠軍賽（沒有分半決賽和總冠軍兩個階段），PLG 才有分 `playoffs` 和 `finals`。

## 球隊別名

### PLG
| 別名 | 正式名稱 |
|------|----------|
| 富邦、勇士 | 臺北富邦勇士 |
| 璞園、領航猿 | 桃園璞園領航猿 |
| 台鋼、獵鷹 | 台鋼獵鷹 |
| 洋基、洋基工程 | 洋基工程 |

### TPBL
| 別名 | 正式名稱 |
|------|----------|
| 台新、戰神 | 臺北台新戰神 |
| 中信、特攻 | 新北中信特攻 |
| 國王 | 新北國王 |
| 雲豹 | 桃園台啤永豐雲豹 |
| 夢想家 | 福爾摩沙夢想家 |
| 攻城獅 | 新竹御嵿攻城獅 |
| 海神 | 高雄全家海神 |

## 球員別名

歸化改名、跨聯盟不同譯名都支援，搜尋時自動展開：

| 別名 | 聯盟 | 正式名 |
|------|------|--------|
| 高柏鎧 | PLG | 吉爾貝克 |
| 吉爾貝克 | TPBL | 高柏鎧 |
| Gilbeck | PLG/TPBL | 對應正式名 |
| 飛米 | PLG | 飛米 |
| 霍華德 | PLG | 魔獸 |
| 戴維斯 | PLG | 戴維斯 |

## 台灣籃球維基館

台灣籃球維基館（`wikibasketball.dils.tku.edu.tw`）有 Anubis 防護，`web_fetch` 和 Playwright 無法存取，**使用 Camoufox 可以正常讀取**。

### 什麼時候需要查維基館

- ✅ 球員**跨聯盟經歷**（PLG → T1 → TPBL 完整球隊歷史）
- ✅ **T1 聯盟**歷史數據（已消失的聯盟，官方 API 沒有）
- ✅ 球員**獎項紀錄**（MVP、阻攻王、年度陣容等）
- ✅ **歸化資訊**、生涯轉隊經歷
- ❌ 洋將通常不在維基館（以本土球員為主）

### 查詢方式

使用 CPBL skill 的 Camoufox venv（`skills/cpbl/.venv`），不要用 `web_fetch` 或 Playwright。

```python
from camoufox.sync_api import Camoufox
with Camoufox(headless=True) as browser:
    page = browser.new_page()
    page.goto('https://wikibasketball.dils.tku.edu.tw/wiki/index.php?title=林書豪', timeout=60000)
    page.wait_for_timeout(10000)
    text = page.inner_text('#mw-content-text')
```

### 限制

- Camoufox 啟動較慢（10-15 秒），不適合頻繁查詢
- 洋將（飛米、魔獸等）可能沒有維基館頁面
- 經歷格式多樣，解析仍在持續改進中

## CLI 參數

| 腳本 | 參數 | 說明 |
|------|------|------|
| 全部 | `--league`, `-l` | `plg`、`tpbl` 或 `all` |
| 全部 | `--format`, `-f` | `json`（預設）或 `table` |
| 全部 | `--no-cache` | 停用磁碟快取 |
| 全部 | `--debug` | 輸出 debug 訊息 |
| 賽程/結果 | `--team`, `-t` | 球隊名稱篩選（支援別名） |
| 賽程 | `--next` | 只顯示下一場比賽及倒數 |
| 結果 | `--last`, `-n` | 只顯示最近 N 場 |
| 球員 | `--player`, `-p` | 球員名稱（支援別名） |
| 球員 | `--season`, `-s` | 賽季篩選（如 `2023-24`） |
| 排行榜 | `--stat`, `-s` | 數據類別（pts/reb/ast/stl/blk/tov/pf/eff） |
| 排行榜 | `--top`, `-n` | 顯示前 N 名（預設 10） |
| 比較 | `--player1`, `-p1` | 第一位球員 |
| 比較 | `--player2`, `-p2` | 第二位球員 |
| 比較 | `--season`, `-s` | 比較特定賽季（預設：生涯） |
| Box Score | `--game-id`, `-g` | 比賽 ID |
| 賽程/結果 | `--stage`, `-s` | 賽制過濾：regular/playoffs/play-in/finals/preseason |
| 提醒 | `--team`, `-t` | 指定球隊 |
| 提醒 | `--hours` | 查詢未來幾小時（預設 24） |
| 異動 | `--from-db` | 從本地 DB 讀取 |
| 異動 | `--limit`, `-n` | 最多顯示筆數（預設 30） |

## 快取

結果快取在 `~/.cache/taiwan-basketball/`，TTL 如下：

| 資料類型 | TTL |
|----------|-----|
| 賽程 | 5 分鐘 |
| 比賽結果 | 10 分鐘 |
| 戰績 | 10 分鐘 |
| 球員數據 | 1 小時 |
| 排行榜 | 10 分鐘 |
| 即時比分 | 1 分鐘 |
| Box Score | 5 分鐘 |
| 異動 | 1 小時 |

使用 `--no-cache` 停用快取，或設 `BASKETBALL_DEBUG=1` 查看快取命中。

## 聯盟代碼

| 代碼 | 聯盟 |
|------|------|
| `plg` | P. LEAGUE+（4 隊）|
| `tpbl` | 台灣職業籃球大聯盟（7 隊）|

## 依賴

透過 `uv run` 自動安裝：
- `beautifulsoup4` — HTML 解析
- `lxml` — 快速解析器
- `sqlite3` — Python 內建模組

## 注意事項

- **PLG**：伺服器端渲染 HTML，不需 JS。球員頁面使用 Preciser API 載入逐場數據，經歷區塊提供每季球隊資訊。
- **TPBL**：官方 REST API，球員數據透過 `/games/stats/players?division_id={id}` 取得所有賽季資料，FG%/3P%/FT% 從累計命中/投球數重新計算。
- **球隊名正規化**：統一移除「籃球隊」後綴和英文名，確保不同來源的球隊名一致。
- **球員別名**：支援歸化改名（高柏鎧↔吉爾貝克）和跨聯盟譯名搜尋。
- **賽制過濾**：TPBL 的 `playoffs` 就是總冠軍賽；PLG 才有分 `playoffs` 和 `finals`。
- **並行擷取**：`--league all` 查詢使用 `ThreadPoolExecutor` 並行發送 PLG/TPBL 請求。
- **SBL**（超級籃球聯賽）不支援 — 官方站是 Vue SPA + GraphQL API。
- **即時比分**：TPBL API 原生支援 `IN_PROGRESS`；PLG 依賴時間視窗估算（±3 小時）。
- `avg_minutes` 統一輸出為 `MM:SS` 格式。

## CHANGELOG

### v1.3.0 (2026-05-11)

**新功能**

- 🏀 **賽制過濾**：`--stage` 參數支援 `regular`/`playoffs`/`play-in`/`finals`/`preseason`
  - TPBL：用 `division_id` 判斷（8=熱身賽、9=例行賽、11=季後挑戰賽、12=季後賽）
  - PLG：從不同 URL 抓取不同賽制頁面
  - 中文化顯示：例行賽、季後賽、季後挑戰賽、總冠軍賽、熱身賽

- 🏀 **球員每季效力球隊**：PLG 球員現在能正確顯示每季效力的球隊（不再永遠顯示現役球隊）
  - 三層判斷機制：Preciser API（主）→ 經歷區塊（fallback）→ 頁面基本資料（最後手段）
  - 球隊名正規化：移除「籃球隊」後綴和英文名

- 🏀 **球員別名搜尋**：支援歸化改名和跨聯盟譯名
  - 別名對照表：高柏鎧↔吉爾貝克、飛米↔Flymy/Ironmy 等
  - PLG 和 TPBL 雙向別名解析

- 🏀 **台灣籃球維基館整合**：透過 Camoufox 繞過 Anubis 防護
  - 球員跨聯盟經歷（PLG/T1/TPBL/NBA/CBA 完整球隊歷史）
  - T1 聯盟歷史數據（已消失聯盟）
  - 球員獎項紀錄（MVP、阻攻王、年度陣容等）
  - 歸化資訊、球隊更名歷史

**修復**

- PLG 球員頁面的「球隊」欄位永遠顯示現役球隊 → 現在正確顯示每季效力球隊
- 經歷區塊支援年份格式（`2023` 只有年份沒有範圍，如林書豪的 `2023 PLG 高雄鋼鐵人`）
- 經歷推算只使用同聯盟的條目（避免 CBA/NBA 經歷干擾 PLG 球隊判斷）
- 球員名字從頁面標題正確提取（移除「- 球隊名籃球隊」後綴）
- TPBL 每季數據補上 `team` 欄位