# ⚡ Xagent — 动力电池PACK创新智能体

## PRD v0.2 | 2026-06-11

---

## 1. 架构调整

### v0.1 → v0.2 变更

| 变更 | 说明 |
|------|------|
| ❌ 移除矛盾矩阵 Skill | 后续单独实现 |
| ❌ 移除进化法则 Skill | 后续单独实现 |
| ❌ 移除 PACK 知识 Skill | 后续单独实现 |
| ❌ 移除材料库 Skill | 后续单独实现 |
| ❌ 移除专利检索 Skill | 后续单独实现 |
| ❌ 移除 SQLite 数据模型扩展 | 暂不需要持久化 |
| ✅ 新增 ① 问题识别 | ARIZ 第一步，识别用户初始问题 |
| ✅ 拆分为独立 Skill | 流程控制 + 每步独立 Skill |

---

## 2. Skill 架构

### 2.1 Skill 清单

```
backend/skills/
├── __init__.py              # Skill 注册表
├── ariz_engine.py           # ARIZ 流程引擎（总控调度）
├── ariz_step1_problem.py    # ① 问题识别
├── ariz_step2_components.py # ② 系统组件分析
├── ariz_step3_contacts.py   # ③ 接触关系分析
├── ariz_step4_function.py   # ④ 功能建模
├── ariz_step5_structure.py  # ⑤ 系统结构分析
├── ariz_step6_summary.py    # ⑥ 功能建模问题总结
├── ariz_step7_causal.py     # ⑦ 因果链分析
├── ariz_step8_keypoint.py   # ⑧ 关键问题/切入点
└── ariz_step9_solution.py   # ⑨ 生成创新方案
```

### 2.2 调度关系

```
用户输入
    ↓
[ariz_engine] 总控调度
    │
    ├──→ [ariz_step1_problem]     识别初始问题
    ├──→ [ariz_step2_components]  系统组件分析
    ├──→ [ariz_step3_contacts]    接触关系分析
    ├──→ [ariz_step4_function]    功能建模
    ├──→ [ariz_step5_structure]   系统结构分析
    ├──→ [ariz_step6_summary]     问题总结
    ├──→ [ariz_step7_causal]      因果链分析
    ├──→ [ariz_step8_keypoint]    关键问题定义
    └──→ [ariz_step9_solution]    方案生成

ariz_engine 负责：
- 判断当前处于哪一步
- 调用对应 step skill
- 汇总各步结果
- 维护流程状态（在内存中，通过对话上下文传递）
```

### 2.3 每个 Step Skill 的职责

每个 Step Skill 统一接口：

```python
SKILL = {
    "description": "ARIZ 第N步：XXX",
    "parameters": { ... },  # 该步需要的输入参数
    "func": step_function    # 执行函数
}
```

**输入**：对话上下文 + 上一步结果（JSON）
**输出**：该步分析结果（JSON）+ 需要用户确认/补充的问题

---

## 3. ARIZ 流程定义（9 步）

> ⚠️ 以下为框架定义，待逐步讨论确认

---

### ① 问题识别（ariz_step1_problem）

**目标**：三步聚焦——识别具体系统、明确问题现象、聚焦具体矛盾

**核心原则**：
- 不能笼统说"电池有问题" → 必须定位到具体子系统（箱体/热管理/BMS/...）
- 不能说"散热不好" → 必须是可观测可量化的症状
- 不能说"想降低温度" → 必须提炼出"改善A → 恶化B"的矛盾结构

**输入**：用户的自由文本描述

**处理**：三步追问法
1. **具体系统定位** — 问题发生在哪个子系统？
2. **问题现象明确** — 什么工况下、什么参数超标、超标多少？
3. **聚焦具体矛盾** — 核心矛盾是什么？（改善XX → 恶化YY）

**输出**：

```json
{
  "problem_object": "方形铝壳电池PACK液冷热管理系统",
  "phenomenon": "2C倍率连续放电30min后，电芯最高温度48°C，最低37°C，温差11°C，超过设计指标",
  "constraints": ["不增加冷却系统重量", "不增加系统功耗", "成本增幅<5%"],
  "goal": "最高温度≤40°C，温差≤5°C",
  "contradiction_hint": "提高散热能力 → 增加重量/成本/功耗",
  "clarification_needed": ["环境温度范围？", "现有冷却方案？", "是否已尝试过其他方案？"]
}
```

---

### ② 系统组件分析（ariz_step2_components）

**目标**：分解问题系统，识别超系统/系统/子系统所有组件

**输入**：① 的输出

**输出**：

