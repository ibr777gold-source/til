import AudioPlayer from './AudioPlayer';
import {useEffect,useRef,useState} from 'react';
type Word={target:string;meaning:string;example?:string;example_translation?:string;media_id?:string|null};
export default function WordList({words,ru}:{words:Word[];ru:boolean}){
 const [voice,setVoice]=useState<SpeechSynthesisVoice|null>(null),[error,setError]=useState(''),[speed,setSpeed]=useState('1');
 const targetLang=ru?'uz':'ru';
 const current=useRef<SpeechSynthesisUtterance|null>(null);
 useEffect(()=>{
  if(!('speechSynthesis' in window)||!('SpeechSynthesisUtterance' in window))return;
  const synthesis=window.speechSynthesis;
  const update=()=>setVoice(synthesis.getVoices().find(v=>v.lang.toLowerCase().split(/[-_]/)[0]===targetLang)||null);
  update();synthesis.addEventListener('voiceschanged',update);
  return()=>{synthesis.removeEventListener('voiceschanged',update);current.current=null;synthesis.cancel()};
 },[targetLang]);
 function speak(text:string){
  if(!voice)return;
  setError('');
  const synthesis=window.speechSynthesis;
  current.current=null;synthesis.cancel();
  const utterance=new SpeechSynthesisUtterance(text);utterance.voice=voice;utterance.lang=voice.lang;utterance.rate=Number(speed);current.current=utterance;
  utterance.onend=()=>{if(current.current===utterance)current.current=null};
  utterance.onerror=(event)=>{if(current.current!==utterance)return;current.current=null;if(event.error==='canceled'||event.error==='interrupted')return;setError(ru?'Не удалось воспроизвести синтезированную речь.':'Sun’iy nutqni ijro etib bo‘lmadi.')};
  try{synthesis.speak(utterance)}catch{current.current=null;setError(ru?'Не удалось воспроизвести синтезированную речь.':'Sun’iy nutqni ijro etib bo‘lmadi.')}
 }
 const needsVoice=words.some(w=>!w.media_id);
 return <>{voice&&words.some(w=>!w.media_id)&&<label className="speech-speed">{ru?'Скорость речи':'Nutq tezligi'} <select value={speed} onChange={e=>setSpeed(e.target.value)}><option value="1">{ru?'Обычная':'Oddiy'}</option><option value="0.75">{ru?'Медленная':'Sekin'}</option></select></label>}<div className="word-list">{words.map((w,i)=><div key={i}><strong>{w.target}</strong><span>{w.meaning}{w.example&&w.example_translation&&<span className="word-example"><b>{w.example}</b><small>{w.example_translation}</small></span>}{w.media_id?<AudioPlayer src={'/api/media/'+w.media_id} ru={ru} label={(ru?'Запись: ':'Yozuv: ')+w.target}/>:voice&&<button type="button" className="speech-button" onClick={()=>speak(w.target)} aria-label={(ru?'Озвучить: ':'Tinglash: ')+w.target}>▶ {ru?'Слушать':'Tinglash'}</button>}</span></div>)}</div>{needsVoice&&<p className="muted">{voice?(ru?'Озвучивание создано компьютером и может быть неточным; проверенные записи готовятся.':'Ovoz kompyuter tomonidan yaratiladi va noaniq bo‘lishi mumkin; tekshirilgan yozuvlar tayyorlanmoqda.'):(ru?'Синтез речи для этого языка недоступен на вашем устройстве; проверенные записи готовятся.':'Qurilmangizda bu til uchun sun’iy ovoz mavjud emas; tekshirilgan yozuvlar tayyorlanmoqda.')}</p>}{error&&<p role="alert">{error}</p>}</>
}
