"""Xagent - Agent 项目主入口"""
import json
import os
import structlog
from flask import Flask, request, Response, jsonify
from flask_cors import CORS
from dotenv import load_dotenv
from openai import OpenAI

from skills import SKILLS

load_dotenv()

# ---- 结构化日志 ----
structlog.configure(
    processors=[
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.add_log_level,
        structlog.dev.ConsoleRenderer(),
    ],
)
logger = structlog.get_logger()

# ---- Flask 初始化 ----
app = Flask(__name__)
CORS(app)

# ---- LLM 客户端（Xiaomi MiMo） ----
client = OpenAI(
    api_key=os.getenv("XIAOMI_API_KEY"),
    base_url=os.getenv("XIAOMI_BASE_URL"),
)
MODEL = os.getenv("XIAOMI_MODEL", "mimo-v2.5")

logger.info("xagent_started", model=MODEL, skills=list(SKILLS.keys()))

# ---- 构建工具定义 ----
def build_tools():
    tools = []
    for name, skill_info in SKILLS.items():
        tools.append({
            "type": "function",
            "function": {
                "name": name,
                "description": skill_info["description"],
                "parameters": skill_info["parameters"],
            }
        })
    return tools

# ---- SSE 流式聊天接口 ----
@app.route("/api/chat", methods=["POST"])
def chat():
    data = request.json
    messages = data.get("messages", [])
    logger.info("chat_received", message_count=len(messages))

    def generate():
        tools = build_tools()
        
        # 收集工具调用信息
        tool_calls = {}
        
        response = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "system", "content": "你是一个智能助手，可以根据需要调用工具完成任务。"}] + messages,
            tools=tools if tools else None,
            stream=True,
        )

        for chunk in response:
            if not chunk.choices:
                continue
            
            delta = chunk.choices[0].delta

            # 处理工具调用
            if delta.tool_calls:
                for tc in delta.tool_calls:
                    tc_index = tc.index
                    if tc_index not in tool_calls:
                        tool_calls[tc_index] = {"id": tc.id, "name": "", "arguments": ""}
                    
                    if tc.function:
                        if tc.function.name:
                            tool_calls[tc_index]["name"] = tc.function.name
                        if tc.function.arguments:
                            tool_calls[tc_index]["arguments"] += tc.function.arguments

            # 流式文本
            if delta.content:
                yield f'data: {json.dumps({"type": "content", "text": delta.content}, ensure_ascii=False)}\n\n'

        # 执行收集到的工具调用
        for tc_index, tc_info in tool_calls.items():
            func_name = tc_info["name"]
            if func_name and func_name in SKILLS:
                try:
                    args = json.loads(tc_info["arguments"]) if tc_info["arguments"] else {}
                except json.JSONDecodeError:
                    args = {}
                
                logger.info("tool_called", tool=func_name, args=list(args.keys()))
                try:
                    result = SKILLS[func_name]["func"](**args)
                    logger.info("tool_completed", tool=func_name)
                except Exception as e:
                    result = {"error": str(e)}
                    logger.error("tool_failed", tool=func_name, error=str(e))
                
                yield f'data: {json.dumps({"type": "tool_result", "tool": func_name, "result": result}, ensure_ascii=False)}\n\n'

        yield "data: [DONE]\n\n"

    return Response(generate(), mimetype="text/event-stream")

# ---- 获取可用 Skill 列表 ----
@app.route("/api/skills", methods=["GET"])
def list_skills():
    return jsonify([
        {"name": name, "description": info["description"]}
        for name, info in SKILLS.items()
    ])

if __name__ == "__main__":
    port = int(os.getenv("FLASK_PORT", 8000))
    debug = os.getenv("FLASK_DEBUG", "true").lower() == "true"
    logger.info("server_starting", port=port, debug=debug)
    app.run(port=port, debug=debug)
