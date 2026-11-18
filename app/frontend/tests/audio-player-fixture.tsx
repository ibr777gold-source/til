import React from 'react';
import {createRoot} from 'react-dom/client';
import AudioPlayer from '../src/AudioPlayer';
import '../src/style.css';

createRoot(document.getElementById('root')!).render(<AudioPlayer src="/unused-audio.mp3" ru={false} label="Mashqni tinglash"/>);
