Three fundamental prompt operations:

1. Reductive: Summarization, distillation, extraction, characterization, evaluation
    
2. Transformational: Reformatting, refactoring, language change, restructuring, modification, clarification
    
3. Generative: Drafting, planning, brainstorming, problem-solving, hypothesizing, amplification
    

Key concepts:

- Bloom's taxonomy: Language models capable of remember, understand, apply, analyze, evaluate, create
    
- Latent content: Knowledge embedded in model, activated by prompts
    
- Emerging capabilities: Theory of mind, implied cognition, logical reasoning, in-context learning
    
- Hallucination as creativity: Necessary for imagination and innovation
    

Prompt engineering principles:

- Understand model capabilities and limitations
    
- Leverage latent knowledge through appropriate prompting
    
- Recognize and utilize emerging capabilities
    
- View hallucination as a feature for creative tasks
    
- Ground creative outputs in reality when necessary
---
To facilitate the reproduction of our interaction and achieve similar results in the future, I'll provide a comprehensive set of prompts that capture the essence of our conversation. These prompts incorporate best practices and production-ready prompt engineering principles.

## Initial Prompt

1. **Task Description**  
    Provide a detailed description of the task, including the problem statement, requirements, and constraints.  
    Example:
    
    ```
    text
    ```
    
    ``Create a bash function `view_files` to view HTML files in a specified browser. The function should handle file type, filtering, and sorting. Implement argument parsing using `getopts` and provide a user-friendly interface.``
    
2. **Context and Constraints**  
    Specify any relevant context, constraints, or assumptions that might impact the solution.  
    Example:
    
    ```
    text
    ```
    
    ``The function will be used in a WSL environment, and the browser should be launched using the `wslpath` command. The default browser is Brave, and the function should support filtering by file type and sorting alphabetically.``
    

## **Follow-up Prompts**

1. **Error Handling and Debugging**  
    Request the implementation of error handling and debugging mechanisms.  
    Example:
    
    ```
    text
    ```
    
    ``Enhance the `view_files` function to include error handling for invalid arguments, missing dependencies, and file access issues. Implement a debugging mechanism using a separate `debug_view_files` function that can be toggled via a debug flag.``
    
2. **Feature Enhancements**  
    Specify additional features or improvements to be made to the function.  
    Example:
    
    ```
    text
    ```
    
    ``Extend the `view_files` function to support multiple file types (e.g., HTML, SVG, PDF) and implement a pattern matching system for filtering files. Configure the function to use different browsers based on the file type.``
    
3. **Code Refactoring and Optimization**  
    Request code refactoring and optimization for improved performance, readability, and maintainability.  
    Example:
    
    ```
    text
    ```
    
    ``Refactor the `view_files` function to improve code organization, modularity, and performance. Optimize the find command and file processing logic for efficiency.``
    
4. **Testing and Validation**  
    Specify the need for testing and validation mechanisms to ensure the function's correctness and reliability.  
    Example:
    
    ```
    text
    ```
    
    ``Develop a testing framework for the `view_files` function to validate its behavior under various scenarios, including edge cases and error conditions. Implement unit tests and integration tests to ensure the function's correctness and reliability.``
    
5. **Documentation and Usage**  
    Request documentation and usage guidelines for the function.  
    Example:
    
    ```
    text
    ```
    
    ``Create documentation for the `view_files` function, including usage examples, configuration guidelines, and troubleshooting tips. Provide clear instructions on how to use the function and its various options.``
    

## **Prompt Engineering Principles**

1. **Specificity**: Provide specific, well-defined tasks and requirements.
    
2. **Clarity**: Use clear, concise language to avoid ambiguity.
    
3. **Context**: Furnish relevant context and constraints that might impact the solution.
    
4. **Modularity**: Break down complex tasks into smaller, manageable components.
    
5. **Testing**: Emphasize the importance of testing and validation mechanisms.
    

By using these prompts and incorporating prompt engineering principles, you'll be able to effectively communicate your requirements to the large language model and obtain high-quality code and solutions.Do you have any further questions about these prompts or would you like me to elaborate on any specific aspect?

**Rewrite**

**Search Images**

**Search Videos**

**Generate Image**
