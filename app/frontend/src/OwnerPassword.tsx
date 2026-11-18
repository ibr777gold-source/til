import React,{useState} from 'react';
export default function OwnerPassword(){
 const [busy,setBusy]=useState(false),[message,setMessage]=useState(''),[error,setError]=useState('');
 async function submit(e:React.FormEvent<HTMLFormElement>){e.preventDefault();const form=e.currentTarget,f=new FormData(form);setMessage('');setError('');
  if(f.get('new_password')!==f.get('confirm_password')){setError('The new passwords do not match.');return}
  setBusy(true);try{const r=await fetch('/api/owner/password',{method:'POST',credentials:'include',headers:{'Content-Type':'application/json'},body:JSON.stringify({current_password:f.get('current_password'),new_password:f.get('new_password')})});const data=await r.json();if(!r.ok)throw Error(typeof data.detail==='string'?data.detail:'Could not update the password.');form.reset();setMessage(data.message)}catch(e){setError((e as Error).message)}finally{setBusy(false)}
 }
 return <section className="editor-form"><div className="overline">ACCOUNT SECURITY</div><h2>Change owner password</h2><p>Other signed-in sessions will be signed out when you change your password.</p><form onSubmit={submit}><label>Current password<input name="current_password" type="password" autoComplete="current-password" maxLength={128} required/></label><label>New password<input name="new_password" type="password" autoComplete="new-password" minLength={8} maxLength={128} required/></label><label>Confirm new password<input name="confirm_password" type="password" autoComplete="new-password" minLength={8} maxLength={128} required/></label>{error&&<p role="alert">{error}</p>}{message&&<p role="status">{message}</p>}<button className="button dark" disabled={busy}>Change password</button></form></section>
}
