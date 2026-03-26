#!/bin/bash
# Autonomous Coder - Copilot Code Review Step
# 所有 task 完成後觸發 GitHub Copilot (Opus 4.6) 審查程式碼並建立 PR
# 用法: ./copilot-review.sh [project_path] [github_repo]

set -e

PROJECT_PATH=${1:-$(pwd)}
REPO=${2:-""}
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

TASKS_FILE="$SCRIPT_DIR/tasks.json"
CONFIG_FILE="$PROJECT_PATH/.copilot-review.json"

echo "🔍 Copilot Code Review 啟動"
echo "專案路徑: $PROJECT_PATH"
echo "倉庫: $REPO"
echo ""

# 從 tasks.json 取得 branch name
BRANCH=$(jq -r '.branchName // "main"' "$TASKS_FILE" 2>/dev/null || echo "main")
BASE_BRANCH="main"

# 如果有 config，讀取設定
if [ -f "$CONFIG_FILE" ]; then
    BASE_BRANCH=$(jq -r '.baseBranch // "main"' "$CONFIG_FILE")
    REVIEW_FOCUS=$(jq -r '.reviewFocus | join(", ")' "$CONFIG_FILE" 2>/dev/null || echo "code quality, performance, security")
    INSTRUCTIONS=$(jq -r '.instructions // "Review all code changes and create a PR if improvements are needed."' "$CONFIG_FILE")
else
    REVIEW_FOCUS="code quality, performance, security, best practices"
    INSTRUCTIONS="Review all code changes on this branch. Check for bugs, performance issues, and style consistency. If improvements are needed, commit them directly and create a PR. Otherwise, just create a summary PR."
fi

# 確認有 gh CLI
if ! command -v gh &> /dev/null; then
    echo "❌ 找不到 gh CLI"
    echo "請先安裝：https://cli.github.com/"
    exit 1
fi

# 確認 gh 已登入
if ! gh auth status &> /dev/null; then
    echo "❌ gh CLI 未登入"
    echo "請執行：gh auth login"
    exit 1
fi

# 自動偵測 repo
if [ -z "$REPO" ]; then
    REPO=$(cd "$PROJECT_PATH" && git remote get-url origin 2>/dev/null | sed 's|.*github.com[:/]||;s|\.git$||' || echo "")
fi

if [ -z "$REPO" ]; then
    echo "❌ 無法偵測 GitHub repo，請手動指定："
    echo "   ./copilot-review.sh $PROJECT_PATH owner/repo"
    exit 1
fi

echo "📋 設定："
echo "   分支: $BRANCH → $BASE_BRANCH"
echo "   倉庫: $REPO"
echo "   Review: $REVIEW_FOCUS"
echo ""

# 推送分支到遠端
echo "📤 推送分支到遠端..."
cd "$PROJECT_PATH"
git push -u origin "$BRANCH" 2>&1 || {
    echo "⚠️ Push 失敗，嘗試 force push..."
    git push -u origin "$BRANCH" --force 2>&1
}

# 取得 diff 摘要
DIFF_SUMMARY=$(git log "$BASE_BRANCH..$BRANCH" --oneline 2>/dev/null || git log --oneline -20)
CHANGED_FILES=$(git diff --name-only "$BASE_BRANCH..$BRANCH" 2>/dev/null | head -50 || git diff --name-only HEAD~10 | head -50)

COMMIT_COUNT=$(echo "$DIFF_SUMMARY" | wc -l)

echo "📊 變更摘要："
echo "   $COMMIT_COUNT 個 commits"
echo "$DIFF_SUMMARY" | head -10
echo ""

# 建構 Copilot prompt
COPILOT_PROMPT="## Code Review Request

**Repository**: $REPO
**Branch**: $BRANCH (target: $BASE_BRANCH)
**Changes**: $COMMIT_COUNT commits

### Changed Files
$CHANGED_FILES

### Review Instructions
$INSTRUCTIONS

### Focus Areas
$REVIEW_FOCUS

### What to do
1. Review ALL code changes on branch '$BRANCH' compared to '$BASE_BRANCH'
2. For each issue found:
   - If trivial (typos, formatting, obvious bugs): fix directly and commit
   - If significant: add a PR review comment explaining the issue
3. After reviewing, create a Pull Request with:
   - Title summarizing all changes
   - Body listing commits and any improvements made during review
   - Labels: 'auto-review', 'needs-human-approval'
4. Do NOT merge the PR. The human will review and merge.

### Constraints
- Do NOT change the overall architecture or add new features
- Only fix issues related to code quality, bugs, and the focus areas above
- Preserve existing functionality — all tests must still pass"

echo "🤖 觸發 GitHub Copilot Agent (Opus 4.6)..."

# 呼叫 gh copilot agent
gh copilot agent \
    --model opus-4.6 \
    --prompt "$COPILOT_PROMPT" \
    --repo "$REPO" \
    --branch "$BRANCH" \
    2>&1 | tee /tmp/copilot-review-$(date +%Y%m%d-%H%M%S).log

echo ""
echo "✅ Copilot Review 完成！"
echo "👉 請到 GitHub 查看 PR 並審查 Copilot 的修改："
echo "   https://github.com/$REPO/pulls"
