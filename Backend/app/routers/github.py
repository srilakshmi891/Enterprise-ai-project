"""
GitHub Router: Protected endpoints for repository management and file retrieval.
All endpoints require JWT Bearer authentication.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, Query, status

from app.models.user import User
from app.routers.auth import get_current_user
from app.schemas.github import (
    RepositorySummary,
    RepositoryDetail,
    FileTreeItem,
    FileContentResponse,
)
from app.services.github_service import (
    list_user_repositories,
    get_repository_details,
    list_repository_files,
    get_file_content,
)

router = APIRouter(prefix="/github", tags=["GitHub Integration"])


# ---------------------------------------------------------------------------
# GET /github/repos
# ---------------------------------------------------------------------------
@router.get(
    "/repos",
    response_model=List[RepositorySummary],
    summary="List accessible GitHub repositories",
)
async def get_repositories(
    visibility: str = Query(default="all", description="Repository visibility: all, public, or private"),
    per_page: int = Query(default=30, ge=1, le=100, description="Results per page"),
    page: int = Query(default=1, ge=1, description="Page number"),
    current_user: User = Depends(get_current_user),
):
    """
    List repositories accessible to the configured GitHub account.
    Requires Bearer JWT authentication.
    """
    return await list_user_repositories(
        visibility=visibility,
        per_page=per_page,
        page=page,
    )


# ---------------------------------------------------------------------------
# GET /github/repos/{owner}/{repo}
# ---------------------------------------------------------------------------
@router.get(
    "/repos/{owner}/{repo}",
    response_model=RepositoryDetail,
    summary="Get repository details",
)
async def get_repo_details(
    owner: str,
    repo: str,
    current_user: User = Depends(get_current_user),
):
    """
    Fetch detailed information for a specific repository.
    Requires Bearer JWT authentication.
    """
    return await get_repository_details(owner=owner, repo=repo)


# ---------------------------------------------------------------------------
# GET /github/repos/{owner}/{repo}/files
# ---------------------------------------------------------------------------
@router.get(
    "/repos/{owner}/{repo}/files",
    response_model=List[FileTreeItem],
    summary="List repository files and subdirectories",
)
async def get_repo_files(
    owner: str,
    repo: str,
    path: str = Query(default="", description="Directory path inside repository"),
    current_user: User = Depends(get_current_user),
):
    """
    List directory entries (files and folders) inside a repository path.
    Requires Bearer JWT authentication.
    """
    return await list_repository_files(owner=owner, repo=repo, path=path)


# ---------------------------------------------------------------------------
# GET /github/repos/{owner}/{repo}/file
# ---------------------------------------------------------------------------
@router.get(
    "/repos/{owner}/{repo}/file",
    response_model=FileContentResponse,
    summary="Retrieve file content and decoded text",
)
async def get_repo_file_content(
    owner: str,
    repo: str,
    path: str = Query(..., description="File path inside repository (e.g. README.md or app/main.py)"),
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve file metadata, raw base64 content, and decoded UTF-8 text for a file.
    Requires Bearer JWT authentication.
    """
    return await get_file_content(owner=owner, repo=repo, path=path)
