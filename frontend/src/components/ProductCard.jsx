import React, { useState } from 'react';
import { ExternalLink, Sparkles, Tag } from 'lucide-react';

export default function ProductCard({ item }) {
  const [imageError, setImageError] = useState(false);

  const {
    sku,
    name,
    score,
    image_url,
    product_url,
    price,
    retail_price
  } = item;

  const displayPrice = typeof price === 'number' ? price.toLocaleString('en-IN') : price;
  const displayRetail = typeof retail_price === 'number' ? retail_price.toLocaleString('en-IN') : retail_price;
  const hasDiscount = retail_price && retail_price > price;

  const fallbackImage = "https://images.unsplash.com/photo-1610030469983-98e550d6193c?w=500&auto=format&fit=crop&q=60";

  return (
    <div className="product-card" id={`product-card-${sku || Math.random().toString(36).substr(2, 9)}`}>
      <div className="product-card-img-wrap">
        <img
          src={imageError ? fallbackImage : (image_url || fallbackImage)}
          alt={name || "Saree"}
          className="product-card-img"
          loading="lazy"
          onError={() => setImageError(true)}
        />
        {score !== undefined && score !== null && (
          <div className="product-score-badge">
            <Sparkles size={11} />
            <span>{typeof score === 'number' ? `${score.toFixed(1)}%` : score} Match</span>
          </div>
        )}
      </div>

      <div className="product-card-info">
        <div>
          <h3 className="product-name" title={name}>{name || "Handcrafted Saree"}</h3>
        </div>

        <div>
          <div className="product-pricing">
            <span className="price-discounted">₹{displayPrice}</span>
            {hasDiscount && (
              <span className="price-retail">₹{displayRetail}</span>
            )}
          </div>

          <div style={{ marginTop: '12px' }}>
            <a
              href={product_url || '#'}
              target="_blank"
              rel="noopener noreferrer"
              className="product-action-btn"
              id={`view-product-btn-${sku || 'link'}`}
            >
              <span>View Product</span>
              <ExternalLink size={13} />
            </a>
          </div>
        </div>
      </div>
    </div>
  );
}
