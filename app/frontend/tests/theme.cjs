const {chromium}=require('playwright-core');
const base=process.env.TIL_E2E_BASE_URL, browserPath=process.env.TIL_BROWSER_PATH;
if(!base||!browserPath)throw Error('Set TIL_E2E_BASE_URL and TIL_BROWSER_PATH.');
const url=new URL(base);
if(url.protocol!=='http:'||!['127.0.0.1','localhost'].includes(url.hostname))throw Error('Test server must be local.');
(async()=>{
 const browser=await chromium.launch({executablePath:browserPath,headless:true,args:['--no-sandbox']});
 const context=await browser.newContext({colorScheme:'dark'});
 const page=await context.newPage();
 try{
  await page.goto(base);
  await page.getByRole('button',{name:'Qorong‘i mavzuni yoqish'}).waitFor();
  if(await page.evaluate(()=>document.documentElement.dataset.theme)!=='light')throw Error('New visitor did not start in light mode on a dark device');
  if(await page.evaluate(()=>getComputedStyle(document.documentElement).colorScheme)!=='light')throw Error('Browser controls did not use light mode');
  await page.getByRole('button',{name:'Qorong‘i mavzuni yoqish'}).click();
  await page.getByRole('button',{name:'Yorug‘ mavzuni yoqish'}).waitFor();
  await page.reload();
  await page.getByRole('button',{name:'Yorug‘ mavzuni yoqish'}).waitFor();
  if(await page.evaluate(()=>document.documentElement.dataset.theme)!=='dark')throw Error('Chosen dark mode did not persist');
  await page.getByRole('button',{name:'Yorug‘ mavzuni yoqish'}).click();
  await page.emulateMedia({colorScheme:'dark'});
  await page.reload();
  await page.getByRole('button',{name:'Qorong‘i mavzuni yoqish'}).waitFor();
  if(await page.evaluate(()=>document.documentElement.dataset.theme)!=='light')throw Error('Chosen light mode did not persist');
  console.log('Theme: light by default, dark toggle, and saved choices passed.');
 }finally{await browser.close()}
})().catch(e=>{console.error(e);process.exitCode=1});
