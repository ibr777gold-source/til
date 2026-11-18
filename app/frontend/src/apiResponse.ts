export class ApiError extends Error {
 constructor(public status:number,message:string,public detail:string|null=null){super(message);this.name='ApiError'}
}
export function connectionMessage(){return document.documentElement.lang==='ru'?'Связь с сервером прервана. Попробуйте ещё раз.':'Server bilan aloqa uzildi. Qayta urinib ko‘ring.'}
function localizedError(status:number,detail:unknown){
 const ru=document.documentElement.lang==='ru';
 const messages:Record<string,[string,string]>={
  'Incorrect email or password':['Email yoki parol noto‘g‘ri.','Неверный адрес электронной почты или пароль.'],
  'This email is already registered':['Bu email bilan hisob allaqachon yaratilgan.','Этот адрес уже зарегистрирован.'],
  'Please sign in':['Davom etish uchun hisobga kiring.','Войдите в аккаунт, чтобы продолжить.'],
  'Invalid origin':['Ilova manzili server sozlamalariga mos kelmaydi.','Адрес приложения не соответствует настройкам сервера.'],
  'Too many requests; try again later':['Juda ko‘p urinish. Biroz kutib, qayta urinib ko‘ring.','Слишком много попыток. Подождите и попробуйте снова.'],
  'Answer every exercise first':['Avval barcha mashqlarga javob bering.','Сначала ответьте на все задания.'],
  'Practice missed exercises before completing the lesson':['Darsni yakunlashdan oldin xato qilingan mashqlarni takrorlang.','Перед завершением урока повторите задания с ошибками.'],
  'Exercise already answered':['Bu mashqqa javob allaqachon saqlangan. Darsni qayta oching.','Ответ уже сохранён. Откройте урок снова.'],
  'Review session is unavailable':['Takrorlash sessiyasi tugagan. Ro‘yxatni qayta oching.','Сессия повторения завершена. Откройте список снова.'],
  'This lesson is temporarily unavailable':['Bu dars vaqtincha mavjud emas.','Этот урок временно недоступен.'],
  'No completed attempt found':['Hozircha yakunlangan natija yo‘q.','Завершённых результатов пока нет.'],
 };
 if(typeof detail==='string'&&messages[detail])return messages[detail][ru?1:0];
 if(status===422)return ru?'Проверьте введённые данные и попробуйте снова.':'Kiritilgan ma’lumotlarni tekshirib, qayta urinib ko‘ring.';
 if(status===429)return messages['Too many requests; try again later'][ru?1:0];
 if(status>=500)return connectionMessage();
 return ru?'Не удалось выполнить запрос. Попробуйте ещё раз.':'So‘rov bajarilmadi. Qayta urinib ko‘ring.';
}
export async function readJson(response:Response):Promise<any>{
 let data:unknown;
 try{data=await response.json()}catch{throw new ApiError(response.status,response.status>=500?connectionMessage():localizedError(response.status,null))}
 if(!response.ok){
  const detail=typeof data==='object'&&data!==null&&'detail' in data?(data as {detail:unknown}).detail:null;
  throw new ApiError(response.status,localizedError(response.status,detail),typeof detail==='string'?detail:null);
 }
 return data;
}
export async function requestJson(url:string,options:RequestInit={}){
 let response:Response;
 try{response=await fetch(url,options)}catch{throw new Error(connectionMessage())}
 return readJson(response);
}
