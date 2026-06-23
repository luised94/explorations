"use strict";
const fs=require("fs"); const {JSDOM}=require("jsdom");
const html=fs.readFileSync("index.html","utf8");
let pass=0,fail=0; const ck=(n,c)=>{c?(pass++,console.log("  ok  - "+n)):(fail++,console.log("  FAIL- "+n));};
function fetchStub(){
  return async(url,opts)=>{
    const j=(o,ok=true,s=200)=>({ok,status:s,async json(){return o;},async text(){return JSON.stringify(o);}});
    if(url==="/api/categories")return j({categories:[{id:1,name:"arithmetic",description:"",config:{}}]});
    if(url==="/api/banks")return j({banks:[]});
    if(url==="/api/session/start"||url.indexOf("/api/session/start")===0)return j({session_id:7});
    if(url==="/api/session/end")return j({ended:true});
    if(url.indexOf("/api/question")===0)return j({qtype:"arithmetic",question_text:"6 + 7",expected:"13",question_id:null,alternatives:null,media_url:null});
    if(url==="/api/answer")return j({correct:true,expected:"13",user_input:"13",session_stats:{total:1,correct:1,accuracy:1.0,streak:1}});
    return j({error:"x"},false,404);
  };
}
(async()=>{
  const dom=new JSDOM(html,{runScripts:"dangerously",pretendToBeVisual:true,beforeParse(w){
    w.fetch=fetchStub(); w.navigator.sendBeacon=()=>true;
    w.SpeechSynthesisUtterance=function(t){this.text=t;this.lang="";};
    w.speechSynthesis={speak(){},cancel(){}};
  }});
  await new Promise(r=>setTimeout(r,150));
  const win=dom.window,doc=win.document;
  ck("arithmetic question rendered",doc.getElementById("expression").textContent==="6 + 7");
  ck("speaker hidden on arithmetic",doc.getElementById("speaker").hidden===true);
  ck("answer input visible",doc.getElementById("answer-row").hidden===false);
  ck("phase answering",win.state.phase==="answering");
  // submit an answer
  doc.getElementById("answer").value="13";
  await win.submitAnswer(); await new Promise(r=>setTimeout(r,40));
  ck("stats total updated to 1",doc.getElementById("stat-total").textContent==="1");
  ck("feedback phase after submit",win.state.phase==="feedback");
  console.log("\n"+pass+" passed, "+fail+" failed");
  process.exit(fail?1:0);
})().catch(e=>{console.error(e);process.exit(2);});
