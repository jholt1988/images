import React, { useState } from 'react';
import ImageCard from '../components/ImageCard';

export default function Dashboard({ images = [] }) {
  const [selectedIds, setSelectedIds] = useState([]);
  const [isAnalyzingBatch, setIsAnalyzingBatch] = useState(false);

  // Toggle selection for a single image
  const handleToggleSelect = (id) => {
    setSelectedIds(prev =>
      prev.includes(id) ? prev.filter(item => item !== id) : [...prev, id]
    );
  };

  // Execute Batch Analysis
  const handleBatchAnalyze = async () => {
    if (selectedIds.length === 0) return;
    setIsAnalyzingBatch(true);

    try {
      const response = await fetch('/api/v1/images/analyze/batch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(selectedIds),
      });

      if (response.ok) {
        const data = await response.json();
        console.log('Batch analysis completed:', data.results);
        // Refresh your image list or state here to display the new analysis
        window.location.reload();
      } else {
        console.error('Batch analysis failed');
      }
    } catch (error) {
      console.error('Network error during batch analysis:', error);
    } finally {
      setIsAnalyzingBatch(false);
    }
  };

  return (
    <div className="p-6">
      {/* Batch Actions Toolbar */}
      <div className="flex justify-between items-center mb-6 bg-slate-800 p-4 rounded-lg border border-slate-700">
        <span className="text-sm text-slate-300">
          {selectedIds.length} item(s) selected
        </span>

        {selectedIds.length > 0 && (
          <div className="flex gap-3">
            <button
              onClick={handleBatchAnalyze}
              disabled={isAnalyzingBatch}
              className="px-4 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white rounded text-sm font-medium transition-colors flex items-center gap-2"
            >
              {isAnalyzingBatch ? 'Analyzing...' : `Analyze Selected (${selectedIds.length})`}
            </button>
          </div>
        )}
      </div>

      {/* Grid of Image Cards */}
      {/* Grid of Image Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-6">
        {images?.length > 0 ? (
          images.map((image) => (
            <ImageCard
              key={image.id}
              image={image}
              isSelected={selectedIds.includes(image.id)}
              onToggleSelect={handleToggleSelect}
            />
          ))
        ) : (
          <p className="text-slate-400 col-span-full text-center py-8">
            Loading images or no images found...
          </p>
        )}
      </div>
    </div>
  );
}