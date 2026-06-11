# ARIZ Flow Implementation Plan

> **For agentic workers:** Use superpowers-open:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 实现完整的 ARIZ 9步分析流程，后端 session state 管理 + 动态 system prompt + 前端折叠卡片+详情面板

**Architecture:** 后端 ariz_flow.py 作为流程控制核心，维护 SessionState，动态生成 system prompt 注入历史结果。工具调用后更新 state 并自动推进步骤。前端解析工具调用结果渲染步骤卡片和详情面板。

**Tech Stack:** Python/Flask, SQLite, Next.js/React, Tailwind CSS

---

## 现有代码分析

已有代码基本实现了设计文档的架构，但存在以下问题需修复：

| 问题 | 位置 | 说明 |
|------|------|------|
| Session state 无清理 | ariz_flow.py | 新建对话时未重置 state |
| System prompt 未注入历史结果 | ariz_flow.py | build_system_prompt 缺少 history_context |
| Step 2 数据库查询未传入 prompt | ariz_flow.py | Step 2 的 prompt 未包含 Step 1 的数据库查询结果 |
| 工具调用结果未存入 session | app.py | handle_ariz_tool_call 未调用 save_step_result |
| 前端消息解析不完整 | Message.tsx | extractArizSteps 可能漏掉多步骤结果 |
| 详情面板数据嵌套未处理 | ArizDetailPanel.tsx | step2_result 等嵌套结构未兼容 |

---

## Task 1: 修复后端 Session State 管理

**Files:**
- Modify: `backend/ariz_flow.py`

- [ ] **Step 1: 修复 get_session_state 确保新对话自动初始化**

```python
def get_session_state(conv_id: str) -> dict:
    """获取会话的 ARIZ 状态，不存在则初始化"""
    if conv_id not in _session_states:
        _session_states[conv_id] = {
            "current_step": "problem",
            "step_results": {},
            "step_history": [],
        }
    return _session_states[conv_id]
```

- [ ] **Step 2: 修复 advance_step 记录历史**

```python
def advance_step(conv_id: str) -> str:
    """前进到下一步"""
    state = get_session_state(conv_id)
    idx = get_step_index(state["current_step"])
    if idx < len(ARIZ_STEPS) - 1:
        # 记录当前步骤确认时间
        state["step_history"].append({
            "step": state["current_step"],
            "confirmed_at": datetime.now().isoformat(),
        })
        next_step = ARIZ_STEPS[idx + 1][0]
        state["current_step"] = next_step
        return next_step
    return None
```

- [ ] **Step 3: 修复 rollback_to_step 完整实现**

```python
def rollback_to_step(conv_id: str, target_step: str) -> dict:
    """回退到指定步骤，清空后续结果"""
    state = get_session_state(conv_id)
    target_idx = get_step_index(target_step)
    if target_idx < 0:
        return {"error": f"未知步骤: {target_step}"}

    # 删除目标步骤及之后的所有结果
    for step_name, _ in ARIZ_STEPS[target_idx:]:
        state["step_results"].pop(step_name, None)

    # 清空目标步骤之后的历史
    state["step_history"] = [
        h for h in state["step_history"]
        if get_step_index(h["step"]) < target_idx
    ]

    state["current_step"] = target_step
    logger.info("ariz_rolled_back", conv_id=conv_id, target=target_step)
    return {"rolled_back_to": target_step, "message": f"已回退到：{get_step_label(target_step)}"}
```

- [ ] **Step 4: 验证**

在 Python shell 中测试：
```python
from ariz_flow import get_session_state, advance_step, rollback_to_step, save_step_result
state = get_session_state("test1")
save_step_result("test1", "problem", {"problem_object": "热管理"})
advance_step("test1")
save_step_result("test1", "components", {"all_components": ["冷却板"]})
print(state["step_results"].keys())  # 应有 problem, components
rollback_to_step("test1", "problem")
print(state["step_results"].keys())  # 应只有 problem
```

- [ ] **Step 5: Commit**

```bash
git add backend/ariz_flow.py
git commit -m "fix: 修复 session state 管理（初始化/历史/回退）"
```

---

## Task 2: 修复 System Prompt 动态生成

**Files:**
- Modify: `backend/ariz_flow.py`

- [ ] **Step 1: 新增 history 注入函数**

在 ariz_flow.py 中添加：

