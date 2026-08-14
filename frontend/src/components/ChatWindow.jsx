import React, { useState, useRef, useEffect } from 'react';
import { 
  Send, 
  Sparkles, 
  Image as ImageIcon, 
  X, 
  ShoppingBag, 
  Eye, 
  Command,
  ArrowUpRight
} from 'lucide-react';
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
  sidebarOpen,
  onQuickPrompt
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
    e.target.style.height = 'auto';
    e.target.style.height = `${Math.min(e.target.scrollHeight, 120)}px`;
  };

  const hasAttachment = Boolean(selectedFile || imageUrl);

  const welcomeStarters = [
    { label: "Bridal Sarees under ₹5,000", prompt: "Show me heavy bridal sarees under 5000 rupees" },
    { label: "Red Silk Kanjivaram", prompt: "Find rich red silk Kanjivaram sarees with golden zari" },
    { label: "Pastel Floral Organza", prompt: "Show lightweight pastel floral organza sarees" },
    { label: "Contrast Blouse Combinations", prompt: "Recommend saree styles with contrasting designer blouse options" }
  ];

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
              Upload a picture of any saree you love on the left panel, paste an image link, or chat naturally about fabrics, zari borders, and occasions. Our boutique AI agent will discover the closest matches in our live catalogue.
            </p>

            <div className="feature-cards">
              <div className="feature-card">
                <ImageIcon className="feature-card-icon" size={22} />
                <h4>Visual Matching</h4>
                <p>Upload any saree photo or Pinterest reference image</p>
              </div>

              <div className="feature-card">
                <ShoppingBag className="feature-card-icon" size={22} />
                <h4>Smart Budgeting</h4>
                <p>Filter seamlessly by "under ₹3,500" or "budget options"</p>
              </div>

              <div className="feature-card">
                <Eye className="feature-card-icon" size={22} />
                <h4>Border & Pallu RRF</h4>
                <p>Triple-vector RRF ranking for fine zari & weave details</p>
              </div>
            </div>

            <div style={{ marginTop: '16px', width: '100%' }}>
              <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.05em', fontWeight: '600' }}>
                Try one of these styling requests
              </div>
              <div className="welcome-starters">
                {welcomeStarters.map((starter, idx) => (
                  <button
                    key={idx}
                    type="button"
                    className="starter-chip"
                    onClick={() => onQuickPrompt(starter.prompt)}
                  >
                    <span>{starter.label}</span>
                    <ArrowUpRight size={13} style={{ opacity: 0.7 }} />
                  </button>
                ))}
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

      {/* Floating Sticky Input Bar */}
      <div className="chat-input-wrapper">
        <form onSubmit={handleSubmit} className="chat-input-box">
          {/* Active File / URL attachment chip */}
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
                style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', display: 'flex', padding: 0 }}
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
                style={{ background: 'none', border: 'none', color: 'inherit', cursor: 'pointer', display: 'flex', padding: 0 }}
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
              style={{ width: '36px', height: '36px', flexShrink: 0 }}
            >
              <ImageIcon size={17} />
            </button>
          )}

          <textarea
            ref={textareaRef}
            rows={1}
            value={inputText}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder={hasAttachment ? "Add specific requests (e.g., 'only under ₹3,000' or 'wedding wear')..." : "Ask about sarees, styles, budget options, or upload an image on the left..."}
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
          <span>Press <strong>Enter</strong> to send, <strong>Shift + Enter</strong> for new line</span>
          <span>Powered by Gemini Multi-Modal Embeddings & Qdrant Hybrid Search</span>
        </div>
      </div>
    </main>
  );
}
