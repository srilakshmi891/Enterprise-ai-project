import React, { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { documentsApi } from '../api/documents';
import { githubApi } from '../api/github';
import { jiraApi } from '../api/jira';
import {
  FileText,
  CheckCircle2,
  Database,
  Github,
  Trello,
  MessageSquare,
  ArrowRight,
  Sparkles,
  Layers,
  Cpu,
} from 'lucide-react';
import { Loading } from '../components/Loading';

export const Dashboard: React.FC = () => {
  const { user } = useAuth();
  const [stats, setStats] = useState({
    totalDocs: 0,
    processedDocs: 0,
    indexedDocs: 0,
    githubRepos: 0,
    jiraProjects: 0,
  });
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchDashboardData = async () => {
      setLoading(true);
      try {
        const [docsRes, reposRes, projectsRes] = await Promise.allSettled([
          documentsApi.list(1, 100),
          githubApi.getRepositories(1, 100),
          jiraApi.getProjects(),
        ]);

        let totalDocs = 0;
        let processedDocs = 0;
        let indexedDocs = 0;
        let githubRepos = 0;
        let jiraProjects = 0;

        if (docsRes.status === 'fulfilled') {
          totalDocs = docsRes.value.total;
          processedDocs = docsRes.value.documents.filter(
            (d) => d.status === 'processed' || d.status === 'chunked' || d.status === 'embedded' || d.status === 'indexed'
          ).length;
          indexedDocs = docsRes.value.documents.filter((d) => d.status === 'indexed').length;
        }

        if (reposRes.status === 'fulfilled') {
          githubRepos = reposRes.value.length;
        }

        if (projectsRes.status === 'fulfilled') {
          jiraProjects = projectsRes.value.length;
        }

        setStats({
          totalDocs,
          processedDocs,
          indexedDocs,
          githubRepos,
          jiraProjects,
        });
      } catch (err) {
        console.error('Failed to load dashboard stats', err);
      } finally {
        setLoading(false);
      }
    };

    fetchDashboardData();
  }, []);

  if (loading) {
    return <Loading message="Loading enterprise metrics..." />;
  }

  const statCards = [
    {
      title: 'Total Documents',
      value: stats.totalDocs,
      icon: FileText,
      color: 'from-blue-500/20 to-blue-600/10 border-blue-500/30 text-blue-400',
      to: '/documents',
    },
    {
      title: 'Processed Text',
      value: stats.processedDocs,
      icon: CheckCircle2,
      color: 'from-emerald-500/20 to-emerald-600/10 border-emerald-500/30 text-emerald-400',
      to: '/documents',
    },
    {
      title: 'Indexed Vectors',
      value: stats.indexedDocs,
      icon: Database,
      color: 'from-purple-500/20 to-purple-600/10 border-purple-500/30 text-purple-400',
      to: '/documents',
    },
    {
      title: 'GitHub Repos',
      value: stats.githubRepos,
      icon: Github,
      color: 'from-slate-700/40 to-slate-800/20 border-slate-700 text-slate-300',
      to: '/github',
    },
    {
      title: 'Jira Projects',
      value: stats.jiraProjects,
      icon: Trello,
      color: 'from-cyan-500/20 to-blue-600/10 border-cyan-500/30 text-cyan-400',
      to: '/jira',
    },
  ];

  const quickNav = [
    {
      title: 'Ask AI Assistant',
      desc: 'Ground questions across your documents, GitHub commits, and Jira issues.',
      icon: MessageSquare,
      to: '/assistant',
      badge: 'Multi-Turn RAG',
      accent: 'border-brand-500/40 hover:border-brand-500 bg-brand-950/20 hover:bg-brand-950/40 text-brand-400',
    },
    {
      title: 'Document Intelligence',
      desc: 'Upload PDFs, Word docs, Markdown, chunk and index vectors into ChromaDB.',
      icon: FileText,
      to: '/documents',
      badge: 'Pipelines',
      accent: 'border-blue-500/40 hover:border-blue-500 bg-blue-950/20 hover:bg-blue-950/40 text-blue-400',
    },
    {
      title: 'GitHub Repositories',
      desc: 'Explore source files, view directory trees, and inspect repo contents.',
      icon: Github,
      to: '/github',
      badge: 'Code Sync',
      accent: 'border-slate-700 hover:border-slate-500 bg-slate-900/40 hover:bg-slate-900/80 text-slate-300',
    },
    {
      title: 'Jira Project Issues',
      desc: 'Browse issue backlogs, sprint tracking, and project tasks.',
      icon: Trello,
      to: '/jira',
      badge: 'Agile Tracker',
      accent: 'border-cyan-500/40 hover:border-cyan-500 bg-cyan-950/20 hover:bg-cyan-950/40 text-cyan-400',
    },
  ];

  return (
    <div className="space-y-8">
      {/* Header Banner */}
      <div className="relative p-6 sm:p-8 rounded-2xl bg-gradient-to-r from-slate-900 via-slate-850 to-slate-900 border border-slate-800 overflow-hidden shadow-xl">
        <div className="absolute right-0 top-0 bottom-0 w-1/3 bg-gradient-to-l from-brand-500/10 to-transparent pointer-events-none" />
        <div className="relative z-10">
          <div className="inline-flex items-center gap-2 px-3 py-1 mb-4 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-semibold">
            <Sparkles className="w-3.5 h-3.5" /> Welcome back, {user?.name || user?.username}!
          </div>
          <h2 className="text-2xl sm:text-3xl font-extrabold text-white tracking-tight">
            Enterprise Intelligence Workspace
          </h2>
          <p className="text-slate-400 text-sm max-w-2xl mt-2">
            Ask multi-turn natural language questions, ingest enterprise documents, and query GitHub repositories & Jira projects through semantic retrieval.
          </p>
        </div>
      </div>

      {/* Metrics Grid */}
      <div>
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">
          Enterprise Knowledge Metrics
        </h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-5 gap-4">
          {statCards.map((card) => {
            const Icon = card.icon;
            return (
              <Link
                key={card.title}
                to={card.to}
                className={`p-5 rounded-xl border bg-gradient-to-b ${card.color} transition hover:scale-[1.02] hover:shadow-lg flex flex-col justify-between`}
              >
                <div className="flex items-center justify-between">
                  <span className="text-xs font-semibold text-slate-400">{card.title}</span>
                  <Icon className="w-5 h-5 opacity-80" />
                </div>
                <div className="mt-4 flex items-baseline justify-between">
                  <span className="text-3xl font-extrabold text-white">{card.value}</span>
                  <ArrowRight className="w-4 h-4 opacity-50 hover:opacity-100 transition" />
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* Quick Actions Grid */}
      <div>
        <h3 className="text-sm font-bold uppercase tracking-wider text-slate-400 mb-4">
          Quick Modules
        </h3>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {quickNav.map((item) => {
            const Icon = item.icon;
            return (
              <Link
                key={item.title}
                to={item.to}
                className={`p-6 rounded-xl border ${item.accent} transition flex flex-col justify-between group shadow-sm`}
              >
                <div>
                  <div className="flex items-center justify-between mb-3">
                    <div className="p-2.5 rounded-lg bg-slate-900/80 border border-slate-800">
                      <Icon className="w-6 h-6" />
                    </div>
                    <span className="text-[11px] font-bold uppercase tracking-wider px-2.5 py-1 rounded-full bg-slate-800/80 border border-slate-700 text-slate-300">
                      {item.badge}
                    </span>
                  </div>
                  <h4 className="text-lg font-bold text-white group-hover:text-brand-300 transition">
                    {item.title}
                  </h4>
                  <p className="text-sm text-slate-400 mt-1">{item.desc}</p>
                </div>
                <div className="mt-6 flex items-center gap-2 text-xs font-semibold text-slate-300 group-hover:translate-x-1 transition-transform">
                  <span>Open Module</span>
                  <ArrowRight className="w-4 h-4" />
                </div>
              </Link>
            );
          })}
        </div>
      </div>

      {/* System Status Footprint */}
      <div className="p-5 rounded-xl bg-slate-900/60 border border-slate-800 flex flex-wrap items-center justify-between gap-4 text-xs">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="w-2.5 h-2.5 rounded-full bg-brand-500 animate-pulse" />
            <span className="font-semibold text-slate-300">FastAPI Backend Operational</span>
          </div>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-1.5 text-slate-400">
            <Cpu className="w-4 h-4 text-blue-400" /> Intent Router Active
          </div>
          <span className="text-slate-600">|</span>
          <div className="flex items-center gap-1.5 text-slate-400">
            <Layers className="w-4 h-4 text-purple-400" /> Chroma Vector DB Connected
          </div>
        </div>
        <div className="text-slate-500">API Endpoint: http://127.0.0.1:8001</div>
      </div>
    </div>
  );
};
