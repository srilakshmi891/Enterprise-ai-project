"""
Jira Service layer: Async client for Jira Cloud REST API v3.
Interacts with Jira API using httpx with Basic Authentication (JIRA_EMAIL, JIRA_API_TOKEN).
Migrated to modern Jira Cloud JQL Search API (/rest/api/3/search/jql).
"""
from typing import List, Optional, Any, Dict
import httpx
from fastapi import HTTPException, status

from app.config import settings
from app.schemas.jira import (
    JiraUser,
    JiraStatus,
    JiraPriority,
    JiraIssueType,
    JiraProjectSummary,
    JiraProjectDetail,
    JiraIssueSummary,
    JiraIssueDetail,
    JiraSearchResult,
)


def _is_mock_jira() -> bool:
    """Determine if mock Jira data should be served."""
    token = settings.JIRA_API_TOKEN
    return bool(token and token.strip().startswith("mock-"))


def _check_jira_config():
    """Verify that Jira configuration settings are set."""
    if _is_mock_jira():
        return
    if not settings.JIRA_URL or not settings.JIRA_EMAIL or not settings.JIRA_API_TOKEN:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Jira integration is not fully configured. Please set JIRA_URL, JIRA_EMAIL, and JIRA_API_TOKEN in .env.",
        )


def _get_jira_auth() -> httpx.BasicAuth:
    """Return BasicAuth tuple for Jira API."""
    _check_jira_config()
    return httpx.BasicAuth(
        username=(settings.JIRA_EMAIL or "").strip(),
        password=(settings.JIRA_API_TOKEN or "").strip(),
    )


def _get_jira_headers() -> dict:
    """Build request headers for Jira API."""
    return {
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _parse_adf_text(content_obj: Any) -> Optional[str]:
    """Parse Atlassian Document Format (ADF) dict or raw string into plain text."""
    if not content_obj:
        return None
    if isinstance(content_obj, str):
        return content_obj
    if isinstance(content_obj, dict):
        texts = []
        def _extract(node):
            if isinstance(node, dict):
                if node.get("type") == "text" and "text" in node:
                    texts.append(node["text"])
                for child in node.get("content", []):
                    _extract(child)
            elif isinstance(node, list):
                for item in node:
                    _extract(item)
        _extract(content_obj)
        return " ".join(texts) if texts else None
    return None


def _handle_jira_error(response: httpx.Response, project_key: Optional[str] = None, issue_key: Optional[str] = None):
    """Map Jira API status codes to appropriate FastAPI HTTP exceptions."""
    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Jira API authentication failed. Check JIRA_EMAIL and JIRA_API_TOKEN configuration.",
        )
    elif response.status_code == status.HTTP_403_FORBIDDEN:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Access forbidden by Jira API. Check user permissions in Jira Cloud.",
        )
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        if issue_key:
            msg = f"Jira issue '{issue_key}' not found."
        elif project_key:
            msg = f"Jira project '{project_key}' not found."
        else:
            msg = "Jira resource not found."
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )
    elif response.status_code == status.HTTP_400_BAD_REQUEST:
        err_detail = "Invalid request or JQL syntax error sent to Jira API."
        try:
            err_json = response.json()
            if "errorMessages" in err_json and err_json["errorMessages"]:
                err_detail = f"Jira API error: {' '.join(err_json['errorMessages'])}"
        except Exception:
            pass
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=err_detail,
        )
    elif response.status_code == status.HTTP_429_TOO_MANY_REQUESTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Jira API rate limit exceeded.",
        )
    elif response.status_code >= 500:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Jira API upstream error: {response.status_code}",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Jira API error: {response.text}",
        )


# ---------------------------------------------------------------------------
# Mock data generators for Jira
# ---------------------------------------------------------------------------
def _get_mock_projects() -> List[JiraProjectSummary]:
    return [
        JiraProjectSummary(
            id="10000",
            key="MOCK",
            name="Enterprise Core Platform",
            projectTypeKey="software",
            self="https://mock.atlassian.net/rest/api/3/project/MOCK",
        ),
        JiraProjectSummary(
            id="10001",
            key="AI",
            name="AI Assistant & Intelligence",
            projectTypeKey="software",
            self="https://mock.atlassian.net/rest/api/3/project/AI",
        ),
    ]


