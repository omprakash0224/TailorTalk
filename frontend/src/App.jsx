import React, { useState } from 'react';
import { 
  Sparkles, 
  RotateCcw, 
  PanelLeftClose, 
  PanelLeft, 
  ShoppingBag,
  ExternalLink
} from 'lucide-react';
import { useChat } from './hooks/useChat';
import ImageUploadSidebar from './components/ImageUploadSidebar';
import ChatWindow from './components/ChatWindow';

export default function App() {
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [selectedFile, setSelectedFile] = useState(null);
  const [imageUrl, setImageUrl] = useState('');

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
      {/* Top Application Header */}
      <header className="app-header">
        <div className="brand-section">
          <div className="brand-logo">🥻</div>
          <div className="brand-info">
            <h1>TailorTalk</h1>
            <p>Visual Saree Stylist</p>
          </div>
        </div>

        <div className="header-actions">
          <button
            type="button"
            className={`btn-icon ${sidebarOpen ? 'active' : ''}`}
            onClick={() => setSidebarOpen((prev) => !prev)}
            title={sidebarOpen ? "Hide Image Studio" : "Show Image Studio"}
            id="toggle-sidebar-btn"
          >
            {sidebarOpen ? <PanelLeftClose size={18} /> : <PanelLeft size={18} />}
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
        </div>
      </header>

      {/* Main Content: Sidebar + Chat Window */}
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
        />
      </div>
    </div>
  );
}
