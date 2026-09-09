from unittest.mock import patch
import httpx
from fastapi.testclient import TestClient
from app.main import app
from app.config import settings

from app.database import Base, engine, SessionLocal
from app.schemas.auth import UserRegister
from app.services.auth_service import register_user

def run_integration_tests():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        register_user(db, UserRegister(
            username="sree_dev2026",
            email="sree_dev2026@enterprise.com",
            password="Sree@2026"
        ))
    except Exception:
        pass
    finally:
        db.close()

    client = TestClient(app)
    
    # 1. Login to get authenticated JWT
    login_res = client.post("/auth/login", json={"username": "sree_dev2026", "password": "Sree@2026"})
    assert login_res.status_code == 200, f"Login failed: {login_res.text}"
    token = login_res.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    print("[PASS] 1. Authentication successful, JWT token obtained.")

    # -------------------------------------------------------------
    # GITHUB INTEGRATION TESTS
    # -------------------------------------------------------------
    # 2. List Repositories
    repos_res = client.get("/github/repos", headers=headers)
    assert repos_res.status_code == 200, f"List repos failed: {repos_res.text}"
    repos = repos_res.json()
    assert len(repos) > 0
    repo = repos[0]
    owner = repo["owner"]["login"]
    repo_name = repo["name"]
    print(f"[PASS] 2. GitHub List Repos: Found repository '{owner}/{repo_name}'")

    # 3. Get Repo Details
    detail_res = client.get(f"/github/repos/{owner}/{repo_name}", headers=headers)
    assert detail_res.status_code == 200, f"Repo detail failed: {detail_res.text}"
    print(f"[PASS] 3. GitHub Repo Details: {detail_res.json().get('full_name')}")

    # 4. List Root Files
    files_res = client.get(f"/github/repos/{owner}/{repo_name}/files", headers=headers)
    assert files_res.status_code == 200, f"List files failed: {files_res.text}"
    root_files = files_res.json()
    assert any(f["name"] == "README.md" for f in root_files)
    assert any(f["name"] == "src" and f["type"] == "dir" for f in root_files)
    print(f"[PASS] 4. GitHub Root Files: Found {len(root_files)} items including README.md and src/")

    # 5. List Subdirectory Files (path=src)
    src_files_res = client.get(f"/github/repos/{owner}/{repo_name}/files?path=src", headers=headers)
    assert src_files_res.status_code == 200, f"List subfolder failed: {src_files_res.text}"
    src_files = src_files_res.json()
    assert any(f["name"] == "app.py" for f in src_files)
    print(f"[PASS] 5. GitHub Subdirectory Navigation: Found {len(src_files)} items inside src/")

    # 6. Get File Content (README.md)
    readme_res = client.get(f"/github/repos/{owner}/{repo_name}/file?path=README.md", headers=headers)
    assert readme_res.status_code == 200, f"Get file content failed: {readme_res.text}"
    readme_data = readme_res.json()
    assert "decoded_content" in readme_data and readme_data["decoded_content"] is not None
    print(f"[PASS] 6. GitHub File Content: Successfully read '{readme_data['name']}' ({readme_data['size']} bytes)")

    # 7. Verify GitHub Upstream Error Mapping to 502 (Never 401)
    mock_gh_401 = httpx.Response(status_code=401, text="Bad credentials", request=httpx.Request("GET", "https://api.github.com/user/repos"))
    with patch.object(settings, "GITHUB_TOKEN", "ghp_real_but_expired_token"):
        with patch("httpx.AsyncClient.get", return_value=mock_gh_401):
            err_res = client.get("/github/repos", headers=headers)
            assert err_res.status_code == 502, f"Expected 502 Bad Gateway, got {err_res.status_code}"
            print("[PASS] 7. GitHub Upstream 401 correctly mapped to 502 Bad Gateway.")

    # -------------------------------------------------------------
    # JIRA INTEGRATION TESTS
    # -------------------------------------------------------------
    # 8. List Jira Projects
    proj_res = client.get("/jira/projects", headers=headers)
    assert proj_res.status_code == 200, f"List projects failed: {proj_res.text}"
    projects = proj_res.json()
    assert len(projects) > 0
    project_key = projects[0]["key"]
    print(f"[PASS] 8. Jira List Projects: Found project '{project_key}' ({projects[0]['name']})")

    # 9. Get Jira Project Details
    proj_detail_res = client.get(f"/jira/projects/{project_key}", headers=headers)
    assert proj_detail_res.status_code == 200, f"Project detail failed: {proj_detail_res.text}"
    print(f"[PASS] 9. Jira Project Details: {proj_detail_res.json().get('name')}")

    # 10. Search Issues via JQL (Modern /rest/api/3/search/jql)
    jql_query = f'project = "{project_key}" ORDER BY priority DESC'
    search_res = client.get(f"/jira/search?jql={jql_query}", headers=headers)
    assert search_res.status_code == 200, f"JQL search failed: {search_res.text}"
    search_data = search_res.json()
    assert "issues" in search_data and len(search_data["issues"]) > 0
    first_issue = search_data["issues"][0]
    print(f"[PASS] 10. Jira JQL Search: Found {len(search_data['issues'])} issues for '{jql_query}' (First: {first_issue['key']})")

    # 11. List Project Issues
    proj_issues_res = client.get(f"/jira/projects/{project_key}/issues", headers=headers)
    assert proj_issues_res.status_code == 200, f"Project issues failed: {proj_issues_res.text}"
    print(f"[PASS] 11. Jira Project Backlog: Retrieved {len(proj_issues_res.json()['issues'])} issues.")

    # 12. Get Issue Details
    issue_detail_res = client.get(f"/jira/issues/{first_issue['key']}", headers=headers)
    assert issue_detail_res.status_code == 200, f"Issue detail failed: {issue_detail_res.text}"
    print(f"[PASS] 12. Jira Issue Details: {issue_detail_res.json().get('summary')}")

    # 13. Verify Jira Modern Endpoint /rest/api/3/search/jql Calling in Live/Mock Client
    mock_jira_payload = {
        "startAt": 0,
        "maxResults": 50,
        "total": 1,
        "issues": [
            {
                "id": "20001",
                "key": "REAL-1",
                "fields": {
                    "summary": "Live JQL search endpoint issue",
                    "status": {"name": "In Progress"},
                    "issuetype": {"name": "Story"},
                    "priority": {"name": "High"},
                }
            }
        ]
    }
    # 13. Verify Jira Modern Endpoint POST /rest/api/3/search/jql Calling in Live Client
    mock_jira_payload = {
        "startAt": 0,
        "maxResults": 50,
        "total": 1,
        "issues": [
            {
                "id": "20001",
                "key": "REAL-1",
                "fields": {
                    "summary": "Live JQL search endpoint issue",
                    "status": {"name": "In Progress"},
                    "issuetype": {"name": "Story"},
                    "priority": {"name": "High"},
                }
            }
        ]
    }
    mock_jira_200 = httpx.Response(status_code=200, json=mock_jira_payload, request=httpx.Request("POST", "https://enterprise.atlassian.net/rest/api/3/search/jql"))
    with patch.object(settings, "JIRA_API_TOKEN", "real_token_123"), \
         patch.object(settings, "JIRA_URL", "https://enterprise.atlassian.net"), \
         patch.object(settings, "JIRA_EMAIL", "test@enterprise.com"), \
         patch("httpx.AsyncClient.post", return_value=mock_jira_200) as mock_post:
        live_search_res = client.get("/jira/search?jql=project=REAL", headers=headers)
        assert live_search_res.status_code == 200
        called_url = str(mock_post.call_args[0][0])
        assert "/rest/api/3/search/jql" in called_url, f"Expected call to /rest/api/3/search/jql, got {called_url}"
        assert not called_url.endswith("/rest/api/3/search"), "Obsolete Jira endpoint /rest/api/3/search must NOT be called!"
        print(f"[PASS] 13. Verified modern Jira API endpoint: {called_url}")

    # 14. Verify Project Card Click Backlog for AI Project
    ai_issues_res = client.get("/jira/projects/AI/issues", headers=headers)
    assert ai_issues_res.status_code == 200, f"AI project issues failed: {ai_issues_res.text}"
    ai_issues = ai_issues_res.json()["issues"]
    assert len(ai_issues) > 0 and ai_issues[0]["key"].startswith("AI-")
    print(f"[PASS] 14. Project Card Click 'AI': Loaded {len(ai_issues)} issues (First: {ai_issues[0]['key']})")

    # 15. Verify Jira Upstream Error Mapping to 502
    mock_jira_401 = httpx.Response(status_code=401, text="Unauthorized", request=httpx.Request("GET", "https://enterprise.atlassian.net/rest/api/3/search/jql"))
    with patch.object(settings, "JIRA_API_TOKEN", "invalid_jira_token"), \
         patch.object(settings, "JIRA_URL", "https://enterprise.atlassian.net"), \
         patch.object(settings, "JIRA_EMAIL", "test@enterprise.com"), \
         patch("httpx.AsyncClient.get", return_value=mock_jira_401):
        jira_err_res = client.get("/jira/projects", headers=headers)
        assert jira_err_res.status_code == 502, f"Expected 502 Bad Gateway, got {jira_err_res.status_code}"
        print("[PASS] 15. Jira Upstream 401 correctly mapped to 502 Bad Gateway.")

    # 16. Verify User Remains Authenticated on GET /auth/me
    me_res = client.get("/auth/me", headers=headers)
    assert me_res.status_code == 200
    print("[PASS] 16. User session active and authenticated (/auth/me returns 200 OK).")

    print("\n" + "=" * 65)
    print("ALL GITHUB & JIRA INTEGRATION TESTS PASSED WITH 100% SUCCESS!")
    print("=" * 65)

if __name__ == "__main__":
    run_integration_tests()
