type Line={speaker:string;text:string};
export default function Dialogue({lines}:{lines:Line[]}){return <div className="dialogue" role="group" aria-label="Dialogue">{lines.map((line,i)=><div className="dialogue-line" key={i}><span>{line.speaker}</span><p>{line.text}</p></div>)}</div>}
