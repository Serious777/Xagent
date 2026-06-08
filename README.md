# ⚡ Xagent

AI Agent with Skill System

## 技术栈

- **后端:** Python + Flask + OpenAI SDK + structlog
- **前端:** Next.js + Vercel AI SDK + Tailwind CSS
- **LLM:** Xiaomi MiMo

## 快速启动

### 后端

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env  # 编辑 .env 填入 API Key
python app.py
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

## Skills

- **web_search** - 搜索互联网
- **llm_wiki** - 知识库管理

## 项目结构

```
Xagent/
├── backend/
│   ├── app.py              # Flask 主入口
│   ├── skills/             # Skill 模块
│   └── requirements.txt
├── frontend/
│   ├── app/                # Next.js 页面
│   ├── components/         # React 组件
│   └── package.json
└── README.md
```
