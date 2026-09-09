import React, { useEffect, useState, useRef } from 'react';
import { documentsApi } from '../api/documents';
import { DocumentItem, ChunkItem } from '../types/document';
import {
  Upload,
  FileText,
  Trash2,
  Download,
  Play,
  Scissors,
  Cpu,
  Database,
  Eye,
  RefreshCw,
  X,
  AlertTriangle,
  CheckCircle,
  Clock,
  FileCode,
} from 'lucide-react';
import { Loading } from '../components/Loading';
import { ErrorMessage } from '../components/ErrorMessage';

export const Documents: React.FC = () => {
  const [documents, setDocuments] = useState<DocumentItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [actionInProgress, setActionInProgress] = useState<number | null>(null);
  const [actionType, setActionType] = useState<string>('');

  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Modals state
  const [viewTextModal, setViewTextModal] = useState<{ id: number; filename: string; text: string } | null>(null);
  const [viewChunksModal, setViewChunksModal] = useState<{ id: number; filename: string; chunks: ChunkItem[] } | null>(null);
  const [deleteConfirmModal, setDeleteConfirmModal] = useState<{ id: number; filename: string } | null>(null);

  const fileInputRef = useRef<HTMLInputElement>(null);

  const fetchDocuments = async (p = page) => {
    setLoading(true);
    setError(null);
    try {
      const res = await documentsApi.list(p, 20);
      setDocuments(res.documents);
      setTotal(res.total);
      setPage(res.page);
    } catch (err: any) {
      console.error('Failed to load documents', err);
      setError(err.response?.data?.detail || 'Failed to fetch documents.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDocuments(1);
  }, []);

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;

    setUploading(true);
    setError(null);
    setSuccess(null);

    try {
      const newDoc = await documentsApi.upload(file);
      setSuccess(`Uploaded ${newDoc.filename} successfully!`);
      await fetchDocuments(1);
    } catch (err: any) {
      console.error('Upload error', err);
      setError(err.response?.data?.detail || 'Document upload failed.');
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = '';
    }
  };

  const handleProcess = async (id: number) => {
    setActionInProgress(id);
    setActionType('Extracting Text');
    setError(null);
    setSuccess(null);
    try {
      await documentsApi.process(id);
      setSuccess('Text extraction completed successfully.');
      await fetchDocuments(page);
    } catch (err: any) {
      console.error('Process error', err);
      setError(err.response?.data?.detail || 'Extraction failed.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleChunk = async (id: number) => {
    setActionInProgress(id);
    setActionType('Chunking Text');
    setError(null);
    setSuccess(null);
    try {
      const res = await documentsApi.chunk(id, 1000, 200);
      setSuccess(`Chunked into ${res.total_chunks} chunks successfully.`);
      await fetchDocuments(page);
    } catch (err: any) {
      console.error('Chunk error', err);
      setError(err.response?.data?.detail || 'Chunking failed.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleEmbed = async (id: number) => {
    setActionInProgress(id);
    setActionType('Generating Embeddings');
    setError(null);
    setSuccess(null);
    try {
      const res = await documentsApi.embed(id);
      setSuccess(`Generated ${res.total_chunks} embeddings (${res.embedding_dimension}-dim) successfully.`);
      await fetchDocuments(page);
    } catch (err: any) {
      console.error('Embed error', err);
      setError(err.response?.data?.detail || 'Embedding generation failed.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleIndex = async (id: number) => {
    setActionInProgress(id);
    setActionType('Indexing in ChromaDB');
    setError(null);
    setSuccess(null);
    try {
      const res = await documentsApi.index(id);
      setSuccess(`Indexed ${res.indexed_chunks} chunks into ChromaDB collection "${res.collection}".`);
      await fetchDocuments(page);
    } catch (err: any) {
      console.error('Index error', err);
      setError(err.response?.data?.detail || 'Chroma indexing failed.');
    } finally {
      setActionInProgress(null);
    }
  };

  const handleViewText = async (doc: DocumentItem) => {
    setError(null);
    try {
      const res = await documentsApi.getText(doc.id);
      setViewTextModal({
        id: doc.id,
        filename: doc.filename,
        text: res.extracted_text || 'No text extracted.',
      });
    } catch (err: any) {
      console.error('View text error', err);
      setError(err.response?.data?.detail || 'Failed to retrieve extracted text.');
    }
  };

  const handleViewChunks = async (doc: DocumentItem) => {
    setError(null);
    try {
      const res = await documentsApi.getChunks(doc.id);
      setViewChunksModal({
        id: doc.id,
        filename: doc.filename,
        chunks: res.chunks,
      });
    } catch (err: any) {
      console.error('View chunks error', err);
      setError(err.response?.data?.detail || 'Failed to retrieve document chunks.');
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirmModal) return;
    const { id, filename } = deleteConfirmModal;
    setError(null);
    setSuccess(null);
    try {
      await documentsApi.delete(id);
      setSuccess(`Deleted ${filename} successfully.`);
      setDeleteConfirmModal(null);
      await fetchDocuments(page);
    } catch (err: any) {
      console.error('Delete error', err);
      setError(err.response?.data?.detail || 'Failed to delete document.');
    }
  };

  const formatFileSize = (bytes: number) => {
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
  };

  const getStatusBadge = (status: DocumentItem['status']) => {
    switch (status) {
      case 'uploaded':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-blue-500/10 text-blue-400 border border-blue-500/20">
            <Clock className="w-3 h-3" /> Uploaded
          </span>
        );
      case 'processing':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-500/10 text-amber-400 border border-amber-500/20 animate-pulse">
            <RefreshCw className="w-3 h-3 animate-spin" /> Processing
          </span>
        );
      case 'processed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            <CheckCircle className="w-3 h-3" /> Processed
          </span>
        );
      case 'failed':
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-red-500/10 text-red-400 border border-red-500/20">
            <AlertTriangle className="w-3 h-3" /> Failed
          </span>
        );
      default:
        return (
          <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold bg-purple-500/10 text-purple-400 border border-purple-500/20">
            <CheckCircle className="w-3 h-3" /> {status}
          </span>
        );
    }
  };

  return (
    <div className="space-y-6">
      {/* Top Header & Actions */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b border-slate-800">
        <div>
          <h2 className="text-2xl font-bold text-white tracking-tight flex items-center gap-2">
            <FileText className="w-7 h-7 text-brand-500" /> Document Intelligence & RAG Pipeline
          </h2>
          <p className="text-sm text-slate-400 mt-1">
            Upload enterprise documents, extract clean text, generate vector embeddings, and index into ChromaDB.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <input
            type="file"
            ref={fileInputRef}
            onChange={handleFileUpload}
            accept=".pdf,.docx,.txt,.md"
            className="hidden"
          />
          <button
            onClick={() => fileInputRef.current?.click()}
            disabled={uploading}
            className="flex items-center gap-2 px-4 py-2.5 bg-gradient-to-r from-brand-600 to-emerald-500 hover:from-brand-500 hover:to-emerald-400 text-white font-semibold rounded-xl text-sm shadow-lg shadow-brand-950/40 transition disabled:opacity-50"
          >
            <Upload className="w-4 h-4" />
            <span>{uploading ? 'Uploading...' : 'Upload Document'}</span>
          </button>
          <button
            onClick={() => fetchDocuments(page)}
            disabled={loading}
            className="p-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 rounded-xl border border-slate-700 transition"
            title="Refresh list"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
          </button>
        </div>
      </div>

      {/* Notifications */}
      {error && <ErrorMessage message={error} onDismiss={() => setError(null)} />}
      {success && (
        <div className="flex items-center justify-between p-4 border rounded-lg bg-emerald-950/40 border-emerald-800/60 text-emerald-200 text-sm font-medium">
          <div className="flex items-center gap-2">
            <CheckCircle className="w-5 h-5 text-emerald-400" />
            <span>{success}</span>
          </div>
          <button onClick={() => setSuccess(null)} className="text-emerald-400 hover:text-emerald-200">
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Pipeline Status Banner */}
      {actionInProgress !== null && (
        <div className="p-4 rounded-xl bg-slate-900 border border-brand-500/40 flex items-center justify-between animate-pulse">
          <div className="flex items-center gap-3">
            <RefreshCw className="w-5 h-5 text-brand-400 animate-spin" />
            <span className="text-sm font-semibold text-slate-200">
              Running pipeline: <span className="text-brand-400">{actionType}</span> on document #{actionInProgress}...
            </span>
          </div>
        </div>
      )}

      {/* Documents Table */}
      <div className="bg-slate-900/80 border border-slate-800 rounded-2xl overflow-hidden shadow-xl">
        {loading && documents.length === 0 ? (
          <Loading message="Loading documents..." />
        ) : documents.length === 0 ? (
          <div className="p-12 text-center">
            <FileCode className="w-12 h-12 text-slate-600 mx-auto mb-3" />
            <h3 className="text-base font-bold text-slate-300">No documents found</h3>
            <p className="text-xs text-slate-500 mt-1 max-w-sm mx-auto">
              Upload PDF, DOCX, TXT, or Markdown documents to start extracting knowledge and indexing into vector database.
            </p>
          </div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-950/60 text-slate-400 text-xs uppercase tracking-wider border-b border-slate-800">
                <tr>
                  <th className="px-6 py-4 font-semibold">Document</th>
                  <th className="px-4 py-4 font-semibold">Format</th>
                  <th className="px-4 py-4 font-semibold">Size</th>
                  <th className="px-4 py-4 font-semibold">Status</th>
                  <th className="px-4 py-4 font-semibold">Uploaded</th>
                  <th className="px-6 py-4 font-semibold text-right">Pipeline Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/60">
                {documents.map((doc) => {
                  const isBusy = actionInProgress === doc.id;
                  return (
                    <tr key={doc.id} className="hover:bg-slate-800/40 transition">
                      <td className="px-6 py-4">
                        <div className="font-semibold text-slate-200">{doc.filename}</div>
                        <div className="text-xs text-slate-500">ID: #{doc.id}</div>
                      </td>
                      <td className="px-4 py-4">
                        <span className="px-2 py-0.5 rounded bg-slate-800 text-slate-300 font-mono text-xs font-semibold">
                          .{doc.file_type}
                        </span>
                      </td>
                      <td className="px-4 py-4 text-slate-400">{formatFileSize(doc.file_size)}</td>
                      <td className="px-4 py-4">{getStatusBadge(doc.status)}</td>
                      <td className="px-4 py-4 text-slate-400 text-xs">
                        {new Date(doc.created_at).toLocaleDateString()}
                      </td>
                      <td className="px-6 py-4 text-right">
                        <div className="flex items-center justify-end gap-1.5 flex-wrap">
                          {/* Extract Text */}
                          <button
                            onClick={() => handleProcess(doc.id)}
                            disabled={isBusy}
                            className="p-1.5 rounded-lg bg-blue-950/40 hover:bg-blue-900/60 text-blue-400 border border-blue-800/40 transition disabled:opacity-50"
                            title="1. Process text extraction"
                          >
                            <Play className="w-3.5 h-3.5" />
                          </button>

                          {/* Chunk */}
                          <button
                            onClick={() => handleChunk(doc.id)}
                            disabled={isBusy || doc.status === 'uploaded'}
                            className="p-1.5 rounded-lg bg-indigo-950/40 hover:bg-indigo-900/60 text-indigo-400 border border-indigo-800/40 transition disabled:opacity-50"
                            title="2. Chunk extracted text"
                          >
                            <Scissors className="w-3.5 h-3.5" />
                          </button>

                          {/* Embed */}
                          <button
                            onClick={() => handleEmbed(doc.id)}
                            disabled={isBusy || doc.status === 'uploaded'}
                            className="p-1.5 rounded-lg bg-purple-950/40 hover:bg-purple-900/60 text-purple-400 border border-purple-800/40 transition disabled:opacity-50"
                            title="3. Generate vector embeddings"
                          >
                            <Cpu className="w-3.5 h-3.5" />
                          </button>

                          {/* Index */}
                          <button
                            onClick={() => handleIndex(doc.id)}
                            disabled={isBusy || doc.status === 'uploaded'}
                            className="p-1.5 rounded-lg bg-emerald-950/40 hover:bg-emerald-900/60 text-emerald-400 border border-emerald-800/40 transition disabled:opacity-50"
                            title="4. Index into ChromaDB"
                          >
                            <Database className="w-3.5 h-3.5" />
                          </button>

                          {/* View Text */}
                          {doc.extracted_text && (
                            <button
                              onClick={() => handleViewText(doc)}
                              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                              title="View extracted plain text"
                            >
                              <Eye className="w-3.5 h-3.5" />
                            </button>
                          )}

                          {/* View Chunks */}
                          <button
                            onClick={() => handleViewChunks(doc)}
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition text-[11px] font-mono font-bold px-2"
                            title="Inspect text chunks"
                          >
                            Chunks
                          </button>

                          {/* Download */}
                          <button
                            onClick={() => documentsApi.download(doc.id, doc.filename)}
                            className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-300 border border-slate-700 transition"
                            title="Download original document file"
                          >
                            <Download className="w-3.5 h-3.5" />
                          </button>

                          {/* Delete */}
                          <button
                            onClick={() => setDeleteConfirmModal({ id: doc.id, filename: doc.filename })}
                            disabled={isBusy}
                            className="p-1.5 rounded-lg bg-red-950/40 hover:bg-red-900/60 text-red-400 border border-red-800/40 transition disabled:opacity-50"
                            title="Delete document & vectors"
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            {total > 0 && (
              <div className="px-6 py-3 bg-slate-950/40 border-t border-slate-800/80 text-xs text-slate-500 flex justify-between items-center">
                <span>Showing {documents.length} of {total} documents</span>
                <span className="font-mono text-[10px]">Page {page}</span>
              </div>
            )}
          </div>
        )}
      </div>

      {/* View Text Modal */}
      {viewTextModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-3xl p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <FileText className="w-5 h-5 text-brand-400" /> Extracted Text: {viewTextModal.filename}
              </h3>
              <button
                onClick={() => setViewTextModal(null)}
                className="text-slate-400 hover:text-slate-200 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="mt-4 flex-1 overflow-y-auto p-4 bg-slate-950 rounded-xl border border-slate-800/80 font-mono text-xs text-slate-300 leading-relaxed whitespace-pre-wrap">
              {viewTextModal.text}
            </div>
          </div>
        </div>
      )}

      {/* View Chunks Modal */}
      {viewChunksModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-4xl p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl max-h-[85vh] flex flex-col">
            <div className="flex items-center justify-between pb-4 border-b border-slate-800">
              <h3 className="text-lg font-bold text-white flex items-center gap-2">
                <Scissors className="w-5 h-5 text-purple-400" /> Document Chunks ({viewChunksModal.chunks.length}): {viewChunksModal.filename}
              </h3>
              <button
                onClick={() => setViewChunksModal(null)}
                className="text-slate-400 hover:text-slate-200 transition"
              >
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="mt-4 flex-1 overflow-y-auto space-y-3 p-1">
              {viewChunksModal.chunks.length === 0 ? (
                <div className="text-center py-8 text-slate-500 text-sm">No chunks generated yet.</div>
              ) : (
                viewChunksModal.chunks.map((c) => (
                  <div
                    key={c.id || c.chunk_index}
                    className="p-4 rounded-xl bg-slate-950 border border-slate-800 text-xs space-y-2"
                  >
                    <div className="flex items-center justify-between text-slate-400 font-mono">
                      <span className="font-bold text-brand-400">Chunk #{c.chunk_index}</span>
                      <span>{c.char_count} characters</span>
                    </div>
                    <div className="text-slate-200 font-mono text-xs leading-relaxed whitespace-pre-wrap">
                      {c.text}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>
        </div>
      )}

      {/* Delete Confirmation Modal */}
      {deleteConfirmModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-sm">
          <div className="w-full max-w-md p-6 bg-slate-900 border border-slate-800 rounded-2xl shadow-2xl">
            <div className="flex items-center gap-3 text-red-400 mb-3">
              <AlertTriangle className="w-6 h-6" />
              <h3 className="text-lg font-bold text-white">Delete Document?</h3>
            </div>
            <p className="text-sm text-slate-400">
              Are you sure you want to delete <span className="font-semibold text-slate-200">"{deleteConfirmModal.filename}"</span>?
              This will permanently delete the physical file, metadata, and all indexed vector embeddings from ChromaDB.
            </p>
            <div className="mt-6 flex items-center justify-end gap-3">
              <button
                onClick={() => setDeleteConfirmModal(null)}
                className="px-4 py-2 text-xs font-semibold text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 rounded-xl transition"
              >
                Cancel
              </button>
              <button
                onClick={handleDelete}
                className="px-4 py-2 text-xs font-semibold text-white bg-red-600 hover:bg-red-500 rounded-xl transition"
              >
                Delete Permanently
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
