# 台灣職籃 🏀

OpenClaw Agent Skill — 台灣職業籃球資訊查詢，支援 PLG（P. LEAGUE+）與 TPBL（台灣職業籃球大聯盟）。

## 版本

v1.3.0

## 完整文件

詳見 [SKILL.md](SKILL.md)， [CHANGELOG.md](CHANGELOG.md)。

## 功能總覽

| 功能 | 說明 |
|------|------|
| 賽程查詢 | PLG / TPBL 賽程、倒數計時、球隊篩選 |
| 比賽結果 | 最近比賽結果、球隊篩選 |
| 戰績排行 | PLG / TPBL 排名 |
| 球員數據 | 歷年數據、每季效力球隊、別名搜尋 |
| 排行榜 | 得分王、籃板王、助攻王等 |
| 球員比較 | 兩位球員對比 |
| 即時比分 | 進行中的比賽分數 |
| Box Score | 單場詳細球員數據 |
| 比賽提醒 | 訂閱球隊、自動通知 |
| 球員異動 | 交易、簽約、轉隊 |
| 賽制過濾 ✨ | 例行賽、季後賽、季後挑戰賽、總冠軍賽、熱身賽 |
| 維基館查詢 ✨ | 台灣籃球維基館歷史資料（跨聯盟經歷、獎項、T1 數據） |

## 快速開始

所有腳本使用 `uv run` 執行：

```bash
# 雙聯盟賽程（並行查詢）
uv run scripts/basketball_schedule.py --league all

# 戰績排行
uv run scripts/basketball_standings.py --league plg
uv run scripts/basketball_standings.py --league tpbl

# 最近比賽結果
uv run scripts/basketball_games.py --league all --last 5

# 球員數據（支援別名：高柏鎧↔吉爾貎克）
uv run scripts/basketball_player.py --league all --player 高柏鎧
uv run scripts/basketball_player.py --league plg --player 飛米

# 季後賽賽程
uv run scripts/basketball_schedule.py --league all --stage playoffs

# 即時比分
uv run scripts/basketball_live.py --league all

# Box Score
uv run scripts/basketball_boxscore.py --league tpbl --game-id 123

# 比賽提醒
uv run scripts/basketball_notify.py add --team 戰神 --league tpbl
uv run scripts/basketball_notify.py check --hours 24

# 球員異動
uv run scripts/basketball_transactions.py --league all
```

## v1.3.0 更新重點

- 🏀 **賽制過濾**：`--stage playoffs` / `--stage play-in` 等，支援例行賽到總冠軍賽
- 🏀 **球員每季球隊**：飛米在鋼鐵人不再顯示成富邦勇士，三層判斷機制（Preciser API → 經歷 → 頁面）
- 🏀 **球員別名**：搜「高柏鎧」能找到 PLG 的「吉爾貝克」，雙向解析
- 🏀 **維基館整合**：Camoufox 繞過 Anubis，抓取跨聯盟經歷、T1 歷史、獎項紀錄
- 🐛 **球隊名正規化**：統一移除「籃球隊」後綴和英文名
- 🐛 **經歷年份格式**：支援 `2023` 只有年份的格式（如林書豪）

## 資料來源

| 來源 | 說明 |
|------|------|
| PLG 官網 | HTML 爬蟲 |
| TPBL 官方 API | REST API |
| 台灣籃球維基館 | Camoufox 繞過 Anubis |
| 本地 SQLite | `~/.local/share/taiwan-basketball/basketball.db` |

## 授權

MIT