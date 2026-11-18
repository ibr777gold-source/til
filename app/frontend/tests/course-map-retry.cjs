const {chromium}=require('playwright-core');
if(!process.env.TIL_BROWSER_PATH)throw Error('Set TIL_BROWSER_PATH to a Chromium executable.');
(async()=>{
 const {createServer}=await import('vite');
 const server=await createServer({configFile:false,root:process.cwd(),server:{host:'127.0.0.1',port:0},appType:'custom'});
 server.middlewares.use((req,res,next)=>{if(req.url!=='/'){next();return}res.setHeader('Content-Type','text/html');res.end('<div id="root"></div><script type="module" src="/tests/course-map-fixture.tsx"></script>')});
 await server.listen();
 const browser=await chromium.launch({executablePath:process.env.TIL_BROWSER_PATH,headless:true,args:['--no-sandbox']});
 try{
  const page=await browser.newPage();let calls=0;
  await page.route('**/api/courses/uz-ru/modules',route=>{calls++;return calls===1?route.fulfill({status:503,body:'unavailable'}):route.fulfill({status:200,json:[{number:1,title:'Birinchi modul',objective:'Mashq',status:'demo',lessons:[{id:'sample',title:'Birinchi dars',minutes:8,demo:true}]}]})});
  await page.goto(`http://127.0.0.1:${server.httpServer.address().port}/`);
  await page.getByRole('alert').waitFor();
  await page.getByRole('button',{name:/Qayta urinish/}).click();
  await page.getByRole('button',{name:/Birinchi dars/}).waitFor();
  if(await page.getByRole('alert').count())throw Error('Error remains visible after successful retry');
  console.log('Course map: failure and successful retry passed');
 }finally{await browser.close();await server.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
