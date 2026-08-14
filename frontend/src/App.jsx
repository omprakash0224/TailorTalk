import React, { useState } from 'react';
import { 
  Sparkles, 
  RotateCcw, 
  PanelLeftClose, 
  PanelLeft, 
  HelpCircle,
  X,
  Layers,
  ShoppingBag
} from 'lucide-react';
import { useChat } from './hooks/useChat';
import ImageUploadSidebar from './components/ImageUploadSidebar';
import ChatWindow from './components/ChatWindow';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [imageUrl, setImageUrl] = useState('');
  const [showInfoModal, setShowInfoModal] = useState(false);

  const {
    sessionId,
    messages,
    isLoading,
    sendMessage,
    clearChat,
  } = useChat();

  const handleQuickPrompt = (promptText) => {
    sendMessage({
      message: promptText,
      file: selectedFile,
      imageUrl: imageUrl || null,
    });
    setSelectedFile(null);
    setImageUrl('');
  };

  return (
    <div className="app-container">
      {/* Top Application Header Navbar */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo" title="TailorTalk Visual Saree AI">🥻</div>
          <div className="brand-info">
            <h1>TailorTalk</h1>
            <p>Visual Saree Stylist & Concierge</p>
          </div>

          <div className="status-pill" style={{ marginLeft: '12px' }}>
            <span className="status-dot"></span>
            <span>AI Engine Ready</span>
          </div>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className={`btn-icon ${sidebarOpen ? 'active' : ''}`}
            onClick={() => setSidebarOpen((prev) => !prev)}
            title={sidebarOpen ? "Hide Image Upload Studio" : "Show Image Upload Studio"}
            id="toggle-sidebar-btn"
          >
            {sidebarOpen ? <PanelLeftClose size={19} /> : <PanelLeft size={19} />}
          </button>

          <button
            type="button"
            className="btn-icon"
            onClick={clearChat}
            title="Start New Conversation"
            id="new-chat-btn"
          >
            <RotateCcw size={18} />
          </button>

          <button
            type="button"
            className="btn-icon"
            onClick={() => setShowInfoModal(true)}
            title="How TailorTalk AI Works"
            id="info-modal-btn"
          >
            <HelpCircle size={19} />
          </button>
        </div>
      </header>

      {/* Main Viewport: Left Sidebar (Upload Studio) + Right Chat Window */}
      <div className="main-content">
        <ImageUploadSidebar
          isOpen={sidebarOpen}
          selectedFile={selectedFile}
          setSelectedFile={setSelectedFile}
          imageUrl={imageUrl}
          setImageUrl={setImageUrl}
          onQuickPrompt={handleQuickPrompt}
        />

        <ChatWindow
          messages={messages}
          isLoading={isLoading}
          onSendMessage={sendMessage}
          selectedFile={selectedFile}
          onClearFile={() => setSelectedFile(null)}
          imageUrl={imageUrl}
          onClearUrl={() => setImageUrl('')}
          onOpenSidebar={() => setSidebarOpen(true)}
          sidebarOpen={sidebarOpen}
          onQuickPrompt={handleQuickPrompt}
        />
      </div>

      {/* AI Search Engine Info Modal */}
      {showInfoModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.75)',
          backdropFilter: 'blur(10px)',
          zIndex: 100,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div style={{
            background: 'var(--bg-tertiary)',
            border: '1px solid var(--border-gold)',
            borderRadius: 'var(--radius-lg)',
            maxWidth: '520px',
            width: '100%',
            padding: '28px',
            boxShadow: 'var(--shadow-lg)',
            position: 'relative'
          }}>
            <button
              onClick={() => setShowInfoModal(false)}
              style={{
                position: 'absolute',
                top: '18px',
                right: '18px',
                background: 'var(--bg-glass)',
                border: '1px solid var(--border-glass)',
                color: 'var(--text-secondary)',
                borderRadius: '50%',
                width: '32px',
                height: '32px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer'
              }}
            >
              <X size={16} />
            </button>

            <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(245, 166, 35, 0.15)',
                border: '1px solid var(--border-gold)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: 'var(--accent-gold)'
              }}>
                <Sparkles size={20} />
              </div>
              <div>
                <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '1.2rem', color: 'var(--text-primary)' }}>
                  How TailorTalk Visual AI Works
                </h3>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>Dual-Crop & Multi-Vector RRF Ranking</p>
              </div>
            </div>

            <div style={{ fontSize: '0.85rem', color: 'var(--text-secondary)', lineHeight: '1.6', display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <p>
                <strong style={{ color: 'var(--accent-gold)' }}>1. Visual Image Analysis:</strong> Uploading an image triggers dual-crop feature extraction isolating both overall saree patterns and close-up zari pallu textures.
              </p>
              <p>
                <strong style={{ color: 'var(--accent-gold)' }}>2. Vector Embeddings:</strong> High-dimensional embeddings are compared against our catalogue vector database in real-time.
              </p>
              <p>
                <strong style={{ color: 'var(--accent-gold)' }}>3. Reciprocal Rank Fusion (RRF):</strong> Text preferences (price limits, occasions, colors) are merged with visual vectors to deliver precise boutique recommendations.
              </p>
            </div>

            <button
              onClick={() => setShowInfoModal(false)}
              style={{
                marginTop: '24px',
                width: '100%',
                padding: '12px',
                background: 'linear-gradient(135deg, var(--accent-gold) 0%, #d97706 100%)',
                color: '#000',
                fontWeight: '700',
                border: 'none',
                borderRadius: 'var(--radius-md)',
                cursor: 'pointer'
              }}
            >
              Got It
            </button>
          </div>
        </div>
      )}
    </div>
  );
}
