# Xagent 迁移 Plan A：基础设施搭建

> **For agentic workers:** Use superpowers-open:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 搭建 LangGraph + Deep Agents 的基础设施层——LLM 客户端封装、Prompt 外置、依赖安装，为后续流程迁移做准备。

**Architecture:** 将现有 OpenAI SDK 直接调用替换为 LangChain ChatOpenAI wrapper，将硬编码 prompt 提取为独立 Markdown 文件，新增依赖并验证兼容性。

**Tech Stack:** langchain-core, langchain-openai, langgraph, deepagents, python-dotenv

---

## 文件结构总览

```
backend/
├── llm.py                    # [创建] LLM 客户端封装
├── prompts.py                # [创建] Prompt 加载器
├── prompts/                  # [创建] Prompt 文件目录
│   ├── system.md
│   ├── step1_problem.md
│   ├── step2_components.md
│   ├── step3_contacts.md
│   ├── step4_function.md
│   ├── step5_structure.md
│   ├── step6_summary.md
│   ├── step7_causal.md
│   ├── step8_keypoint.md
│   └── step9_solution.md
├── requirements.txt          # [修改] 新增依赖
├── tests/
│   ├── test_llm.py           # [创建] LLM 客户端测试
│   └── test_prompts.py       # [创建] Prompt 加载测试
```

---

### Task 1: 更新依赖

**Files:**
- Modify: `backend/requirements.txt`

- [ ] **Step 1: 更新 requirements.txt**

```txt
flask
flask-cors
openai
python-dotenv
structlog
requests
langchain-core>=1.4.0
langchain-openai>=1.3.0
langgraph>=0.2.0
deepagents>=0.1.0
```

- [ ] **Step 2: 安装依赖**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
pip install -r requirements.txt
```

Expected: 所有依赖安装成功，无报错。

- [ ] **Step 3: 验证安装**

```bash
python3 -c "
import langchain_core
import langchain_openai
import langgraph
print(f'langchain-core: {langchain_core.__version__}')
print(f'langchain-openai: {langchain_openai.__version__}')
print(f'langgraph: {langgraph.__version__}')
"
```

Expected: 打印三个版本号，无 ImportError。

- [ ] **Step 4: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/requirements.txt
git commit -m "chore: add langchain/langgraph/deepagents dependencies"
```

---

### Task 2: 创建 LLM 客户端封装

**Files:**
- Create: `backend/llm.py`
- Create: `backend/tests/test_llm.py`

- [ ] **Step 1: 创建 llm.py**

```python
"""LLM 客户端封装 — 基于 LangChain ChatOpenAI"""
import os
from functools import lru_cache
from langchain_openai import ChatOpenAI


@lru_cache(maxsize=1)
def get_llm() -> ChatOpenAI:
    """获取 LLM 客户端（单例）"""
    return ChatOpenAI(
        model=os.getenv("XIAOMI_MODEL", "mimo-v2.5"),
        base_url=os.getenv("XIAOMI_BASE_URL"),
        api_key=os.getenv("XIAOMI_API_KEY"),
        streaming=True,
        timeout=120,
    )


def get_llm_no_stream() -> ChatOpenAI:
    """获取非流式 LLM 客户端（用于摘要等场景）"""
    return ChatOpenAI(
        model=os.getenv("XIAOMI_MODEL", "mimo-v2.5"),
        base_url=os.getenv("XIAOMI_BASE_URL"),
        api_key=os.getenv("XIAOMI_API_KEY"),
        streaming=False,
        timeout=120,
    )
```

- [ ] **Step 2: 创建 test_llm.py**

```python
"""LLM 客户端测试"""
import pytest
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_get_llm_returns_chatopenai():
    """验证 get_llm 返回 ChatOpenAI 实例"""
    from llm import get_llm

    llm = get_llm()
    from langchain_openai import ChatOpenAI
    assert isinstance(llm, ChatOpenAI)


def test_get_llm_singleton():
    """验证 get_llm 返回同一实例"""
    from llm import get_llm

    llm1 = get_llm()
    llm2 = get_llm()
    assert llm1 is llm2


def test_get_llm_no_stream():
    """验证 get_llm_no_stream 关闭流式"""
    from llm import get_llm_no_stream

    llm = get_llm_no_stream()
    assert llm.streaming is False
```

