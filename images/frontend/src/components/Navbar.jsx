import React from 'react';
import { Upload, Camera, Database, TrendingUp, Settings } from 'lucide-react';

function Navbar({ activeTab, setActiveTab }) {
  const tabs = [
    { id: 'dashboard', name: 'Dashboard', icon: Upload },
    { id: 'upload', name: 'Upload', icon: Camera },
    { id: 'analysis', name: 'Analysis', icon: Database },
    { id: 'projects', name: 'Projects', icon: TrendingUp },
    { id: 'settings', name: 'Settings', icon: Settings },
  ];

  return (
    <nav className="bg-slate-800 border-b border-slate-700 sticky top-0 z-50">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <div className="flex items-center space-x-2">
            <Camera className="h-8 w-8 text-blue-500" />
            <span className="text-xl font-bold bg-gradient-to-r from-blue-400 to-purple-500 bg-clip-text text-transparent">
              Image Analyzer
            </span>
          </div>
          <div className="hidden md:flex space-x-2">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2 rounded-md text-sm font-medium transition-colors ${
                  activeTab === tab.id
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-300 hover:bg-slate-700 hover:text-white'
                }`}
              >
                <tab.icon className="w-4 h-4 inline-block mr-2" />
                {tab.name}
              </button>
            ))}
          </div>
        </div>
      </div>
    </nav>
  );
}

export default Navbar;
