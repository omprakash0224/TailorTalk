import React, { useState, useRef, useEffect } from 'react';
import { Send, Sparkles, Image as ImageIcon, X, ShoppingBag, Eye, HelpCircle } from 'lucide-react';
import MessageBubble from './MessageBubble';
import TypingIndicator from './TypingIndicator';

export default function ChatWindow({
  messages,
  isLoading,
  onSendMessage,
  selectedFile,
  onClearFile,
  imageUrl,
  onClearUrl,
  onOpenSidebar,
  sidebarOpen
}) {
  const [inputText, setInputText] = useState('');
  const messagesEndRef = useRef(null);
  const textareaRef = useRef(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  const handleSubmit = (e) => {
    e?.preventDefault();
    if ((!inputText.trim() && !selectedFile && !imageUrl) || isLoading) {
      return;
    }

    onSendMessage({
      message: inputText,
      file: selectedFile,
      imageUrl: imageUrl || null,
    });

    setInputText('');
    onClearFile();
    onClearUrl();

    if (textareaRef.current) {
      textareaRef.current.style.height = 'auto';
    }
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleTextareaChange = (e) => {
    setInputText(e.target.value);
    // Auto-resize
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  const hasAttachment = Boolean(selectedFile || imageUrl);

  return (
    <main className="chat-container" id="chat-window-main">
      <div className="messages-list" id="chat-messages-container">
        {messages.length === 0 ? (
          <div className="welcome-container" id="welcome-screen">
            <div className="welcome-badge">
              <Sparkles size={13} />
              <span>TailorTalk AI Concierge</span>
            </div>
            
            <h2 className="welcome-title">Find Your Dream Saree With Visual AI</h2>
            
            <p className="welcome-desc">
              Upload a picture of any saree you love, paste an image link, or ask questions about fabrics, zari borders, and colors. Our boutique AI agent will discover the closest matches in our live catalogue.
            </p>

            <div className="feature-cards">
              <div className="feature-card">
                <ImageIcon className="feature-card-icon" size={20} />
                <h4>Visual Matching</h4>
                <p>Upload any saree photo or Pinterest reference</p>
              </div>

              <div className="feature-card">
                <ShoppingBag className="feature-card-icon" size={20} />
                <h4>Smart Budgeting</h4>
                <p>Filter seamlessly by "under ₹3,500" or "cheaper"</p>
              </div>

              <div className="feature-card">
                <Eye className="feature-card-icon" size={20} />
                <h4>Border & Pallu</h4>
                <p>Triple-vector RRF ranking for fine zari details</p>
              </div>
            </div>
          </div>
        ) : (
          messages.map((msg) => (
            <MessageBubble key={msg.id} message={msg} />
          ))
        )}

        {isLoading && <TypingIndicator />}
        <div ref={messagesEndRef} />
      </div>

      {/* Input Area */}
      <div className="chat-input-wrapper">
        <form onSubmit={handleSubmit} className="chat-input-box">
          {/* Active File / URL chip */}
          {selectedFile && (
            <div className="active-attachment-chip" id="active-file-chip">
              <img
                src={URL.createObjectURL(selectedFile)}
                alt="Upload preview"
                className="active-attachment-thumb"
              />
              <span>{selectedFile.name.length > 15 ? selectedFile.name.substring(0, 15) + '...' : selectedFile.name}</span>
              <button
                type="button"
                onClick={onClearFile}
                style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', display: 'flex' }}
                title="Remove attachment"
              >
                <X size={13} />
              </button>
            </div>
          )}

          {imageUrl && !selectedFile && (
            <div className="active-attachment-chip" id="active-url-chip">
              <ImageIcon size={14} />
              <span>Image URL attached</span>
              <button
                type="button"
                onClick={onClearUrl}
                style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', display: 'flex' }}
                title="Remove URL"
              >
                <X size={13} />
              </button>
            </div>
          )}

          {!hasAttachment && !sidebarOpen && (
            <button
              type="button"
              onClick={onOpenSidebar}
              className="btn-icon"
              title="Open Image Upload Studio"
              id="quick-open-upload-btn"
              style={{ width: '34px', height: '34px' }}
            >
              <ImageIcon size={16} />
            </button>
          )}

          <textarea
            ref={textareaRef}
            rows={1}
            value={inputText}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder={hasAttachment ? "Add specific requests (e.g., 'only under ₹3,000' or 'wedding wear')..." : "Ask about sarees, styles, or upload an image to find matches..."}
            className="chat-textarea"
            id="chat-message-input"
          />

          <button
            type="submit"
            disabled={(!inputText.trim() && !hasAttachment) || isLoading}
            className="btn-send"
            id="send-message-btn"
            title="Send message"
          >
            <Send size={18} />
          </button>
        </form>

        <div className="input-footer-note">
          Powered by Gemini Multi-Modal Embeddings & Qdrant Hybrid RRF Search
        </div>
      </div>
    </main>
  );
}
