The essence of programming is style. Another word for style is design. Style is more than readability, and readability is table stakes, a means to an end rather than an end in itself.


Systematically and analytically revise the following code to understand its conceptual structure and provide specific feedback for each section using tiger style.

1. Conceptual Understanding: - Identify the main purpose of each section of the code - Understand the logical flow and dependencies between sections - Recognize any assumptions or constraints inherent in the code
    
2. Dijkstra on simplicity And Elegance: simplicity is how we bring our design goals together, how we identify the "super idea" that solves the axes simultaneously, to achieve something elegant.
    
3. Gandalf on Technical Debt: What could go wrong? What's wrong? Which question would we rather ask?
    
    Since it's hard enough to discover showstoppers, when we do find them, we solve them. There is a zero technical debt policy.
    
4. Provide the following in your analysis:  
    1\. Conceptual Summary: Summarize the main purpose and logic of each section.  
    2\. Feedback and Suggestions: Offer specific feedback and refactoring suggestions for each section based on the principles of tiger style.  
    3\. Provide a reorganization following the tiger style paradigm with a function/main organization:  
    Include a comment section at the top that provides a brief full-sentence conceptual logical description of the script and a usage comment.  
    #Description:  
    #Usage:  
    If there are any hard-coded values, turn the script into an command line argument accepting version.  
    Create a function for each section of the code and main function that orchestrates the logic between the functions. Always include a function that validates input called validate_input. If validate_input fails, the script should exit and output a useful usage message. Each function should have a useful print or cat statement that says the function call has started. Use unambiguous descriptive non-overlapping names for variables and functions.  
    Remember to use efficient R programming, and follow best practices, integrating your latent knowledge, expertise, and technical developer wisdom.
    
    ```code
    

Referred in [#Main Workspace Note](zotero://note/u/EZ49J5CV/?ignore=1&line=-1)
---
The essence of programming is style. Another word for style is design. Style is more than readability, and readability is table stakes, a means to an end rather than an end in itself.

Systematically and analytically revise the following code to understand its conceptual structure and provide specific feedback for each section using tiger style.  
Nasa's Power of Ten:

\-Use simple, explicit control flowÿfor clarity.ÿDo not use recursionÿto ensure that all executions that should be bounded are bounded. Useÿonly a minimum of excellent abstractionsÿbut only if they make the best sense of the domain.

\-Put a limit on everythingÿbecause, in reality, this is what we expect-everything has a limit. For example, all loops and all queues must have a fixed upper bound to prevent infinite loops or tail latency spikes.

\-Assertions detect programmer errors. The only correct way to handle corrupt code is to crash. Assert all function arguments and return values, pre/postconditions and invariants.ÿA function must not operate blindly on data it has not checked. The golden rule of assertions is to assert theÿpositive spaceÿthat you do expect AND to assert theÿnegative spaceÿthat you do not expect.

\-Enforce aÿhard limit of 70 lines per function. Good function shape is often the inverse of an hourglass: a few parameters, a simple return type, and a lot of meaty logic between the braces. Centralize control flow and state manipulation. Explicitly pass options to library functions at the call site.

\-Compound conditions that evaluate multiple booleans make it difficult for the reader to verify that all cases are handled. Split compound conditions into simple conditions using nestedÿif/elseÿbranches.

1. Karlton on Developer Experience:
    
    \-Always motivate, always say why.
    
    \-Get the nouns and verbs just right.ÿGreat names are the essence of great code, they capture what a thing is or does, and provide a crisp, intuitive mental model.
    
    \-Useÿsnake_caseÿfor function, variable, and file names. The underscore is the closest thing we have as programmers to a space, and helps to separate words and encourage descriptive names.
    
    \-Do not abbreviate variable names. Add units or qualifiers to variable names, and put the units or qualifiers last, sorted by descending significance, so that the variable starts with the most significant word, and ends with the least significant word.
    
    When choosing related names, try hard to find names with the same number of characters so that related variables all line up in the source. Don't overload names with multiple meanings that are context-dependent. Think of how names will be used outside the code, in documentation or communication. For example, a noun is often a better descriptor than an adjective or present participle, because a noun can be directly used in correspondence without having to be rephrased
    
    \-When a single function calls out to a helper function or callback, prefix the name of the helper function with the name of the calling function to show the call history. For example,ÿread_sector()ÿandÿread_sector_callback(). Callbacks go last in the list of parameters. This mirrors control flow: callbacks are alsoÿinvokedÿlast.
    
    \-Orderÿmatters for readability (even if it doesn't affect semantics). On the first read, a file is read top-down, so put important things near the top. Theÿmainÿfunction goes first. At the same time, not everything has a single right order. When in doubt, consider sorting alphabetically, taking advantage of big-endian naming.
    
    \-Don't forget to say why. Code alone is not documentation. Use comments to explain why you wrote the code the way you did. Don't forget to say how. Show your workings. Comments are sentences, with a space after the slash, with a capital letter and a full stop, or a colon if they relate to something that follows. Comments are well-written prose describing the code, not just scribbles in the margin.
    
    \-For the rest follow R best practices.
---
The essence of Tiger Style programming is style. A collective give-and-take at the intersection of engineering and art. Numbers and human intuition. Reason and experience. First principles and knowledge. Precision and poetry. Just like music. A tight beat. A rare groove. Words that rhyme and rhymes that break. Biodigital jazz. This is what we've learned along the way. The best is yet to come. Another word for style is design. Style is more than readability, and readability is table stakes, a means to an end rather than an end in itself.

Systematically and analytically revise the following code to understand its conceptual structure and provide specific feedback for each section using tiger style.

1. Conceptual Understanding: - Identify the main purpose of each section of the code - Understand the logical flow and dependencies between sections - Recognize any assumptions or constraints inherent in the code
    
2. Dijkstra on simplicity And Elegance: simplicity is how we bring our design goals together, how we identify the "super idea" that solves the axes simultaneously, to achieve something elegant.
    
3. Gandalf on Technical Debt: What could go wrong? What's wrong? Which question would we rather ask?
    
    Since it's hard enough to discover showstoppers, when we do find them, we solve them. There is a zero technical debt policy.
    
4. Nasa's Power of Ten:
    
    \-Use simple, explicit control flowÿfor clarity.ÿDo not use recursionÿto ensure that all executions that should be bounded are bounded. Useÿonly a minimum of excellent abstractionsÿbut only if they make the best sense of the domain.
    
    \-Put a limit on everythingÿbecause, in reality, this is what we expect-everything has a limit. For example, all loops and all queues must have a fixed upper bound to prevent infinite loops or tail latency spikes.
    
    \-Assertions detect programmer errors. The only correct way to handle corrupt code is to crash. Assert all function arguments and return values, pre/postconditions and invariants.ÿA function must not operate blindly on data it has not checked. The golden rule of assertions is to assert theÿpositive spaceÿthat you do expect AND to assert theÿnegative spaceÿthat you do not expect.
    
    \-Enforce aÿhard limit of 70 lines per function. Good function shape is often the inverse of an hourglass: a few parameters, a simple return type, and a lot of meaty logic between the braces. Centralize control flow and state manipulation. Explicitly pass options to library functions at the call site.
    
    \-Compound conditions that evaluate multiple booleans make it difficult for the reader to verify that all cases are handled. Split compound conditions into simple conditions using nestedÿif/elseÿbranches.
    
5. Karlton on Developer Experience:
    
    \-Always motivate, always say why.
    
    \-Get the nouns and verbs just right.ÿGreat names are the essence of great code, they capture what a thing is or does, and provide a crisp, intuitive mental model.
    
    \-Useÿsnake_caseÿfor function, variable, and file names. The underscore is the closest thing we have as programmers to a space, and helps to separate words and encourage descriptive names.
    
    \-Do not abbreviate variable names. Add units or qualifiers to variable names, and put the units or qualifiers last, sorted by descending significance, so that the variable starts with the most significant word, and ends with the least significant word.
    
    When choosing related names, try hard to find names with the same number of characters so that related variables all line up in the source. Don't overload names with multiple meanings that are context-dependent. Think of how names will be used outside the code, in documentation or communication. For example, a noun is often a better descriptor than an adjective or present participle, because a noun can be directly used in correspondence without having to be rephrased
    
    \-When a single function calls out to a helper function or callback, prefix the name of the helper function with the name of the calling function to show the call history. For example,ÿread_sector()ÿandÿread_sector_callback(). Callbacks go last in the list of parameters. This mirrors control flow: callbacks are alsoÿinvokedÿlast.
    
    \-Orderÿmatters for readability (even if it doesn't affect semantics). On the first read, a file is read top-down, so put important things near the top. Theÿmainÿfunction goes first. At the same time, not everything has a single right order. When in doubt, consider sorting alphabetically, taking advantage of big-endian naming.
    
    \-Don't forget to say why. Code alone is not documentation. Use comments to explain why you wrote the code the way you did. Don't forget to say how. Show your workings. Comments are sentences, with a space after the slash, with a capital letter and a full stop, or a colon if they relate to something that follows. Comments are well-written prose describing the code, not just scribbles in the margin.
    
    \-For the rest follow R best practices.
    
    Provide the following in your analysis:  
    1\. Conceptual Summary: Summarize the main purpose and logic of each section.  
    2\. Feedback and Suggestions: Offer specific feedback and refactoring suggestions for each section based on the principles of tiger style.  
    3\. Provide a reorganization following the tiger style paradigm with a function/main organization:  
    Include a comment section at the top that provides a brief full-sentence conceptual logical description of the script and a usage comment.  
    #Description:  
    #Usage:  
    If there are any hard-coded values, turn the script into an command line argument accepting version.  
    Create a function for each section of the code and main function that orchestrates the logic between the functions. Always include a function that validates input called validate_input. If validate_input fails, the script should exit and output a useful usage message. Each function should have a useful print or cat statement that says the function call has started. Use unambiguous descriptive non-overlapping names for variables and functions.  
    Remember to use efficient R programming, and follow best practices, integrating your latent knowledge, expertise, and technical developer wisdom.
    
    ```code
    

Referred in [#Main Workspace Note](zotero://note/u/EZ49J5CV/?ignore=1&line=-1)
---
