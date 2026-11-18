const {chromium}=require('playwright-core');
if(!process.env.TIL_BROWSER_PATH)throw Error('Set TIL_BROWSER_PATH to a Chromium executable.');
(async()=>{
 const {createServer}=await import('vite');
 const server=await createServer({configFile:false,root:process.cwd(),server:{host:'127.0.0.1',port:0},appType:'custom'});
 server.middlewares.use((req,res,next)=>{if(req.url!=='/'){next();return}res.setHeader('Content-Type','text/html');res.end('<div id="root"></div><script type="module" src="/tests/matching-fixture.tsx"></script>')});
 await server.listen();const browser=await chromium.launch({executablePath:process.env.TIL_BROWSER_PATH,headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage();await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/`);
  const check=page.getByRole('button',{name:'Check'}),first=page.getByLabel('бир mos javob'),second=page.getByLabel('два mos javob');
  await first.selectOption('bir');await page.getByText('Har bir qator uchun mos javobni tanlang: 1 / 2').waitFor();
  if(!await check.isDisabled()||!await second.locator('option[value="bir"]').isDisabled())throw Error('Partial or duplicate selection allowed');
  await second.selectOption('ikki');await page.getByText('Har bir qator uchun mos javobni tanlang: 2 / 2').waitFor();
  if(await check.isDisabled()||JSON.parse(await page.locator('output').textContent())['два']!=='ikki')throw Error('Complete pairs unavailable');
  await first.selectOption('');if(!await check.isDisabled())throw Error('Clearing a pair did not invalidate answer');
  console.log('Matching: unique, complete and cleared selections passed');
 }finally{await browser.close();await server.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