```python
def _summarize_step_result(step_name: str, result: dict) -> str:
    """将步骤结果转为 LLM 可读的摘要文本"""
    if step_name == "problem":
        d = result.get("step1_result", result)
        lines = []
        if d.get("problem_object"): lines.append(f"- 问题对象：{d['problem_object']}")
        if d.get("phenomenon"): lines.append(f"- 现象：{d['phenomenon']}")
        if d.get("goal"): lines.append(f"- 目标：{d['goal']}")
        if d.get("constraints"): lines.append(f"- 约束：{'、'.join(d['constraints'])}")
        if d.get("contradiction_hint"): lines.append(f"- 矛盾方向：{d['contradiction_hint']}")
        return "\n".join(lines)

    elif step_name == "components":
        d = result.get("step2_result", result)
        lines = []
        if d.get("supersystem"): lines.append(f"- 超系统：{d['supersystem']}")
        if d.get("system_name"): lines.append(f"- 系统：{d['system_name']}")
        comps = d.get("all_components", [])
        if comps:
            comp_names = [c if isinstance(c, str) else c.get("name", str(c)) for c in comps]
            lines.append(f"- 组件：{'、'.join(comp_names)}")
        return "\n".join(lines)

    elif step_name == "contacts":
        contacts = result.get("contacts", [])
        lines = [f"- 共{len(contacts)}个接触关系"]
        for c in contacts[:5]:
            lines.append(f"  {c.get('component_a','')} ↔ {c.get('component_b','')}：{c.get('contact_type','')}")
        return "\n".join(lines)

    elif step_name == "function":
        funcs = result.get("functions", [])
        type_map = {"useful": "有用", "insufficient": "不足", "excessive": "过度", "harmful": "有害", "missing": "缺失"}
        lines = [f"- 共{len(funcs)}个功能"]
        for f in funcs[:5]:
            t = type_map.get(f.get("type", ""), f.get("type", ""))
            lines.append(f"  {f.get('source','')} → {f.get('function','')} → {f.get('target','')}（{t}）")
        return "\n".join(lines)

    else:
        # 其他步骤：简要展示
        return json.dumps(result, ensure_ascii=False)[:300]


def inject_history(step_results: dict) -> str:
    """将已完成步骤的结果注入为历史上下文"""
    if not step_results:
        return ""

    lines = ["已完成的分析步骤："]
    for step_name, _ in ARIZ_STEPS:
        if step_name in step_results:
            label = get_step_label(step_name)
            summary = _summarize_step_result(step_name, step_results[step_name])
            lines.append(f"\n【{label}】\n{summary}")

    return "\n".join(lines)
```

- [ ] **Step 2: 修改 build_system_prompt 注入历史**

找到 build_system_prompt 函数，在 `step_guide` 之后、`重要规则` 之前插入：

```python
    # 历史结果注入
    history = inject_history(state.get("step_results", {}))
```

然后在返回的字符串中，将 `{step_guide}` 后面加上 `{history}`：

```python
    return f"""你是一个专注于动力电池 PACK 创新的 AI Agent...

{progress}

{step_guide}

{history}

重要规则：
..."""
```

注意：build_system_prompt 需要接收 state 参数（目前只接收 current_step）。修改签名：

```python
def build_system_prompt(current_step: str, state: dict = None) -> str:
```

调用处传入 state。

- [ ] **Step 3: 修改 app.py 中的调用**

在 chat() 的 generate() 中：

```python
state = get_session_state(conv_id_for_flow)
current_step = state["current_step"]
system_prompt = build_system_prompt(current_step, state)  # 传入 state
```

- [ ] **Step 4: 验证**

启动后端，发送消息后检查 system prompt 是否包含历史结果。

- [ ] **Step 5: Commit**

```bash
git add backend/ariz_flow.py backend/app.py
git commit -m "feat: system prompt 动态注入历史步骤结果"
```

---

## Task 3: 修复工具调用结果存储

**Files:**
- Modify: `backend/app.py`

- [ ] **Step 1: 修改 handle_ariz_tool_call 确保存入 session state**

当前代码已有 save_step_result 调用，但需要确认数据结构正确。检查 handle_ariz_tool_call 中每一步的 save 调用：

Step 1 保存的应该是完整返回数据（含 step1_result 和 database_query），还是只保存 args？

根据设计文档，保存 args（用户确认的数据），database_query 作为附加信息。

修改 Step 1 的保存逻辑：

