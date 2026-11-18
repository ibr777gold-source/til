"""Unreviewed synthetic listening samples for local demonstration only."""
# Each tuple is (speech text, answer options, explanation). The first option is
# the answer; callers reorder options before presenting the exercise.
SAMPLES = {
 'uz-ru': {
  1:('ма',['ма','мо','му'],'Eshitilgan bo‘g‘in — ма.'),
  2:('шар',['Ш','Ж','Ч'],'«Шар» so‘zi Ш harfi bilan boshlanadi.'),
  3:('спасибо',['Rahmat','Salom','Xayr'],'Спасибо — rahmat.'),
  4:('книга',['kitob','stol','ruchka'],'Книга — kitob.'),
  5:('два',['ikki','bir','uch'],'Два — ikki.'),
  6:('мама',['ona','ota','aka yoki uka'],'Мама — ona.'),
  7:('читать',['o‘qimoq','ishlamoq','gapirmoq'],'Читать — o‘qimoq.'),
  8:('хлеб',['non','suv','choy'],'Хлеб — non.'),
  9:('школа',['maktab','do‘kon','bozor'],'Школа — maktab.'),
  10:('я дома',['Men uydaman','Men ishlayman','Men o‘qiyman'],'Я дома — men uydaman.'),
 },
 'ru-uz': {
  1:('salom',['привет','книга','школа'],'Salom — привет.'),
  2:('o‘rik',['абрикос','лес','десять'],'O‘rik — абрикос.'),
  3:('rahmat',['Спасибо','Привет','До свидания'],'Rahmat — спасибо.'),
  4:('men',['я','мы','ты'],'Men — я.'),
  5:('ikki',['два','один','три'],'Ikki — два.'),
  6:('ona',['мать','отец','старший брат'],'Ona — мать.'),
  7:('o‘qimoq',['читать','работать','говорить'],'O‘qimoq — читать.'),
  8:('non',['хлеб','вода','чай'],'Non — хлеб.'),
  9:('maktab',['школа','магазин','рынок'],'Maktab — школа.'),
  10:('men uydaman',['Я дома','Я работаю','Я учусь'],'Men uydaman — я дома.'),
 }
}

def listening_exercise(course, module):
    text, options, explanation = SAMPLES[course][module]
    prompt = 'Послушайте слово или фразу. Что это означает?' if course == 'ru-uz' else ('Bo‘g‘inni tinglang va yozuvini tanlang.' if module == 1 else 'So‘zni tinglang. Qaysi harf bilan boshlanadi?' if module == 2 else 'So‘z yoki iborani tinglang. U nimani anglatadi?')
    return {'id':'sample-listening','type':'listen_choice','prompt':prompt,'audio_src':f'/audio/synthetic/{course}-m{module:02}.mp3','options':[options[1],options[0],options[2]],'answers':[options[0]],'explanation':explanation}
