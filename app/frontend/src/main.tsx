import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './App';
import OwnerDashboard from './OwnerDashboard';

// Apply the saved preference before rendering either the learner or owner view.
try {
 const theme = localStorage.getItem('til-theme');
 if (theme === 'light' || theme === 'dark') document.documentElement.dataset.theme = theme;
} catch { /* System preference remains available when storage is disabled. */ }

createRoot(document.getElementById('root')!).render(<React.StrictMode>{new URLSearchParams(location.search).has('admin')?<OwnerDashboard/>:<App/>}</React.StrictMode>);
