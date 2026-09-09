export interface JiraUser {
  accountId?: string;
  displayName?: string;
  emailAddress?: string;
  active?: boolean;
  avatarUrls?: Record<string, string>;
}

export interface JiraProjectSummary {
  id: string;
  key: string;
  name: string;
  projectTypeKey?: string;
  avatarUrls?: Record<string, string>;
  self?: string;
}

export interface JiraIssueSummary {
  id: string;
  key: string;
  self?: string;
  summary: string;
  status?: string;
  issue_type?: string;
  priority?: string;
  assignee?: string;
  reporter?: string;
  created?: string;
  updated?: string;
}

export interface JiraSearchResult {
  startAt: number;
  maxResults: number;
  total: number;
  issues: JiraIssueSummary[];
}
