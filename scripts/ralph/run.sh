#!/bin/bash
# Autonomous Coder - OpenClaw 版 Ralph
# 用法: ./run.sh [max_iterations] [project_path]

set -e

MAX_ITERATIONS=${1:-20}
PROJECT_PATH=${2:-$(pwd)}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TASKS_FILE="$SCRIPT_DIR/tasks.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.md"
PROMPT_FILE="$SCRIPT_DIR/prompt.md"

echo "🦾 Autonomous Coder 啟動"
echo "專案路徑: $PROJECT_PATH"
echo "任務清單: $TASKS_FILE"
echo "最大迭代: $MAX_ITERATIONS"
echo ""

# 檢查必要檔案
if [ ! -f "$TASKS_FILE" ]; then
    echo "❌ 找不到 tasks.json，請先建立任務清單"
    exit 1
fi

if [ ! -f "$PROGRESS_FILE" ]; then
    echo "# Progress Log" > "$PROGRESS_FILE"
    echo "" >> "$PROGRESS_FILE"
    echo "Started: $(date '+%Y-%m-%d %H:%M')" >> "$PROGRESS_FILE"
    echo "" >> "$PROGRESS_FILE"
    echo "## Codebase Patterns" >> "$PROGRESS_FILE"
    echo "" >> "$PROGRESS_FILE"
    echo "建立 progress.md"
fi

# 主循環
for i in $(seq 1 $MAX_ITERATIONS); do
    echo "═══════════════════════════════════════"
    echo "迭代 $i / $MAX_ITERATIONS"
    echo "═══════════════════════════════════════"
    
    # 檢查是否還有待處理任務
    PENDING_COUNT=$(jq '[.tasks[] | select(.status == "pending")] | length' "$TASKS_FILE" 2>/dev/null || echo "0")
    
    if [ "$PENDING_COUNT" -eq 0 ]; then
        echo ""
        echo "✅ 所有任務完成！"
        echo "<ralph>COMPLETE</ralph>"
        exit 0
    fi
    
    # 檢查是否全部卡住
    BLOCKED_COUNT=$(jq '[.tasks[] | select(.status == "blocked")] | length' "$TASKS_FILE" 2>/dev/null || echo "0")
    TOTAL_COUNT=$(jq '.tasks | length' "$TASKS_FILE" 2>/dev/null || echo "0")
    
    if [ "$BLOCKED_COUNT" -ge "$TOTAL_COUNT" ]; then
        echo ""
        echo "⚠️ 所有任務都被卡住了！"
        echo "<ralph>STUCK</ralph>"
        exit 2
    fi
    
    # 讀取 prompt 模板並替換變數
    if [ -f "$PROMPT_FILE" ]; then
        PROMPT=$(cat "$PROMPT_FILE" | \
            sed "s|{{TASKS_FILE}}|$TASKS_FILE|g" | \
            sed "s|{{PROGRESS_FILE}}|$PROGRESS_FILE|g" | \
            sed "s|{{PROJECT_PATH}}|$PROJECT_PATH|g")
    else
        # 使用內建 prompt
        PROMPT="你是 Autonomous Coder，一個自主編碼 agent。

你的任務：
1. 讀取 $TASKS_FILE 找下一個 status='pending' 的 task
2. 讀取 $PROGRESS_FILE 了解專案模式
3. 實作該 task（只做一個）
4. 跑 typecheck 和 tests
5. 成功則 commit：'feat: [TASK-ID] - Title'
6. 更新 tasks.json 的 status 為 'done'
7. 追加學習到 progress.md

失敗處理：
- 失敗 3 次 → 標記 status='blocked'，跳到下一個
- 全部卡住 → 輸出 <ralph>STUCK</ralph>

完成條件：
- 全部完成 → 輸出 <ralph>COMPLETE</ralph>"
    fi
    
    echo "任務狀態：$PENDING_COUNT 個待處理，$BLOCKED_COUNT 個卡住"
    echo ""
    
    # 這裡可以用 sessions_spawn 或直接呼叫 openclaw
    # 目前先輸出 prompt 讓用戶手動執行
    echo "--- PROMPT START ---"
    echo "$PROMPT"
    echo "--- PROMPT END ---"
    echo ""
    
    # TODO: 自動執行
    # openclaw spawn --agent codeney --message "$PROMPT" --cwd "$PROJECT_PATH"
    
    sleep 2
done

echo ""
echo "達到最大迭代次數 $MAX_ITERATIONS"
exit 1
