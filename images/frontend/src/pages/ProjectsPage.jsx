import React, { useState, useEffect } from 'react';
import { FolderPlus, Folder, Edit2, Trash2, FileText, Download } from 'lucide-react';
import api from '../utils/api';

export default function ProjectsPage() {
  const [projects, setProjects] = useState([]);
  const [newProjectName, setNewProjectName] = useState('');
  const [newProjectDesc, setNewProjectDesc] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadProjects();
  }, []);

  const loadProjects = async () => {
    try {
      const response = await api.get('/projects');
      setProjects(response.data.projects || []);
    } catch (error) {
      console.error('Failed to load projects:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleCreateProject = async () => {
    if (!newProjectName.trim()) return;

    try {
      const response = await api.post('/projects', {
        name: newProjectName,
        description: newProjectDesc,
      });
      setProjects([...projects, response.data.project]);
      setNewProjectName('');
      setNewProjectDesc('');
    } catch (error) {
      console.error('Failed to create project:', error);
    }
  };

  const handleDeleteProject = async (projectId) => {
    if (window.confirm('Delete this project?')) {
      try {
        await api.delete(`/projects/${projectId}`);
        setProjects(projects.filter(p => p.id !== projectId));
      } catch (error) {
        console.error('Failed to delete project:', error);
      }
    }
  };

  const handleCompileProject = async (projectId, format) => {
    try {
      const response = await api.post('/compile', {
        project_id: projectId,
        output_format: format,
      });

      // Download the compiled file
      const blob = new Blob([JSON.stringify(response.data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `${projectId}_compiled.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (error) {
      console.error('Failed to compile project:', error);
    }
  };

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Projects</h1>
          <p className="text-slate-400">Organize your analyzed images into projects</p>
        </div>
      </div>

      {/* Create Project Form */}
      <div className="bg-slate-800 p-6 rounded-lg border border-slate-700">
        <h2 className="text-xl font-semibold mb-4 flex items-center">
          <FolderPlus className="w-5 h-5 mr-2" />
          Create New Project
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Project Name</label>
            <input
              type="text"
              value={newProjectName}
              onChange={(e) => setNewProjectName(e.target.value)}
              placeholder="e.g., Vacation Photos, Product Shots"
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
          <div>
            <label className="block text-sm font-medium mb-2">Description (optional)</label>
            <input
              type="text"
              value={newProjectDesc}
              onChange={(e) => setNewProjectDesc(e.target.value)}
              placeholder="Brief description of this project"
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            />
          </div>
        </div>
        <button
          onClick={handleCreateProject}
          disabled={!newProjectName.trim()}
          className="mt-4 bg-green-600 hover:bg-green-700 disabled:opacity-50 px-6 py-2 rounded-lg transition-colors"
        >
          Create Project
        </button>
      </div>

      {/* Projects List */}
      <div>
        <h2 className="text-xl font-semibold mb-4">Your Projects</h2>
        {loading ? (
          <div className="text-center py-8">
            <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-500 mx-auto"></div>
            <p className="mt-4 text-slate-400">Loading projects...</p>
          </div>
        ) : projects.length === 0 ? (
          <div className="bg-slate-800 p-8 rounded-lg border border-slate-700 text-center">
            <Folder className="w-12 h-12 text-slate-600 mx-auto mb-4" />
            <h3 className="text-lg font-semibold mb-2">No Projects Yet</h3>
            <p className="text-slate-400">Create your first project to organize images</p>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {projects.map(project => (
              <div key={project.id} className="bg-slate-800 p-4 rounded-lg border border-slate-700 hover:border-blue-500 transition-colors">
                <div className="flex items-start justify-between mb-3">
                  <Folder className="w-6 h-6 text-blue-400" />
                  <div className="flex gap-1">
                    <button className="text-slate-400 hover:text-blue-400">
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      onClick={() => handleDeleteProject(project.id)}
                      className="text-slate-400 hover:text-red-400"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
                <h3 className="font-semibold mb-1">{project.name}</h3>
                <p className="text-sm text-slate-400 mb-3 truncate">{project.description}</p>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-500">{project.total_images || 0} images</span>
                  <div className="flex gap-2">
                    <button
                      onClick={() => handleCompileProject(project.id, 'json')}
                      className="px-2 py-1 bg-blue-600 hover:bg-blue-700 rounded flex items-center"
                    >
                      <Download className="w-3 h-3 mr-1" />
                      JSON
                    </button>
                    <button
                      onClick={() => handleCompileProject(project.id, 'markdown')}
                      className="px-2 py-1 bg-purple-600 hover:bg-purple-700 rounded flex items-center"
                    >
                      <FileText className="w-3 h-3 mr-1" />
                      MD
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
