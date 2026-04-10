import pytest
import json
import os
from httpx import AsyncClient
from fastapi.testclient import TestClient
from main import app, TODO_FILE

client = TestClient(app)

@pytest.fixture(autouse=True)
def cleanup_todo_file():
    """테스트 실행 전후로 todo.json 파일을 정리합니다."""
    # 테스트 전 기존 파일 백업
    backup_file = None
    if os.path.exists(TODO_FILE):
        backup_file = f"{TODO_FILE}.backup"
        os.rename(TODO_FILE, backup_file)
    
    yield
    
    # 테스트 후 정리
    if os.path.exists(TODO_FILE):
        os.remove(TODO_FILE)
    
    # 백업 파일 복원
    if backup_file and os.path.exists(backup_file):
        os.rename(backup_file, TODO_FILE)

@pytest.fixture
def sample_todo():
    """테스트용 샘플 Todo 항목을 제공합니다."""
    return {
        "id": 1,
        "title": "테스트 할일",
        "description": "테스트용 설명",
        "completed": False,
        "due_date": "2024-12-31"
    }

@pytest.fixture
def sample_todos():
    """테스트용 복수의 Todo 항목을 제공합니다."""
    return [
        {
            "id": 1,
            "title": "첫 번째 할일",
            "description": "첫 번째 설명",
            "completed": False,
            "due_date": "2024-12-31"
        },
        {
            "id": 2,
            "title": "두 번째 할일",
            "description": "두 번째 설명",
            "completed": True,
            "due_date": None
        }
    ]

class TestGetTodos:
    def test_get_todos_empty_list(self):
        """빈 Todo 목록을 조회할 때 빈 리스트를 반환하는지 테스트합니다."""
        response = client.get("/todos")
        assert response.status_code == 200
        assert response.json() == []

    def test_get_todos_with_data(self, sample_todos):
        """기존 Todo 항목들이 있을 때 정상적으로 조회되는지 테스트합니다."""
        # 테스트 데이터 저장
        with open(TODO_FILE, "w") as file:
            json.dump(sample_todos, file)
        
        response = client.get("/todos")
        assert response.status_code == 200
        assert response.json() == sample_todos

class TestCreateTodo:
    def test_create_todo_success(self, sample_todo):
        """새로운 Todo 항목을 성공적으로 생성하는지 테스트합니다."""
        response = client.post("/todos", json=sample_todo)
        assert response.status_code == 200
        assert response.json() == sample_todo
        
        # 파일에 저장되었는지 확인
        with open(TODO_FILE, "r") as file:
            todos = json.load(file)
            assert len(todos) == 1
            assert todos[0] == sample_todo

    def test_create_todo_without_due_date(self):
        """due_date 없이 Todo 항목을 생성하는지 테스트합니다."""
        todo_data = {
            "id": 1,
            "title": "할일",
            "description": "설명",
            "completed": False
        }
        response = client.post("/todos", json=todo_data)
        assert response.status_code == 200
        response_data = response.json()
        assert response_data["due_date"] is None

    def test_create_todo_invalid_data(self):
        """잘못된 데이터로 Todo 항목 생성 시 실패하는지 테스트합니다."""
        invalid_todo = {
            "id": "invalid_id",  # 문자열은 int가 아님
            "title": "제목",
            "description": "설명",
            "completed": False
        }
        response = client.post("/todos", json=invalid_todo)
        assert response.status_code == 422

    def test_create_todo_missing_required_fields(self):
        """필수 필드가 없을 때 Todo 항목 생성이 실패하는지 테스트합니다."""
        incomplete_todo = {
            "title": "제목만 있음"
        }
        response = client.post("/todos", json=incomplete_todo)
        assert response.status_code == 422

