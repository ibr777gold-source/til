const {chromium}=require('playwright-core');
if(!process.env.TIL_BROWSER_PATH)throw Error('Set TIL_BROWSER_PATH to a Chromium executable.');
(async()=>{
 const {createServer}=await import('vite');
 const server=await createServer({configFile:false,root:process.cwd(),server:{host:'127.0.0.1',port:0},appType:'custom'});
 server.middlewares.use((req,res,next)=>{if(req.url!=='/'){next();return}res.setHeader('Content-Type','text/html');res.end('<div id="root"></div><script type="module" src="/tests/checkpoint-fixture.tsx"></script>')});
 await server.listen();
 const browser=await chromium.launch({executablePath:process.env.TIL_BROWSER_PATH,headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage();let release,seen;
  const gate=new Promise(resolve=>release=resolve),submitted=new Promise(resolve=>seen=resolve);
  await page.route('**/api/demo-checkpoint/uz-ru',async route=>{
   if(route.request().method()==='GET')return route.fulfill({status:200,json:{title:'Test',content_version:'a'.repeat(64),exercises:[{id:'q1',type:'choice',prompt:'Choose',options:['A','B']}]}});
   seen();await gate;await route.abort('failed');
  });
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/`);
  await page.getByLabel('A',{exact:true}).check();
  await page.getByRole('button',{name:/Tekshirish/}).click();await submitted;
  if(!await page.getByLabel('B',{exact:true}).isDisabled())throw Error('Answer remained editable while submitting');
  release();await page.getByRole('alert').getByText('Javoblarni tekshirib bo‘lmadi. Qayta urinib ko‘ring.').waitFor();
  if(await page.getByLabel('B',{exact:true}).isDisabled())throw Error('Answer stayed disabled after failure');
  console.log('Checkpoint: input lock and localized failure passed');
 }finally{await browser.close();await server.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
