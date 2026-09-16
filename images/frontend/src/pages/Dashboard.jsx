import React from 'react';
import { Link } from 'react-router-dom';
import { Upload, Camera, FileImage, Database, TrendingUp } from 'lucide-react';

export default function Dashboard() {
  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="text-center">
        <h1 className="text-3xl font-bold">Image Analysis Dashboard</h1>
        <p className="text-slate-400 mt-2">Manage and analyze your image collection</p>
      </div>

      {/* Quick Stats */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <div className="bg-slate-800 p-6 rounded-lg border border-slate-700 hover:border-blue-500 transition-colors">
          <Database className="w-12 h-12 text-blue-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">Image Storage</h3>
          <p className="text-slate-400 mb-4">View and manage all your uploaded images</p>
          <Link
            to="/analysis"
            className="block text-center bg-blue-600 hover:bg-blue-700 px-4 py-2 rounded-lg transition-colors"
          >
            View Images
          </Link>
        </div>

        <div className="bg-slate-800 p-6 rounded-lg border border-slate-700 hover:border-green-500 transition-colors">
          <TrendingUp className="w-12 h-12 text-green-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">Start Analysis</h3>
          <p className="text-slate-400 mb-4">Upload images and run AI analysis</p>
          <Link
            to="/upload"
            className="block text-center bg-green-600 hover:bg-green-700 px-4 py-2 rounded-lg transition-colors"
          >
            Upload & Analyze
          </Link>
        </div>

        <div className="bg-slate-800 p-6 rounded-lg border border-slate-700 hover:border-purple-500 transition-colors">
          <FileImage className="w-12 h-12 text-purple-400 mx-auto mb-4" />
          <h3 className="text-xl font-semibold mb-2">Projects</h3>
          <p className="text-slate-400 mb-4">Create and manage image projects</p>
          <Link
            to="/projects"
            className="block text-center bg-purple-600 hover:bg-purple-700 px-4 py-2 rounded-lg transition-colors"
          >
            View Projects
          </Link>
        </div>
      </div>

      {/* Quick Actions */}
      <div className="bg-slate-800 p-6 rounded-lg border border-slate-700">
        <h2 className="text-xl font-semibold mb-4">Quick Actions</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <Link
            to="/upload"
            className="flex items-center p-4 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
          >
            <Upload className="w-6 h-6 mr-3 text-blue-400" />
            <div className="text-left">
              <h3 className="font-semibold">Upload Images</h3>
              <p className="text-sm text-slate-400">Add new images to analyze</p>
            </div>
          </Link>

          <Link
            to="/analysis"
            className="flex items-center p-4 bg-slate-700 hover:bg-slate-600 rounded-lg transition-colors"
          >
            <Camera className="w-6 h-6 mr-3 text-green-400" />
            <div className="text-left">
              <h3 className="font-semibold">Analyze Collection</h3>
              <p className="text-sm text-slate-400">Run AI analysis on images</p>
            </div>
          </Link>
        </div>
      </div>

      {/* Status */}
      <div className="bg-slate-800 p-6 rounded-lg border border-slate-700">
        <h2 className="text-xl font-semibold mb-4">System Status</h2>
        <div className="space-y-3">
          <div className="flex items-center justify-between p-3 bg-slate-700 rounded">
            <span className="flex items-center">
              <div className="w-3 h-3 bg-green-400 rounded-full mr-3"></div>
              Backend API
            </span>
            <span className="text-green-400 font-semibold">Running</span>
          </div>
          <div className="flex items-center justify-between p-3 bg-slate-700 rounded">
            <span className="flex items-center">
              <div className="w-3 h-3 bg-blue-400 rounded-full mr-3"></div>
              Database
            </span>
            <span className="text-blue-400 font-semibold">Connected</span>
          </div>
        </div>
      </div>
    </div>
  );
}