class TestUpdateTodo:
    def test_update_todo_success(self, sample_todos):
        """기존 Todo 항목을 성공적으로 수정하는지 테스트합니다."""
        # 테스트 데이터 저장
        with open(TODO_FILE, "w") as file:
            json.dump(sample_todos, file)
        
        updated_todo = {
            "id": 1,
            "title": "수정된 제목",
            "description": "수정된 설명",
            "completed": True,
            "due_date": "2025-01-01"
        }
        
        response = client.put("/todos/1", json=updated_todo)
        assert response.status_code == 200
        assert response.json() == updated_todo
        
        # 파일에 수정사항이 저장되었는지 확인
        with open(TODO_FILE, "r") as file:
            todos = json.load(file)
            updated_item = next(todo for todo in todos if todo["id"] == 1)
            assert updated_item["title"] == "수정된 제목"
            assert updated_item["completed"] == True

    def test_update_todo_not_found(self):
        """존재하지 않는 Todo 항목 수정 시 404 에러가 발생하는지 테스트합니다."""
        updated_todo = {
            "id": 999,
            "title": "존재하지 않는 항목",
            "description": "설명",
            "completed": False
        }
        
        response = client.put("/todos/999", json=updated_todo)
        assert response.status_code == 404
        assert "To-Do item not found" in response.json()["detail"]

    def test_update_todo_invalid_data(self, sample_todos):
        """잘못된 데이터로 Todo 항목 수정 시 실패하는지 테스트합니다."""
        # 테스트 데이터 저장
        with open(TODO_FILE, "w") as file:
            json.dump(sample_todos, file)
        
        invalid_update = {
            "id": "invalid",
            "title": "제목",
            "description": "설명",
            "completed": "not_boolean"
        }
        
        response = client.put("/todos/1", json=invalid_update)
        assert response.status_code == 422

class TestDeleteTodo:
    def test_delete_todo_success(self, sample_todos):
        """기존 Todo 항목을 성공적으로 삭제하는지 테스트합니다."""
        # 테스트 데이터 저장
        with open(TODO_FILE, "w") as file:
            json.dump(sample_todos, file)
        
        response = client.delete("/todos/1")
        assert response.status_code == 200
        assert response.json() == {"message": "To-Do item deleted"}
        
        # 파일에서 삭제되었는지 확인
        with open(TODO_FILE, "r") as file:
            todos = json.load(file)
            assert len(todos) == 1
            assert todos[0]["id"] == 2

    def test_delete_todo_not_exists(self):
        """존재하지 않는 Todo 항목 삭제 시에도 성공 메시지를 반환하는지 테스트합니다."""
        response = client.delete("/todos/999")
        assert response.status_code == 200
        assert response.json() == {"message": "To-Do item deleted"}

    def test_delete_all_todos(self, sample_todos):
        """모든 Todo 항목을 삭제할 수 있는지 테스트합니다."""
        # 테스트 데이터 저장
        with open(TODO_FILE, "w") as file:
            json.dump(sample_todos, file)
        
        # 모든 항목 삭제
        for todo in sample_todos:
            response = client.delete(f"/todos/{todo['id']}")
            assert response.status_code == 200
        
        # 빈 파일 확인
        with open(TODO_FILE, "r") as file:
            todos = json.load(file)
            assert len(todos) == 0

class TestRootEndpoint:
    def test_read_root_success(self):
        """루트 엔드포인트가 HTML을 성공적으로 반환하는지 테스트합니다."""
        template_path = "templates/index.html"
        original_content = None

        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                original_content = f.read()

        os.makedirs("templates", exist_ok=True)
        test_html = "<html><body><h1>Test Page</h1></body></html>"

        with open(template_path, "w", encoding="utf-8") as file:
            file.write(test_html)

        try:
            response = client.get("/")
            assert response.status_code == 200
            assert response.headers["content-type"] == "text/html; charset=utf-8"
            assert "Test Page" in response.text
        finally:
            if original_content is not None:
                with open(template_path, "w", encoding="utf-8") as f:
                    f.write(original_content)
            else:
                if os.path.exists(template_path):
                    os.remove(template_path)
                if os.path.exists("templates"):
                    os.rmdir("templates")

    def test_read_root_file_not_found(self):
        """HTML 파일이 없을 때 에러가 발생하는지 테스트합니다."""
        template_path = "templates/index.html"
        original_content = None

        if os.path.exists(template_path):
            with open(template_path, "r", encoding="utf-8") as f:
                original_content = f.read()
            os.remove(template_path)

        try:
            response = client.get("/")
            assert response.status_code == 500
        finally:
            if original_content is not None:
                with open(template_path, "w", encoding="utf-8") as f:
                    f.write(original_content)