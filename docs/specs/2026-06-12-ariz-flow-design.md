# Xagent ARIZ Flow 设计文档

**日期**：2026-06-12
**版本**：v1.0
**状态**：已确认

---

## 1. 概述

为 Xagent 动力电池PACK创新智能体实现完整的 ARIZ 9步分析流程。核心目标：通过后端 session state 管理实现稳定的步骤间数据传递，前端以折叠卡片+详情面板的形式展示结构化分析结果。

## 2. 架构设计

### 2.1 系统架构

```
用户输入 → LLM（system prompt 动态生成）→ 工具调用 → 后端更新 session state → 返回结果 → 前端渲染
```

核心模块：
- `ariz_flow.py`：流程控制核心（SessionState、system prompt 生成、工具调用处理、回退）
- `component_db.py`：组件知识库读写
- `app.py`：Flask 主入口，集成 ARIZ 工具调用

### 2.2 数据流

```
SessionState（内存）
  ↓
build_system_prompt() 读取 state
  ↓
system prompt = 角色 + 进度条 + 步骤指引 + 历史结果摘要 + 全局规则
  ↓
LLM 根据 prompt 决定调用哪个工具
  ↓
handle_tool_call() 更新 state + 返回结果
  ↓
前端解析结果 → 渲染步骤卡片 + 详情面板
```

## 3. Session State 数据模型

```python
SessionState = {
    "current_step": "problem",          # 当前步骤名
    "step_results": {                   # 各步结果（工具调用 args）
        "problem": { ... },
        "components": { ... },
        "contacts": { ... },
        "function": { ... },
        "structure": { ... },
        "summary": { ... },
        "causal": { ... },
        "keypoint": { ... },
        "solution": { ... }
    },
    "step_history": [                   # 步骤流转历史
        {"step": "problem", "entered_at": "...", "confirmed_at": "..."}
    ]
}
```

关键规则：
- `step_results` 只在用户确认后写入
- 回退时：删除目标步骤及之后的所有 `step_results`，`current_step` 回到目标步骤
- system prompt 注入时：只注入已完成步骤的结果摘要
- session state 存在内存中，不持久化

## 4. System Prompt 动态生成

```python
def build_system_prompt(session_state):
    base = "你是动力电池PACK创新智能体，基于TRIZ ARIZ方法论..."
    progress = build_progress(session_state.current_step)
    step_guide = STEP_GUIDES[current_step]
    history_context = inject_history(session_state.step_results)
    rules = "输出用自然文本，不要代码块..."
    return base + progress + step_guide + history_context + rules
```

历史结果注入格式（摘要，非完整 JSON）：

```
【问题识别结果】
- 问题对象：热管理系统
- 现象：2C放电时温度48°C，温差11°C
- 目标：≤40°C，温差≤5°C

【系统组件分析结果】
- 超系统：整车底盘（-30°C~55°C）
- 组件：冷却板、冷却液、管路、水泵...
```

## 5. 工具调用与步骤路由

```python
def handle_tool_call(conv_id, tool_name, args):
    state = get_session_state(conv_id)
    step_num = extract_step_num(tool_name)
    
    # 保存结果
    state.step_results[current_step] = args
    
    # Step 1 特殊：自动查数据库
    if step_num == 1:
        db_result = query_components(args["system_keywords"])
        args["_database_query"] = db_result
    
    # 自动推进
    next_step = advance_step(current_step)
    state.current_step = next_step
    
    return {"step": step_num, "status": "confirmed", "data": args}
```

## 6. 回退机制

```python
def rollback_to_step(conv_id, target_step):
    state = get_session_state(conv_id)
    target_idx = get_step_index(target_step)
    
    # 删除目标步骤及之后的结果
    for step_name, _ in ARIZ_STEPS[target_idx:]:
        state.step_results.pop(step_name, None)
    
    state.current_step = target_step
    return {"rolled_back_to": target_step}
```

用户触发：对话中说"修改第X步"或"回到第X步"。

## 7. 前端渲染设计

### 7.1 布局

左对话区（flex-1） + 右详情面板（480px，可折叠）

### 7.2 消息渲染

```
LLM 回复文本
  ↓ 解析工具调用
  ├─ 无工具调用 → Markdown 渲染
  └─ 有工具调用 → 文本 + 步骤卡片
       ↓ 点击"查看"
       右侧详情面板
```

### 7.3 步骤卡片（ArizStepCard）

折叠态：摘要行 + 步骤标题 + "查看"按钮

### 7.4 详情面板（ArizDetailPanel）

| 步骤 | 展示形式 |
|------|----------|
| Step 1 | 字段列表：问题对象/现象/目标/约束/待澄清问题 |
| Step 2 | 组件表格：组件名/功能/来源标记(库)/删除/新增 |
| Step 3 | 接触关系表格：组件A/组件B/接触类型/界面 |
| Step 4 | 功能模型表格：源→功能→目标/类型标签/描述 |
| Step 5-9 | 结构化展示（逐步细化） |

## 8. 设计决策记录

| 决策 | 选择 | 理由 |
|------|------|------|
| Step 2 确认交互 | 展示完整列表，确认即推进 | 简单高效，减少交互轮次 |
| 步骤间数据传递 | 后端 session state + 注入 prompt | 稳定可靠，不依赖 LLM 记忆 |
| 中途修改 | 完整回退，清空后续结果 | 保证数据一致性 |
| Step 3-9 深度 | 轻量（LLM驱动） | 快速迭代，后续逐步加重 |
