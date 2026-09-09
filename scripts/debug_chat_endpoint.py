import sys
from pathlib import Path

root_dir = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_dir))

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)

print("Sending POST /api/chat...")
response = client.post("/api/chat", json={"message": "What is the minimum attendance requirement?"})
print("STATUS CODE:", response.status_code)
print("RESPONSE BODY:", response.text)
