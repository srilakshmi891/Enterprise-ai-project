"""
GitHub Service layer: Async client for GitHub REST API v3.
Interacts with GitHub API using httpx and settings.GITHUB_TOKEN.
"""
import base64
from typing import List, Optional
import httpx
from fastapi import HTTPException, status

from app.config import settings
from app.schemas.github import (
    RepositoryOwner,
    RepositorySummary,
    RepositoryDetail,
    FileTreeItem,
    FileContentResponse,
)

GITHUB_API_BASE_URL = "https://api.github.com"


def _is_mock_github() -> bool:
    """Determine if mock GitHub data should be served."""
    token = settings.GITHUB_TOKEN
    return bool(token and token.strip().startswith("mock-"))


def _get_github_headers() -> dict:
    """Build request headers for GitHub API."""
    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "Enterprise-AI-Assistant",
    }
    if settings.GITHUB_TOKEN and not settings.GITHUB_TOKEN.strip().startswith("mock-"):
        headers["Authorization"] = f"Bearer {settings.GITHUB_TOKEN.strip()}"
    return headers


def _handle_github_error(response: httpx.Response, owner: Optional[str] = None, repo: Optional[str] = None, path: Optional[str] = None):
    """Map GitHub API status codes to appropriate FastAPI HTTP exceptions."""
    if response.status_code == status.HTTP_401_UNAUTHORIZED:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="GitHub API authentication failed. Check GITHUB_TOKEN configuration.",
        )
    elif response.status_code == status.HTTP_403_FORBIDDEN:
        rate_remaining = response.headers.get("x-ratelimit-remaining")
        if rate_remaining == "0":
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="GitHub API rate limit exceeded. Please try again later or configure GITHUB_TOKEN.",
            )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Access forbidden by GitHub API. Check GITHUB_TOKEN permissions.",
        )
    elif response.status_code == status.HTTP_404_NOT_FOUND:
        if path and repo and owner:
            msg = f"File or path '{path}' not found in repository '{owner}/{repo}'."
        elif repo and owner:
            msg = f"Repository '{owner}/{repo}' not found on GitHub."
        else:
            msg = "Resource not found on GitHub."
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=msg,
        )
    elif response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid request parameters sent to GitHub API.",
        )
    elif response.status_code >= 500:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API upstream error: {response.status_code}",
        )
    else:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"GitHub API error: {response.text}",
        )


# ---------------------------------------------------------------------------
# Mock data generators for development / testing environments
# ---------------------------------------------------------------------------
def _get_mock_repo_summary() -> RepositorySummary:
    return RepositorySummary(
        id=10001,
        name="mock-repo",
        full_name="mock-owner/mock-repo",
        private=True,
        html_url="https://github.com/mock-owner/mock-repo",
        description="Mock GitHub Repository for development and testing.",
        language="Python",
        created_at="2026-08-30T12:00:00Z",
        updated_at="2026-08-30T12:00:00Z",
        stargazers_count=10,
        watchers_count=5,
        fork=False,
        url="https://api.github.com/repos/mock-owner/mock-repo",
        default_branch="main",
        owner=RepositoryOwner(
            login="mock-owner",
            id=10000,
            avatar_url="https://github.com/mock-owner.png",
            html_url="https://github.com/mock-owner",
        ),
    )


def _get_mock_file_tree(path: str = "") -> List[FileTreeItem]:
    clean = path.strip("/")
    if not clean:
        return [
            FileTreeItem(
                name="src",
                path="src",
                sha="mock-tree-sha-src",
                size=0,
                url="https://api.github.com/repos/mock-owner/mock-repo/contents/src",
                html_url="https://github.com/mock-owner/mock-repo/tree/main/src",
                type="dir",
            ),
            FileTreeItem(
                name="README.md",
                path="README.md",
                sha="mock-blob-sha-readme",
                size=1204,
                url="https://api.github.com/repos/mock-owner/mock-repo/contents/README.md",
                html_url="https://github.com/mock-owner/mock-repo/blob/main/README.md",
                type="file",
            ),
            FileTreeItem(
                name="requirements.txt",
                path="requirements.txt",
                sha="mock-blob-sha-req",
                size=340,
                url="https://api.github.com/repos/mock-owner/mock-repo/contents/requirements.txt",
                html_url="https://github.com/mock-owner/mock-repo/blob/main/requirements.txt",
                type="file",
            ),
            FileTreeItem(
                name="main.py",
                path="main.py",
                sha="mock-blob-sha-main",
                size=850,
                url="https://api.github.com/repos/mock-owner/mock-repo/contents/main.py",
                html_url="https://github.com/mock-owner/mock-repo/blob/main/main.py",
                type="file",
            ),
        ]
    elif clean == "src":
        return [
            FileTreeItem(
                name="app.py",
                path="src/app.py",
                sha="mock-blob-sha-app",
                size=1420,
                url="https://api.github.com/repos/mock-owner/mock-repo/contents/src/app.py",
                html_url="https://github.com/mock-owner/mock-repo/blob/main/src/app.py",
                type="file",
            ),
            FileTreeItem(
                name="utils.py",
                path="src/utils.py",
                sha="mock-blob-sha-utils",
                size=620,
                url="https://api.github.com/repos/mock-owner/mock-repo/contents/src/utils.py",
                html_url="https://github.com/mock-owner/mock-repo/blob/main/src/utils.py",
                type="file",
            ),
        ]
    return []


