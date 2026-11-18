import React from 'react';
import {createRoot} from 'react-dom/client';
import Feedback from '../src/Feedback';

createRoot(document.getElementById('root')!).render(<Feedback lessonId="uz-ru-greetings" previewCourse="uz-ru" ru={false}/>);
