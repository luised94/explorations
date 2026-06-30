"use strict";
/* C-2U-d: the import panel must close on a second toggle click. The handler
   always flipped the hidden attribute correctly, but .import-panel set
   display:flex in CSS, which overrides the UA [hidden]{display:none} default,
   so the panel stayed visible -- the "import won't close" bug. The fix is an
   explicit .import-panel[hidden]{display:none} guard whose specificity beats
   the base .import-panel rule.

   NOTE on the assertion strategy: jsdom does not model the CSS cascade for
   [hidden] vs an explicit display the way a real browser does (it reports
   display:none for a hidden element regardless of the guard), so reading
   getComputedStyle would pass even with the bug present and prove nothing.
   This test therefore asserts (a) the behavioral attribute toggle and (b) the
   stylesheet actually contains the [hidden] guard with at least the
   specificity of the base rule -- which IS the fix. */
const fs=require("fs"); const {JSDOM}=require("jsdom");
const html=fs.readFileSync("index.html","utf8");
let pass=0,fail=0; const ck=(n,c)=>{c?(pass++,console.log("  ok  - "+n)):(fail++,console.log("  FAIL- "+n));};
function fetchStub(){
  return async(url)=>{
    const j=(o,ok=true,s=200)=>({ok,status:s,async json(){return o;},async text(){return JSON.stringify(o);}});
    if(url==="/api/categories")return j({categories:[{id:1,name:"arithmetic",description:"",config:{}}]});
    if(url==="/api/banks")return j({banks:[]});
    if(url==="/api/difficulty-rungs")return j({rungs:[
      {rung:1,operator_depth:1,recurse_probability:0.0,max_result_value:null},
      {rung:2,operator_depth:2,recurse_probability:0.5,max_result_value:null},
      {rung:3,operator_depth:2,recurse_probability:0.7,max_result_value:null},
      {rung:4,operator_depth:3,recurse_probability:0.7,max_result_value:100000}
    ]});
    if(url==="/api/session/start"||url.indexOf("/api/session/start")===0)return j({session_id:7});
    if(url==="/api/session/end")return j({ended:true});
    if(url.indexOf("/api/question")===0)return j({qtype:"arithmetic",question_text:"6 + 7",expected:"13",question_id:null,alternatives:null,media_url:null,difficulty:null,leaf_count:2});
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
  const toggle=doc.getElementById("import-toggle");
  const panel=doc.getElementById("import-panel");

  // --- behavioral: the attribute toggle is symmetric ---
  ck("import panel starts hidden",panel.hidden===true);
  toggle.dispatchEvent(new win.Event("click"));
  await new Promise(r=>setTimeout(r,30));
  ck("first click opens (aria-expanded true)",toggle.getAttribute("aria-expanded")==="true");
  ck("first click clears hidden",panel.hidden===false);
  toggle.dispatchEvent(new win.Event("click"));
  await new Promise(r=>setTimeout(r,30));
  ck("second click closes (aria-expanded false)",toggle.getAttribute("aria-expanded")==="false");
  ck("second click sets hidden again",panel.hidden===true);

  // --- the fix: the stylesheet carries the [hidden] guard ---
  // Pull the CSS text out of the document's <style> and assert the guard rule
  // exists. Without it, [hidden] is overridden by .import-panel{display:flex}
  // and the panel never visually closes despite the attribute being correct.
  var css="";
  var styles=doc.querySelectorAll("style");
  for(var i=0;i<styles.length;i++){ css+=styles[i].textContent; }
  var guard=/\.import-panel\[hidden\]\s*\{\s*display:\s*none/.test(css);
  ck("stylesheet has .import-panel[hidden]{display:none} guard",guard);

  // --- the corrected import-help difficulty range (matches the 4-rung table) ---
  toggle.dispatchEvent(new win.Event("click"));
  await new Promise(r=>setTimeout(r,30));
  const help=doc.querySelector(".import-help");
  ck("import help mentions difficulty (1-4)",help&&help.textContent.indexOf("difficulty (1-4)")!==-1);
  ck("import help no longer says (1-5)",help&&help.textContent.indexOf("(1-5)")===-1);

  console.log("\n"+pass+" passed, "+fail+" failed");
  process.exit(fail?1:0);
})().catch(e=>{console.error(e);process.exit(2);});
