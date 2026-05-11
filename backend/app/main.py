"""
智学导评 V0.2 后端入口。

This is the backend entry point for the V0.2 AI Guided SQL Assessment Platform.

当前文件只是项目骨架占位，用于确认目录结构。
正式施工时由 Codex 根据 docs/ 中的需求文档逐步实现。
"""

from fastapi import FastAPI

app = FastAPI(title="AI Guided SQL Assessment")


@app.get("/")
def read_root():
    """返回系统健康检查信息。Return a simple health-check message."""
    return {"message": "AI Guided SQL Assessment V0.2"}
