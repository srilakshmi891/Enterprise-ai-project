from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

def test_flow():
    client = TestClient(app)
    
    # 1. Login
    r = client.post("/auth/login", json={"username": "sree_dev2026", "password": "Sree@2026"})
    print("1. Login status:", r.status_code)
    assert r.status_code == 200, f"Login failed: {r.text}"
    token = r.json()["access_token"]
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Get /auth/me
    r_me = client.get("/auth/me", headers=headers)
    print("2. /auth/me status:", r_me.status_code, r_me.json())
    assert r_me.status_code == 200
    
    # 3. Simulate GitHub upstream 401 error (e.g. invalid/expired GITHUB_TOKEN)
    mock_resp = httpx.Response(status_code=401, text="Bad credentials", request=httpx.Request("GET", "https://api.github.com/user/repos"))
    with patch.object(settings, "GITHUB_TOKEN", "ghp_invalidtoken123"):
        with patch("httpx.AsyncClient.get", return_value=mock_resp):
            r_gh_err = client.get("/github/repos", headers=headers)
            print("3. Simulated GitHub 401 returned backend status:", r_gh_err.status_code, r_gh_err.json())
            # MUST return 502 Bad Gateway to the frontend, NEVER 401!
            assert r_gh_err.status_code == 502, f"Expected 502 Bad Gateway for upstream error, got {r_gh_err.status_code}"

    # 4. Simulate Jira upstream 401 error
    mock_jira_resp = httpx.Response(status_code=401, text="Unauthorized", request=httpx.Request("GET", "https://mock.atlassian.net/rest/api/3/project"))
    with patch.object(settings, "JIRA_API_TOKEN", "jira_invalid_token"):
        with patch("httpx.AsyncClient.get", return_value=mock_jira_resp):
            r_jira_err = client.get("/jira/projects", headers=headers)
            print("4. Simulated Jira 401 returned backend status:", r_jira_err.status_code, r_jira_err.json())
            # MUST return 502 Bad Gateway to the frontend, NEVER 401!
            assert r_jira_err.status_code == 502, f"Expected 502 Bad Gateway for upstream error, got {r_jira_err.status_code}"

    # 5. Get /github/repos WITHOUT JWT
    r_no_jwt = client.get("/github/repos")
    print("5. /github/repos without JWT status:", r_no_jwt.status_code)
    assert r_no_jwt.status_code == 401, f"Should return 401 when JWT is missing: {r_no_jwt.text}"
    
    print("\n==================================================")
    print("SUCCESS: ALL AUTH & SESSION PERSISTENCE TESTS PASSED!")
    print("==================================================")

if __name__ == "__main__":
    test_flow()
