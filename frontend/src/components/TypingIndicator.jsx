import React from 'react';
import { Sparkles } from 'lucide-react';

export default function TypingIndicator() {
  return (
    <div className="message-row assistant" id="typing-indicator">
      <div className="avatar assistant">
        <Sparkles size={18} />
      </div>
      <div className="bubble-content">
        <div className="typing-bubble">
          <div className="typing-dot" />
          <div className="typing-dot" />
          <div className="typing-dot" />
          <span className="typing-text">Finding perfect sarees...</span>
        </div>
      </div>
    </div>
  );
}
