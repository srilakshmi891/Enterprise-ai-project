import React, { useEffect, useState } from 'react';
import { jiraApi } from '../api/jira';
import { JiraProjectSummary, JiraIssueSummary } from '../types/jira';
import {
  Trello,
  Search,
  ArrowLeft,
  ClipboardList,
  CheckCircle2,
  AlertCircle,
  HelpCircle,
} from 'lucide-react';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';

export const Jira: React.FC = () => {
  const [projects, setProjects] = useState<JiraProjectSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Selected project backlog view
  const [selectedProject, setSelectedProject] = useState<JiraProjectSummary | null>(null);
  const [issuesList, setIssuesList] = useState<JiraIssueSummary[]>([]);
  const [issuesLoading, setIssuesLoading] = useState(false);

  // JQL Search Bar
  const [jqlQuery, setJqlQuery] = useState<string>('');
  const [searchResults, setSearchResults] = useState<JiraIssueSummary[] | null>(null);

  const fetchProjects = async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await jiraApi.getProjects();
      setProjects(data);
    } catch (err: any) {
      console.error('Failed to load Jira projects', err);
      setError(err.response?.data?.detail || 'Failed to retrieve Jira projects.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchProjects();
  }, []);

  const handleSelectProject = async (proj: JiraProjectSummary) => {
    setSelectedProject(proj);
    setIssuesLoading(true);
    setSearchResults(null);
    setError(null);
    try {
      const res = await jiraApi.getProjectIssues(proj.key, 0, 50);
      setIssuesList(res.issues);
    } catch (err: any) {
      console.error('Failed to load project issues', err);
      setError(err.response?.data?.detail || 'Failed to fetch project issues backlog.');
    } finally {
      setIssuesLoading(false);
    }
  };

  const handleJqlSearch = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!jqlQuery.trim()) return;

    setIssuesLoading(true);
    setError(null);
    try {
      const res = await jiraApi.searchIssues(jqlQuery, 0, 50);
      setSearchResults(res.issues);
      setSelectedProject(null); // Clear selected project card view when searching globally
    } catch (err: any) {
      console.error('JQL search failed', err);
      setError(err.response?.data?.detail || 'JQL Query execution failed. Check JQL syntax.');
    } finally {
      setIssuesLoading(false);
    }
  };

  const getStatusIcon = (status?: string) => {
    const s = status?.toLowerCase() || '';
    if (s.includes('done') || s.includes('complete') || s.includes('resolved')) {
      return <CheckCircle2 className="w-4 h-4 text-emerald-400" />;
    }
    if (s.includes('progress') || s.includes('active') || s.includes('review')) {
      return <HelpCircle className="w-4 h-4 text-blue-400 animate-pulse" />;
    }
    return <AlertCircle className="w-4 h-4 text-slate-500" />;
  };

  if (loading) {
    return <Loading message="Syncing with Jira Cloud API..." />;
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="pb-6 border-b border-slate-800 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <Trello className="w-7 h-7 text-cyan-400" /> Jira Project Backlog Explorer
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Track agile project boards, list issues, and execute structured JQL query searches.
          </p>
        </div>

        {/* Global JQL search form */}
        <form onSubmit={handleJqlSearch} className="flex items-center gap-2 w-full sm:max-w-md">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-3 w-4 h-4 text-slate-500" />
            <input
              type="text"
              value={jqlQuery}
              onChange={(e) => setJqlQuery(e.target.value)}
              placeholder="JQL: project = PROJ ORDER BY priority DESC"
              className="w-full pl-9 pr-4 py-2 bg-slate-900 border border-slate-850 rounded-xl text-slate-200 placeholder-slate-500 text-xs focus:outline-none focus:border-cyan-500"
            />
          </div>
          <button
            type="submit"
            className="px-3.5 py-2 bg-cyan-600 hover:bg-cyan-500 text-white font-semibold rounded-xl text-xs transition"
          >
            Search
          </button>
        </form>
      </div>

      {error && <ErrorMessage message={error} onDismiss={() => setError(null)} />}

      {/* Main View Grid: Left list projects, Right view issues details */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Side: Projects List */}
        <div className="lg:col-span-1 space-y-3">
          <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400 mb-3">
            Projects Backlog
          </h3>

          {projects.length === 0 ? (
            <div className="p-8 text-center bg-slate-900/60 border border-slate-800 rounded-2xl text-xs text-slate-500">
              No Jira projects found. Configure JIRA_URL & tokens in backend `.env` file.
            </div>
          ) : (
            projects.map((proj) => (
              <div
                key={proj.id}
                onClick={() => handleSelectProject(proj)}
                className={`p-4 rounded-xl border cursor-pointer transition ${
                  selectedProject?.id === proj.id
                    ? 'bg-cyan-500/10 border-cyan-500/30 text-cyan-300'
                    : 'bg-slate-900/80 border-slate-800 text-slate-300 hover:bg-slate-900 hover:border-slate-700'
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-[10px] font-bold tracking-wider px-2 py-0.5 rounded bg-slate-800 text-slate-400 font-mono">
                    {proj.key}
                  </span>
                  <span className="text-[10px] text-slate-500 uppercase">{proj.projectTypeKey}</span>
                </div>
                <h4 className="text-sm font-bold text-white mt-2 truncate">{proj.name}</h4>
              </div>
            ))
          )}
        </div>

        {/* Right Side: Backlog Issues Table list */}
        <div className="lg:col-span-2 space-y-3">
          {/* Section title */}
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-bold uppercase tracking-wider text-slate-400">
              {selectedProject
                ? `Backlog issues for: ${selectedProject.name}`
                : searchResults
                ? `JQL Search Results (${searchResults.length})`
                : 'Select project or run JQL search'}
            </h3>
            {searchResults && (
              <button
                onClick={() => {
                  setSearchResults(null);
                  fetchProjects();
                }}
                className="text-xs text-brand-400 flex items-center gap-1"
              >
                <ArrowLeft className="w-3.5 h-3.5" /> Reset View
              </button>
            )}
          </div>

          <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl min-h-[300px] flex flex-col">
            {issuesLoading ? (
              <Loading message="Syncing issues feed..." />
            ) : !selectedProject && !searchResults ? (
              <div className="flex-1 flex flex-col items-center justify-center p-12 text-center text-slate-500">
                <ClipboardList className="w-12 h-12 text-slate-700 mb-3 animate-pulse" />
                <p className="text-xs">
                  Click on an active project card on the left panel, or write JQL to filter issues globally.
                </p>
              </div>
            ) : (
              (() => {
                const issues = searchResults || issuesList;
                if (issues.length === 0) {
                  return (
                    <div className="flex-1 flex flex-col items-center justify-center p-12 text-center text-slate-500">
                      <ClipboardList className="w-12 h-12 text-slate-700 mb-3" />
                      <p className="text-xs">No active issues found in backlog.</p>
                    </div>
                  );
                }
                return (
                  <div className="overflow-x-auto">
                    <table className="w-full text-left text-xs">
                      <thead className="bg-slate-950/60 text-slate-400 text-[10px] uppercase tracking-wider border-b border-slate-800">
                        <tr>
                          <th className="px-6 py-3.5 font-semibold">Key</th>
                          <th className="px-4 py-3.5 font-semibold">Summary</th>
                          <th className="px-4 py-3.5 font-semibold">Type</th>
                          <th className="px-4 py-3.5 font-semibold">Priority</th>
                          <th className="px-6 py-3.5 font-semibold text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-slate-800/60">
                        {issues.map((issue) => (
                          <tr key={issue.id} className="hover:bg-slate-850/40 transition">
                            <td className="px-6 py-4 font-mono font-bold text-cyan-400">{issue.key}</td>
                            <td className="px-4 py-4 font-medium text-slate-200 max-w-xs truncate">
                              {issue.summary}
                            </td>
                            <td className="px-4 py-4">
                              <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-400 border border-slate-700/60 font-semibold uppercase text-[9px]">
                                {issue.issue_type || 'Task'}
                              </span>
                            </td>
                            <td className="px-4 py-4 text-slate-400 uppercase text-[9px]">{issue.priority || 'Medium'}</td>
                            <td className="px-6 py-4 text-right">
                              <div className="inline-flex items-center gap-1.5 font-semibold text-slate-300">
                                {getStatusIcon(issue.status)}
                                <span>{issue.status || 'To Do'}</span>
                              </div>
                            </td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                );
              })()
            )}
          </div>
        </div>
      </div>
    </div>
  );
};
