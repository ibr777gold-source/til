import React from 'react';
import {createRoot} from 'react-dom/client';
import CourseMap from '../src/CourseMap';

createRoot(document.getElementById('root')!).render(<CourseMap course="uz-ru" ru={false} progress={[]} onStart={()=>{}} onCheckpoint={()=>{}} onBack={()=>{}}/>);
