import React from 'react';
import {createRoot} from 'react-dom/client';
import DemoCheckpoint from '../src/DemoCheckpoint';

createRoot(document.getElementById('root')!).render(<DemoCheckpoint course="uz-ru" ru={false} onBack={()=>{}}/>);
