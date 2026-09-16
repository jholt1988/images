import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { Settings as SettingsIcon, Save, CheckCircle, RefreshCw, Monitor } from 'lucide-react';

const api = axios.create({
  baseURL: '/api/v1',
  headers: { 'Content-Type': 'application/json' },
});

export default function SettingsPage() {
  const [config, setConfig] = useState({
    VLM_ENGINE: 'ollama',
    OLLAMA_URL: 'https://73d4kjrf9en6q2-11434.proxy.runpod.net/',
    OLLAMA_MODEL: 'feadxus/Huihui-Qwen3-VL-4B-Instruct-abliterated:BF16',
    OPENAI_API_KEY: '',
    OPENAI_MODEL: 'gpt-4o',
    UPLOAD_MAX_SIZE: '10MB',
  });
  const [availableModels, setAvailableModels] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);

  const loadConfig = async () => {
    try {
      const res = await api.get('/settings');
      setConfig(prev => ({ ...prev, ...res.data }));
      
      // Fetch models after getting settings to use correct engine/url
      fetchModels();
    } catch (err) {
      setError('Failed to load settings: ' + err.message);
    }
  };

  const fetchModels = async () => {
    try {
      const res = await api.get('/models');
      setAvailableModels(res.data.models || []);
      // Set default model if none selected. Prefer a vision-capable model so
      // the app doesn't default to a text-only model that can't analyze images.
      if (!config.OLLAMA_MODEL && res.data.models?.length > 0) {
        const preferred =
          res.data.models.find(m => m.is_vision) || res.data.models[0];
        setConfig(prev => ({ ...prev, OLLAMA_MODEL: preferred.full_name }));
      }
    } catch (err) {
      console.error('Failed to fetch models:', err);
    }
  };

  useEffect(() => {
    loadConfig();
  }, []);

  // Refetch models when engine changes
  useEffect(() => {
    fetchModels();
  }, [config.VLM_ENGINE]);

  const handleSave = async () => {
    setLoading(true);
    setError('');
    try {
      await api.post('/settings', config);
      setSaved(true);
      setTimeout(() => setSaved(false), 3000);
      fetchModels(); // Refresh available models
    } catch (err) {
      setError('Failed to save settings: ' + err.response?.data?.detail || err.message);
    } finally {
      setLoading(false);
    }
  };

  const handleChange = (key, value) => {
    setConfig(prev => ({ ...prev, [key]: value }));
  };

  const ollamaModels = Array.isArray(availableModels)
    ? availableModels
        .filter(m => m.engine === 'ollama')
        // Surface vision-capable models first so a working picker is on top;
        // keep text-only ones available rather than hiding them.
        .sort((a, b) => Number(b.is_vision === true) - Number(a.is_vision === true))
    : [];
  const openaiModels = Array.isArray(availableModels) ? availableModels.filter(m => m.engine === 'openai') : [];

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold">Settings</h1>
          <p className="text-slate-400">Configure the image analysis system</p>
        </div>
      </div>

      {/* Status Indicator */}
      {saved && (
        <div className="bg-green-600/20 border border-green-500 p-4 rounded-lg flex items-center">
          <CheckCircle className="w-5 h-5 mr-2 text-green-400" />
          <span className="text-green-400">Settings saved successfully</span>
        </div>
      )}
      
      {error && (
        <div className="bg-red-600/20 border border-red-500 p-4 rounded-lg">
          <span className="text-red-400">{error}</span>
        </div>
      )}

      {/* VLM Configuration */}
      <div className="bg-slate-800 p-6 rounded-lg border border-slate-700">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold flex items-center">
            <SettingsIcon className="w-5 h-5 mr-2" />
            Vision Model Configuration
          </h2>
          <button
            onClick={fetchModels}
            className="text-slate-400 hover:text-white transition-colors p-2"
            title="Refresh model list"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
        </div>
        
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">VLM Engine</label>
            <select
              value={config.VLM_ENGINE}
              onChange={(e) => handleChange('VLM_ENGINE', e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="ollama">Ollama (Local)</option>
              <option value="openai">OpenAI (Cloud)</option>
            </select>
          </div>

          {config.VLM_ENGINE === 'ollama' && (
            <>
              <div>
                <label className="block text-sm font-medium mb-2">Ollama URL</label>
                <input
                  type="text"
                  value={config.OLLAMA_URL}
                  onChange={(e) => handleChange('OLLAMA_URL', e.target.value)}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="http://localhost:11434"
                />
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">Ollama Model</label>
                <select
                  value={config.OLLAMA_MODEL || ''}
                  onChange={(e) => handleChange('OLLAMA_MODEL', e.target.value)}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                >
                  {ollamaModels.length > 0 ? (
                    ollamaModels.map((model) => (
                      <option key={model.full_name} value={model.full_name}>
                        {model.name}
                      </option>
                    ))
                  ) : (
                    <option value="">No models found</option>
                  )}
                </select>
                <button
                  onClick={fetchModels}
                  className="mt-2 text-sm text-blue-400 hover:text-blue-300 flex items-center"
                >
                  <RefreshCw className="w-3 h-3 mr-1" />
                  Refresh model list
                </button>
                {ollamaModels.length === 0 && (
                  <p className="text-xs text-slate-500">Models listed here will appear automatically from Ollama</p>
                )}
              </div>
            </>
          )}

          {config.VLM_ENGINE === 'openai' && (
            <>
              <div>
                <label className="block text-sm font-medium mb-2">OpenAI API Key</label>
                <input
                  type="password"
                  value={config.OPENAI_API_KEY}
                  onChange={(e) => handleChange('OPENAI_API_KEY', e.target.value)}
                  className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  placeholder="sk-..."
                />
                <p className="mt-1 text-xs text-slate-500">
                  Saved key is shown masked. Enter a new key to replace it, or clear the field to remove it.
                </p>
              </div>
              <div>
                <label className="block text-sm font-medium mb-2">OpenAI Model</label>
                {openaiModels.length > 0 && (
                  <select
                    value={config.OPENAI_MODEL || openaiModels[0]?.name || ''}
                    onChange={(e) => handleChange('OPENAI_MODEL', e.target.value)}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                  >
                    {openaiModels.map((model) => (
                      <option key={model.engine} value={model.name}>{model.name}</option>
                    ))}
                  </select>
                )}
                {(openaiModels.length === 0 || (!config.OPENAI_MODEL && openaiModels.length === 0)) && (
                  <input
                    type="text"
                    value={config.OPENAI_MODEL}
                    onChange={(e) => handleChange('OPENAI_MODEL', e.target.value)}
                    className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
                    placeholder="gpt-4o"
                  />
                )}
              </div>
            </>
          )}
        </div>
      </div>

      {/* Upload Configuration */}
      <div className="bg-slate-800 p-6 rounded-lg border border-slate-700">
        <h2 className="text-xl font-semibold flex items-center mb-4">
          <Monitor className="w-5 h-5 mr-2" />
          Upload Settings
        </h2>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-sm font-medium mb-2">Max File Size</label>
            <select
              value={config.UPLOAD_MAX_SIZE}
              onChange={(e) => handleChange('UPLOAD_MAX_SIZE', e.target.value)}
              className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            >
              <option value="1MB">1 MB</option>
              <option value="5MB">5 MB</option>
              <option value="10MB">10 MB</option>
              <option value="50MB">50 MB</option>
            </select>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex justify-end">
        <button
          onClick={handleSave}
          disabled={loading}
          className="bg-blue-600 hover:bg-blue-700 px-6 py-3 rounded-lg flex items-center disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {loading ? (
            <>
              <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
              Saving...
            </>
          ) : (
            <>
              <Save className="w-4 h-4 mr-2" />
              Save Settings
            </>
          )}
        </button>
      </div>
    </div>
  );
}
