import React, { useState, useEffect } from 'react';

export default function SettingsPage() {
  const [settings, setSettings] = useState({ theme: 'light', notifications: true });
  const [statusMessage, setStatusMessage] = useState('');

  // Fetch settings on mount
  useEffect(() => {
    fetch('/api/settings')
      .then((res) => res.json())
      .then((data) => setSettings(data))
      .catch((err) => console.error('Failed to load settings', err));
  }, []);

  // Handle setting changes and sync with backend
  const handleSettingChange = async (key, value) => {
    const updatedSettings = { ...settings, [key]: value };
    setSettings(updatedSettings); // Optimistic UI update

    try {
      const response = await fetch('/api/settings', {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(updatedSettings),
      });

      if (response.ok) {
        setStatusMessage('Settings saved successfully!');
        setTimeout(() => setStatusMessage(''), 3000);
      } else {
        setStatusMessage('Failed to save settings.');
      }
    } catch (error) {
      console.error('Error updating settings:', error);
      setStatusMessage('Network error while saving.');
    }
  };

  return (
    <div className="max-w-2xl mx-auto p-6 bg-white rounded-lg shadow">
      <h2 className="text-2xl font-bold mb-4">Application Settings</h2>

      {statusMessage && (
        <div className="mb-4 p-2 bg-blue-100 text-blue-700 rounded text-sm">
          {statusMessage}
        </div>
      )}

      <div className="space-y-4">
        {/* Theme Setting */}
        <div className="flex items-center justify-between">
          <label className="font-medium text-gray-700">Dark Mode</label>
          <input
            type="checkbox"
            checked={settings.theme === 'dark'}
            onChange={(e) => handleSettingChange('theme', e.target.checked ? 'dark' : 'light')}
            className="h-5 w-5 text-blue-600 rounded"
          />
        </div>

        {/* Notifications Setting */}
        <div className="flex items-center justify-between">
          <label className="font-medium text-gray-700">Enable Notifications</label>
          <input
            type="checkbox"
            checked={settings.notifications}
            onChange={(e) => handleSettingChange('notifications', e.target.checked)}
            className="h-5 w-5 text-blue-600 rounded"
          />
        </div>
      </div>
    </div>
  );
}