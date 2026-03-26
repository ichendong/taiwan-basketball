#!/bin/bash
# Autonomous Coder - 自動執行版（透過 OpenClaw）
# 用法: ./run-auto.sh [max_iterations] [project_path] [agent_id]

set -e

MAX_ITERATIONS=${1:-20}
PROJECT_PATH=${2:-$(pwd)}
AGENT_ID=${3:-codeney}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TASKS_FILE="$SCRIPT_DIR/tasks.json"
PROGRESS_FILE="$SCRIPT_DIR/progress.md"
PROMPT_FILE="$SCRIPT_DIR/prompt.md"

echo "🦾 Autonomous Coder (Auto) 啟動"
echo "專案路徑: $PROJECT_PATH"
echo "Agent: $AGENT_ID"
echo "最大迭代: $MAX_ITERATIONS"
echo ""

# 檢查 OpenClaw CLI
if ! command -v openclaw &> /dev/null; then
    echo "❌ 找不到 openclaw CLI"
    echo "請先安裝：npm install -g openclaw"
    exit 1
fi

# 檢查 jq
if ! command -v jq &> /dev/null; then
    echo "❌ 找不到 jq"
    echo "請先安裝：sudo apt install jq"
    exit 1
fi

# 檢查必要檔案
if [ ! -f "$TASKS_FILE" ]; then
    echo "❌ 找不到 tasks.json"
    exit 1
fi

if [ ! -f "$PROGRESS_FILE" ]; then
    echo "# Progress Log" > "$PROGRESS_FILE"
    echo "" >> "$PROGRESS_FILE"
    echo "Started: $(date '+%Y-%m-%d %H:%M')" >> "$PROGRESS_FILE"
fi

# 主循環
for i in $(seq 1 $MAX_ITERATIONS); do
    ITERATION_START=$(date +%s)
    
    echo ""
    echo "═══════════════════════════════════════"
    echo "🔄 迭代 $i / $MAX_ITERATIONS"
    echo "═══════════════════════════════════════"
    
    # 檢查待處理任務
    PENDING=$(jq '[.tasks[] | select(.status == "pending")] | length' "$TASKS_FILE")
    BLOCKED=$(jq '[.tasks[] | select(.status == "blocked")] | length' "$TASKS_FILE")
    DONE=$(jq '[.tasks[] | select(.status == "done")] | length' "$TASKS_FILE")
    TOTAL=$(jq '.tasks | length' "$TASKS_FILE")
    
    echo "📊 狀態：$DONE/$TOTAL 完成，$PENDING 待處理，$BLOCKED 卡住"
    
    if [ "$PENDING" -eq 0 ]; then
        echo ""
        echo "✅ 所有任務完成！"
        
        # 通知
        openclaw notify --agent "$AGENT_ID" --message "🦾 Autonomous Coder 完成！$DONE 個任務全部完成。" 2>/dev/null || true
        
        echo "<ralph>COMPLETE</ralph>"
        exit 0
    fi
    
    if [ "$BLOCKED" -ge "$TOTAL" ]; then
        echo ""
        echo "⚠️ 所有任務都被卡住了！"
        openclaw notify --agent "$AGENT_ID" --message "⚠️ Autonomous Coder 卡住了！所有 $TOTAL 個任務都被 block。" 2>/dev/null || true
        echo "<ralph>STUCK</ralph>"
        exit 2
    fi
    
    # 取得下一個任務
    NEXT_TASK=$(jq '.tasks[] | select(.status == "pending") | sort_by(.priority) | .[0]' "$TASKS_FILE" 2>/dev/null || echo "")
    TASK_ID=$(echo "$NEXT_TASK" | jq -r '.id' 2>/dev/null || echo "")
    TASK_TITLE=$(echo "$NEXT_TASK" | jq -r '.title' 2>/dev/null || echo "")
    
    if [ -z "$TASK_ID" ] || [ "$TASK_ID" = "null" ]; then
        echo "❌ 無法取得下一個任務"
        exit 1
    fi
    
    echo "🎯 執行任務：$TASK_ID - $TASK_TITLE"
    
    # 建立 prompt
    PROMPT="你是 Autonomous Coder，正在執行迭代 $i。

## 當前任務
- ID: $TASK_ID
- 標題: $TASK_TITLE
- 準則: $(echo "$NEXT_TASK" | jq -r '.criteria | join(", ")')

## 你的工作
1. 讀取專案現有結構
2. 實作該任務（只做這一個）
3. 執行 typecheck 和 tests
4. 成功 → git commit
5. 更新 $TASKS_FILE 標記 status='done'
6. 追加學習到 $PROGRESS_FILE

## 專案資訊
- 路徑: $PROJECT_PATH
- 任務清單: $TASKS_FILE
- 進度記錄: $PROGRESS_FILE

## 重要
- 一次只做一個任務
- 失敗就標記 failedAttempts++
- 失敗 3 次標記 status='blocked'"

    # 執行
    echo "🚀 啟動 sub-agent..."
    
    # 使用 sessions_spawn（如果可用）
    if openclaw spawn --help &> /dev/null; then
        openclaw spawn \
            --agent "$AGENT_ID" \
            --message "$PROMPT" \
            --cwd "$PROJECT_PATH" \
            --timeout 300000 \
            2>&1 | tee "/tmp/ralph-iteration-$i.log"
    else
        # Fallback: 直接呼叫
        echo "$PROMPT"
        echo ""
        echo "--- 請手動執行上述 prompt ---"
    fi
    
    ITERATION_END=$(date +%s)
    DURATION=$((ITERATION_END - ITERATION_START))
    
    echo ""
    echo "⏱️ 迭代耗時：${DURATION}s"
    
    sleep 3
done

echo ""
echo "達到最大迭代次數 $MAX_ITERATIONS"
openclaw notify --agent "$AGENT_ID" --message "🦾 Autonomous Coder 達到最大迭代 $MAX_ITERATIONS，已暫停。" 2>/dev/null || true
exit 1
