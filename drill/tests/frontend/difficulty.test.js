"use strict";
/* C-2U-b: the difficulty rung selector. Drives the real index.html under
   jsdom and asserts:
     - the selector populates from GET /api/difficulty-rungs (Default + rungs),
     - picking a rung sets state.difficulty AND the next /api/question URL
       carries &difficulty=,
     - picking "Default" clears it (state.difficulty null, no &difficulty=),
     - a difficulty change re-fetches but records NO /api/answer (the discard
       is stats-safe),
     - switching to a non-arithmetic category disables the control and clears
       any selected rung. */
const fs=require("fs"); const {JSDOM}=require("jsdom");
const html=fs.readFileSync("index.html","utf8");
let pass=0,fail=0; const ck=(n,c)=>{c?(pass++,console.log("  ok  - "+n)):(fail++,console.log("  FAIL- "+n));};
const calls=[];
function fetchStub(){
  return async(url,opts)=>{
    calls.push({url, body: opts && opts.body ? JSON.parse(opts.body) : null});
    const j=(o,ok=true,s=200)=>({ok,status:s,async json(){return o;},async text(){return JSON.stringify(o);}});
    if(url==="/api/categories")return j({categories:[
      {id:1,name:"arithmetic",description:"",config:{}},
      {id:2,name:"vocabulary",description:"",config:{}}
    ]});
    if(url==="/api/banks")return j({banks:[
      {id:11,name:"spanish",category_id:2,language:"es"}
    ]});
    if(url==="/api/session/start"||url.indexOf("/api/session/start")===0)return j({session_id:7});
    if(url==="/api/session/end")return j({ended:true});
    if(url==="/api/difficulty-rungs")return j({rungs:[
      {rung:1,operator_depth:1,recurse_probability:0.0,max_result_value:null},
      {rung:2,operator_depth:2,recurse_probability:0.5,max_result_value:null},
      {rung:3,operator_depth:2,recurse_probability:0.7,max_result_value:null},
      {rung:4,operator_depth:3,recurse_probability:0.7,max_result_value:100000}
    ]});
    if(url.indexOf("/api/question")===0){
      /* C-2U-c: echo the served rung so the active-rung badge can render.
         Parse it out of the URL the client built from state.difficulty. */
      var m=url.match(/[?&]difficulty=(\d+)/);
      var served=m?parseInt(m[1],10):null;
      return j({qtype:"arithmetic",question_text:"6 + 7",expected:"13",question_id:null,alternatives:null,media_url:null,difficulty:served,leaf_count:2});
    }
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
  const diff=doc.getElementById("difficulty");

  // --- population from the endpoint ---
  ck("difficulty endpoint was fetched",calls.some(c=>c.url==="/api/difficulty-rungs"));
  ck("first option is Default (empty value)",diff.options[0].value===""&&diff.options[0].textContent==="Default");
  ck("four rung options follow Default",diff.options.length===5);
  ck("rung option value is the numeric rung",diff.options[1].value==="1");
  ck("rung label composed from facts (nested/ceiling)",diff.options[4].textContent.indexOf("Rung 4")===0
      && diff.options[4].textContent.indexOf("nested")!==-1
      && diff.options[4].textContent.indexOf("100000")!==-1);
  ck("rung 1 reads as flat / any size",diff.options[1].textContent.indexOf("flat")!==-1
      && diff.options[1].textContent.indexOf("any size")!==-1);

  // --- default state: null, no difficulty in URL ---
  ck("state.difficulty starts null",win.state.difficulty===null);
  const qBefore=calls.filter(c=>c.url.indexOf("/api/question")===0).pop();
  ck("default question URL omits difficulty",qBefore&&qBefore.url.indexOf("difficulty=")===-1);
  // --- C-2U-c: active-rung badge hidden on the default path ---
  const badge=doc.getElementById("active-rung");
  ck("active-rung badge hidden on default path",badge.hidden===true);

  // --- picking a rung sets state + next question URL carries it ---
  const answersBefore=calls.filter(c=>c.url==="/api/answer").length;
  diff.value="3";
  diff.dispatchEvent(new win.Event("change"));
  await new Promise(r=>setTimeout(r,60));
  ck("picking rung 3 sets state.difficulty",win.state.difficulty===3);
  const qAfter=calls.filter(c=>c.url.indexOf("/api/question")===0).pop();
  ck("next question URL carries difficulty=3",qAfter&&qAfter.url.indexOf("difficulty=3")!==-1);
  ck("difficulty change recorded NO answer (stats-safe discard)",
     calls.filter(c=>c.url==="/api/answer").length===answersBefore);
  // --- C-2U-c: badge now shows the served rung's descriptor ---
  ck("active-rung badge visible for a non-default rung",badge.hidden===false);
  ck("active-rung badge names rung 3",badge.textContent.indexOf("Rung 3")===0);

  // --- "Default" clears it ---
  diff.value="";
  diff.dispatchEvent(new win.Event("change"));
  await new Promise(r=>setTimeout(r,60));
  ck("Default clears state.difficulty to null",win.state.difficulty===null);
  const qDefault=calls.filter(c=>c.url.indexOf("/api/question")===0).pop();
  ck("Default question URL omits difficulty again",qDefault&&qDefault.url.indexOf("difficulty=")===-1);
  // --- C-2U-c: badge hidden again on returning to default ---
  ck("active-rung badge hidden again on Default",badge.hidden===true);

  // --- non-arithmetic gating: control disabled, rung cleared ---
  diff.value="2";
  diff.dispatchEvent(new win.Event("change"));
  await new Promise(r=>setTimeout(r,60));
  const cat=doc.getElementById("category");
  cat.value="2";
  cat.dispatchEvent(new win.Event("change"));
  await new Promise(r=>setTimeout(r,60));
  ck("difficulty disabled for non-arithmetic",diff.disabled===true);
  ck("difficulty note shown for non-arithmetic",doc.getElementById("difficulty-note").hidden===false);
  ck("switching away from arithmetic clears state.difficulty",win.state.difficulty===null);

  console.log("\n"+pass+" passed, "+fail+" failed");
  process.exit(fail?1:0);
})().catch(e=>{console.error(e);process.exit(2);});
