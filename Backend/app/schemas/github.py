"""
Pydantic schemas for GitHub API integration.
"""
from typing import Optional, List
from pydantic import BaseModel, Field


class RepositoryOwner(BaseModel):
    """GitHub repository owner model."""
    login: str
    id: int
    avatar_url: str
    html_url: str


class RepositorySummary(BaseModel):
    """Summary representation of a GitHub repository."""
    id: int
    name: str
    full_name: str
    owner: RepositoryOwner
    private: bool
    html_url: str
    description: Optional[str] = None
    fork: bool
    url: str
    created_at: Optional[str] = None
    updated_at: Optional[str] = None
    stargazers_count: int = 0
    watchers_count: int = 0
    language: Optional[str] = None
    default_branch: str = "main"


class RepositoryDetail(RepositorySummary):
    """Detailed representation of a GitHub repository."""
    size: int = 0
    open_issues_count: int = 0
    forks_count: int = 0
    subscribers_count: Optional[int] = 0
    network_count: Optional[int] = 0
    topics: List[str] = Field(default_factory=list)
    visibility: str = "public"


class FileTreeItem(BaseModel):
    """Representation of a file or directory item inside a repository."""
    name: str
    path: str
    sha: str
    size: int = 0
    url: str
    html_url: Optional[str] = None
    type: str  # "file" or "dir" or "submodule" or "symlink"


class FileContentResponse(BaseModel):
    """File content response including raw base64 and UTF-8 decoded text."""
    name: str
    path: str
    sha: str
    size: int
    encoding: str  # usually "base64"
    content: str
    decoded_content: Optional[str] = None
    html_url: Optional[str] = None
    download_url: Optional[str] = None
