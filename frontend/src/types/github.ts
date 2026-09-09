export interface RepositoryOwner {
  login: string;
  id: number;
  avatar_url: string;
  html_url: string;
}

export interface RepositorySummary {
  id: number;
  name: string;
  full_name: string;
  owner: RepositoryOwner;
  private: boolean;
  html_url: string;
  description?: string;
  fork: boolean;
  url: string;
  created_at?: string;
  updated_at?: string;
  stargazers_count: number;
  watchers_count: number;
  language?: string;
  default_branch: string;
}

export interface RepositoryDetail extends RepositorySummary {
  size: number;
  open_issues_count: number;
  forks_count: number;
  subscribers_count?: number;
  network_count?: number;
  topics: string[];
  visibility: string;
}

export interface FileTreeItem {
  name: string;
  path: string;
  sha: string;
  size: number;
  url: string;
  html_url?: string;
  type: 'file' | 'dir' | 'submodule' | 'symlink';
}

export interface FileContentResponse {
  name: string;
  path: string;
  sha: string;
  size: number;
  encoding: string;
  content: string;
  decoded_content?: string;
  html_url?: string;
  download_url?: string;
}
