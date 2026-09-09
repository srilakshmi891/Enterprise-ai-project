"""
Pydantic schemas for Jira API integration.
"""
from typing import Optional, List, Any, Dict
from pydantic import BaseModel, Field


class JiraUser(BaseModel):
    """Jira user representation."""
    accountId: Optional[str] = None
    displayName: Optional[str] = None
    emailAddress: Optional[str] = None
    active: Optional[bool] = True
    avatarUrls: Optional[Dict[str, str]] = None


class JiraStatus(BaseModel):
    """Jira issue status model."""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    statusCategory: Optional[Dict[str, Any]] = None


class JiraPriority(BaseModel):
    """Jira issue priority model."""
    id: Optional[str] = None
    name: str
    iconUrl: Optional[str] = None


class JiraIssueType(BaseModel):
    """Jira issue type model (e.g. Bug, Story, Task, Epic)."""
    id: Optional[str] = None
    name: str
    description: Optional[str] = None
    subtask: bool = False
    iconUrl: Optional[str] = None


class JiraProjectSummary(BaseModel):
    """Summary representation of a Jira project."""
    id: str
    key: str
    name: str
    projectTypeKey: Optional[str] = "software"
    avatarUrls: Optional[Dict[str, str]] = None
    self_link: Optional[str] = Field(default=None, alias="self")


class JiraProjectDetail(JiraProjectSummary):
    """Detailed representation of a Jira project."""
    description: Optional[str] = None
    lead: Optional[JiraUser] = None
    issueTypes: List[JiraIssueType] = Field(default_factory=list)
    projectCategory: Optional[Dict[str, Any]] = None


class JiraIssueSummary(BaseModel):
    """Summary representation of a Jira issue."""
    id: str
    key: str
    self_link: Optional[str] = Field(default=None, alias="self")
    summary: str
    status: Optional[str] = None
    issue_type: Optional[str] = None
    priority: Optional[str] = None
    assignee: Optional[str] = None
    reporter: Optional[str] = None
    created: Optional[str] = None
    updated: Optional[str] = None


class JiraIssueDetail(BaseModel):
    """Detailed representation of a Jira issue."""
    id: str
    key: str
    self_link: Optional[str] = Field(default=None, alias="self")
    summary: str
    description: Optional[str] = None
    status: Optional[JiraStatus] = None
    issue_type: Optional[JiraIssueType] = Field(default=None, alias="issueType")
    priority: Optional[JiraPriority] = None
    assignee: Optional[JiraUser] = None
    reporter: Optional[JiraUser] = None
    project: Optional[JiraProjectSummary] = None
    created: Optional[str] = None
    updated: Optional[str] = None


class JiraSearchResult(BaseModel):
    """Search/pagination wrapper for Jira issues."""
    startAt: int = 0
    maxResults: int = 50
    total: int = 0
    issues: List[JiraIssueSummary] = Field(default_factory=list)
