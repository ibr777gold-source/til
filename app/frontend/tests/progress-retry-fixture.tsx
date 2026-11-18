import React from 'react';
import {createRoot} from 'react-dom/client';
import ProgressOverview from '../src/ProgressOverview';

createRoot(document.getElementById('root')!).render(<ProgressOverview course="uz-ru" ru={false} onBack={()=>{}}/>);