def _get_mock_issues(project_key: Optional[str] = None) -> List[JiraIssueSummary]:
    key_prefix = project_key if project_key else "MOCK"
    return [
        JiraIssueSummary(
            id="10101",
            key=f"{key_prefix}-101",
            summary="Implement Semantic Chunking and Hybrid Vector Retrieval in ChromaDB",
            status="In Progress",
            issue_type="Story",
            priority="High",
            assignee="Sree Dev",
            reporter="Product Lead",
            created="2026-08-28T10:00:00.000+0000",
            updated="2026-09-01T14:30:00.000+0000",
        ),
        JiraIssueSummary(
            id="10102",
            key=f"{key_prefix}-102",
            summary="Migrate Jira issue search endpoints to modern /rest/api/3/search/jql API",
            status="Done",
            issue_type="Task",
            priority="Highest",
            assignee="Backend Team",
            reporter="Architecture Guild",
            created="2026-08-29T11:15:00.000+0000",
            updated="2026-09-04T09:00:00.000+0000",
        ),
        JiraIssueSummary(
            id="10103",
            key=f"{key_prefix}-103",
            summary="Enable multi-turn conversational memory with isolated session persistence",
            status="To Do",
            issue_type="Story",
            priority="Medium",
            assignee="AI Engineer",
            reporter="Product Lead",
            created="2026-08-30T16:45:00.000+0000",
            updated="2026-08-30T16:45:00.000+0000",
        ),
        JiraIssueSummary(
            id="10104",
            key=f"{key_prefix}-104",
            summary="Fix GitHub Repository Explorer directory tree navigation and file content viewer",
            status="Done",
            issue_type="Bug",
            priority="High",
            assignee="Frontend Team",
            reporter="QA Engineer",
            created="2026-09-02T13:20:00.000+0000",
            updated="2026-09-04T18:10:00.000+0000",
        ),
    ]


# ---------------------------------------------------------------------------
# Public Service Functions
# ---------------------------------------------------------------------------
async def list_projects() -> List[JiraProjectSummary]:
    """Fetch projects accessible to the configured Jira account."""
    if _is_mock_jira():
        return _get_mock_projects()

    _check_jira_config()
    auth = _get_jira_auth()
    base_url = settings.JIRA_URL.rstrip("/")
    url = f"{base_url}/rest/api/3/project"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, auth=auth, headers=_get_jira_headers())
        if response.is_error:
            _handle_jira_error(response)

        data = response.json()
        if not isinstance(data, list):
            return []

        projects = []
        for p in data:
            projects.append(
                JiraProjectSummary(
                    id=str(p.get("id")),
                    key=p.get("key", ""),
                    name=p.get("name", ""),
                    projectTypeKey=p.get("projectTypeKey", "software"),
                    avatarUrls=p.get("avatarUrls"),
                    self=p.get("self"),
                )
            )
        return projects


async def get_project_details(project_key: str) -> JiraProjectDetail:
    """Fetch detailed information for a specific Jira project."""
    if _is_mock_jira() or project_key in ["MOCK", "AI"]:
        return JiraProjectDetail(
            id="10000" if project_key == "MOCK" else "10001",
            key=project_key,
            name=f"{project_key} Enterprise Project",
            projectTypeKey="software",
            description="Agile project for Enterprise AI Assistant development and integrations.",
            lead=JiraUser(
                accountId="mock-lead-123",
                displayName="Project Lead",
                emailAddress="lead@enterprise.com",
                active=True,
            ),
            issueTypes=[
                JiraIssueType(id="1", name="Story", description="User story feature", subtask=False),
                JiraIssueType(id="2", name="Task", description="Technical task", subtask=False),
                JiraIssueType(id="3", name="Bug", description="Defect fix", subtask=False),
            ],
        )

    _check_jira_config()
    auth = _get_jira_auth()
    base_url = settings.JIRA_URL.rstrip("/")
    url = f"{base_url}/rest/api/3/project/{project_key}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, auth=auth, headers=_get_jira_headers())
        if response.is_error:
            _handle_jira_error(response, project_key=project_key)

        p = response.json()
        lead_data = None
        if "lead" in p and isinstance(p["lead"], dict):
            lead_data = JiraUser(
                accountId=p["lead"].get("accountId"),
                displayName=p["lead"].get("displayName"),
                emailAddress=p["lead"].get("emailAddress"),
                active=p["lead"].get("active", True),
                avatarUrls=p["lead"].get("avatarUrls"),
            )

        issue_types = []
        for it in p.get("issueTypes", []):
            issue_types.append(
                JiraIssueType(
                    id=str(it.get("id")),
                    name=it.get("name", ""),
                    description=it.get("description"),
                    subtask=it.get("subtask", False),
                    iconUrl=it.get("iconUrl"),
                )
            )

        return JiraProjectDetail(
            id=str(p.get("id")),
            key=p.get("key", ""),
            name=p.get("name", ""),
            projectTypeKey=p.get("projectTypeKey", "software"),
            avatarUrls=p.get("avatarUrls"),
            self=p.get("self"),
            description=p.get("description"),
            lead=lead_data,
            issueTypes=issue_types,
            projectCategory=p.get("projectCategory"),
        )


