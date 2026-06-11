-- Xagent 系统组件知识库
-- 稳定存储系统/子系统/功能映射，供 ARIZ Step 2 调用

-- 系统表（顶层系统分类）
CREATE TABLE IF NOT EXISTS systems (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,          -- "热管理系统"
    description TEXT,                    -- "负责PACK温度控制，含加热和冷却"
    pack_type TEXT DEFAULT 'generic',    -- 适用的PACK类型：generic/方形/圆柱/软包
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);

-- 子系统/组件表（挂在某个系统下）
CREATE TABLE IF NOT EXISTS components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    system_id INTEGER NOT NULL,          -- 所属系统
    name TEXT NOT NULL,                  -- "冷却板"
    description TEXT,                    -- "液冷系统的核心散热部件"
    is_core INTEGER DEFAULT 0,          -- 是否为核心组件（1=是）
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (system_id) REFERENCES systems(id) ON DELETE CASCADE,
    UNIQUE(system_id, name)
);

-- 组件功能表（一个组件可以有多个功能）
CREATE TABLE IF NOT EXISTS component_functions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id INTEGER NOT NULL,
    function_name TEXT NOT NULL,         -- "散热"
    function_type TEXT DEFAULT 'useful', -- useful/primary/supporting
    description TEXT,                    -- "通过液冷循环带走电芯热量"
    target TEXT,                         -- 功能作用对象："电芯模组"
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (component_id) REFERENCES components(id) ON DELETE CASCADE
);

-- 组件关系表（组件之间的典型接触/交互关系）
CREATE TABLE IF NOT EXISTS component_relations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_a_id INTEGER NOT NULL,
    component_b_id INTEGER NOT NULL,
    relation_type TEXT NOT NULL,         -- "热传导"/"对流换热"/"机械固定"/"电气连接"
    interface_desc TEXT,                 -- "导热垫界面"
    is_typical INTEGER DEFAULT 1,       -- 是否为典型关系
    FOREIGN KEY (component_a_id) REFERENCES components(id) ON DELETE CASCADE,
    FOREIGN KEY (component_b_id) REFERENCES components(id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX IF NOT EXISTS idx_components_system ON components(system_id);
CREATE INDEX IF NOT EXISTS idx_functions_component ON component_functions(component_id);
CREATE INDEX IF NOT EXISTS idx_relations_a ON component_relations(component_a_id);
CREATE INDEX IF NOT EXISTS idx_relations_b ON component_relations(component_b_id);
