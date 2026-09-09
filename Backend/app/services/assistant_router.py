"""
Intent Router for AI Project Assistant.
Deterministic keyword/rule-based intent classification.
Do NOT use Gemini or non-deterministic ML models for intent classification.
"""
from typing import Optional


class IntentType:
    DOCUMENT = "DOCUMENT"
    GITHUB = "GITHUB"
    JIRA = "JIRA"
    GENERAL_PROJECT = "GENERAL_PROJECT"


DOCUMENT_KEYWORDS = {
    "document",
    "documents",
    "file",
    "files",
    "pdf",
    "documentation",
    "uploaded",
    "report",
    "content",
    "what does the document say",
    "according to the document",
}

GITHUB_KEYWORDS = {
    "github",
    "repository",
    "repositories",
    "repo",
    "repos",
    "commit",
    "branch",
    "branches",
    "code repository",
}

JIRA_KEYWORDS = {
    "jira",
    "issue",
    "issues",
    "ticket",
    "tickets",
    "sprint",
    "backlog",
    "task",
}


def classify_intent(question: str, document_id: Optional[int] = None) -> str:
    """
    Classify user question into one of 4 deterministic intents:
    - DOCUMENT
    - GITHUB
    - JIRA
    - GENERAL_PROJECT
    """
    # 0. If document_id filter is explicitly provided, intent is DOCUMENT
    if document_id is not None:
        return IntentType.DOCUMENT

    q_lower = question.lower().strip()

    # Check GITHUB keywords first
    for kw in GITHUB_KEYWORDS:
        if kw in q_lower:
            return IntentType.GITHUB

    # Check JIRA keywords
    for kw in JIRA_KEYWORDS:
        if kw in q_lower:
            return IntentType.JIRA

    # Check DOCUMENT keywords
    for kw in DOCUMENT_KEYWORDS:
        if kw in q_lower:
            return IntentType.DOCUMENT

    # Check specific phrases for Jira project query e.g., "jira project", "jira projects", "what jira projects"
    if "jira" in q_lower or "project" in q_lower and ("jira" in q_lower or "ticket" in q_lower):
        return IntentType.JIRA

    # Fallback to GENERAL_PROJECT
    return IntentType.GENERAL_PROJECT