async def search_issues(jql: str, start_at: int = 0, max_results: int = 50) -> JiraSearchResult:
    """
    Search Jira issues using JQL with pagination.
    Uses modern Jira Cloud REST API v3 JQL endpoint (POST /rest/api/3/search/jql).
    """
    upper_jql = jql.upper()
    if _is_mock_jira() or "MOCK" in upper_jql or "AI" in upper_jql:
        key_prefix = "AI" if "AI" in upper_jql else "MOCK"
        mock_issues = _get_mock_issues(project_key=key_prefix)
        return JiraSearchResult(
            startAt=start_at,
            maxResults=max_results,
            total=len(mock_issues),
            issues=mock_issues,
        )

    _check_jira_config()
    auth = _get_jira_auth()
    base_url = settings.JIRA_URL.rstrip("/")
    
    # Modern Jira Cloud REST API v3 JQL search endpoint
    url = f"{base_url}/rest/api/3/search/jql"
    fields_list = ["summary", "status", "issuetype", "priority", "assignee", "reporter", "created", "updated"]
    post_payload = {
        "jql": jql,
        "startAt": start_at,
        "maxResults": max_results,
        "fields": fields_list,
    }

    async with httpx.AsyncClient(timeout=10.0) as client:
        # 1. Primary: POST /rest/api/3/search/jql
        response = await client.post(url, auth=auth, headers=_get_jira_headers(), json=post_payload)
        
        # 2. Fallback: GET /rest/api/3/search/jql if method not allowed
        if response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED:
            params = {
                "jql": jql,
                "startAt": start_at,
                "maxResults": max_results,
                "fields": ",".join(fields_list),
            }
            response = await client.get(url, auth=auth, headers=_get_jira_headers(), params=params)

        if response.is_error:
            _handle_jira_error(response)

        data = response.json()
        raw_issues = data.get("issues", [])
        
        parsed_issues = []
        for issue in raw_issues:
            fields = issue.get("fields", {})
            parsed_issues.append(
                JiraIssueSummary(
                    id=str(issue.get("id")),
                    key=issue.get("key", ""),
                    self=issue.get("self"),
                    summary=fields.get("summary", ""),
                    status=fields.get("status", {}).get("name") if fields.get("status") else None,
                    issue_type=fields.get("issuetype", {}).get("name") if fields.get("issuetype") else None,
                    priority=fields.get("priority", {}).get("name") if fields.get("priority") else None,
                    assignee=fields.get("assignee", {}).get("displayName") if fields.get("assignee") else None,
                    reporter=fields.get("reporter", {}).get("displayName") if fields.get("reporter") else None,
                    created=fields.get("created"),
                    updated=fields.get("updated"),
                )
            )

        return JiraSearchResult(
            startAt=data.get("startAt", start_at),
            maxResults=data.get("maxResults", max_results),
            total=data.get("total", len(parsed_issues)),
            issues=parsed_issues,
        )


