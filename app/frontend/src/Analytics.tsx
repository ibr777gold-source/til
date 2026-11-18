import {useEffect,useState} from 'react';
type Overview={period_days:number;events:Record<string,number>;learners_completing_practice:number};
export default function Analytics(){const [data,setData]=useState<Overview|null>(null),[error,setError]=useState(false);
 useEffect(()=>{fetch('/api/admin/analytics/overview',{credentials:'include'}).then(r=>{if(!r.ok)throw Error();return r.json()}).then(setData).catch(()=>setError(true))},[]);
 return <section className="editor-form"><div className="overline">LAST 7 DAYS</div><h3>Learning activity</h3>{error&&<p role="alert">Could not load activity.</p>}{data&&<><div className="analytics-grid"><div><strong>{data.learners_completing_practice}</strong><span>Learners completing practice</span></div><div><strong>{data.events.lesson_started||0}</strong><span>Lessons started</span></div><div><strong>{data.events.lesson_completed||0}</strong><span>Lessons completed</span></div><div><strong>{data.events.feedback_submitted||0}</strong><span>Feedback reports</span></div></div><p className="muted">Counts include prototype activity. Includes completed lessons and review sessions with scored answers.</p></>}</section>
}
