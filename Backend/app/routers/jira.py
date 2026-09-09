"""
Jira Router: Protected endpoints for Jira project and issue management.
All endpoints require JWT Bearer authentication.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.jira import (
    JiraProjectSummary,
    JiraProjectDetail,
    JiraIssueSummary,
    JiraIssueDetail,
    JiraSearchResult,
)
from app.services.jira_service import (
    list_projects,
    get_project_details,
    list_project_issues,
    get_issue_details,
    search_issues,
)

router = APIRouter(prefix="/jira", tags=["Jira Integration"])


# ---------------------------------------------------------------------------
# GET /jira/projects
# ---------------------------------------------------------------------------
@router.get(
    "/projects",
    response_model=List[JiraProjectSummary],
    summary="List accessible Jira projects",
)
async def get_projects(
    current_user: User = Depends(get_current_user),
):
    """
    List all projects accessible to the configured Jira account.
    Requires Bearer JWT authentication.
    """
    return await list_projects()


# ---------------------------------------------------------------------------
# GET /jira/issues/search and GET /jira/search
# ---------------------------------------------------------------------------
@router.get(
    "/issues/search",
    response_model=JiraSearchResult,
    summary="Search Jira issues using JQL",
)
@router.get(
    "/search",
    response_model=JiraSearchResult,
    summary="Search Jira issues using JQL (alias)",
)
async def search_jira_issues(
    jql: str = Query(..., description="JQL search query, e.g. project = PROJ ORDER BY created DESC"),
    start_at: int = Query(default=0, ge=0, description="Start index for pagination"),
    max_results: int = Query(default=50, ge=1, le=100, description="Maximum results per page"),
    current_user: User = Depends(get_current_user),
):
    """
    Search Jira issues using a JQL (Jira Query Language) query string.
    Requires Bearer JWT authentication.
    """
    return await search_issues(jql=jql, start_at=start_at, max_results=max_results)


# ---------------------------------------------------------------------------
# GET /jira/issues/{issue_key}
# ---------------------------------------------------------------------------
@router.get(
    "/issues/{issue_key}",
    response_model=JiraIssueDetail,
    summary="Get Jira issue details",
)
async def get_issue_by_key(
    issue_key: str,
    current_user: User = Depends(get_current_user),
):
    """
    Fetch detailed information for a specific Jira issue (e.g. PROJ-123).
    Requires Bearer JWT authentication.
    """
    return await get_issue_details(issue_key=issue_key)


# ---------------------------------------------------------------------------
# GET /jira/projects/{project_key}
# ---------------------------------------------------------------------------
@router.get(
    "/projects/{project_key}",
    response_model=JiraProjectDetail,
    summary="Get Jira project details",
)
async def get_project_by_key(
    project_key: str,
    current_user: User = Depends(get_current_user),
):
    """
    Fetch detailed information for a specific Jira project (e.g. PROJ).
    Requires Bearer JWT authentication.
    """
    return await get_project_details(project_key=project_key)


# ---------------------------------------------------------------------------
# GET /jira/projects/{project_key}/issues
# ---------------------------------------------------------------------------
@router.get(
    "/projects/{project_key}/issues",
    response_model=JiraSearchResult,
    summary="List issues in a Jira project",
)
async def get_project_issues(
    project_key: str,
    start_at: int = Query(default=0, ge=0, description="Start index for pagination"),
    max_results: int = Query(default=50, ge=1, le=100, description="Maximum results per page"),
    current_user: User = Depends(get_current_user),
):
    """
    List issues belonging to a specific Jira project.
    Requires Bearer JWT authentication.
    """
    return await list_project_issues(project_key=project_key, start_at=start_at, max_results=max_results)
