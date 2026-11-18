import React, {useState} from 'react';
import {createRoot} from 'react-dom/client';
import MatchPairs from '../src/MatchPairs';

function Fixture(){const [answer,setAnswer]=useState('');return <><MatchPairs left={['бир','два']} right={['bir','ikki']} disabled={false} ru={false} onChange={setAnswer}/><button disabled={!answer}>Check</button><output>{answer}</output></>}
createRoot(document.getElementById('root')!).render(<Fixture/>);
