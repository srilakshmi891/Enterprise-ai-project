import React from 'react';
import { NavLink } from 'react-router-dom';
import {
  LayoutDashboard,
  FileText,
  MessageSquare,
  Github,
  Trello,
  Cpu,
  Layers,
} from 'lucide-react';

export const Sidebar: React.FC = () => {
  const navItems = [
    { to: '/dashboard', label: 'Dashboard', icon: LayoutDashboard },
    { to: '/documents', label: 'Documents & RAG', icon: FileText },
    { to: '/assistant', label: 'AI Assistant', icon: MessageSquare },
    { to: '/github', label: 'GitHub Repos', icon: Github },
    { to: '/jira', label: 'Jira Projects', icon: Trello },
  ];

  return (
    <aside className="w-64 bg-slate-900/60 border-r border-slate-800 flex flex-col justify-between p-4 shrink-0 min-h-[calc(100vh-4rem)]">
      <div className="space-y-6">
        <div>
          <div className="px-3 text-[11px] font-bold tracking-wider text-slate-500 uppercase">
            Workspace
          </div>
          <nav className="mt-3 space-y-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  className={({ isActive }) =>
                    `flex items-center space-x-3 px-3 py-2.5 rounded-lg text-sm font-medium transition ${
                      isActive
                        ? 'bg-brand-500/15 text-brand-400 border border-brand-500/30 shadow-sm'
                        : 'text-slate-400 hover:text-slate-200 hover:bg-slate-800/60'
                    }`
                  }
                >
                  <Icon className="w-4 h-4 shrink-0" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        <div className="pt-4 border-t border-slate-800/80">
          <div className="px-3 text-[11px] font-bold tracking-wider text-slate-500 uppercase">
            Architecture
          </div>
          <div className="mt-3 px-3 py-3 rounded-lg bg-slate-950/60 border border-slate-800 text-xs space-y-2">
            <div className="flex items-center justify-between text-slate-400">
              <span className="flex items-center gap-1.5"><Cpu className="w-3.5 h-3.5 text-blue-400" /> Model:</span>
              <span className="font-semibold text-slate-300">Gemini 1.5 Flash</span>
            </div>
            <div className="flex items-center justify-between text-slate-400">
              <span className="flex items-center gap-1.5"><Layers className="w-3.5 h-3.5 text-purple-400" /> Embeddings:</span>
              <span className="font-semibold text-slate-300">all-MiniLM-L6-v2</span>
            </div>
            <div className="flex items-center justify-between text-slate-400">
              <span className="flex items-center gap-1.5"><Layers className="w-3.5 h-3.5 text-emerald-400" /> Vector DB:</span>
              <span className="font-semibold text-slate-300">ChromaDB</span>
            </div>
          </div>
        </div>
      </div>

      <div className="p-3 rounded-lg bg-slate-800/40 border border-slate-800 text-[11px] text-slate-500 text-center">
        Enterprise AI Platform v1.0.0
      </div>
    </aside>
  );
};
