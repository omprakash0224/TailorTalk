import React, { useState, useRef } from 'react';
import { 
  Upload, 
  Image as ImageIcon, 
  Link as LinkIcon, 
  Trash2, 
  Sparkles, 
  Layers, 
  ChevronRight,
  Maximize2,
  X
} from 'lucide-react';

export default function ImageUploadSidebar({
  isOpen,
  selectedFile,
  setSelectedFile,
  imageUrl,
  setImageUrl,
  onQuickPrompt,
}) {
  const [isDragging, setIsDragging] = useState(false);
  const [showImagePreviewModal, setShowImagePreviewModal] = useState(false);
  const fileInputRef = useRef(null);

  const handleDragOver = (e) => {
    e.preventDefault();
    setIsDragging(true);
  };

  const handleDragLeave = () => {
    setIsDragging(false);
  };

  const handleDrop = (e) => {
    e.preventDefault();
    setIsDragging(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      const file = e.dataTransfer.files[0];
      if (file.type.startsWith('image/')) {
        setSelectedFile(file);
        setImageUrl('');
      }
    }
  };

  const handleFileChange = (e) => {
    if (e.target.files && e.target.files[0]) {
      setSelectedFile(e.target.files[0]);
      setImageUrl('');
    }
  };

  const handleRemoveFile = () => {
    setSelectedFile(null);
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const samplePrompts = [
    { label: "Find similar bridal sarees", text: "Find sarees matching this design for a bridal ceremony" },
    { label: "Show sarees under ₹4,000", text: "Show only options under 4000 rupees" },
    { label: "Find rich zari border styles", text: "Find sarees with a similar heavy zari border and pallu" },
    { label: "What fabric is this style?", text: "What fabric and weave style is this saree?" }
  ];

  const fileObjectUrl = selectedFile ? URL.createObjectURL(selectedFile) : null;

  return (
    <aside className={`sidebar ${!isOpen ? 'sidebar-collapsed' : ''}`} id="search-sidebar">
      <div className="sidebar-header">
        <div className="sidebar-title">
          <Layers size={18} />
          <span>Upload Studio</span>
        </div>
        <span className="sidebar-badge">Visual Search</span>
      </div>

      <div className="sidebar-body">
        {/* Upload Zone */}
        <div>
          <div className="input-label" style={{ marginBottom: '10px' }}>
            <span>Query Saree Image</span>
            {selectedFile && <span style={{ color: 'var(--accent-gold-light)', fontSize: '0.75rem' }}>Active Query</span>}
          </div>

          {selectedFile ? (
            <div className="preview-card">
              <div style={{ position: 'relative' }}>
                <img
                  src={fileObjectUrl}
                  alt="Selected saree preview"
                  className="preview-image"
                />
                <button
                  type="button"
                  onClick={() => setShowImagePreviewModal(true)}
                  style={{
                    position: 'absolute',
                    top: '8px',
                    right: '8px',
                    background: 'rgba(0, 0, 0, 0.65)',
                    color: 'white',
                    border: 'none',
                    borderRadius: 'var(--radius-sm)',
                    padding: '6px',
                    cursor: 'pointer',
                    display: 'flex'
                  }}
                  title="Expand Preview"
                >
                  <Maximize2 size={14} />
                </button>
              </div>

              <div className="preview-actions">
                <span className="preview-badge">
                  <ImageIcon size={12} />
                  <span>{selectedFile.name.length > 18 ? selectedFile.name.substring(0, 15) + '...' : selectedFile.name}</span>
                </span>
                <button
                  type="button"
                  onClick={handleRemoveFile}
                  className="btn-remove"
                  id="remove-uploaded-image-btn"
                >
                  <Trash2 size={12} />
                  <span>Remove</span>
                </button>
              </div>
            </div>
          ) : (
            <div
              className={`dropzone ${isDragging ? 'dragging' : ''}`}
              onDragOver={handleDragOver}
              onDragLeave={handleDragLeave}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              id="image-dropzone"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept="image/jpeg,image/png,image/webp,image/jpg"
                style={{ display: 'none' }}
                onChange={handleFileChange}
                id="file-input-hidden"
              />
              <div className="dropzone-icon">
                <Upload size={22} />
              </div>
              <div className="dropzone-text">Upload Saree Photo</div>
              <div className="dropzone-subtext">Drag & drop or click to browse</div>
              <div className="dropzone-subtext" style={{ marginTop: '6px', color: 'var(--accent-gold-light)', opacity: 0.8, fontSize: '0.72rem' }}>
                JPG, PNG, WEBP up to 10MB
              </div>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="divider">or use web link</div>

        {/* URL Input */}
        <div className="input-group">
          <label className="input-label" htmlFor="image-url-input">
            <span>Image Web URL</span>
            <LinkIcon size={13} style={{ color: 'var(--text-muted)' }} />
          </label>
          <input
            id="image-url-input"
            type="url"
            className="input-field"
            placeholder="https://example.com/saree.jpg"
            value={imageUrl}
            onChange={(e) => {
              setImageUrl(e.target.value);
              if (e.target.value) setSelectedFile(null);
            }}
          />
        </div>

        {/* Quick Assistant Prompts */}
        <div>
          <label className="input-label" style={{ marginBottom: '10px' }}>
            <span>Quick Styling Prompts</span>
            <Sparkles size={13} style={{ color: 'var(--accent-gold)' }} />
          </label>
          <div className="quick-prompts">
            {samplePrompts.map((p, idx) => (
              <button
                key={idx}
                type="button"
                className="quick-prompt-btn"
                onClick={() => onQuickPrompt(p.text)}
                id={`quick-prompt-${idx}`}
              >
                <span>{p.label}</span>
                <ChevronRight size={14} className="quick-prompt-btn-icon" />
              </button>
            ))}
          </div>
        </div>

        {/* Sidebar Info Footer */}
        <div className="sidebar-info-box">
          <div className="sidebar-info-header">
            <Sparkles size={14} />
            <span>AI Dual-Crop Matching</span>
          </div>
          <p className="sidebar-info-desc">
            Our engine extracts color histograms, body patterns, and intricate zari border weaves for high-precision boutique retrieval.
          </p>
        </div>
      </div>

      {/* Expanded Image Modal */}
      {showImagePreviewModal && fileObjectUrl && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0, 0, 0, 0.85)',
          backdropFilter: 'blur(12px)',
          zIndex: 100,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: '20px'
        }}>
          <div style={{ position: 'relative', maxWidth: '90vw', maxHeight: '90vh' }}>
            <button
              onClick={() => setShowImagePreviewModal(false)}
              style={{
                position: 'absolute',
                top: '-40px',
                right: 0,
                background: 'rgba(255, 255, 255, 0.2)',
                border: 'none',
                color: 'white',
                borderRadius: '50%',
                width: '36px',
                height: '36px',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                cursor: 'pointer'
              }}
            >
              <X size={20} />
            </button>
            <img
              src={fileObjectUrl}
              alt="Full preview"
              style={{
                maxWidth: '100%',
                maxHeight: '80vh',
                borderRadius: 'var(--radius-md)',
                objectFit: 'contain',
                boxShadow: 'var(--shadow-lg)'
              }}
            />
          </div>
        </div>
      )}
    </aside>
  );
}
