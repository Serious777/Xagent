"""Flask API 集成测试"""
import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


class TestFlaskAPI(unittest.TestCase):
    """测试 Flask API 路由"""

    @classmethod
    def setUpClass(cls):
        from app import app, DB_PATH
        cls._orig_db = DB_PATH
        cls._tmpdir = tempfile.mkdtemp()
        # 使用临时数据库
        import app as app_module
        app_module.DB_PATH = os.path.join(cls._tmpdir, "test_xagent.db")
        app_module.init_db()
        cls.client = app.test_client()

    @classmethod
    def tearDownClass(cls):
        import app as app_module
        app_module.DB_PATH = cls._orig_db

    def test_list_conversations_empty(self):
        resp = self.client.get("/api/conversations")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIsInstance(data, list)

    def test_create_conversation(self):
        resp = self.client.post("/api/conversations")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIn("id", data)
        self.assertEqual(data["title"], "新对话")
        return data["id"]

    def test_create_and_delete_conversation(self):
        # 创建
        resp = self.client.post("/api/conversations")
        data = json.loads(resp.data)
        conv_id = data["id"]

        # 删除
        resp = self.client.delete(f"/api/conversations/{conv_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.data)["ok"])

    def test_update_conversation_title(self):
        resp = self.client.post("/api/conversations")
        conv_id = json.loads(resp.data)["id"]

        resp = self.client.patch(
            f"/api/conversations/{conv_id}",
            data=json.dumps({"title": "新标题"}),
            content_type="application/json",
        )
        self.assertEqual(resp.status_code, 200)

    def test_get_messages_empty(self):
        resp = self.client.post("/api/conversations")
        conv_id = json.loads(resp.data)["id"]

        resp = self.client.get(f"/api/conversations/{conv_id}/messages")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(len(data), 0)

    def test_ariz_status(self):
        resp = self.client.post("/api/conversations")
        conv_id = json.loads(resp.data)["id"]

        resp = self.client.get(f"/api/ariz/status/{conv_id}")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertEqual(data["current_step"], "problem")

    def test_ariz_reset(self):
        resp = self.client.post("/api/conversations")
        conv_id = json.loads(resp.data)["id"]

        resp = self.client.post(f"/api/ariz/reset/{conv_id}")
        self.assertEqual(resp.status_code, 200)
        self.assertTrue(json.loads(resp.data)["ok"])

    def test_ariz_confirm_no_result(self):
        resp = self.client.post("/api/conversations")
        conv_id = json.loads(resp.data)["id"]

        resp = self.client.post(f"/api/ariz/confirm/{conv_id}")
        self.assertEqual(resp.status_code, 400)

    def test_list_skills(self):
        resp = self.client.get("/api/skills")
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.data)
        self.assertIsInstance(data, list)

    def test_error_handler_404(self):
        resp = self.client.get("/api/nonexistent")
        self.assertEqual(resp.status_code, 404)


if __name__ == "__main__":
    unittest.main()
