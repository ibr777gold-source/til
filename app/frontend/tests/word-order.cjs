const {chromium}=require('playwright-core');
if(!process.env.TIL_BROWSER_PATH)throw Error('Set TIL_BROWSER_PATH to a Chromium executable.');
(async()=>{
 const {createServer}=await import('vite');
 const server=await createServer({configFile:false,root:process.cwd(),server:{host:'127.0.0.1',port:0},appType:'custom'});
 server.middlewares.use((req,res,next)=>{if(req.url!=='/'){next();return}res.setHeader('Content-Type','text/html');res.end('<div id="root"></div><script type="module" src="/tests/word-order-fixture.tsx"></script>')});
 await server.listen();const browser=await chromium.launch({executablePath:process.env.TIL_BROWSER_PATH,headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage();await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/`);
  const check=page.getByRole('button',{name:'Check'});await page.getByRole('button',{name:'Men',exact:true}).click();
  await page.getByText('Barcha so‘zlarni tartib bilan tanlang: 1 / 2').waitFor();
  if(!await check.isDisabled())throw Error('Partial answer can be submitted');
  await page.getByRole('button',{name:'yozaman',exact:true}).click();
  await page.getByText('Barcha so‘zlarni tartib bilan tanlang: 2 / 2').waitFor();
  if(await check.isDisabled()||await page.locator('output').textContent()!=='Men yozaman')throw Error('Complete answer unavailable');
  await page.getByRole('button',{name:'Men olib tashlash'}).click();
  if(!await check.isDisabled())throw Error('Removing a word did not invalidate answer');
  console.log('Word order: partial, complete and edited answers passed');
 }finally{await browser.close();await server.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
