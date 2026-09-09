export interface DocumentItem {
  id: number;
  filename: string;
  file_type: string;
  mime_type: string;
  file_size: number;
  status: 'uploaded' | 'processing' | 'processed' | 'failed' | 'chunked' | 'embedded' | 'indexed';
  created_at: string;
  updated_at: string;
  extracted_text?: string;
}

export interface DocumentListResponse {
  documents: DocumentItem[];
  total: number;
  page: number;
  per_page: number;
}

export interface DocumentProcessResponse {
  id: number;
  status: string;
  extracted_text?: string;
  message?: string;
}

export interface ChunkItem {
  id: number;
  document_id: number;
  chunk_index: number;
  text: string;
  char_count: number;
  embedding_model?: string;
  created_at?: string;
}

export interface DocumentChunkListResponse {
  document_id: number;
  total_chunks: number;
  chunks: ChunkItem[];
}

export interface DocumentEmbeddingResponse {
  document_id: number;
  total_chunks: number;
  embedding_model: string;
  embedding_dimension: number;
  status: string;
}

export interface DocumentIndexResponse {
  document_id: number;
  indexed_chunks: number;
  collection: string;
  status: string;
}
