import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './App';
import OwnerDashboard from './OwnerDashboard';

// Apply a saved preference before rendering; new visitors start in light mode.
let theme: 'light' | 'dark' = 'light';
try {
 if (localStorage.getItem('til-theme') === 'dark') theme = 'dark';
} catch { /* Light mode remains available when storage is disabled. */ }
document.documentElement.dataset.theme = theme;

createRoot(document.getElementById('root')!).render(<React.StrictMode>{new URLSearchParams(location.search).has('admin')?<OwnerDashboard/>:<App/>}</React.StrictMode>);
