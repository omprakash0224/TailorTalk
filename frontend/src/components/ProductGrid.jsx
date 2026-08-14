import React from 'react';
import { Sparkles, Grid } from 'lucide-react';
import ProductCard from './ProductCard';

export default function ProductGrid({ results }) {
  if (!results || results.length === 0) {
    return null;
  }

  return (
    <div className="product-grid-section" id="product-results-grid">
      <div className="product-grid-header">
        <div className="product-grid-title">
          <Sparkles size={14} />
          <span>Curated Recommendations ({results.length})</span>
        </div>
      </div>
      
      <div className="product-grid">
        {results.map((product, idx) => (
          <ProductCard key={product.sku || idx} item={product} />
        ))}
      </div>
    </div>
  );
}
