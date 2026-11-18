import {useEffect,useState} from 'react';
type Action='preview'|'learning'|'review'|'checkpoint'|'listening'|'feedback'|'profile'|'map'|'course';
type Feature={title:string;detail:string;action?:Action};
export default function DemoFeatures({ru,signedIn,onBack,onOpen}:{ru:boolean;signedIn:boolean;onBack:()=>void;onOpen:(action:Action)=>void}){
 const [emailAvailable,setEmailAvailable]=useState<boolean|null>(null);
 const [counts,setCounts]=useState<{ru:number;uz:number}|null>(null);
 useEffect(()=>{let live=true;Promise.all(['uz-ru','ru-uz'].map(course=>fetch('/api/courses/'+course+'/lessons').then(r=>{if(!r.ok)throw Error();return r.json()}))).then(([a,b])=>{if(live)setCounts({ru:a.length,uz:b.length})}).catch(()=>{});return()=>{live=false}},[]);
 useEffect(()=>{let live=true;fetch('/api/capabilities').then(r=>{if(!r.ok)throw Error();return r.json()}).then(data=>{if(live)setEmailAvailable(data.password_reset_email===true)}).catch(()=>{if(live)setEmailAvailable(null)});return()=>{live=false}},[]);
 const ready:Feature[]=ru?[
  {title:'Пробное упражнение',action:'preview',detail:'Попробуйте без регистрации; ответ не сохраняется.'},
  {title:'Два направления и примерные уроки',action:'learning',detail:'Регистрация, упражнения, продолжение урока и объяснения ответов.'},
  {title:'Повторение и прогресс',action:'review',detail:'Возвращайтесь к ошибкам и отслеживайте завершённые уроки.'},
  {title:'Пробная проверка',action:'checkpoint',detail:'Три вопроса по приветствиям; результат сохраняется, но не определяет уровень.'},
  {title:'Пробное аудирование',action:'listening',detail:'Два задания с синтетическим голосом; при отсутствии голоса устройства используются созданные заранее аудиофайлы. Результат не сохраняется.'},
  {title:'Отзывы',action:'feedback',detail:'Сообщайте о проблемах в пробном упражнении или уроке.'},
  {title:'План курса и практика по модулям',action:'map',detail:'Открывайте примеры уроков и пробную проверку каждого доступного модуля.'},
  {title:'Практика по всему курсу',action:'course',detail:'Десять тем, синтетическое аудио и письменный диалог. Это не экзамен A1.'},
  {title:'Настройки профиля',action:'profile',detail:'Измените имя или цель; запросите удаление аккаунта.'}
 ]:[
  {title:'Sinov mashqi',action:'preview',detail:'Ro‘yxatdan o‘tmasdan sinab ko‘ring; javob saqlanmaydi.'},
  {title:'Ikki yo‘nalish va namuna darslar',action:'learning',detail:'Ro‘yxatdan o‘tish, mashqlar, darsni davom ettirish va javob izohlari.'},
  {title:'Takrorlash va natijalar',action:'review',detail:'Xatolarga qayting va tugallangan darslarni kuzating.'},
  {title:'Namuna sinov',action:'checkpoint',detail:'Salomlashuv bo‘yicha uch savol; natija saqlanadi, lekin til darajasini belgilamaydi.'},
  {title:'Namuna tinglash mashqi',action:'listening',detail:'Ikkita mashqni sun’iy ovoz yoki oldindan yaratilgan audio bilan sinab ko‘ring; natija saqlanmaydi.'},
  {title:'Fikr bildirish',action:'feedback',detail:'Sinov mashqi yoki darsdagi muammo haqida xabar bering.'},
  {title:'Kurs rejasi va modul mashqlari',action:'map',detail:'Namuna darslarni va mavjud modullardagi sinovlarni oching.'},
  {title:'Kurs bo‘yicha mashq',action:'course',detail:'O‘nta mavzu, sun’iy audio va yozma muloqot. Bu A1 imtihoni emas.'},
  {title:'Profil sozlamalari',action:'profile',detail:'Ism yoki maqsadni o‘zgartiring; hisobni o‘chirishni so‘rang.'}
 ];
 const planned:Feature[]=ru?[
  {title:'Курс: проверка содержания',action:'map',detail:'В каждом направлении доступны 60 уроков в 10 модулях. Проверка преподавателями и подтверждение покрытия A1 ещё нужны.'},
  {title:'Аудио: проверка произношения',action:'listening',detail:'Аудирование доступно во всех модульных проверках. Записи синтетические; проверка носителями языка ещё нужна.'},
  {title:'Проверки: подтверждение результатов',action:'course',detail:'Модульные проверки охватывают все шесть уроков и аудирование. Проверка курса включает десять тем, аудирование и письменный диалог. Оценка устной речи и валидация уровня ещё нужны.'},
  {title:'Восстановление пароля',detail:emailAvailable===true?'Отправка писем настроена; доставка зависит от почтового сервиса.':emailAvailable===false?'Отправка писем для этой платформы не настроена.':'Состояние отправки писем сейчас недоступно.'}
 ]:[
  {title:'Kurs: mazmun tekshiruvi',action:'map',detail:'Har yo‘nalishda 10 modul va 60 ta dars mavjud. Mutaxassis tekshiruvi va A1 mavzulari qamrovini tasdiqlash hali kerak.'},
  {title:'Audio: talaffuz tekshiruvi',action:'listening',detail:'Barcha modul sinovlarida tinglash mavjud. Audio sun’iy yaratilgan; ona tilida so‘zlovchi mutaxassis tekshiruvi hali kerak.'},
  {title:'Sinovlar: natijalarni tasdiqlash',action:'course',detail:'Modul sinovlari oltita dars va tinglashni qamraydi. Kurs sinovida o‘nta mavzu, tinglash va yozma muloqot mavjud. Og‘zaki nutq bahosi va til darajasini tasdiqlash hali kerak.'},
  {title:'Parolni tiklash',detail:emailAvailable===true?'Xat yuborish sozlangan; yetkazish pochta xizmatiga bog‘liq.':emailAvailable===false?'Xat yuborish hali sozlanmagan.':'Xat yuborish holatini hozir aniqlab bo‘lmadi.'}
 ];
 function section(title:string,items:Feature[]){return <section className="feature-section"><h2>{title}</h2>{items.map(item=><div className="feature-item" key={item.title}><strong>{item.title}</strong><p>{item.detail}</p>{item.action&&<button type="button" className="text-button feature-link" onClick={()=>onOpen(item.action!)}>{!signedIn&&!['preview','listening','feedback'].includes(item.action)?(ru?'Войти и попробовать':'Kirish va sinab ko‘rish'):(ru?'Открыть':'Ochish')} →</button>}</div>)}</section>}
 return <main className="feature-page wrap"><button className="back" onClick={onBack}>← {ru?'Назад':'Orqaga'}</button><div className="progress-head"><div className="overline">TIL · MVP</div><h1>{ru?'Что можно попробовать':'Nimalarni sinab ko‘rish mumkin'}</h1><p>{ru?'Это версия платформы для сбора отзывов.':'Bu fikr-mulohaza yig‘ish uchun yaratilgan namuna versiya.'}</p><button className="button dark" onClick={()=>onOpen('preview')}>{ru?'Попробовать упражнение':'Mashqni sinab ko‘rish'} →</button></div>{counts&&<p className="draft-notice">{ru?`Доступно сейчас: ${counts.ru} уроков русского и ${counts.uz} уроков узбекского. Учебные материалы ожидают проверки преподавателями.`:`Hozir mavjud: rus tili uchun ${counts.ru} ta, o‘zbek tili uchun ${counts.uz} ta dars. Namuna materiallar mutaxassis tekshiruvini kutmoqda.`}</p>}<div className="feature-grid">{section(ru?'Доступно на платформе':'Mavjud imkoniyatlar',ready)}{section(ru?'Ещё в работе':'Hali tayyorlanmoqda',planned)}</div></main>
}
