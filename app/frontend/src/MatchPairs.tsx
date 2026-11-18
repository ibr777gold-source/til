import {useState} from 'react';
export default function MatchPairs({left,right,disabled,onChange,ru}:{left:string[];right:string[];disabled:boolean;onChange:(answer:string)=>void;ru:boolean}){
 const [pairs,setPairs]=useState<Map<string,string>>(()=>new Map());
 function update(key:string,value:string){const next=new Map(pairs);if(value)next.set(key,value);else next.delete(key);setPairs(next);const values=[...next.values()];onChange(values.length===left.length&&new Set(values).size===left.length?JSON.stringify(Object.fromEntries(next)):'')}
 return <div className="match-pairs"><p className="muted" aria-live="polite">{ru?'Для каждой строки выберите соответствие':'Har bir qator uchun mos javobni tanlang'}: {pairs.size} / {left.length}</p>{left.map((item,i)=><label key={i}><span>{item}</span><select value={pairs.get(item)||''} disabled={disabled} onChange={e=>update(item,e.target.value)} aria-label={`${item} ${ru?'соответствие':'mos javob'}`}><option value="">{ru?'Выберите':'Tanlang'}</option>{right.map((option,j)=><option key={j} value={option} disabled={[...pairs.values()].includes(option)&&pairs.get(item)!==option}>{option}</option>)}</select></label>)}</div>
}
