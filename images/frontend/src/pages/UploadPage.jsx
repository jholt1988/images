import React, { useState } from 'react';
import { Upload, Camera, AlertCircle, FileImage, CheckCircle, Loader2 } from 'lucide-react';

export default function UploadPage() {
  const [files, setFiles] = useState([]);
  const [uploadProgress, setUploadProgress] = useState({});
  const [isUploading, setIsUploading] = useState(false);

  const handleFilesChange = (event) => {
    const selectedFiles = Array.from(event.target.files).filter(file =>
      file.type.startsWith('image/')
    );
    setFiles(selectedFiles);
  };

  const handleSubmit = () => {
    handleUpload();
  };

  const handleUpload = async () => {
    if (files.length === 0) return;

    setIsUploading(true);
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));

    try {
      const response = await fetch('/api/v1/images/upload/batch', {
        method: 'POST',
        body: formData,
      });

      const data = await response.json();
      setUploadProgress(prev => ({
        ...prev,
        uploadTime: new Date().toLocaleTimeString(),
        imageCount: data.count
      }));

      setFiles([]);
    } catch (error) {
      console.error('Upload failed:', error);
    } finally {
      setIsUploading(false);
    }
  };

  const removeFile = (index) => {
    setFiles(files.filter((_, i) => i !== index));
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-3xl font-bold">Upload Images</h1>
        <p className="text-slate-400">Upload images for AI analysis</p>
      </div>

      {/* Upload Area */}
      <div
        className="border-2 border-dashed border-slate-600 rounded-lg p-8 text-center hover:border-blue-500 transition-colors"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          const droppedFiles = Array.from(e.dataTransfer.files).filter(file =>
            file.type.startsWith('image/')
          );
          setFiles([...files, ...droppedFiles]);
        }}
      >
        <Upload className="w-12 h-12 text-slate-500 mx-auto mb-4" />
        <h3 className="text-xl font-semibold mb-2">Drop images here or click to upload</h3>
        <p className="text-slate-400 mb-4">Supports JPG, PNG, GIF, WebP (max 10MB per file)</p>
        <label className="inline-flex items-center px-6 py-3 bg-blue-600 hover:bg-blue-700 rounded-lg cursor-pointer">
          <Camera className="w-4 h-4 mr-2" />
          <span>Choose Files</span>
          <input
            type="file"
            multiple
            accept="image/*"
            onChange={handleFilesChange}
            className="hidden"
          />
        </label>
      </div>

      {/* Selected Files */}
      {files.length > 0 && (
        <div className="bg-slate-800 p-6 rounded-lg border border-slate-700">
          <h2 className="text-xl font-semibold mb-4">
            Selected Files ({files.length})
          </h2>
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {files.map((file, index) => (
              <div key={index} className="bg-slate-700 p-4 rounded-lg relative">
                <FileImage className="w-6 h-6 text-slate-400 mb-2" />
                <p className="text-sm truncate">{file.name}</p>
                <p className="text-xs text-slate-400">
                  {(file.size / 1024 / 1024).toFixed(2)} MB
                </p>
                <button
                  onClick={() => removeFile(index)}
                  className="absolute top-2 right-2 text-red-400 hover:text-red-300"
                >
                  ×
                </button>
              </div>
            ))}
          </div>
          <div className="mt-6 flex justify-end">
            <button
              onClick={handleSubmit}
              disabled={isUploading}
              className="bg-green-600 hover:bg-green-700 disabled:opacity-50 px-6 py-3 rounded-lg flex items-center"
            >
              {isUploading ? (
                <>
                  <Loader2 className="w-4 h-4 mr-2 animate-spin" />
                  Uploading...
                </>
              ) : (
                <>
                  <CheckCircle className="w-4 h-4 mr-2" />
                  Upload All
                </>
              )}
            </button>
          </div>
        </div>
      )}

      {/* Upload Progress */}
      {Object.keys(uploadProgress).length > 0 && (
        <div className="bg-slate-800 p-6 rounded-lg border border-slate-700">
          <h2 className="text-xl font-semibold mb-4">Upload Summary</h2>
          <div className="space-y-2">
            <p className="text-slate-300">Time: {uploadProgress.uploadTime}</p>
            <p className="text-slate-300">Images: {uploadProgress.imageCount}</p>
          </div>
        </div>
      )}
    </div>
  );
}