```python
if step_num == 1:
    # 保存用户确认的问题数据
    save_step_result(conv_id, "problem", args)
    # 查询数据库
    db_result = query_components_for_step2(args)
    # 将数据库查询结果附加到返回数据中
    args_with_db = {**args, "_database_query": db_result}
    advance_step(conv_id)
    return json.dumps({
        "status": "confirmed",
        "message": f"问题识别已确认，进入第2步：系统组件分析",
        "step1_result": args,
        "_database_query": db_result,
    }, ensure_ascii=False)
```

- [ ] **Step 2: 验证**

```python
from ariz_flow import get_session_state
# 模拟 Step 1 调用后
state = get_session_state("test2")
# 检查 step_results["problem"] 是否有数据
```

- [ ] **Step 3: Commit**

```bash
git add backend/app.py
git commit -m "fix: 工具调用结果正确存入 session state"
```

---

## Task 4: 修复前端消息解析

**Files:**
- Modify: `frontend/components/Message.tsx`

- [ ] **Step 1: 检查 extractArizSteps 的正则**

当前正则：
```
/\*\*调用工具: (ariz_step\d_\w+)\*\*\n```json\n([\s\S]*?)\n```/g
```

后端生成的工具调用文本格式：
```
**调用工具: ariz_step1_problem**
```json
{...}
```
```

正则应该能匹配。但需要确认 `[\s\S]*?` 能否正确匹配多行 JSON（包括嵌套的 `**` 和 ```）。

问题可能是 JSON 中包含 `\n` 导致匹配提前终止。改用更宽松的匹配：

```typescript
const toolRegex = /\*\*调用工具: (ariz_step\d_\w+)\*\*\n```json\n([\s\S]*?)\n```\n/g;
```

或者用贪婪匹配 + 末尾 ``` 定位：

```typescript
const toolRegex = /\*\*调用工具: (ariz_step\d_\w+)\*\*\n```json\n([\s\S]*?)\n```\s*\n?/g;
```

- [ ] **Step 2: 添加调试日志**

在 extractArizSteps 中添加 console.log 确认匹配：

```typescript
console.log('Parsing message, length:', content.length);
console.log('Match found:', !!match, 'tool:', toolName);
```

- [ ] **Step 3: 验证**

启动前后端，发送消息后检查浏览器控制台输出。

- [ ] **Step 4: Commit**

```bash
git add frontend/components/Message.tsx
git commit -m "fix: 修复消息中工具调用结果的正则解析"
```

---

## Task 5: 修复前端详情面板数据兼容

**Files:**
- Modify: `frontend/components/ArizDetailPanel.tsx`

- [ ] **Step 1: 确认 Step1Detail 兼容嵌套数据**

已修复（data.step1_result || data）。验证 Step2Detail 也做了兼容。

检查 Step2Detail 中 database_query 的使用：当 components 是字符串数组时，从 data.database_query.primary_system.components 中查找详情。

- [ ] **Step 2: Step3-9 Detail 数据兼容**

确认 Step3Detail、Step4Detail 等也处理了嵌套结构（step3_result、step4_result 等）。

如果工具返回 `{status, step3_result: {contacts: [...]}}`，Step3Detail 需要：
```typescript
const d = data.step3_result || data;
const contacts = d.contacts || [];
```

- [ ] **Step 3: Commit**

```bash
git add frontend/components/ArizDetailPanel.tsx
git commit -m "fix: 详情面板兼容嵌套数据结构"
```

---

## Task 6: 端到端验证

- [ ] **Step 1: 启动后端**

```bash
cd backend && source venv/bin/activate && python3 app.py
```

- [ ] **Step 2: 启动前端**

```bash
cd frontend && npm run dev
```

- [ ] **Step 3: 测试 Step 1 完整流程**

1. 打开 http://localhost:3000
2. 输入：液冷散热不够，2C放电时电芯温度48°C
3. 确认 Agent 追问了具体子系统和量化参数
4. 确认 Agent 输出自然文本格式的结果（非 JSON 代码块）
5. 确认步骤卡片出现
6. 点击"查看"确认详情面板显示正确数据

- [ ] **Step 4: 测试 Step 1→2 流程**

1. 在 Step 1 确认后，确认自动进入 Step 2
2. 确认 Step 2 展示了数据库中的组件列表
3. 确认步骤卡片显示在 Step 1 卡片之后

- [ ] **Step 5: 测试回退**

1. 在 Step 2 说"修改第1步"
2. 确认回退到 Step 1，Step 2 的卡片消失
3. 确认可以重新走 Step 1

- [ ] **Step 6: 最终 Commit**

```bash
git add -A
git commit -m "feat: ARIZ 1-2步完整流程跑通"
```
