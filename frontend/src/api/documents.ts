import { apiClient } from './client';
import {
  DocumentItem,
  DocumentListResponse,
  DocumentProcessResponse,
  DocumentChunkListResponse,
  DocumentEmbeddingResponse,
  DocumentIndexResponse,
} from '../types/document';

export const documentsApi = {
  upload: async (file: File): Promise<DocumentItem> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<DocumentItem>('/documents/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  list: async (page = 1, per_page = 20): Promise<DocumentListResponse> => {
    const response = await apiClient.get<DocumentListResponse>('/documents', {
      params: { page, per_page },
    });
    return response.data;
  },

  getDetail: async (id: number): Promise<DocumentItem> => {
    const response = await apiClient.get<DocumentItem>(`/documents/${id}`);
    return response.data;
  },

  download: async (id: number, filename: string): Promise<void> => {
    const response = await apiClient.get(`/documents/${id}/download`, {
      responseType: 'blob',
    });
    const url = window.URL.createObjectURL(new Blob([response.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', filename);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  },

  delete: async (id: number): Promise<void> => {
    await apiClient.delete(`/documents/${id}`);
  },

  process: async (id: number): Promise<DocumentProcessResponse> => {
    const response = await apiClient.post<DocumentProcessResponse>(`/documents/${id}/process`);
    return response.data;
  },

  getText: async (id: number): Promise<DocumentProcessResponse> => {
    const response = await apiClient.get<DocumentProcessResponse>(`/documents/${id}/text`);
    return response.data;
  },

  chunk: async (id: number, chunkSize = 1000, chunkOverlap = 200): Promise<DocumentChunkListResponse> => {
    const response = await apiClient.post<DocumentChunkListResponse>(
      `/documents/${id}/chunk`,
      null,
      { params: { chunk_size: chunkSize, chunk_overlap: chunkOverlap } }
    );
    return response.data;
  },

  getChunks: async (id: number): Promise<DocumentChunkListResponse> => {
    const response = await apiClient.get<DocumentChunkListResponse>(`/documents/${id}/chunks`);
    return response.data;
  },

  embed: async (id: number): Promise<DocumentEmbeddingResponse> => {
    const response = await apiClient.post<DocumentEmbeddingResponse>(`/documents/${id}/embed`);
    return response.data;
  },

  getEmbeddings: async (id: number): Promise<DocumentEmbeddingResponse> => {
    const response = await apiClient.get<DocumentEmbeddingResponse>(`/documents/${id}/embeddings`);
    return response.data;
  },

  index: async (id: number): Promise<DocumentIndexResponse> => {
    const response = await apiClient.post<DocumentIndexResponse>(`/documents/${id}/index`);
    return response.data;
  },
};
