#!/bin/bash
# Xagent 停止脚本
echo "🛑 停止 Xagent 服务..."

# 停止 Flask
pkill -f "python app.py" 2>/dev/null && echo "  后端已停止" || echo "  后端未运行"

# 停止 Next.js
pkill -f "next dev" 2>/dev/null && echo "  前端已停止" || echo "  前端未运行"

echo "✅ 完成"
