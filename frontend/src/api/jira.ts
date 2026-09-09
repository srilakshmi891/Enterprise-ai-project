import { apiClient } from './client';
import { JiraProjectSummary, JiraSearchResult, JiraIssueSummary } from '../types/jira';

export const jiraApi = {
  getProjects: async (): Promise<JiraProjectSummary[]> => {
    const response = await apiClient.get<JiraProjectSummary[]>('/jira/projects');
    return response.data;
  },

  getProjectDetail: async (projectKey: string): Promise<any> => {
    const response = await apiClient.get(`/jira/projects/${projectKey}`);
    return response.data;
  },

  getProjectIssues: async (projectKey: string, startAt = 0, maxResults = 50): Promise<JiraSearchResult> => {
    const response = await apiClient.get<JiraSearchResult>(`/jira/projects/${projectKey}/issues`, {
      params: { start_at: startAt, max_results: maxResults },
    });
    return response.data;
  },

  searchIssues: async (jql: string, startAt = 0, maxResults = 50): Promise<JiraSearchResult> => {
    const response = await apiClient.get<JiraSearchResult>('/jira/issues/search', {
      params: { jql, start_at: startAt, max_results: maxResults },
    });
    return response.data;
  },

  getIssueDetail: async (issueKey: string): Promise<JiraIssueSummary> => {
    const response = await apiClient.get<JiraIssueSummary>(`/jira/issues/${issueKey}`);
    return response.data;
  },
};
