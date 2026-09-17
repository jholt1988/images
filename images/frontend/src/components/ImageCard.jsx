import React, { useState } from 'react';
import { AlertCircle, CheckCircle, Trash2, Eye } from 'lucide-react';

const PLACEHOLDER =
  'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="1" height="1"%3E%3C/svg%3E';

export default function ImageCard({ image, onAnalyze, onDelete, analysisProgress, isSelected, onToggleSelect }) {
  const [showAnalysis, setShowAnalysis] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  return (
    <div className={`bg-slate-800 rounded-lg border overflow-hidden shadow-lg transition-all ${isSelected ? 'border-blue-500 ring-2 ring-blue-500/50' : 'border-slate-700'}`}>
      <div className="relative h-48 bg-slate-900 flex items-center justify-center">
        {/* Selection Checkbox */}
        <div className="absolute top-2 left-2 z-10">
          <input
            type="checkbox"
            checked={isSelected}
            onChange={() => onToggleSelect(image.id)}
            className="w-5 h-5 rounded text-blue-600 focus:ring-blue-500 cursor-pointer"
          />
        </div>

        {isLoading && (
          <div className="absolute inset-0 flex items-center justify-center bg-slate-700/50 animate-pulse text-xs text-slate-400">
            Loading preview...
          </div>
        )}

        <img
          src={`/api/images/file/${image.id}`}
          alt={image.filename}
          className={`w-full h-48 object-cover transition-opacity duration-300 ${isLoading ? 'opacity-0' : 'opacity-100'}`}
          onLoad={() => setIsLoading(false)}
          onError={(e) => {
            setIsLoading(false);
            e.target.src = PLACEHOLDER;
          }}
        />

        <div className="absolute top-2 right-2 bg-slate-900/60 p-1 rounded-full backdrop-blur-sm">
          {/* Status Indicator */}
          {analysisProgress === 'analyzing' && <AlertCircle className="w-4 h-4 text-yellow-400 animate-spin" />}
          {analysisProgress === 'complete' && <CheckCircle className="w-4 h-4 text-green-400" />}
          {analysisProgress === 'error' && <AlertCircle className="w-4 h-4 text-red-400" />}
        </div>
      </div>

      <div className="p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold truncate text-slate-100" title={image.filename}>
            {image.filename}
          </h3>
          <button
            onClick={() => setShowAnalysis(!showAnalysis)}
            className="text-blue-400 hover:text-blue-300 transition-colors"
            title="View Analysis"
          >
            <Eye className="w-4 h-4" />
          </button>
        </div>

        {/* Existing metadata & buttons... */}
      </div>
    </div>
  );
}