import {useEffect, useRef, useState} from 'react';

/** Native controls retain keyboard and assistive technology support. */
export default function AudioPlayer({src,ru,label}:{src:string;ru:boolean;label:string}) {
 const audio=useRef<HTMLAudioElement>(null);
 const [speed,setSpeed]=useState('1');
 const [failed,setFailed]=useState(false);
 useEffect(()=>{setFailed(false)},[src]);
 useEffect(()=>{if(audio.current)audio.current.playbackRate=Number(speed)},[speed,src]);
 function retry(){
  setFailed(false);
  audio.current?.load();
 }
 return <span className="audio-player">
  <audio ref={audio} controls preload="none" src={src} aria-label={label} onError={()=>setFailed(true)} onCanPlay={()=>setFailed(false)}/>
  <label className="speech-speed">{ru?'Скорость записи':'Yozuv tezligi'} <select value={speed} onChange={event=>setSpeed(event.target.value)}><option value="1">{ru?'Обычная':'Oddiy'}</option><option value="0.75">{ru?'Медленная':'Sekin'}</option></select></label>
  {failed&&<span role="alert">{ru?'Не удалось загрузить запись.':'Yozuvni yuklab bo‘lmadi.'} <button type="button" className="text-button" onClick={retry}>{ru?'Повторить':'Qayta urinish'}</button></span>}
 </span>;
}
