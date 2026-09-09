export type IntentType = 'DOCUMENT' | 'GITHUB' | 'JIRA' | 'GENERAL_PROJECT';

export interface AssistantSource {
  type: string;
  filename?: string;
  document_id?: number;
  chunk_id?: number;
  chunk_index?: number;
  repo?: string;
  issue_key?: string;
  project?: string;
  distance?: number;
}

export interface AssistantAskRequest {
  question: string;
  top_k?: number;
  document_id?: number | null;
}

export interface AssistantAskResponse {
  question: string;
  intent: IntentType;
  answer: string;
  sources: AssistantSource[];
  retrieved_count: number;
}

export interface ChatMessage {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
  created_at?: string;
  intent?: IntentType;
  sources?: AssistantSource[];
}

export interface ConversationSession {
  id: number;
  title: string;
  created_at: string;
  updated_at: string;
  messages?: ChatMessage[];
}

export interface ConversationListResponse {
  total: number;
  page: number;
  per_page: number;
  items: ConversationSession[];
}

export interface ChatRequest {
  question: string;
  conversation_id?: number | null;
  top_k?: number;
  document_id?: number | null;
}

export interface ChatResponse {
  conversation_id: number;
  question: string;
  intent: IntentType;
  answer: string;
  sources: AssistantSource[];
  retrieved_count: number;
}
