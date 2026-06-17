#!/bin/bash
# ============================================
# Xagent 一键启动脚本
# 用法: ./start.sh [--legacy]
#   默认: LangGraph + Deep Agents 新引擎
#   --legacy: 使用旧引擎
# ============================================

set -e

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

# 路径
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
BACKEND_DIR="$SCRIPT_DIR/backend"
FRONTEND_DIR="$SCRIPT_DIR/frontend"

# 参数解析
USE_LANGGRAPH="true"
if [[ "$1" == "--legacy" ]]; then
    USE_LANGGRAPH="false"
    echo -e "${YELLOW}⚠️  使用旧引擎模式${NC}"
else
    echo -e "${GREEN}🚀 使用 LangGraph + Deep Agents 新引擎${NC}"
fi

# 清理函数
cleanup() {
    echo ""
    echo -e "${YELLOW}🛑 正在停止服务...${NC}"
    if [[ -n "$BACKEND_PID" ]]; then
        kill "$BACKEND_PID" 2>/dev/null && echo -e "  后端已停止 (PID: $BACKEND_PID)"
    fi
    if [[ -n "$FRONTEND_PID" ]]; then
        kill "$FRONTEND_PID" 2>/dev/null && echo -e "  前端已停止 (PID: $FRONTEND_PID)"
    fi
    echo -e "${GREEN}✅ 已停止所有服务${NC}"
    exit 0
}

trap cleanup SIGINT SIGTERM EXIT

# 检查依赖
echo ""
echo "📦 检查依赖..."

# Python 虚拟环境
if [[ ! -d "$BACKEND_DIR/venv" ]]; then
    echo -e "${RED}❌ 未找到 Python 虚拟环境，请先运行:${NC}"
    echo "   cd backend && python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt"
    exit 1
fi

# Node modules
if [[ ! -d "$FRONTEND_DIR/node_modules" ]]; then
    echo -e "${YELLOW}⚠️  未找到 node_modules，正在安装...${NC}"
    cd "$FRONTEND_DIR" && npm install
fi

echo -e "${GREEN}✅ 依赖检查通过${NC}"

# 启动后端
echo ""
echo "🔧 启动后端 (Flask + LangGraph)..."
cd "$BACKEND_DIR"
source venv/bin/activate
USE_LANGGRAPH="$USE_LANGGRAPH" FLASK_DEBUG=false FLASK_PORT=8000 python app.py &
BACKEND_PID=$!
echo -e "  ${GREEN}后端已启动 (PID: $BACKEND_PID) → http://localhost:8000${NC}"

# 等待后端就绪
echo -n "  等待后端就绪"
for i in $(seq 1 15); do
    if curl -s http://localhost:8000/api/conversations > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# 启动前端
echo ""
echo "🎨 启动前端 (Next.js)..."
cd "$FRONTEND_DIR"
npm run dev &
FRONTEND_PID=$!
echo -e "  ${GREEN}前端已启动 (PID: $FRONTEND_PID) → http://localhost:3000${NC}"

# 等待前端就绪
echo -n "  等待前端就绪"
for i in $(seq 1 20); do
    if curl -s http://localhost:3000 > /dev/null 2>&1; then
        echo -e " ${GREEN}✓${NC}"
        break
    fi
    echo -n "."
    sleep 1
done

# 启动完成
echo ""
echo "============================================"
echo -e "${GREEN}✅ Xagent 启动完成！${NC}"
echo ""
echo "  🌐 前端: http://localhost:3000"
echo "  🔧 后端: http://localhost:8000"
echo ""
echo "  引擎: $([ "$USE_LANGGRAPH" = "true" ] && echo "LangGraph + Deep Agents" || echo "Legacy")"
echo ""
echo "  按 Ctrl+C 停止所有服务"
echo "============================================"
echo ""

# 保持前台运行
wait