- [ ] **Step 3: 运行测试**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python -m pytest tests/test_llm.py -v
```

Expected: 3 tests PASSED。

- [ ] **Step 4: 验证实际调用**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python3 -c "
from dotenv import load_dotenv
load_dotenv()
from llm import get_llm
llm = get_llm()
result = llm.invoke('说一个字')
print(f'回复: {result.content}')
print('LLM 客户端封装正常 ✓')
"
```

Expected: 打印 MiMo 回复 + "LLM 客户端封装正常 ✓"。

- [ ] **Step 5: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/llm.py backend/tests/test_llm.py
git commit -m "feat: add LangChain LLM client wrapper"
```

---

### Task 3: 创建 Prompt 文件目录和加载器

**Files:**
- Create: `backend/prompts.py`
- Create: `backend/prompts/system.md`
- Create: `backend/tests/test_prompts.py`

- [ ] **Step 1: 创建 prompts.py**

```python
"""Prompt 文件加载器"""
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent / "prompts"


def load_prompt(name: str) -> str:
    """加载 prompt 模板文件

    Args:
        name: prompt 名称（不含 .md 后缀），如 "system"、"step1_problem"

    Returns:
        prompt 文本内容

    Raises:
        FileNotFoundError: prompt 文件不存在
    """
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return path.read_text(encoding="utf-8")


def list_prompts() -> list[str]:
    """列出所有可用的 prompt 名称"""
    return [p.stem for p in PROMPTS_DIR.glob("*.md")]
```

- [ ] **Step 2: 创建 prompts/ 目录和 system.md**

```bash
mkdir -p /Users/chenyw/PROJECT/Xagent/backend/prompts
```

创建 `backend/prompts/system.md`：

```markdown
你是一个专注于动力电池 PACK 创新的 AI Agent，基于 TRIZ ARIZ 方法论引导工程师完成系统化创新分析。

