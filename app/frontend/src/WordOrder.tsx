import {useState} from 'react';
export default function WordOrder({tokens,disabled,onChange,ru}:{tokens:string[];disabled:boolean;onChange:(answer:string)=>void;ru:boolean}){
 const [chosen,setChosen]=useState<number[]>([]);
 function update(next:number[]){setChosen(next);onChange(next.map(i=>tokens[i]).join(' '))}
 return <div className="word-order"><div className="overline">{ru?'ВАШ ОТВЕТ':'JAVOBINGIZ'}</div><div className="order-answer" aria-live="polite">{chosen.length?chosen.map((index,i)=><button type="button" disabled={disabled} key={index} onClick={()=>update(chosen.filter((_,n)=>n!==i))} aria-label={`${tokens[index]} ${ru?'убрать':'olib tashlash'}`}>{tokens[index]} ×</button>):<span>{ru?'Выберите слова по порядку':'So‘zlarni tartib bilan tanlang'}</span>}</div><div className="order-tokens">{tokens.map((token,i)=><button type="button" key={i} disabled={disabled||chosen.includes(i)} onClick={()=>update([...chosen,i])}>{token}</button>)}</div></div>
}
