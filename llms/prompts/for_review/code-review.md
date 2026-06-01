Workflow Strategy Code review

Begin with a high-level review of your R code:

- Code Structure Prompt: "Evaluate the overall structure of the R code, including function organization and package structure. Propose restructuring that improves logical flow and maintainability."
    
- Naming Conventions Prompt: "Analyze the variable, function, and class names in the R code. Suggest improvements that enhance clarity and adhere to R naming conventions."
    

2. R-Specific Best Practices
    

Focus on R-specific aspects:

- R Style Guide Prompt: "Review the R code for adherence to the Tidyverse style guide. Suggest modifications that align with idiomatic R practices."
    
- Functional Programming Prompt: "Identify opportunities to leverage R's functional programming features. Propose refactoring that makes use of functions like map(), reduce(), and filter()."
    

3. Performance Optimization
    

Address R-specific performance concerns:

- Vectorization Prompt: "Analyze the code for loops that could be vectorized. Suggest vectorized alternatives that improve performance."
    
- Memory Management Prompt: "Examine the code for efficient use of memory. Propose optimizations that reduce memory usage, particularly for large datasets."
    

4. Data Manipulation and Analysis
    

Focus on R's strengths in data handling:

- Tidyverse Usage Prompt: "Review the code for opportunities to use Tidyverse packages (dplyr, tidyr, etc.). Suggest refactoring that leverages these packages for more efficient and readable data manipulation."
    
- Statistical Analysis Prompt: "Analyze the statistical methods used in the code. Propose improvements or alternatives that enhance the robustness or efficiency of the analysis."
    

5. Visualization
    

Address R's powerful visualization capabilities:

- ggplot2 Usage Prompt: "Examine the visualization code. Suggest improvements using ggplot2 that enhance the clarity and effectiveness of the data presentation."
    

6. Package Development (if applicable)
    

If you're developing an R package:

- Package Structure Prompt: "Review the package structure. Suggest improvements in organization, documentation, and adherence to CRAN policies."
    
- Roxygen2 Documentation Prompt: "Analyze the function documentation. Propose enhancements using roxygen2 to improve clarity and completeness of the documentation."
    

7. Testing and Quality Assurance
    

Implement robust testing practices:

- Unit Testing Prompt: "Review the code for testability. Suggest additions or modifications to facilitate comprehensive unit testing using testthat or similar frameworks."
    
- Code Coverage Prompt: "Analyze the current test coverage. Propose additional tests to increase coverage and improve code reliability."
    

8. Reproducibility
    

Ensure your R code is reproducible:

- Reproducibility Prompt: "Examine the code for reproducibility. Suggest improvements that enhance the reproducibility of the analysis, such as using renv for package management or creating self-contained R Markdown documents."
    

9. Error Handling and Debugging
    

Improve the robustness of your code:

- Error Handling Prompt: "Review the error handling in the code. Propose improvements using tryCatch() or similar mechanisms to gracefully handle potential errors."
    
- Debugging Prompt: "Suggest additions that facilitate easier debugging, such as strategic placement of browser() calls or use of logging packages."
    

10. Code Optimization
    

Look for opportunities to optimize your R code:

- Profiling Prompt: "Analyze the code performance using profiling tools. Identify bottlenecks and suggest optimizations."
    
- Parallel Processing Prompt: "Examine the code for opportunities to implement parallel processing. Propose modifications using packages like parallel or future to improve performance on multi-core systems."
    

11. Integration with Other Tools
    

Consider how your R code integrates with other tools:

- RMarkdown Integration Prompt: "Review how the R code integrates with RMarkdown. Suggest improvements for creating more effective, reproducible reports."
    
- Version Control Prompt: "Analyze the code structure in the context of version control. Propose organization that facilitates easier collaboration and version management."
    

12. Final Review and Documentation
    

Conclude with a comprehensive review:

- Holistic Review Prompt: "Perform a final review of the revised R code. Suggest any last refinements that would improve overall quality, readability, and efficiency."
    
- README Documentation Prompt: "Review or propose a README file for the R project. Suggest content that effectively communicates the purpose, usage, and any dependencies of the code."
    

1. Start with the high-level review (steps 1-2) to get an overall picture and address major structural issues.
    
2. Move to R-specific optimizations (steps 3-5) to leverage R's strengths.
    
3. If applicable, address package development concerns (step 6).
    
4. Implement robust testing and quality assurance measures (steps 7-9).
    
5. Fine-tune performance and integration aspects (steps 10-11).
    
6. Conclude with a final review and documentation update (step 12).
