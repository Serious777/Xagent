"""组件知识库 — 数据库读写层"""
import os
import sqlite3
import structlog

logger = structlog.get_logger()

DB_PATH = os.path.join(os.path.dirname(__file__), "components.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "db_schema.sql")


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    """初始化数据库表"""
    conn = get_db()
    with open(SCHEMA_PATH) as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()
    logger.info("component_db_initialized", path=DB_PATH)


def search_system(keyword: str) -> list:
    """
    根据关键词搜索系统。
    用于 ARIZ Step 1 → Step 2 过渡：
    用户说"热管理有问题"，匹配到"热管理系统"。
    """
    conn = get_db()
    rows = conn.execute(
        "SELECT id, name, description FROM systems WHERE name LIKE ? OR description LIKE ?",
        (f"%{keyword}%", f"%{keyword}%"),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_system_components(system_id: int) -> dict:
    """
    获取某个系统下的所有组件及其功能。
    返回完整结构，供 ARIZ Step 2 使用。
    """
    conn = get_db()

    # 获取系统信息
    system = conn.execute(
        "SELECT id, name, description FROM systems WHERE id = ?", (system_id,)
    ).fetchone()
    if not system:
        conn.close()
        return {"error": f"系统ID {system_id} 不存在"}

    system_dict = dict(system)

    # 获取组件
    components = conn.execute(
        "SELECT id, name, description, is_core FROM components WHERE system_id = ?",
        (system_id,),
    ).fetchall()

    component_list = []
    for comp in components:
        comp_dict = dict(comp)

        # 获取组件功能
        functions = conn.execute(
            "SELECT function_name, function_type, description, target "
            "FROM component_functions WHERE component_id = ?",
            (comp["id"],),
        ).fetchall()
        comp_dict["functions"] = [dict(f) for f in functions]

        component_list.append(comp_dict)

    # 获取组件间关系
    relations = conn.execute(
        """
        SELECT ca.name as component_a, cb.name as component_b,
               r.relation_type, r.interface_desc
        FROM component_relations r
        JOIN components ca ON r.component_a_id = ca.id
        JOIN components cb ON r.component_b_id = cb.id
        WHERE ca.system_id = ? AND cb.system_id = ?
        """,
        (system_id, system_id),
    ).fetchall()

    conn.close()

    return {
        "system": system_dict,
        "components": component_list,
        "relations": [dict(r) for r in relations],
    }


def get_all_systems() -> list:
    """列出所有已录入的系统"""
    conn = get_db()
    rows = conn.execute("SELECT id, name, description FROM systems ORDER BY id").fetchall()
    conn.close()
    return [dict(r) for r in rows]


def add_system(name: str, description: str = "") -> int:
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO systems (name, description) VALUES (?, ?)",
        (name, description),
    )
    conn.commit()
    system_id = cursor.lastrowid
    conn.close()
    return system_id


def add_component(system_id: int, name: str, description: str = "", is_core: int = 0) -> int:
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO components (system_id, name, description, is_core) VALUES (?, ?, ?, ?)",
        (system_id, name, description, is_core),
    )
    conn.commit()
    comp_id = cursor.lastrowid
    conn.close()
    return comp_id


def add_function(component_id: int, function_name: str, description: str = "",
                 function_type: str = "useful", target: str = "") -> int:
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO component_functions (component_id, function_name, function_type, description, target) "
        "VALUES (?, ?, ?, ?, ?)",
        (component_id, function_name, function_type, description, target),
    )
    conn.commit()
    func_id = cursor.lastrowid
    conn.close()
    return func_id


def add_relation(component_a_id: int, component_b_id: int,
                 relation_type: str, interface_desc: str = "") -> int:
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO component_relations (component_a_id, component_b_id, relation_type, interface_desc) "
        "VALUES (?, ?, ?, ?)",
        (component_a_id, component_b_id, relation_type, interface_desc),
    )
    conn.commit()
    rel_id = cursor.lastrowid
    conn.close()
    return rel_id
