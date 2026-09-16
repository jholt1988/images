import React, { useState } from 'react';
import { AlertCircle, CheckCircle, Trash2, Eye } from 'lucide-react';

// No on-disk placeholder asset ships with the repo, so use an inline 1px data
// URI as the broken-image fallback instead of '/placeholder.jpg' (which 404s).
const PLACEHOLDER =
  'data:image/svg+xml,%3Csvg xmlns="http://www.w3.org/2000/svg" width="1" height="1"%3E%3C/svg%3E';

export default function ImageCard({ image, onAnalyze, onDelete, analysisProgress }) {
  const [showAnalysis, setShowAnalysis] = useState(false);

  const getStatusIcon = () => {
    switch (analysisProgress) {
      case 'analyzing':
        return <AlertCircle className="w-4 h-4 text-yellow-400" />;
      case 'complete':
        return <CheckCircle className="w-4 h-4 text-green-400" />;
      case 'error':
        return <AlertCircle className="w-4 h-4 text-red-400" />;
      default:
        return null;
    }
  };

  return (
    <div className="bg-slate-800 rounded-lg border border-slate-700 overflow-hidden">
      <div className="relative">
        <img
          src={`/api/v1/images/file/${image.id}`}
          alt={image.filename}
          className="w-full h-48 object-cover"
          onError={(e) => {
            e.target.src = PLACEHOLDER;
            e.target.alt = 'Image preview unavailable';
          }}
        />
        <div className="absolute top-2 right-2">
          {getStatusIcon()}
        </div>
        {image.has_analysis && (
          <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/80 to-transparent p-4">
            <p className="text-sm text-white font-medium">{image.primary_type}</p>
          </div>
        )}
      </div>

      <div className="p-4">
        <div className="flex items-center justify-between mb-2">
          <h3 className="font-semibold truncate" title={image.filename}>
            {image.filename}
          </h3>
          <button
            onClick={() => setShowAnalysis(!showAnalysis)}
            className="text-blue-400 hover:text-blue-300"
            title="View Analysis"
          >
            <Eye className="w-4 h-4" />
          </button>
        </div>

        <div className="flex items-center justify-between text-sm text-slate-400 mb-4">
          <span>{image.file_size ? `${(image.file_size / 1024 / 1024).toFixed(1)} MB` : 'Unknown size'}</span>
          <span>{new Date(image.created_at).toLocaleDateString()}</span>
        </div>

        {image.has_analysis && showAnalysis && (
          <div className="mb-4 p-3 bg-slate-700 rounded text-left">
            <p className="text-sm text-slate-300">
              <span className="font-medium">Description:</span> {image.description}
            </p>
            <p className="text-sm text-slate-300 mt-2">
              <span className="font-medium">Tags:</span> {image.tags ? JSON.parse(image.tags).join(', ') : 'None'}
            </p>
            <p className="text-sm text-slate-300 mt-2">
              <span className="font-medium">Quality:</span> {image.quality_score ? `${(image.quality_score * 100).toFixed(0)}%` : 'N/A'}
            </p>
          </div>
        )}

        <div className="flex gap-2">
          {!image.has_analysis && (
            <button
              onClick={() => onAnalyze && onAnalyze(image.id)}
              disabled={analysisProgress === 'analyzing'}
              className="flex-1 px-3 py-2 bg-blue-600 hover:bg-blue-700 disabled:opacity-50 rounded text-sm transition-colors"
            >
              Analyze
            </button>
          )}
          <button
            onClick={onDelete}
            className="px-3 py-2 bg-red-600 hover:bg-red-700 rounded text-sm transition-colors"
          >
            Delete
          </button>
        </div>
      </div>
    </div>
  );
}
