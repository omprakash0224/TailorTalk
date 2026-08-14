import { useState, useCallback, useEffect } from 'react';

// Generates or retrieves a persistent session ID for the tab
const getSessionId = () => {
  let sid = sessionStorage.getItem('tailortalk_session_id');
  if (!sid) {
    sid = 'sess_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
    sessionStorage.setItem('tailortalk_session_id', sid);
  }
  return sid;
};

export function useChat() {
  const [sessionId, setSessionId] = useState(getSessionId);
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const sendMessage = useCallback(async ({ message, file = null, imageUrl = null }) => {
    if ((!message || !message.trim()) && !file && !imageUrl) {
      return;
    }

    const trimmedMsg = message?.trim() || (file ? "Find similar sarees to this uploaded image" : "Find similar sarees to this image URL");
    const userMsgId = 'user_' + Date.now();

    // Create thumbnail preview URL if local file
    let previewUrl = null;
    if (file) {
      previewUrl = URL.createObjectURL(file);
    } else if (imageUrl) {
      previewUrl = imageUrl;
    }

    const newUserMessage = {
      id: userMsgId,
      role: 'user',
      content: trimmedMsg,
      attachedImage: previewUrl,
      timestamp: new Date(),
    };

    setMessages((prev) => [...prev, newUserMessage]);
    setIsLoading(true);
    setError(null);

    try {
      const formData = new FormData();
      formData.append('session_id', sessionId);
      formData.append('message', trimmedMsg);
      
      if (file) {
        formData.append('image', file);
      }
      if (imageUrl) {
        formData.append('image_url', imageUrl);
      }

      const response = await fetch('/api/chat', {
        method: 'POST',
        body: formData,
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `Server error: ${response.status}`);
      }

      const data = await response.json();
      
      const assistantMessage = {
        id: 'asst_' + Date.now(),
        role: 'assistant',
        content: data.reply || "Here is what I found in our saree collection:",
        results: data.results || null,
        timestamp: new Date(),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err) {
      console.error('Failed to send message:', err);
      setError(err.message || 'Something went wrong. Please try again.');
      
      const errorMessage = {
        id: 'err_' + Date.now(),
        role: 'assistant',
        content: `⚠️ **Error**: ${err.message || 'Unable to connect to the saree boutique agent. Please check your connection and try again.'}`,
        isError: true,
        timestamp: new Date(),
      };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  }, [sessionId]);

  const clearChat = useCallback(() => {
    const newSid = 'sess_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
    sessionStorage.setItem('tailortalk_session_id', newSid);
    setSessionId(newSid);
    setMessages([]);
    setError(null);
  }, []);

  return {
    sessionId,
    messages,
    isLoading,
    error,
    sendMessage,
    clearChat,
  };
}
