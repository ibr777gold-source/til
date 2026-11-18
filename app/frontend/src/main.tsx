import React from 'react';
import {createRoot} from 'react-dom/client';
import App from './App';
import OwnerDashboard from './OwnerDashboard';

createRoot(document.getElementById('root')!).render(<React.StrictMode>{new URLSearchParams(location.search).has('admin')?<OwnerDashboard/>:<App/>}</React.StrictMode>);
