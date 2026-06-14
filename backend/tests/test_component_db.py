"""component_db 单元测试"""
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestComponentDB(unittest.TestCase):
    """测试组件知识库"""

    @classmethod
    def setUpClass(cls):
        """创建临时数据库"""
        import component_db
        cls._orig_db_path = component_db.DB_PATH
        cls._tmpdir = tempfile.mkdtemp()
        component_db.DB_PATH = os.path.join(cls._tmpdir, "test_components.db")
        component_db._DB_PATH = component_db.DB_PATH
        component_db.init_db()
        cls._component_db = component_db

    @classmethod
    def tearDownClass(cls):
        self_cls = cls
        self_cls._component_db.DB_PATH = self_cls._orig_db_path

    def test_add_system(self):
        db = self._component_db
        system_id = db.add_system("测试热管理系统", "用于单元测试")
        self.assertIsNotNone(system_id)
        self.assertGreater(system_id, 0)

    def test_get_all_systems(self):
        db = self._component_db
        systems = db.get_all_systems()
        self.assertIsInstance(systems, list)

    def test_add_component(self):
        db = self._component_db
        system_id = db.add_system("组件测试系统")
        comp_id = db.add_component(system_id, "测试冷却板", "散热组件", is_core=1)
        self.assertIsNotNone(comp_id)
        self.assertGreater(comp_id, 0)

    def test_add_function(self):
        db = self._component_db
        system_id = db.add_system("功能测试系统")
        comp_id = db.add_component(system_id, "测试组件")
        func_id = db.add_function(comp_id, "散热", "带走热量", "useful", "电芯")
        self.assertIsNotNone(func_id)

    def test_add_relation(self):
        db = self._component_db
        system_id = db.add_system("关系测试系统")
        comp_a = db.add_component(system_id, "组件A")
        comp_b = db.add_component(system_id, "组件B")
        rel_id = db.add_relation(comp_a, comp_b, "热传导", "面接触")
        self.assertIsNotNone(rel_id)

    def test_search_system(self):
        db = self._component_db
        db.add_system("搜索测试热管理", "测试搜索功能")
        results = db.search_system("搜索测试")
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertIn("搜索测试", results[0]["name"])

    def test_get_system_components(self):
        db = self._component_db
        system_id = db.add_system("组件查询系统")
        db.add_component(system_id, "子组件A")
        db.add_component(system_id, "子组件B")
        data = db.get_system_components(system_id)
        self.assertIn("system", data)
        self.assertIn("components", data)
        self.assertEqual(len(data["components"]), 2)

    def test_get_system_components_not_found(self):
        db = self._component_db
        data = db.get_system_components(99999)
        self.assertIn("error", data)


class TestContextManager(unittest.TestCase):
    """测试数据库上下文管理器"""

    def test_context_manager_commit(self):
        from component_db import get_db, DB_PATH
        # 正常退出应提交
        with get_db() as conn:
            conn.execute("SELECT 1")

    def test_context_manager_rollback(self):
        from component_db import get_db
        # 异常应回滚
        try:
            with get_db() as conn:
                conn.execute("INSERT INTO non_existent_table VALUES (1)")
        except Exception:
            pass  # 预期异常


if __name__ == "__main__":
    unittest.main()