核心规则（必须遵守）：
- 每一步分析完成后，必须在同一轮对话中同时完成：用自然文本输出分析结果 + 调用对应工具保存。绝对不要分开做。
- 严禁先输出分析结果、等用户确认后才调用工具。工具调用是你的职责，不需要用户授权。
- 严禁在文本中问"请确认""是否正确""对吗"之类的问题。卡片会处理确认流程。
- 工具调用后系统会自动渲染步骤卡片，用户点击卡片上的「确认」按钮进入下一步。
- 用户确认后会自动发送"已确认，请继续下一步"，你直接进入下一步分析。
- 用户可以随时要求修改某个步骤。
- 所有展示给用户的结果用自然文本，不要用代码块。只有真正的代码、命令才用代码块。
- 语言：中文。
- 语气：专业但自然，像经验丰富的工程师同事在对话，不要过于机械。
- 用户确认后直接进入下一步分析，不要重复展示已确认的内容。
```

- [ ] **Step 3: 创建 test_prompts.py**

```python
"""Prompt 加载器测试"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_load_prompt_system():
    """验证能加载 system prompt"""
    from prompts import load_prompt

    content = load_prompt("system")
    assert "动力电池" in content
    assert "TRIZ" in content
    assert len(content) > 100


def test_load_prompt_not_found():
    """验证加载不存在的 prompt 抛出异常"""
    from prompts import load_prompt

    with pytest.raises(FileNotFoundError):
        load_prompt("nonexistent_prompt_xyz")


def test_list_prompts():
    """验证能列出所有 prompt"""
    from prompts import list_prompts

    names = list_prompts()
    assert "system" in names
    assert len(names) >= 1
```

- [ ] **Step 4: 运行测试**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python -m pytest tests/test_prompts.py -v
```

Expected: 3 tests PASSED。

- [ ] **Step 5: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/prompts.py backend/prompts/ backend/tests/test_prompts.py
git commit -m "feat: add prompt loader and system.md"
```

---

### Task 4: 提取 Step 1-3 Prompt 到独立文件

**Files:**
- Create: `backend/prompts/step1_problem.md`
- Create: `backend/prompts/step2_components.md`
- Create: `backend/prompts/step3_contacts.md`

- [ ] **Step 1: 创建 step1_problem.md**

从 `ariz_flow.py` 的 `step_guides["problem"]` 提取内容，写入 `backend/prompts/step1_problem.md`：

```markdown
## 当前步骤：第1步「问题识别」

你的任务是引导用户完成三步聚焦：
1. 具体系统定位 — 问题发生在哪个子系统？（热管理/箱体/电芯模组/BMS/电气？）
2. 问题现象明确 — 什么工况下、什么参数超标、超标多少？（必须量化）
3. 聚焦具体矛盾 — 改善A → 恶化B 的矛盾结构

规则：
- 如果用户描述模糊（如"电池有问题"），必须追问具体子系统。
- 如果现象不可量化（如"散热不好"），必须追问具体参数。
- 如果矛盾不清晰，帮助用户提炼。
- 信息收集完成后，用自然文本输出分析结果，然后立即调用 ariz_step1_problem 工具。
- system_keywords 必须使用系统级名称（如'热管理系统'、'箱体结构'、'BMS'），不要用具体现象（如'低温续航衰减'、'PTC加热'）。
- 严禁先问"请确认"再调工具。必须在同一轮对话中同时完成：输出分析 + 调用工具。
- 工具调用后系统会自动渲染步骤卡片，用户点击卡片上的「确认」按钮进入下一步。
- 如果用户补充信息，重新分析并再次调用工具覆盖保存。

展示格式示例：

问题识别结果：
- 问题对象：热管理系统
- 现象：2C倍率放电时电芯最高温度48°C，温差11°C
- 目标：最高温度≤40°C，温差≤5°C
- 矛盾方向：提高散热 → 增加重量/成本
- 约束条件：不增加系统重量、成本增幅<5%
```

- [ ] **Step 2: 创建 step2_components.md**

从 `ariz_flow.py` 的 `step_guides["components"]` 提取，写入 `backend/prompts/step2_components.md`：

```markdown
## 当前步骤：第2步「系统组件分析」

你的任务：
1. 从历史上下文中找到「问题识别」的数据库组件列表。
2. 用这些数据库组件作为标准组件清单，不要自己编造组件。
3. 补充超系统分析（哪些外部组件与本系统有交互）。
4. 用自然文本展示组件清单，然后立即调用 ariz_step2_components 工具保存。
5. 严禁先问"请确认"再调工具。必须在同一轮对话中同时完成：输出分析 + 调用工具。
6. 工具调用后系统自动渲染卡片，用户点击「确认」进入下一步。

展示格式示例：

超系统：整车底盘环境（-30°C~55°C，振动0.5-3g，IP67防护等级）

系统：热管理系统

组件清单：
1. 冷却板 — 散热、均温
2. 冷却液 — 携带热量
```

- [ ] **Step 3: 创建 step3_contacts.md**

从 `ariz_flow.py` 的 `step_guides["contacts"]` 提取，写入 `backend/prompts/step3_contacts.md`：

```markdown
## 当前步骤：第3步「接触关系分析」

基于第2步的组件列表，分析组件间的接触/交互关系。

规则：
- 用自然文本展示接触关系。
- 分析完成后立即调用 ariz_step3_contacts 工具保存。
- 严禁先问"请确认"再调工具。必须在同一轮对话中同时完成：输出分析 + 调用工具。
- 工具调用后系统自动渲染卡片，用户点击「确认」进入下一步。
- 严禁跳过工具调用。如果你没有调用工具，系统将无法保存分析结果。
- contacts 数组中每个元素必须包含 component_a 和 component_b 字段（组件名称字符串）。
- 如果你无法确定某些组件是否接触，仍应将它们包含在 contacts 中，contact_type 设为 "待分析"。
```

- [ ] **Step 4: 验证 prompt 加载**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python3 -c "
from prompts import load_prompt, list_prompts
print(f'可用 prompts: {list_prompts()}')
for name in ['step1_problem', 'step2_components', 'step3_contacts']:
    content = load_prompt(name)
    print(f'{name}: {len(content)} chars ✓')
"
```

Expected: 三个 prompt 文件都成功加载，打印字符数。

- [ ] **Step 5: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/prompts/step1_problem.md backend/prompts/step2_components.md backend/prompts/step3_contacts.md
git commit -m "feat: extract step 1-3 prompts to markdown files"
```

---

### Task 5: 提取 Step 4-6 Prompt 到独立文件

**Files:**
- Create: `backend/prompts/step4_function.md`
- Create: `backend/prompts/step5_structure.md`
- Create: `backend/prompts/step6_summary.md`

- [ ] **Step 1: 创建 step4_function.md**

从 `ariz_flow.py` 的 `step_guides["function"]` 提取，写入 `backend/prompts/step4_function.md`：

```markdown
## 当前步骤：第4步「功能建模」

基于组件和接触关系，建立功能模型。每条功能关系包含：作用者(source)、作用对象(target)、功能(function)、功能类型(type)。

功能类型只有四种：
- useful：有益功能 — 功能正常执行且对系统目标有正面贡献
- insufficient：不足功能 — 功能存在但未达到最佳效果，需要增强
- excessive：过度功能 — 功能执行超出必要程度，导致负面效应
- harmful：有害功能 — 功能对系统产生负面干扰或不良影响

规则：
- 用自然文本列表展示功能模型。
- 分析完成后立即调用 ariz_step4_function 工具保存。
- 严禁先问"请确认"再调工具。必须在同一轮对话中同时完成：输出分析 + 调用工具。
- 工具调用后系统自动渲染卡片，用户点击「确认」进入下一步。
- 严禁跳过工具调用。如果你没有调用工具，系统将无法保存分析结果。
- functions 数组中每个元素必须包含 source、target、function、type 四个字段。
- 即使某些功能关系不确定，也应包含在数组中，type 设为 useful。
- 每个组件对之间至少分析一条功能关系。
```

- [ ] **Step 2: 创建 step5_structure.md**

从 `ariz_flow.py` 的 `step_guides["structure"]` 提取，写入 `backend/prompts/step5_structure.md`：

```markdown
## 当前步骤：第5步「系统结构分析」

分析系统空间结构，追问布局参数（尺寸/排列/冷却位置/流道走向），识别结构约束和瓶颈。

规则：
- 用自然文本展示结构分析。
- 分析完成后立即调用 ariz_step5_structure 工具保存。
- 严禁先问"请确认"再调工具。必须在同一轮对话中同时完成：输出分析 + 调用工具。
- 工具调用后系统自动渲染卡片，用户点击「确认」进入下一步。
```

- [ ] **Step 3: 创建 step6_summary.md**

从 `ariz_flow.py` 的 `step_guides["summary"]` 提取，写入 `backend/prompts/step6_summary.md`：

```markdown
## 当前步骤：第6步「功能建模问题总结」

从功能模型中提取所有问题，分类为：不足功能/有害功能/过度功能/缺失功能。给出优先级建议。

规则：
- 用自然文本展示问题清单。
- 分析完成后立即调用 ariz_step6_summary 工具保存。
- 严禁先问"请确认"再调工具。必须在同一轮对话中同时完成：输出分析 + 调用工具。
- 工具调用后系统自动渲染卡片，用户点击「确认」进入下一步。
```

- [ ] **Step 4: 验证 prompt 加载**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python3 -c "
from prompts import load_prompt
for name in ['step4_function', 'step5_structure', 'step6_summary']:
    content = load_prompt(name)
    print(f'{name}: {len(content)} chars ✓')
"
```

Expected: 三个 prompt 文件都成功加载。

- [ ] **Step 5: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/prompts/step4_function.md backend/prompts/step5_structure.md backend/prompts/step6_summary.md
git commit -m "feat: extract step 4-6 prompts to markdown files"
```

---

### Task 6: 提取 Step 7-9 Prompt 到独立文件

**Files:**
- Create: `backend/prompts/step7_causal.md`
- Create: `backend/prompts/step8_keypoint.md`
- Create: `backend/prompts/step9_solution.md`

- [ ] **Step 1: 创建 step7_causal.md**

从 `ariz_flow.py` 的 `step_guides["causal"]` 提取，写入 `backend/prompts/step7_causal.md`：

```markdown
## 当前步骤：第7步「因果链分析」

从用户选择的问题开始，逐层追问"为什么"，建立因果链。识别系统级约束和根本原因。找到潜在切入点。

规则：
- 用自然文本展示因果链（树状结构）。
- 分析完成后立即调用 ariz_step7_causal 工具保存。
- 严禁先问"请确认"再调工具。必须在同一轮对话中同时完成：输出分析 + 调用工具。
- 工具调用后系统自动渲染卡片，用户点击「确认」进入下一步。
```

- [ ] **Step 2: 创建 step8_keypoint.md**

从 `ariz_flow.py` 的 `step_guides["keypoint"]` 提取，写入 `backend/prompts/step8_keypoint.md`：

```markdown
## 当前步骤：第8步「关键问题/切入点」

定义技术矛盾（改善A→恶化B）、物理矛盾（同一参数既要大又要小）、理想最终状态（IFR）。

规则：
- 用自然文本展示矛盾定义和IFR。
- 分析完成后立即调用 ariz_step8_keypoint 工具保存。
- 严禁先问"请确认"再调工具。必须在同一轮对话中同时完成：输出分析 + 调用工具。
- 工具调用后系统自动渲染卡片，用户点击「确认」进入下一步。
```

- [ ] **Step 3: 创建 step9_solution.md**

从 `ariz_flow.py` 的 `step_guides["solution"]` 提取，写入 `backend/prompts/step9_solution.md`：

```markdown
## 当前步骤：第9步「生成创新方案」

基于矛盾和发明原理，生成具体方案卡片。每个方案包含：名称、原理、描述、优缺点、可行性、预期效果。

规则：
- 用自然文本展示方案卡片。
- 分析完成后立即调用 ariz_step9_solution 工具保存。
- 严禁先问"请确认"再调工具。必须在同一轮对话中同时完成：输出分析 + 调用工具。
- 工具调用后系统自动渲染卡片，用户点击「确认」完成。
- 生成完整ARIZ分析报告。
```

- [ ] **Step 4: 验证所有 prompt 加载**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python3 -c "
from prompts import load_prompt, list_prompts
all_prompts = list_prompts()
print(f'共 {len(all_prompts)} 个 prompt 文件: {sorted(all_prompts)}')
for name in sorted(all_prompts):
    content = load_prompt(name)
    assert len(content) > 50, f'{name} 内容太短'
    print(f'  {name}: {len(content)} chars ✓')
print('所有 prompt 文件验证通过 ✓')
"
```

Expected: 10 个 prompt 文件全部验证通过（system + 9 个 step）。

- [ ] **Step 5: Commit**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add backend/prompts/step7_causal.md backend/prompts/step8_keypoint.md backend/prompts/step9_solution.md
git commit -m "feat: extract step 7-9 prompts to markdown files"
```

---

### Task 7: 端到端验证 — LLM + Prompt 联动

**Files:**
- None（纯验证）

- [ ] **Step 1: 验证 LLM + Prompt 联动**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python3 -c "
from dotenv import load_dotenv
load_dotenv()

from llm import get_llm
from prompts import load_prompt

llm = get_llm()
system = load_prompt('system')
step1 = load_prompt('step1_problem')

from langchain_core.messages import SystemMessage, HumanMessage

messages = [
    SystemMessage(content=system),
    SystemMessage(content=step1),
    HumanMessage(content='电池包在低温环境下续航衰减严重'),
]

result = llm.invoke(messages)
print(f'Step 1 回复长度: {len(result.content)} chars')
print(f'前200字: {result.content[:200]}...')
print()
print('LLM + Prompt 联动正常 ✓')
"
```

Expected: MiMo 正常回复，内容与 ARIZ Step 1 相关，打印 "LLM + Prompt 联动正常 ✓"。

- [ ] **Step 2: 全量测试运行**

```bash
cd /Users/chenyw/PROJECT/Xagent/backend
source venv/bin/activate
python -m pytest tests/test_llm.py tests/test_prompts.py -v
```

Expected: 6 tests PASSED（3 LLM + 3 Prompts）。

- [ ] **Step 3: Commit（如果需要修复）**

```bash
cd /Users/chenyw/PROJECT/Xagent
git add -A
git commit -m "test: verify LLM + prompt integration"
```
