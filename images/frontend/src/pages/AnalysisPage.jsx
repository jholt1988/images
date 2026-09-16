import React, { useState, useEffect } from 'react';
import { useParams, Link } from 'react-router-dom';
import { Camera, AlertCircle, CheckCircle, Trash2, Folder, TrendingUp, Eye, Tag } from 'lucide-react';
import ImageCard from '../components/ImageCard';
import api from '../utils/api';

export default function AnalysisPage() {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [analysisProgress, setAnalysisProgress] = useState({});

  useEffect(() => {
    loadImages();
  }, []);

  const loadImages = async () => {
    try {
      setLoading(true);
      const response = await api.get('/images/all');
      setImages(response.data.images || []);
    } catch (error) {
      console.error('Failed to load images:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleAnalyze = async (imageId) => {
    try {
      setAnalysisProgress(prev => ({ ...prev, [imageId]: 'analyzing' }));
      await api.post(`/images/${imageId}/analyze`);
      setAnalysisProgress(prev => ({ ...prev, [imageId]: 'complete' }));
      // Reload images to get updated analysis
      setTimeout(loadImages, 500);
    } catch (error) {
      console.error('Analysis failed:', error);
      setAnalysisProgress(prev => ({ ...prev, [imageId]: 'error' }));
    }
  };

  const handleDelete = async (imageId, event) => {
    event.preventDefault();
    if (window.confirm('Delete this image?')) {
      try {
        await api.delete(`/images/${imageId}`);
        setImages(prev => prev.filter(img => img.id !== imageId));
      } catch (error) {
        console.error('Delete failed:', error);
      }
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Image Analysis</h1>
          <p className="text-slate-400">Analyze and manage your image collection</p>
        </div>
        <Link
          to="/upload"
          className="bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg flex items-center"
        >
          <Camera className="w-4 h-4 mr-2" />
          Upload New
        </Link>
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Total Images</p>
              <p className="text-2xl font-bold">{images.length}</p>
            </div>
            <Eye className="w-8 h-8 text-blue-400" />
          </div>
        </div>
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Analyzed</p>
              <p className="text-2xl font-bold">
                {images.filter(img => img.has_analysis).length}
              </p>
            </div>
            <CheckCircle className="w-8 h-8 text-green-400" />
          </div>
        </div>
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Duplicates Found</p>
              <p className="text-2xl font-bold">0</p>
            </div>
            <AlertCircle className="w-8 h-8 text-yellow-400" />
          </div>
        </div>
        <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-slate-400 text-sm">Marked for Deletion</p>
              <p className="text-2xl font-bold">0</p>
            </div>
            <Trash2 className="w-8 h-8 text-red-400" />
          </div>
        </div>
      </div>

      {/* Analysis Controls */}
      <div className="bg-slate-800 p-4 rounded-lg border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-lg font-semibold flex items-center">
            <TrendingUp className="w-5 h-5 mr-2" />
            Analysis Progress
          </h2>
          <button
            onClick={() => {
              // Analyze all unanalyzed images
              const unanalyzed = images.filter(img => !img.has_analysis);
              unanalyzed.forEach(img => handleAnalyze(img.id));
            }}
            disabled={images.every(img => img.has_analysis)}
            className="bg-purple-600 hover:bg-purple-700 disabled:opacity-50 px-4 py-2 rounded-lg"
          >
            Analyze All Unanalyzed
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {images.map(image => (
            <div key={image.id} className="bg-slate-700 p-3 rounded-lg">
              <div className="flex items-center justify-between">
                <div className="flex items-center truncate">
                  <Tag className="w-4 h-4 mr-2 text-slate-400" />
                  <span className="text-sm truncate">{image.filename}</span>
                </div>
                <div className="flex items-center">
                  {image.has_analysis ? (
                    <CheckCircle className="w-4 h-4 text-green-400" />
                  ) : (
                    <button
                      onClick={() => handleAnalyze(image.id)}
                      className="text-xs bg-blue-600 hover:bg-blue-700 px-2 py-1 rounded"
                    >
                      Analyze
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Images Grid */}
      <div>
        <h2 className="text-xl font-semibold mb-4">All Images</h2>
        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
            <p className="mt-4 text-slate-400">Loading images...</p>
          </div>
        ) : images.length === 0 ? (
          <div className="bg-slate-800 p-8 rounded-lg border border-slate-700 text-center">
            <Camera className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Images Yet</h3>
            <p className="text-slate-400 mb-4">Upload some images to get started with analysis</p>
            <Link
              to="/upload"
              className="bg-blue-600 hover:bg-blue-700 px-6 py-2 rounded-lg inline-block"
            >
              Upload Images
            </Link>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {images.map(image => (
              <ImageCard
                key={image.id}
                image={image}
                onAnalyze={() => handleAnalyze(image.id)}
                onDelete={(e) => handleDelete(image.id, e)}
                analysisProgress={analysisProgress[image.id]}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
