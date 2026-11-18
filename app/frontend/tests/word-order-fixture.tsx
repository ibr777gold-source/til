import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import WordOrder from '../src/WordOrder';

function Fixture(){const [answer,setAnswer]=useState('');return <><WordOrder tokens={['Men','yozaman']} disabled={false} ru={false} onChange={setAnswer}/><button disabled={!answer}>Check</button><output>{answer}</output></>}
createRoot(document.getElementById('root')!).render(<Fixture/>);