```json
{
  "supersystem": "整车底盘环境（-30°C~55°C）",
  "system_name": "方形铝壳电池PACK液冷系统",
  "subsystems": ["电芯模组", "冷却板", "冷却液", ...]
}
```

---

### ③ 接触关系分析（ariz_step3_contacts）

**目标**：分析各组件间的接触/交互关系

**输入**：② 的输出

**输出**：

```json
{
  "contacts": [
    {
      "component_a": "电芯模组",
      "component_b": "冷却板",
      "contact_type": "热传导",
      "interface": "导热垫",
      "confirmed": true
    }
  ]
}
```

---

### ④ 功能建模（ariz_step4_function）

**目标**：建立系统功能模型图

**输入**：② 的输出 + ③ 的输出

**输出**：

```json
{
  "functions": [
    {
      "source": "冷却板",
      "target": "电芯模组",
      "function": "散热",
      "type": "insufficient",
      "description": "..."
    }
  ]
}
```

---

### ⑤ 系统结构分析（ariz_step5_structure）

**目标**：分析系统空间结构，识别布局约束

**输入**：② 的输出 + 用户补充

**输出**：

```json
{
  "dimensions": "...",
  "layout_constraints": ["..."],
  "structural_bottlenecks": ["..."]
}
```

---

### ⑥ 功能建模问题总结（ariz_step6_summary）

**目标**：从功能模型中提取并分类所有问题

**输入**：④ 的输出 + ⑤ 的输出

**输出**：

```json
{
  "insufficient_functions": ["..."],
  "harmful_functions": ["..."],
  "excessive_functions": ["..."],
  "missing_functions": ["..."],
  "total_count": 6,
  "priority_hint": "建议优先解决：散热不足、导热系数偏低"
}
```

---

### ⑦ 因果链分析（ariz_step7_causal）

**目标**：从表层问题追溯根因

**输入**：⑥ 的输出（选中的重点问题）

**输出**：

```json
{
  "problem": "冷却板散热能力不足",
  "chain": [
    {"level": 1, "cause": "冷却液流速不够"},
    {"level": 2, "cause": "水泵功率受限"},
    {"level": 3, "cause": "系统功耗预算限制", "is_root": true}
  ],
  "entry_points": ["流道设计优化", "导热材料升级"]
}
```

---

### ⑧ 关键问题/切入点定义（ariz_step8_keypoint）

**目标**：定义核心矛盾 + 理想最终状态

**输入**：⑦ 的输出

**输出**：

```json
{
  "technical_contradictions": [
    {"improve": "散热效率", "worsen": "重量/成本"}
  ],
  "physical_contradictions": [
    {"parameter": "冷却液流量", "want_large": "散热好", "want_small": "能耗低"}
  ],
  "ifr": "冷却系统自身不增加重量/体积/成本，却能完美散热",
  "selected_focus": "TC1"
}
```

---

### ⑨ 生成创新方案（ariz_step9_solution）

**目标**：基于矛盾和原理，生成具体解决方案

**输入**：⑧ 的输出 + ②③④ 的上下文

**输出**：

```json
{
  "solutions": [
    {
      "title": "相变材料辅助散热",
      "principle": "参数变化",
      "description": "...",
      "pros": ["..."],
      "cons": ["..."],
      "feasibility": "medium",
      "estimated_effect": "峰值温度降低5-8°C"
    }
  ]
}
```

---

## 4. 流程控制逻辑

### 4.1 步骤状态

```python
ARIZ_STATES = [
    "problem",      # ① 问题识别
    "components",   # ② 系统组件分析
    "contacts",     # ③ 接触关系分析
    "function",     # ④ 功能建模
    "structure",    # ⑤ 系统结构分析
    "summary",      # ⑥ 问题总结
    "causal",       # ⑦ 因果链分析
    "keypoint",     # ⑧ 关键问题
    "solution",     # ⑨ 方案生成
]
```

### 4.2 调度规则

```
1. 用户说"开始分析"或提出问题 → 进入 step1
2. 每步完成后：
   - 输出该步结果
   - 问用户"是否确认？需要补充/修改？"
   - 用户确认 → 自动进入下一步
   - 用户要求修改 → 在当前步内调整
3. 用户可随时说"跳到第X步"或"重新分析第X步"
4. 所有步完成后输出完整报告
```

---

## 5. 待讨论

**逐步确认以下内容：**

1. 每步的输入/输出字段是否准确？
2. 每步需要向用户追问哪些问题？
3. 各步之间的数据依赖是否正确？
4. 是否有遗漏的分析维度？