def _get_mock_file_content(path: str) -> FileContentResponse:
    clean = path.strip("/")
    contents_map = {
        "README.md": "# Enterprise AI Project\n\nAI-powered project management assistant integrating documents, GitHub, and Jira.",
        "requirements.txt": "fastapi>=0.110.0\nuvicorn>=0.27.0\nhttpx>=0.27.0\npydantic>=2.6.0\nchromadb>=0.4.22\n",
        "main.py": "from app.main import app\n\nif __name__ == '__main__':\n    import uvicorn\n    uvicorn.run(app, host='127.0.0.1', port=8001)\n",
        "src/app.py": "from fastapi import FastAPI\n\napp = FastAPI(title='Enterprise AI Assistant')\n",
        "src/utils.py": "def format_response(data: dict) -> dict:\n    return {'status': 'success', 'data': data}\n",
    }
    text = contents_map.get(clean, f"# Mock Content for {clean}\n\nFile loaded successfully in development mode.")
    raw_b64 = base64.b64encode(text.encode("utf-8")).decode("utf-8")
    name = clean.split("/")[-1] if "/" in clean else clean

    return FileContentResponse(
        name=name,
        path=clean,
        sha="mock-sha-" + name.replace(".", "-"),
        size=len(text.encode("utf-8")),
        encoding="base64",
        content=raw_b64,
        decoded_content=text,
        html_url=f"https://github.com/mock-owner/mock-repo/blob/main/{clean}",
        download_url=f"https://raw.githubusercontent.com/mock-owner/mock-repo/main/{clean}",
    )


# ---------------------------------------------------------------------------
# Public Service Functions
# ---------------------------------------------------------------------------
async def list_user_repositories(
    visibility: str = "all",
    per_page: int = 30,
    page: int = 1,
) -> List[RepositorySummary]:
    """Fetch repositories for the authenticated token account or fallback to public user repos."""
    if _is_mock_github():
        return [_get_mock_repo_summary()]

    headers = _get_github_headers()
    
    async with httpx.AsyncClient(timeout=10.0) as client:
        if settings.GITHUB_TOKEN:
            url = f"{GITHUB_API_BASE_URL}/user/repos"
            params = {"visibility": visibility, "per_page": per_page, "page": page, "sort": "updated"}
        else:
            url = f"{GITHUB_API_BASE_URL}/repositories"
            params = {"since": (page - 1) * per_page}

        response = await client.get(url, headers=headers, params=params)
        
        if response.is_error:
            _handle_github_error(response)

        data = response.json()
        if not isinstance(data, list):
            return []

        return [RepositorySummary(**repo) for repo in data]


async def get_repository_details(owner: str, repo: str) -> RepositoryDetail:
    """Fetch detailed information for a specific repository."""
    if _is_mock_github() or owner == "mock-owner" or repo == "mock-repo":
        mock_sum = _get_mock_repo_summary()
        return RepositoryDetail(
            **mock_sum.model_dump(),
            size=1024,
            open_issues_count=3,
            forks_count=2,
            subscribers_count=4,
            network_count=2,
            topics=["enterprise", "ai", "fastapi"],
            visibility="private" if mock_sum.private else "public",
        )

    headers = _get_github_headers()
    url = f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=headers)
        if response.is_error:
            _handle_github_error(response, owner=owner, repo=repo)

        return RepositoryDetail(**response.json())


async def list_repository_files(owner: str, repo: str, path: str = "") -> List[FileTreeItem]:
    """List directory entries in a repository path."""
    if _is_mock_github() or owner == "mock-owner" or repo == "mock-repo":
        return _get_mock_file_tree(path=path)

    headers = _get_github_headers()
    clean_path = path.strip("/")
    url = f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contents/{clean_path}" if clean_path else f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contents"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=headers)
        if response.is_error:
            _handle_github_error(response, owner=owner, repo=repo, path=path)

        data = response.json()
        if isinstance(data, dict):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path '{path}' points to a file, not a directory. Use GET /github/repos/{owner}/{repo}/file instead.",
            )
        
        return [FileTreeItem(**item) for item in data]


async def get_file_content(owner: str, repo: str, path: str) -> FileContentResponse:
    """Fetch file content from a repository and decode base64 content into UTF-8 string."""
    clean_path = path.strip("/")
    if not clean_path:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Query parameter 'path' is required to fetch file content.",
        )

    if _is_mock_github() or owner == "mock-owner" or repo == "mock-repo":
        return _get_mock_file_content(path=clean_path)

    headers = _get_github_headers()
    url = f"{GITHUB_API_BASE_URL}/repos/{owner}/{repo}/contents/{clean_path}"

    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, headers=headers)
        if response.is_error:
            _handle_github_error(response, owner=owner, repo=repo, path=path)

        data = response.json()
        if isinstance(data, list):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Path '{path}' points to a directory, not a file. Use GET /github/repos/{owner}/{repo}/files instead.",
            )

        raw_content = data.get("content", "")
        encoding = data.get("encoding", "base64")
        decoded_str: Optional[str] = None

        if encoding == "base64" and raw_content:
            try:
                clean_bytes = base64.b64decode(raw_content.replace("\n", "").encode("utf-8"))
                decoded_str = clean_bytes.decode("utf-8")
            except Exception:
                decoded_str = None

        return FileContentResponse(
            name=data["name"],
            path=data["path"],
            sha=data["sha"],
            size=data["size"],
            encoding=encoding,
            content=raw_content,
            decoded_content=decoded_str,
            html_url=data.get("html_url"),
            download_url=data.get("download_url"),
        )
