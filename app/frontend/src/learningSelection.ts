type Lesson={id:string};
type Progress={lesson_id:string;completed:boolean};
type Unfinished={lesson_id:string;course:string};

/** Prefer a saved attempt, then the first incomplete lesson in the ordered course. */
export function chooseNext(course:string,lessons:Lesson[],progress:Progress[],unfinished:Unfinished[]):{id:string;resuming:boolean}|null {
  const saved=unfinished.find(item=>item.course===course);
  if(saved)return {id:saved.lesson_id,resuming:true};
  const lesson=lessons.find(item=>!progress.some(p=>p.lesson_id===item.id&&p.completed))||lessons[0];
  return lesson?{id:lesson.id,resuming:false}:null;
}
