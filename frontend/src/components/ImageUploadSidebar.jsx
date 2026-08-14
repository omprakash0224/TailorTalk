import React, { useState, useRef } from 'react';
import { 
  Upload, 
  Image as ImageIcon, 
  Link as LinkIcon, 
  Trash2, 
  Sparkles, 
  Layers, 
  Filter, 
  ChevronRight,
  HelpCircle
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

  return (
    <aside className={`sidebar ${!isOpen ? 'sidebar-collapsed' : ''}`} id="search-sidebar">
      <div className="sidebar-header">
        <div className="sidebar-title">
          <Layers size={18} />
          <span>Visual Search Studio</span>
        </div>
      </div>

      <div className="sidebar-body">
        {/* Upload Zone */}
        <div>
          <label className="input-label" style={{ marginBottom: '8px', display: 'block' }}>
            Query Saree Image
          </label>

          {selectedFile ? (
            <div className="preview-card">
              <img
                src={URL.createObjectURL(selectedFile)}
                alt="Selected saree preview"
                className="preview-image"
              />
              <div className="preview-actions">
                <span className="preview-badge">
                  <ImageIcon size={12} />
                  <span>Image Loaded</span>
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
              <div className="dropzone-subtext" style={{ marginTop: '4px', opacity: 0.7 }}>
                JPG, PNG, WEBP supported
              </div>
            </div>
          )}
        </div>

        {/* Divider */}
        <div className="divider">or use web link</div>

        {/* URL Input */}
        <div className="input-group">
          <label className="input-label" htmlFor="image-url-input">
            Image Web URL
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
          <label className="input-label" style={{ marginBottom: '8px', display: 'block' }}>
            Quick Styling Prompts
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
                <Sparkles size={13} style={{ flexShrink: 0 }} />
                <span>{p.label}</span>
              </button>
            ))}
          </div>
        </div>

        {/* How it works info */}
        <div style={{ marginTop: 'auto', padding: '14px', background: 'var(--bg-glass)', borderRadius: 'var(--radius-md)', border: '1px solid var(--border-subtle)' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '6px', fontSize: '0.8rem', fontWeight: '600', color: 'var(--text-gold)' }}>
            <Sparkles size={14} />
            <span>AI Dual-Crop Matching</span>
          </div>
          <p style={{ fontSize: '0.72rem', color: 'var(--text-muted)', lineHeight: '1.5' }}>
            Our engine extracts color histograms, body patterns, and intricate zari border weaves for high-precision boutique retrieval.
          </p>
        </div>
      </div>
    </aside>
  );
}
