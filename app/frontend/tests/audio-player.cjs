const {chromium}=require('playwright-core');
const browserPath=process.env.TIL_BROWSER_PATH;
if(!browserPath)throw Error('Set TIL_BROWSER_PATH to a Chromium executable.');

(async()=>{
 const {createServer}=await import('vite');
 const server=await createServer({configFile:false,root:process.cwd(),server:{host:'127.0.0.1',port:0},appType:'custom'});
 server.middlewares.use((req,res,next)=>{
  if(req.url!=='/'){next();return}
  res.setHeader('Content-Type','text/html');
  res.end('<div id="root"></div><script type="module" src="/tests/audio-player-fixture.tsx"></script>');
 });
 await server.listen();
 const browser=await chromium.launch({executablePath:browserPath,headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage({viewport:{width:320,height:700}});
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/`);
  const audio=page.locator('audio');
  await audio.waitFor();
  await page.getByLabel('Yozuv tezligi').focus();
  await page.keyboard.press('End');
  if(await audio.evaluate(node=>node.playbackRate)!==0.75)throw Error('Playback speed did not change');
  await audio.evaluate(node=>{node.load=()=>{window.__retried=true};node.dispatchEvent(new Event('error'))});
  await page.getByRole('alert').getByRole('button',{name:'Qayta urinish'}).click();
  if(!await page.evaluate(()=>window.__retried))throw Error('Retry did not reload audio');
  if(await page.getByRole('alert').count())throw Error('Retry did not clear the error');
  if(await audio.evaluate(node=>node.getBoundingClientRect().right>window.innerWidth))throw Error('Audio overflows mobile viewport');
  console.log('Audio player: keyboard speed, retry and mobile width passed');
 }finally{await browser.close();await server.close()}
})().catch(error=>{console.error(error);process.exitCode=1});