async def list_project_issues(project_key: str, start_at: int = 0, max_results: int = 50) -> JiraSearchResult:
    """List issues for a specific Jira project."""
    clean_key = project_key.strip().replace('"', '')
    if _is_mock_jira() or clean_key in ["MOCK", "AI"]:
        mock_issues = _get_mock_issues(project_key=clean_key)
        return JiraSearchResult(
            startAt=start_at,
            maxResults=max_results,
            total=len(mock_issues),
            issues=mock_issues,
        )
    jql = f'project = "{clean_key}" ORDER BY created DESC'
    return await search_issues(jql=jql, start_at=start_at, max_results=max_results)


async def get_issue_details(issue_key: str) -> JiraIssueDetail:
    """Fetch detailed information for a specific Jira issue."""
    if _is_mock_jira() or issue_key.startswith("MOCK-") or issue_key.startswith("AI-"):
        return JiraIssueDetail(
            id="10101",
            key=issue_key,
            summary="Implement Semantic Chunking and Hybrid Vector Retrieval in ChromaDB",
            description="Comprehensive task to implement recursive text chunking and cosine similarity search.",
            status=JiraStatus(name="In Progress"),
            issueType=JiraIssueType(name="Story", subtask=False),
            priority=JiraPriority(name="High"),
            assignee=JiraUser(displayName="Sree Dev", emailAddress="sree.dev@enterprise.com"),
            reporter=JiraUser(displayName="Product Lead", emailAddress="lead@enterprise.com"),
            created="2026-08-28T10:00:00.000+0000",
            updated="2026-09-01T14:30:00.000+0000",
        )

    _check_jira_config()
    auth = _get_jira_auth()
    base_url = settings.JIRA_URL.rstrip("/")
    url = f"{base_url}/rest/api/3/issue/{issue_key}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, auth=auth, headers=_get_jira_headers())
        if response.is_error:
            _handle_jira_error(response, issue_key=issue_key)

        data = response.json()
        fields = data.get("fields", {})

        status_obj = None
        if fields.get("status"):
            st = fields["status"]
            status_obj = JiraStatus(
                id=str(st.get("id")),
                name=st.get("name", ""),
                description=st.get("description"),
                statusCategory=st.get("statusCategory"),
            )

        type_obj = None
        if fields.get("issuetype"):
            it = fields["issuetype"]
            type_obj = JiraIssueType(
                id=str(it.get("id")),
                name=it.get("name", ""),
                description=it.get("description"),
                subtask=it.get("subtask", False),
                iconUrl=it.get("iconUrl"),
            )

        priority_obj = None
        if fields.get("priority"):
            pr = fields["priority"]
            priority_obj = JiraPriority(
                id=str(pr.get("id")),
                name=pr.get("name", ""),
                iconUrl=pr.get("iconUrl"),
            )

        assignee_obj = None
        if fields.get("assignee") and isinstance(fields["assignee"], dict):
            asgn = fields["assignee"]
            assignee_obj = JiraUser(
                accountId=asgn.get("accountId"),
                displayName=asgn.get("displayName"),
                emailAddress=asgn.get("emailAddress"),
                active=asgn.get("active", True),
                avatarUrls=asgn.get("avatarUrls"),
            )

        reporter_obj = None
        if fields.get("reporter") and isinstance(fields["reporter"], dict):
            rep = fields["reporter"]
            reporter_obj = JiraUser(
                accountId=rep.get("accountId"),
                displayName=rep.get("displayName"),
                emailAddress=rep.get("emailAddress"),
                active=rep.get("active", True),
                avatarUrls=rep.get("avatarUrls"),
            )

        project_obj = None
        if fields.get("project") and isinstance(fields["project"], dict):
            proj = fields["project"]
            project_obj = JiraProjectSummary(
                id=str(proj.get("id")),
                key=proj.get("key", ""),
                name=proj.get("name", ""),
                projectTypeKey=proj.get("projectTypeKey", "software"),
                avatarUrls=proj.get("avatarUrls"),
                self=proj.get("self"),
            )

        desc_text = _parse_adf_text(fields.get("description"))

        return JiraIssueDetail(
            id=str(data.get("id")),
            key=data.get("key", ""),
            self=data.get("self"),
            summary=fields.get("summary", ""),
            description=desc_text,
            status=status_obj,
            issueType=type_obj,
            priority=priority_obj,
            assignee=assignee_obj,
            reporter=reporter_obj,
            project=project_obj,
            created=fields.get("created"),
            updated=fields.get("updated"),
        )
