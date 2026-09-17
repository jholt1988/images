import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Dashboard from './pages/Dashboard';
import Navbar from './components/Navbar';
import UploadPage from './pages/UploadPage';
import AnalysisPage from './pages/AnalysisPage';
import ProjectsPage from './pages/ProjectsPage';
import SettingsPage from './pages/SettingsPage';

export default function App() {
  const [images, setImages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('dashboard');

  // Fetch images from FastAPI backend on component mount
  useEffect(() => {
    const fetchImages = async () => {
      try {
        setLoading(true);
        let response = await fetch('/api/v1/images/all?page=1&limit=50');

        if (!response.ok) {
          console.error('Failed to fetch images:', response.statusText);
    
        }

        const data = await response.json();

        // Extract the array from the backend response object
        setImages(data.images || []);
      } catch (err) {
        console.error('Error fetching images:', err);
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchImages();
  }, []);

 

  

  return (
    <Router>
      <div className="min-h-screen bg-slate-900 text-white">
        <Navbar activeTab={activeTab} setActiveTab={setActiveTab} />

        <main>
          {loading && (
            <div className="text-center py-12 text-slate-400">Loading images...</div>
          )}

          {error && (
            <div className="text-center py-12 text-red-400">Error: {error}</div>
          )}

          {!loading && !error && (
            <Routes>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<Dashboard />} />
              <Route path="/upload" element={<UploadPage />} />
              <Route path="/analysis" element={<AnalysisPage />} />
              <Route path="/projects" element={<ProjectsPage />} />
              <Route path="/settings" element={<SettingsPage />} />
            </Routes>
          )}
  
        </main>
      </div>
    </Router>
  );
}