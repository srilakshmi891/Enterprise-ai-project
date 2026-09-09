import { apiClient } from './client';
import {
  AssistantAskRequest,
  AssistantAskResponse,
  ChatRequest,
  ChatResponse,
  ConversationListResponse,
  ConversationSession,
} from '../types/assistant';

export const assistantApi = {
  ask: async (data: AssistantAskRequest): Promise<AssistantAskResponse> => {
    const response = await apiClient.post<AssistantAskResponse>('/assistant/ask', data);
    return response.data;
  },

  chat: async (data: ChatRequest): Promise<ChatResponse> => {
    const response = await apiClient.post<ChatResponse>('/assistant/chat', data);
    return response.data;
  },

  listConversations: async (page = 1, per_page = 20): Promise<ConversationListResponse> => {
    const response = await apiClient.get<ConversationListResponse>('/conversations', {
      params: { page, per_page },
    });
    return response.data;
  },

  getConversation: async (id: number): Promise<ConversationSession> => {
    const response = await apiClient.get<ConversationSession>(`/conversations/${id}`);
    return response.data;
  },

  createConversation: async (title = 'New Conversation'): Promise<ConversationSession> => {
    const response = await apiClient.post<ConversationSession>('/conversations', { title });
    return response.data;
  },

  deleteConversation: async (id: number): Promise<void> => {
    await apiClient.delete(`/conversations/${id}`);
  },
};
