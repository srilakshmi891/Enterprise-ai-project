import { apiClient } from './client';
import {
  RepositorySummary,
  RepositoryDetail,
  FileTreeItem,
  FileContentResponse,
} from '../types/github';

export const githubApi = {
  getRepositories: async (page = 1, per_page = 30): Promise<RepositorySummary[]> => {
    const response = await apiClient.get<RepositorySummary[]>('/github/repos', {
      params: { page, per_page },
    });
    return response.data;
  },

  getRepositoryDetail: async (owner: string, repo: string): Promise<RepositoryDetail> => {
    const response = await apiClient.get<RepositoryDetail>(`/github/repos/${owner}/${repo}`);
    return response.data;
  },

  getRepositoryFiles: async (owner: string, repo: string, path = ''): Promise<FileTreeItem[]> => {
    const response = await apiClient.get<FileTreeItem[]>(`/github/repos/${owner}/${repo}/files`, {
      params: { path },
    });
    return response.data;
  },

  getFileContent: async (owner: string, repo: string, path: string): Promise<FileContentResponse> => {
    const response = await apiClient.get<FileContentResponse>(`/github/repos/${owner}/${repo}/file`, {
      params: { path },
    });
    return response.data;
  },
};
