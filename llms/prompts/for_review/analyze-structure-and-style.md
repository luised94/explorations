Before making any changes, analyze the structure, style, and conventions you see in llm.py. State what you observe as rules you will follow in all modifications. Specifically:

Section layout. What are the banner sections, what belongs in each, and what are the boundary rules (which sections contain IO, which are pure)?
Function extraction rule. When does a piece of logic get its own function vs. staying inline? State the rule you infer from the existing code, with examples of both (functions that were extracted and logic that was deliberately left inline).
Provider abstraction. How are provider differences handled? What is the mechanism, and what would violate it?
Error handling pattern. Where do errors get caught, where do they propagate, and what is the convention for stderr vs. stdout? How does call_llm's error handling interact with command functions?
Naming conventions. What patterns do you see in function names (cmd_, build_, format_, etc.), variable names, and constants?
What the code deliberately does NOT do. Identify abstractions or patterns that are conspicuously absent - things a typical Python developer might add that this code avoids. State why you think they were avoided.

State each observation as a constraint you will respect. Do not suggest improvements - this is an analysis of what IS, not what could be. I will use your analysis as a checklist when reviewing your subsequent changes.
