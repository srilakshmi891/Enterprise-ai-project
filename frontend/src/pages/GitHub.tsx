import React, { useEffect, useState } from 'react';
import { githubApi } from '../api/github';
import { RepositorySummary, FileTreeItem } from '../types/github';
import {
  Github,
  Folder,
  File,
  ChevronRight,
  ArrowLeft,
  Star,
  Eye,
  GitBranch,
  X,
  FileCode,
} from 'lucide-react';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';

export const GitHub: React.FC = () => {
  const [repos, setRepos] = useState<RepositorySummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Selected repo directory structure view
  const [selectedRepo, setSelectedRepo] = useState<RepositorySummary | null>(null);
  const [currentPath, setCurrentPath] = useState<string>('');
  const [filesList, setFilesList] = useState<FileTreeItem[]>([]);
  const [filesLoading, setFilesLoading] = useState(false);

  // File content viewer modal
  const [viewFileModal, setViewFileModal] = useState<{ path: string; name: string; content: string } | null>(null);

  useEffect(() => {
    const fetchRepos = async () => {
      setLoading(true);
      setError(null);
      try {
        const data = await githubApi.getRepositories(1, 50);
        setRepos(data);
      } catch (err: any) {
        console.error('Failed to fetch github repos', err);
        setError(err.response?.data?.detail || 'Failed to retrieve GitHub repositories.');
      } finally {
        setLoading(false);
      }
    };

    fetchRepos();
  }, []);

  const handleSelectRepo = async (repo: RepositorySummary) => {
    setSelectedRepo(repo);
    setCurrentPath('');
    await fetchRepoFiles(repo.owner.login, repo.name, '');
  };

  const fetchRepoFiles = async (owner: string, repoName: string, path: string) => {
    setFilesLoading(true);
    setError(null);
    try {
      const data = await githubApi.getRepositoryFiles(owner, repoName, path);
      setFilesList(data);
      setCurrentPath(path);
    } catch (err: any) {
      console.error('Failed to load repo files', err);
      setError(err.response?.data?.detail || 'Failed to retrieve repository files tree.');
    } finally {
      setFilesLoading(false);
    }
  };

  const handleFolderClick = (item: FileTreeItem) => {
    if (!selectedRepo) return;
    fetchRepoFiles(selectedRepo.owner.login, selectedRepo.name, item.path);
  };

  const handleFileClick = async (item: FileTreeItem) => {
    if (!selectedRepo) return;
    setFilesLoading(true);
    setError(null);
    try {
      const res = await githubApi.getFileContent(selectedRepo.owner.login, selectedRepo.name, item.path);
      setViewFileModal({
        path: item.path,
        name: item.name,
        content: res.decoded_content || res.content || 'Binary or unreadable file content.',
      });
    } catch (err: any) {
      console.error('Failed to load file contents', err);
      setError(err.response?.data?.detail || 'Failed to fetch file content.');
    } finally {
      setFilesLoading(false);
    }
  };

  const handleNavigateUp = () => {
    if (!selectedRepo || !currentPath) return;
    const parts = currentPath.split('/');
    parts.pop();
    const parentPath = parts.join('/');
    fetchRepoFiles(selectedRepo.owner.login, selectedRepo.name, parentPath);
  };

  if (loading) {
    return <Loading message="Syncing with GitHub API..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-6 border-b border-slate-800 flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Github className="w-7 h-7 text-purple-400" /> GitHub Repository Explorer
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Browse repositories, walk tree directories, and view code files within your project assistant.
          </p>
        </div>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError(null)} />}

      {!selectedRepo ? (
        /* Repositories Cards Grid */
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {repos.length === 0 ? (
            <div className="col-span-full p-12 text-center bg-slate-900/60 border border-slate-800 rounded-2xl">
              <Github className="w-12 h-12 text-slate-600 mx-auto mb-3" />
              <h3 className="text-base font-bold text-slate-300">No repositories accessible</h3>
              <p className="text-xs text-slate-500 mt-1">
                Configure your GITHUB_TOKEN inside backend `.env` file to sync repositories.
              </p>
            </div>
          ) : (
            repos.map((repo) => (
              <div
                key={repo.id}
                onClick={() => handleSelectRepo(repo)}
                className="p-5 bg-slate-900/80 border border-slate-800 rounded-2xl hover:border-purple-500/40 hover:bg-slate-900 transition duration-200 cursor-pointer flex flex-col justify-between group shadow-sm"
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <span className="inline-flex items-center gap-1.5 text-xs text-slate-300 font-mono">
                      <GitBranch className="w-3.5 h-3.5 text-purple-400" /> {repo.default_branch}
                    </span>
                    <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/80">
                      {repo.private ? 'Private' : 'Public'}
                    </span>
                  </div>
                  <h3 className="text-lg font-bold text-white group-hover:text-purple-400 transition truncate">
                    {repo.name}
                  </h3>
                  <p className="text-xs text-slate-400 mt-1 line-clamp-2 h-8">
                    {repo.description || 'No description provided.'}
                  </p>
                </div>

                <div className="mt-5 pt-4 border-t border-slate-800/80 flex items-center justify-between text-xs text-slate-400">
                  <div className="flex items-center gap-3">
                    <span className="flex items-center gap-1">
                      <Star className="w-3.5 h-3.5 text-amber-500" /> {repo.stargazers_count}
                    </span>
                    <span className="flex items-center gap-1">
                      <Eye className="w-3.5 h-3.5 text-blue-400" /> {repo.watchers_count}
                    </span>
                  </div>
                  <span className="font-semibold text-slate-300">{repo.language || 'Code'}</span>
                </div>
              </div>
            ))
          )}
        </div>
      ) : (
        /* Repository Tree Walk View */
        <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
          {/* Tree Navigation Header */}
          <div className="p-4 sm:p-5 border-b border-slate-800 bg-slate-950/40 flex items-center justify-between flex-wrap gap-3">
            <button
              onClick={() => setSelectedRepo(null)}
              className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-lg border border-slate-700 transition"
            >
              <ArrowLeft className="w-3.5 h-3.5" /> Back to Repositories
            </button>

            <div className="text-sm font-bold text-white flex items-center gap-1.5">
              <Github className="w-4 h-4 text-purple-400" /> {selectedRepo.full_name}
            </div>

            <div className="text-xs font-mono bg-slate-950 px-3 py-1.5 rounded-lg border border-slate-800/80 text-slate-400">
              path: <span className="text-purple-400">/{currentPath || 'root'}</span>
            </div>
          </div>

          {/* Directory Content List */}
          {filesLoading ? (
            <Loading message="Syncing file structure..." />
          ) : (
            <div className="divide-y divide-slate-800/60 max-h-[60vh] overflow-y-auto">
              {currentPath && (
                <div
                  onClick={handleNavigateUp}
                  className="flex items-center gap-3 px-6 py-3.5 hover:bg-slate-800/30 cursor-pointer text-xs font-semibold text-brand-400 transition"
                >
                  <Folder className="w-4 h-4 text-brand-500 fill-brand-500/20" />
                  <span>.. (Up one level)</span>
                </div>
              )}

              {filesList.length === 0 ? (
                <div className="p-8 text-center text-xs text-slate-500">Empty directory</div>
              ) : (
                filesList.map((item) => (
                  <div
                    key={item.sha}
                    onClick={() => (item.type === 'dir' ? handleFolderClick(item) : handleFileClick(item))}
                    className="flex items-center justify-between px-6 py-3.5 hover:bg-slate-800/30 cursor-pointer transition"
                  >
                    <div className="flex items-center gap-3 text-xs text-slate-200">
                      {item.type === 'dir' ? (
                        <Folder className="w-4.5 h-4.5 text-brand-500 fill-brand-500/20 shrink-0" />
                      ) : (
                        <File className="w-4.5 h-4.5 text-slate-400 shrink-0" />
                      )}
                      <span className="font-medium">{item.name}</span>
                    </div>

                    <div className="flex items-center gap-3 text-xs text-slate-500 font-mono">
                      {item.type === 'file' && <span>{(item.size / 1024).toFixed(1)} KB</span>}
                      <ChevronRight className="w-4 h-4 text-slate-600" />
                    </div>
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      )}

      {/* File Content Viewer Modal */}
      {viewFileModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-4xl p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <FileCode className="w-5 h-5 text-purple-400" /> {viewFileModal.name}
              </h3>
              <button
                onClick={() => setViewFileModal(null)}
                className="text-slate-400 hover:text-slate-200 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="mt-4 flex-1 overflow-y-auto p-4 bg-slate-950 rounded-xl border border-slate-800/80 font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
              {viewFileModal.content}
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
