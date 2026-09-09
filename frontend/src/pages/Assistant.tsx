import React, { useState, useEffect, useRef } from 'react';
import { assistantApi } from '../api/assistant';
import { documentsApi } from '../api/documents';
import { ChatMessage, AssistantSource, IntentType, ConversationSession } from '../types/assistant';
import { DocumentItem } from '../types/document';
import {
  Send,
  Bot,
  User as UserIcon,
  Sparkles,
  FileText,
  Github,
  Trello,
  Layers,
  Plus,
  Trash2,
  Filter,
  MessageSquare,
  Compass,
} from 'lucide-react';
import { ErrorMessage } from '../components/ErrorMessage';

export const Assistant: React.FC = () => {
  const [conversations, setConversations] = useState<ConversationSession[]>([]);
  const [currentConvId, setCurrentConvId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputQuestion, setInputQuestion] = useState('');
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter options
  const [availableDocs, setAvailableDocs] = useState<DocumentItem[]>([]);
  const [selectedDocId, setSelectedDocId] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Load conversations list and indexed documents on mount
  useEffect(() => {
    const initData = async () => {
      try {
        const [convRes, docRes] = await Promise.allSettled([
          assistantApi.listConversations(1, 50),
          documentsApi.list(1, 100),
        ]);

        if (convRes.status === 'fulfilled') {
          setConversations(convRes.value.items);
          if (convRes.value.items.length > 0) {
            loadConversation(convRes.value.items[0].id);
          }
        }

        if (docRes.status === 'fulfilled') {
          setAvailableDocs(docRes.value.documents);
        }
      } catch (err) {
        console.error('Failed to init assistant data', err);
      }
    };

    initData();
  }, []);

  const loadConversation = async (id: number) => {
    setCurrentConvId(id);
    setError(null);
    try {
      const conv = await assistantApi.getConversation(id);
      setMessages(conv.messages || []);
    } catch (err: any) {
      console.error('Failed to load conversation messages', err);
      setError(err.response?.data?.detail || 'Failed to load conversation.');
    }
  };

  const handleNewConversation = () => {
    setCurrentConvId(null);
    setMessages([]);
    setError(null);
  };

  const handleDeleteConversation = async (id: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await assistantApi.deleteConversation(id);
      const remaining = conversations.filter((c) => c.id !== id);
      setConversations(remaining);
      if (currentConvId === id) {
        if (remaining.length > 0) {
          loadConversation(remaining[0].id);
        } else {
          handleNewConversation();
        }
      }
    } catch (err: any) {
      console.error('Failed to delete conversation', err);
      setError(err.response?.data?.detail || 'Failed to delete conversation.');
    }
  };

  const handleSend = async (e: React.FormEvent) => {
    e.preventDefault();
    const q = inputQuestion.trim();
    if (!q || isSending) return;

    setInputQuestion('');
    setError(null);

    // Optimistic user message
    const userMsg: ChatMessage = {
      role: 'user',
      content: q,
      created_at: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);
    setIsSending(true);

    try {
      // Use multi-turn /assistant/chat API
      const res = await assistantApi.chat({
        question: q,
        conversation_id: currentConvId,
        top_k: 5,
        document_id: selectedDocId,
      });

      // If new conversation was created, update state
      if (!currentConvId && res.conversation_id) {
        setCurrentConvId(res.conversation_id);
        const convsRes = await assistantApi.listConversations(1, 50);
        setConversations(convsRes.items);
      }

      const assistantMsg: ChatMessage = {
        role: 'assistant',
        content: res.answer,
        intent: res.intent,
        sources: res.sources,
        created_at: new Date().toISOString(),
      };

      setMessages((prev) => [...prev, assistantMsg]);
    } catch (err: any) {
      console.error('Chat error', err);
      setError(err.response?.data?.detail || 'Failed to get answer from AI Assistant.');
    } finally {
      setIsSending(false);
    }
  };

  const getIntentBadge = (intent?: IntentType) => {
    switch (intent) {
      case 'DOCUMENT':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <FileText className="w-3 h-3" /> DOCUMENT RAG
          </span>
        );
      case 'GITHUB':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <Github className="w-3 h-3" /> GITHUB REPO
          </span>
        );
      case 'JIRA':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-cyan-500/10 text-cyan-400 border border-cyan-500/20">
            <Trello className="w-3 h-3" /> JIRA ISSUE
          </span>
        );
      case 'GENERAL_PROJECT':
        return (
          <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded text-[11px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <Compass className="w-3 h-3" /> PROJECT OVERVIEW
          </span>
        );
      default:
        return null;
    }
  };

  const samplePrompts = [
    'What documents are available in the workspace?',
    'Summarize the model evaluation guide and key validation techniques.',
    'List all GitHub repositories and their primary languages.',
    'What Jira projects and active issues do we have?',
  ];

  return (
    <div className="flex h-[calc(100vh-8rem)] gap-6">
      {/* Conversations History Sidebar */}
      <div className="w-72 bg-slate-900/80 border border-slate-800 rounded-2xl flex flex-col p-4 shrink-0 overflow-hidden shadow-xl">
        <div className="flex items-center justify-between pb-3 border-b border-slate-800">
          <div className="flex items-center gap-2 text-sm font-bold text-slate-200">
            <MessageSquare className="w-4 h-4 text-brand-400" /> Chats
          </div>
          <button
            onClick={handleNewConversation}
            className="flex items-center gap-1 px-2.5 py-1 text-xs font-semibold bg-brand-600 hover:bg-brand-500 text-white rounded-lg transition"
          >
            <Plus className="w-3.5 h-3.5" /> New
          </button>
        </div>

        <div className="mt-3 flex-1 overflow-y-auto space-y-1.5 pr-1">
          {conversations.length === 0 ? (
            <div className="text-center py-8 text-xs text-slate-500">No previous sessions</div>
          ) : (
            conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => loadConversation(conv.id)}
                className={`flex items-center justify-between px-3 py-2.5 rounded-xl cursor-pointer text-xs font-medium transition group ${
                  currentConvId === conv.id
                    ? 'bg-brand-500/15 border border-brand-500/30 text-brand-300'
                    : 'text-slate-400 hover:bg-slate-800/60 hover:text-slate-200'
                }`}
              >
                <div className="truncate pr-2">{conv.title}</div>
                <button
                  onClick={(e) => handleDeleteConversation(conv.id, e)}
                  className="opacity-0 group-hover:opacity-100 p-1 text-slate-500 hover:text-red-400 transition"
                  title="Delete chat"
                >
                  <Trash2 className="w-3.5 h-3.5" />
                </button>
              </div>
            ))
          )}
        </div>

        {/* Filter Selection */}
        <div className="pt-3 border-t border-slate-800 text-xs">
          <label className="flex items-center gap-1.5 font-semibold text-slate-400 mb-1.5">
            <Filter className="w-3.5 h-3.5" /> Scope to Document
          </label>
          <select
            value={selectedDocId || ''}
            onChange={(e) => setSelectedDocId(e.target.value ? Number(e.target.value) : null)}
            className="w-full px-2.5 py-2 bg-slate-950 border border-slate-800 rounded-lg text-slate-300 text-xs focus:outline-none focus:border-brand-500"
          >
            <option value="">All Documents & Sources</option>
            {availableDocs.map((d) => (
              <option key={d.id} value={d.id}>
                #{d.id} - {d.filename}
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Chat Area */}
      <div className="flex-1 bg-slate-900/80 border border-slate-800 rounded-2xl flex flex-col shadow-xl overflow-hidden">
        {/* Chat Header */}
        <div className="px-6 py-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/40">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-brand-500/10 border border-brand-500/20 text-brand-400">
              <Bot className="w-5 h-5" />
            </div>
            <div>
              <h3 className="text-sm font-bold text-white flex items-center gap-2">
                Project Orchestration & RAG Assistant
                <span className="text-[10px] uppercase font-mono px-2 py-0.5 rounded bg-slate-800 text-slate-400">
                  Gemini 1.5 Flash
                </span>
              </h3>
              <p className="text-xs text-slate-400">
                Ground answers using Documents, GitHub Repositories, and Jira Work items.
              </p>
            </div>
          </div>

          {selectedDocId && (
            <div className="flex items-center gap-1.5 text-xs text-brand-400 bg-brand-500/10 px-3 py-1 rounded-full border border-brand-500/20 font-medium">
              <FileText className="w-3.5 h-3.5" /> Filtered to doc #{selectedDocId}
            </div>
          )}
        </div>

        {/* Error Alert */}
        {error && (
          <div className="px-6 pt-3">
            <ErrorMessage message={error} onDismiss={() => setError(null)} />
          </div>
        )}

        {/* Messages Feed */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {messages.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-center max-w-lg mx-auto py-12">
              <div className="w-16 h-16 rounded-2xl bg-gradient-to-tr from-brand-600/20 to-emerald-400/10 border border-brand-500/30 flex items-center justify-center text-brand-400 mb-4 shadow-xl shadow-brand-950/50">
                <Sparkles className="w-8 h-8" />
              </div>
              <h4 className="text-lg font-bold text-white">How can I assist your project today?</h4>
              <p className="text-xs text-slate-400 mt-1.5 leading-relaxed">
                Ask about uploaded documents, verify model evaluation metrics, inspect GitHub repos, or search Jira backlogs.
              </p>

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-6 w-full text-left">
                {samplePrompts.map((prompt) => (
                  <button
                    key={prompt}
                    onClick={() => setInputQuestion(prompt)}
                    className="p-3 text-xs bg-slate-950/70 hover:bg-slate-800/80 border border-slate-800/80 rounded-xl text-slate-300 hover:text-white transition"
                  >
                    "{prompt}"
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((msg, idx) => (
              <div
                key={idx}
                className={`flex gap-4 ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                {msg.role === 'assistant' && (
                  <div className="w-8 h-8 rounded-xl bg-brand-500/20 border border-brand-500/40 text-brand-400 flex items-center justify-center shrink-0">
                    <Bot className="w-4 h-4" />
                  </div>
                )}

                <div
                  className={`max-w-2xl rounded-2xl p-4 text-sm leading-relaxed shadow-sm ${
                    msg.role === 'user'
                      ? 'bg-brand-600 text-white rounded-tr-none'
                      : 'bg-slate-950 border border-slate-800 text-slate-200 rounded-tl-none'
                  }`}
                >
                  {msg.role === 'assistant' && (
                    <div className="flex items-center justify-between gap-3 mb-2 pb-2 border-b border-slate-800/60">
                      {getIntentBadge(msg.intent)}
                      <span className="text-[10px] text-slate-500 font-mono">
                        {msg.created_at ? new Date(msg.created_at).toLocaleTimeString() : ''}
                      </span>
                    </div>
                  )}

                  <div className="whitespace-pre-wrap">{msg.content}</div>

                  {/* Sources Citation List */}
                  {msg.sources && msg.sources.length > 0 && (
                    <div className="mt-4 pt-3 border-t border-slate-800/80">
                      <div className="text-[11px] font-bold uppercase tracking-wider text-slate-400 mb-2 flex items-center gap-1.5">
                        <Layers className="w-3.5 h-3.5 text-brand-400" /> Grounded Context Sources ({msg.sources.length}):
                      </div>
                      <div className="space-y-1.5">
                        {msg.sources.map((src: AssistantSource, sIdx: number) => (
                          <div
                            key={sIdx}
                            className="p-2 rounded-lg bg-slate-900 border border-slate-800/80 text-xs font-mono flex items-center justify-between text-slate-300"
                          >
                            <div className="flex items-center gap-2 truncate">
                              <span className="text-brand-400 font-bold">[{sIdx + 1}]</span>
                              <span className="truncate">
                                {src.filename || src.repo || src.issue_key || src.project || src.type}
                              </span>
                            </div>
                            {src.distance !== undefined && (
                              <span className="text-[10px] text-slate-500">
                                dist: {src.distance.toFixed(3)}
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>
                  )}
                </div>

                {msg.role === 'user' && (
                  <div className="w-8 h-8 rounded-xl bg-slate-800 border border-slate-700 text-slate-300 flex items-center justify-center shrink-0">
                    <UserIcon className="w-4 h-4" />
                  </div>
                )}
              </div>
            ))
          )}

          {isSending && (
            <div className="flex gap-4 justify-start">
              <div className="w-8 h-8 rounded-xl bg-brand-500/20 border border-brand-500/40 text-brand-400 flex items-center justify-center shrink-0 animate-pulse">
                <Bot className="w-4 h-4" />
              </div>
              <div className="p-4 rounded-2xl rounded-tl-none bg-slate-950 border border-slate-800 text-slate-400 text-xs flex items-center gap-2">
                <span className="w-2 h-2 rounded-full bg-brand-400 animate-ping" />
                Retrieving knowledge and formulating response...
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* Input Bar */}
        <form onSubmit={handleSend} className="p-4 bg-slate-950/60 border-t border-slate-800">
          <div className="flex items-center gap-3">
            <input
              type="text"
              value={inputQuestion}
              onChange={(e) => setInputQuestion(e.target.value)}
              placeholder="Ask anything about documents, GitHub repos, Jira issues, or evaluation..."
              disabled={isSending}
              className="flex-1 px-4 py-3 bg-slate-950 border border-slate-800 rounded-xl text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-brand-500/50 focus:border-brand-500 transition text-sm"
            />
            <button
              type="submit"
              disabled={!inputQuestion.trim() || isSending}
              className="px-5 py-3 bg-gradient-to-r from-brand-600 to-emerald-500 hover:from-brand-500 hover:to-emerald-400 text-white font-semibold rounded-xl text-sm shadow-lg shadow-brand-950/40 transition disabled:opacity-50 flex items-center gap-2"
            >
              <Send className="w-4 h-4" />
              <span className="hidden sm:inline">Send</span>
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
