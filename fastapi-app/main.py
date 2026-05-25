from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
from datetime import date
import json
import os
import logging
import time
from multiprocessing import Queue
from pathlib import Path
from prometheus_fastapi_instrumentator import Instrumentator
from logging_loki import LokiQueueHandler

BASE_DIR = Path(__file__).parent

app = FastAPI()
Instrumentator().instrument(app).expose(app)

# Loki 로그 핸들러 설정
loki_url = os.getenv("LOKI_ENDPOINT", "http://loki:3100/loki/api/v1/push")
loki_handler = LokiQueueHandler(
    Queue(-1),
    url=loki_url,
    tags={"application": "fastapi"},
    version="1",
)
custom_logger = logging.getLogger("custom.access")
custom_logger.setLevel(logging.INFO)
custom_logger.addHandler(loki_handler)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start_time = time.time()
    response = await call_next(request)
    duration = time.time() - start_time
    custom_logger.info(
        f'{request.client.host} - "{request.method} {request.url.path}" '
        f'{response.status_code} {duration:.3f}s'
    )
    return response

# To-Do 항목 모델
class TodoItem(BaseModel):
    id: int
    title: str
    description: str
    completed: bool
    due_date: Optional[str] = None
    created_at: Optional[str] = None
    priority: Optional[str] = "green"
    category: Optional[str] = None

# JSON 파일 경로
TODO_FILE = "todo.json"

# JSON 파일에서 To-Do 항목 로드
def load_todos():
    if os.path.exists(TODO_FILE):
        with open(TODO_FILE, "r") as file:
            return json.load(file)
    return []

# JSON 파일에 To-Do 항목 저장
def save_todos(todos):
    with open(TODO_FILE, "w") as file:
        json.dump(todos, file, indent=4)

# To-Do 목록 조회
@app.get("/todos", response_model=list[TodoItem])
def get_todos():
    return load_todos()

# 신규 To-Do 항목 추가
@app.post("/todos", response_model=TodoItem)
def create_todo(todo: TodoItem):
    todos = load_todos()
    data = todo.model_dump()
    if not data.get("created_at"):
        data["created_at"] = date.today().isoformat()
    todos.append(data)
    save_todos(todos)
    return TodoItem(**data)

# To-Do 항목 수정
@app.put("/todos/{todo_id}", response_model=TodoItem)
def update_todo(todo_id: int, updated_todo: TodoItem):
    todos = load_todos()
    for todo in todos:
        if todo["id"] == todo_id:
            data = updated_todo.model_dump()
            if not data.get("created_at"):
                data["created_at"] = todo.get("created_at")
            todo.update(data)
            save_todos(todos)
            return TodoItem(**todo)
    raise HTTPException(status_code=404, detail="To-Do item not found")

# To-Do 항목 삭제
@app.delete("/todos/{todo_id}", response_model=dict)
def delete_todo(todo_id: int):
    todos = load_todos()
    todos = [todo for todo in todos if todo["id"] != todo_id]
    save_todos(todos)
    return {"message": "To-Do item deleted"}

# HTML 파일 서빙
@app.get("/", response_class=HTMLResponse, responses={500: {"description": "Template file not found"}})
def read_root():
    try:
        with open(BASE_DIR / "templates" / "index.html", "r", encoding="utf-8") as file:
            content = file.read()
        return HTMLResponse(content=content)
    except FileNotFoundError:
        raise HTTPException(status_code=500, detail="Template file not found")

