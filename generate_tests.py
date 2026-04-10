import anthropic
import os

client = anthropic.Anthropic(api_key=os.environ["ANTHROPIC_API_KEY"])

with open("changed_files.txt") as f:
    files = [l.strip() for l in f if l.strip()]

if not files:
    print("변경된 파일 없음, 종료")
    exit(0)

for filepath in files:
    if not os.path.exists(filepath):
        continue

    with open(filepath) as f:
        source_code = f.read()

    print(f"테스트 생성 중: {filepath}")

    prompt = f"아래 FastAPI 코드에 대한 pytest 테스트 코드를 작성해줘.\n\n규칙:\n- pytest와 httpx의 TestClient 사용\n- 각 엔드포인트별 정상/실패 케이스 모두 포함\n- 한국어 docstring으로 각 테스트 설명\n- 코드만 출력하고 다른 설명은 하지 마\n\n파일 경로: {filepath}\n\n소스 코드:\n{source_code}"

    message = client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}]
    )

    test_code = message.content[0].text

    if "```python" in test_code:
        test_code = test_code.split("```python")[1].split("```")[0].strip()

    filename = os.path.basename(filepath).replace(".py", "")
    test_path = f"fastapi-app/tests/test_{filename}_generated.py"
    os.makedirs("fastapi-app/tests", exist_ok=True)

    with open(test_path, "w") as f:
        f.write(test_code)

    print(f"생성 완료: {test_path}")
