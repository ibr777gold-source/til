const {chromium}=require('playwright-core');
if(!process.env.TIL_BROWSER_PATH)throw Error('Set TIL_BROWSER_PATH to a Chromium executable.');
(async()=>{
 const {createServer}=await import('vite');
 const server=await createServer({configFile:false,root:process.cwd(),server:{host:'127.0.0.1',port:0},appType:'custom'});
 server.middlewares.use((req,res,next)=>{if(req.url!=='/'){next();return}res.setHeader('Content-Type','text/html');res.end('<div id="root"></div><script type="module" src="/tests/feedback-fixture.tsx"></script>')});
 await server.listen();const browser=await chromium.launch({executablePath:process.env.TIL_BROWSER_PATH,headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage();let release,seen;
  const gate=new Promise(resolve=>release=resolve),submitted=new Promise(resolve=>seen=resolve);
  await page.route('**/api/preview/uz-ru/feedback',async route=>{seen();await gate;await route.abort('failed')});
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/`);
  await page.getByRole('button',{name:'Fikr bildirish'}).click();
  const input=page.getByLabel('Izoh (ixtiyoriy)');await input.fill('Misol haqida fikr');
  await page.getByRole('button',{name:/Yuborish/}).click();await submitted;
  if(!await input.isDisabled()||!await page.getByRole('button',{name:'Fikr bildirish'}).isDisabled())throw Error('Feedback form remained editable while submitting');
  release();await page.getByRole('alert').waitFor();
  if(await input.isDisabled()||await input.inputValue()!=='Misol haqida fikr')throw Error('Feedback was not retained for retry');
  console.log('Feedback: controls locked during submission and text retained after failure');
 }finally{await browser.close();await server.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
