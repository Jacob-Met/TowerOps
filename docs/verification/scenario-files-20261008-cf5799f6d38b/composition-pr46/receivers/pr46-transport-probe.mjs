import {createRequire} from 'node:module';
import {pathToFileURL} from 'node:url';
import {mkdir,writeFile} from 'node:fs/promises';
import path from 'node:path';
const require=createRequire(import.meta.url),puppeteer=require('puppeteer');
const root=path.resolve(process.argv[2]),out=path.resolve(process.argv[3]),web=path.join(root,'web/airspace');
await mkdir(out,{recursive:true});
const {createServer}=await import(pathToFileURL(path.join(web,'node_modules/vite/dist/node/index.js')));
const server=await createServer({root:web,configFile:false,cacheDir:path.join(out,'vite-cache'),logLevel:'error',optimizeDeps:{noDiscovery:true,include:[]},server:{host:'127.0.0.1',port:0,fs:{allow:[root,path.join(web,'node_modules')]}}});
await server.listen();const base='http://127.0.0.1:'+server.httpServer.address().port;
const result={base,requests:[],pageErrors:[],requestFailures:[],startedAt:new Date().toISOString()};
server.httpServer.on('request',(req,res)=>{const item={url:req.url};result.requests.push(item);res.on('finish',()=>item.status=res.statusCode);});
let browser;
try{
 const start=Date.now();
 try{const r=await fetch(base+'/',{signal:AbortSignal.timeout(8000)});result.http={status:r.status,bytes:(await r.text()).length,ms:Date.now()-start};}catch(error){result.http={error:String(error),ms:Date.now()-start};}
 browser=await puppeteer.launch({executablePath:'/Applications/Google Chrome.app/Contents/MacOS/Google Chrome',headless:true,userDataDir:path.join(out,'profile'),args:['--no-sandbox','--disable-gpu','--disable-background-networking','--disable-component-update','--disable-sync','--no-first-run','--no-default-browser-check']});
 const page=await browser.newPage();page.on('pageerror',e=>result.pageErrors.push(String(e)));page.on('requestfailed',r=>result.requestFailures.push({url:r.url(),failure:r.failure()}));
 try{const r=await page.goto(base+'/',{timeout:12000,waitUntil:'load'});result.browser={status:r.status(),title:await page.title(),world:await page.$eval('#world-json',e=>e.value.slice(0,100))};}catch(error){result.browser={error:String(error),url:page.url()};}
}finally{
 if(browser)await browser.close();await server.close();result.finishedAt=new Date().toISOString();await writeFile(path.join(out,'receipt.json'),JSON.stringify(result,null,2)+'\n');console.log(JSON.stringify(result));
}
