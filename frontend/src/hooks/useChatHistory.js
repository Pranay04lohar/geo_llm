/**
 * Custom hook for managing chat history.
 * 
 * What: Provides state and methods for managing user chat conversations
 * Why: Centralize chat history logic and provide consistent API
 * How: React hook with API integration and local state management
 */

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { 
  getChatConversations, 
  createChatConversation, 
  getChatMessages,
  addChatMessage,
  updateChatConversation,
  deleteChatConversation
} from '../utils/api';

export const useChatHistory = () => {
  const { isAuthenticated, user } = useAuth();
  const [conversations, setConversations] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [currentConversation, setCurrentConversation] = useState(null);
  const [currentMessages, setCurrentMessages] = useState([]);

  // Load conversations when user authenticates
  useEffect(() => {
    if (isAuthenticated && user) {
      loadConversations();
    } else {
      // Clear data when user signs out
      setConversations([]);
      setCurrentConversation(null);
      setCurrentMessages([]);
    }
  }, [isAuthenticated, user]);

  const loadConversations = useCallback(async () => {
    if (!isAuthenticated) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const data = await getChatConversations(50, 0);
      setConversations(data);
    } catch (err) {
      console.error('Error loading conversations:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  const createConversation = useCallback(async (title) => {
    if (!isAuthenticated) return null;
    
    try {
      const newConversation = await createChatConversation(title);
      setConversations(prev => [newConversation, ...prev]);
      return newConversation;
    } catch (err) {
      console.error('Error creating conversation:', err);
      setError(err.message);
      return null;
    }
  }, [isAuthenticated]);

  const loadConversation = useCallback(async (conversationId) => {
    if (!isAuthenticated) return;
    
    setLoading(true);
    setError(null);
    
    try {
      const [conversation, messages] = await Promise.all([
        getChatConversation(conversationId),
        getChatMessages(conversationId)
      ]);
      
      setCurrentConversation(conversation);
      setCurrentMessages(messages);
    } catch (err) {
      console.error('Error loading conversation:', err);
      setError(err.message);
    } finally {
      setLoading(false);
    }
  }, [isAuthenticated]);

  const sendMessage = useCallback(async (conversationId, role, content, metadata = null) => {
    if (!isAuthenticated) return null;
    
    try {
      const message = await addChatMessage(conversationId, role, content, metadata);
      setCurrentMessages(prev => [...prev, message]);
      
      // Update conversation in the list
      setConversations(prev => 
        prev.map(conv => 
          conv.id === conversationId 
            ? { ...conv, updated_at: new Date().toISOString(), message_count: conv.message_count + 1 }
            : conv
        )
      );
      
      return message;
    } catch (err) {
      console.error('Error sending message:', err);
      setError(err.message);
      return null;
    }
  }, [isAuthenticated]);

  const updateConversation = useCallback(async (conversationId, updates) => {
    if (!isAuthenticated) return null;
    
    try {
      const updatedConversation = await updateChatConversation(conversationId, updates);
      setConversations(prev => 
        prev.map(conv => 
          conv.id === conversationId ? updatedConversation : conv
        )
      );
      
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(updatedConversation);
      }
      
      return updatedConversation;
    } catch (err) {
      console.error('Error updating conversation:', err);
      setError(err.message);
      return null;
    }
  }, [isAuthenticated, currentConversation]);

  const deleteConversation = useCallback(async (conversationId) => {
    if (!isAuthenticated) return false;
    
    try {
      await deleteChatConversation(conversationId);
      setConversations(prev => prev.filter(conv => conv.id !== conversationId));
      
      if (currentConversation?.id === conversationId) {
        setCurrentConversation(null);
        setCurrentMessages([]);
      }
      
      return true;
    } catch (err) {
      console.error('Error deleting conversation:', err);
      setError(err.message);
      return false;
    }
  }, [isAuthenticated, currentConversation]);

  const clearCurrentConversation = useCallback(() => {
    setCurrentConversation(null);
    setCurrentMessages([]);
  }, []);

  const refreshConversations = useCallback(() => {
    if (isAuthenticated) {
      loadConversations();
    }
  }, [isAuthenticated, loadConversations]);

  return {
    // State
    conversations,
    currentConversation,
    currentMessages,
    loading,
    error,
    
    // Actions
    loadConversations,
    createConversation,
    loadConversation,
    sendMessage,
    updateConversation,
    deleteConversation,
    clearCurrentConversation,
    refreshConversations,
    
    // Computed
    hasConversations: conversations.length > 0,
    isCurrentConversationLoaded: !!currentConversation
  };
};
