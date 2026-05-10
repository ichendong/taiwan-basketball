# Release Notes

## v1.3.0 (2026-05-11)

### 🆕 新功能

- **賽制過濾（Stage Filter）**
  - 新增 `--stage` 參數：`regular`/`playoffs`/`play-in`/`finals`/`preseason`
  - TPBL：`division_id` 判斷（8=熱身賽、9=例行賽、11=季後挑戰賽、12=季後賽）
  - PLG：從不同 URL 抓取各賽制頁面
  - 中文化顯示

- **球員每季效力球隊**
  - PLG 球員不再永遠顯示現役球隊
  - 三層判斷：Preciser API → 經歷區塊 → 頁面基本資料
  - 球隊名正規化：移除「籃球隊」後綴和英文名

- **球員別名搜尋**
  - 歸化改名：高柏鎧↔吉爾貝克
  - 跨聯盟譯名：Gilbeck/Brandon Gilbeck → 對應正式名
  - 雙向別名：搜 PLG 別名能找到 TPBL 名，反之亦然

- **台灣籃球維基館整合**
  - Camoufox 繞過 Anubis 防護存取 `wikibasketball.dils.tku.edu.tw`
  - 球員跨聯盟經歷（PLG/T1/TPBL/NBA/CBA）
  - T1 聯盟歷史數據（已消失聯盟）
  - 球員獎項紀錄、歸化資訊、球隊更名歷史
  - 本土球員為主，洋將覆蓋較少

### 🐛 修復

- PLG 球員頁面「球隊」欄位永遠顯示現役球隊 → 現在正確顯示每季效力球隊
- 經歷區塊支援年份格式（如林書豪 `2023 PLG 高雄鋼鐵人`）
- 經歷推算只使用同聯盟條目（避免 CBA/NBA 干擾 PLG 球隊判斷）
- 球員名字從頁面標題正確提取（移除「- 球隊名籃球隊」後綴）
- TPBL 每季數據補上 `team` 欄位

### 📝 文件更新

- SKILL.md 改用中文撰寫，完整記錄所有功能與使用方式
- 新增 CHANGELOG.md 記錄版本變更