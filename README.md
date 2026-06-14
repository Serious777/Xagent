# ⚡ Xagent — 动力电池PACK创新智能体

基于 **TRIZ ARIZ 方法论** 的 AI 驱动创新分析系统。通过 9 步结构化流程，引导用户完成从问题识别到创新方案生成的全过程。

## 功能特性

- 🔍 **问题识别** — 提取核心矛盾、定义改进方向
- 🧩 **系统组件分析** — 自动查询组件知识库，识别系统/超系统组件
- 🔗 **接触关系分析** — 生成组件间接触矩阵
- ⚙️ **功能建模** — 基于接触关系构建功能模型（有益/不足/过度/有害）
- 📐 **系统结构分析** — 空间布局与结构约束
- 📋 **问题总结** — 分类整理关键问题
- 🔗 **因果链分析** — 追溯根因
- 🎯 **关键问题定义** — 聚焦核心矛盾
- 💡 **创新方案生成** — 基于 TRIZ 原理提出解决方案

## 技术栈

| 层级 | 技术 |
|------|------|
| 后端 | Python 3.10+ / Flask / OpenAI SDK / structlog |
| 前端 | Next.js 14 / React / Tailwind CSS / Vercel AI SDK |
| 数据库 | SQLite（组件知识库 + 对话存储） |
| LLM | Xiaomi MiMo v2.5 |

## 快速开始

### 前置条件

- Python 3.10+
- Node.js 18+
- npm 或 yarn
- Xiaomi MiMo API Key（[获取地址](https://xiaoai.mi.com)）

### 1. 克隆仓库

```bash
git clone https://github.com/Serious777/Xagent.git
cd Xagent
```

### 2. 启动后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env       # 没有 .env.example 则手动创建
# 编辑 .env，填入以下内容：
#   XIAOMI_API_KEY=你的API密钥
#   XIAOMI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
#   XIAOMI_MODEL=mimo-v2.5

# 初始化组件知识库
python seed_components.py

# 启动服务
python app.py
```

后端运行在 `http://127.0.0.1:8000`

### 3. 启动前端

```bash
cd frontend

# 安装依赖
npm install

# 启动开发服务器
npm run dev
```

前端运行在 `http://localhost:3000`

### 4. 访问

打开浏览器访问 http://localhost:3000，开始 ARIZ 分析流程。

## 环境变量

在 `backend/.env` 中配置：

```env
# 必填
XIAOMI_API_KEY=your_api_key_here

# 可选（有默认值）
XIAOMI_BASE_URL=https://token-plan-cn.xiaomimimo.com/v1
XIAOMI_MODEL=mimo-v2.5
```

## 项目结构

```
Xagent/
├── backend/
│   ├── app.py                  # Flask 主入口，API 路由
│   ├── ariz_flow.py            # ARIZ 9步流程控制
│   ├── component_db.py         # 组件知识库（SQLite）
│   ├── seed_components.py      # 初始化组件数据
│   ├── skills/                 # 各步骤 LLM 工具定义
│   │   ├── ariz_step1_problem.py
│   │   ├── ariz_step2_components.py
│   │   ├── ariz_step3_contacts.py
│   │   ├── ariz_step4_function.py
│   │   ├── ariz_step5_structure.py
│   │   ├── ariz_step6_summary.py
│   │   ├── ariz_step7_causal.py
│   │   ├── ariz_step8_keypoint.py
│   │   └── ariz_step9_solution.py
│   ├── tests/                  # 单元测试
│   ├── requirements.txt
│   └── .env                    # 环境变量（不提交）
├── frontend/
│   ├── app/
│   │   ├── page.tsx            # 主页面
│   │   └── api/                # Next.js API 代理
│   ├── components/
│   │   ├── ArizDetailPanel.tsx  # 步骤详情面板（可全屏）
│   │   ├── ArizStepCard.tsx     # 步骤卡片
│   │   ├── Message.tsx          # 消息气泡
│   │   └── Sidebar.tsx          # 对话侧边栏
│   ├── package.json
│   └── tailwind.config.js
├── docs/                       # PRD 和设计文档
└── README.md
```

## 使用流程

1. **新建对话** — 点击侧边栏「+ 新对话」
2. **输入问题** — 描述你遇到的技术问题（如「如何提升低温续航」）
3. **逐步确认** — 系统依次完成 9 个步骤，每步生成分析卡片
4. **查看方案** — 最终生成基于 TRIZ 原理的创新解决方案

## License

MIT
