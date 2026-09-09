import React from 'react';
import { useAuth } from '../context/AuthContext';
import { LogOut, User as UserIcon, Bot, ShieldCheck } from 'lucide-react';

export const Navbar: React.FC = () => {
  const { user, logout } = useAuth();

  return (
    <header className="sticky top-0 z-40 flex items-center justify-between h-16 px-6 bg-slate-900/90 backdrop-blur-md border-b border-slate-800">
      <div className="flex items-center space-x-3">
        <div className="flex items-center justify-center w-10 h-10 rounded-xl bg-gradient-to-tr from-brand-600 to-emerald-400 text-white shadow-lg shadow-emerald-900/30">
          <Bot className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-base font-bold tracking-tight text-white flex items-center gap-2">
            Enterprise AI Assistant
            <span className="inline-flex items-center gap-1 text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
              <ShieldCheck className="w-3 h-3" /> Secure RAG
            </span>
          </h1>
          <p className="text-xs text-slate-400">Multi-Turn Project Intelligence & Document Retrieval</p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {user && (
          <div className="flex items-center space-x-3 px-3 py-1.5 rounded-lg bg-slate-800/80 border border-slate-700/60 text-sm">
            <div className="w-7 h-7 rounded-full bg-slate-700 flex items-center justify-center text-slate-300 font-bold text-xs">
              <UserIcon className="w-4 h-4" />
            </div>
            <div className="text-left">
              <div className="font-semibold text-slate-200 text-xs">{user.name || user.username}</div>
              <div className="text-[10px] text-slate-400 truncate max-w-[140px]">{user.email}</div>
            </div>
          </div>
        )}

        <button
          onClick={logout}
          className="flex items-center space-x-1.5 px-3 py-1.5 text-xs font-semibold text-slate-300 hover:text-red-300 bg-slate-800 hover:bg-red-950/40 border border-slate-700 hover:border-red-800/50 rounded-lg transition"
          title="Sign out of system"
        >
          <LogOut className="w-4 h-4" />
          <span>Sign Out</span>
        </button>
      </div>
    </header>
  );
};
