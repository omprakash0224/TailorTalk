import React from 'react';
import Markdown from 'react-markdown';
import { User, Sparkles, Image as ImageIcon } from 'lucide-react';
import ProductGrid from './ProductGrid';

export default function MessageBubble({ message }) {
  const isUser = message.role === 'user';

  return (
    <div className={`message-row ${message.role}`} id={`message-${message.id}`}>
      <div className={`avatar ${message.role}`}>
        {isUser ? <User size={18} /> : <Sparkles size={18} />}
      </div>

      <div className="bubble-content">
        {/* If user attached an image, display a badge preview */}
        {isUser && message.attachedImage && (
          <div className="attached-image-badge">
            <img
              src={message.attachedImage}
              alt="Query reference"
              className="attached-image-thumb"
            />
            <span>Visual query reference</span>
          </div>
        )}

        <div className="bubble">
          {isUser ? (
            <p>{message.content}</p>
          ) : (
            <Markdown>{message.content}</Markdown>
          )}
        </div>

        {/* Render Product Grid if assistant returned search matches */}
        {!isUser && message.results && message.results.length > 0 && (
          <ProductGrid results={message.results} />
        )}
      </div>
    </div>
  );
}
