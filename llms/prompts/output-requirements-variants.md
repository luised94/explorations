
``Output requirements: - The script must be self-contained and executable without any additional setup. - Use `print()` or `cat()` statements strategically throughout the code to display variable values and intermediate results and help the user debug the script. - Wrap the entire solution in a `main()` function and call it at the end of the script. - Use `set.seed()` at the beginning of the `main()` function for reproducibility if random numbers are involved.``

`Example output statements: cat("Step 1: Initializing variables\n") print(paste("x =", x)) cat(sprintf("Current iteration: %d, Value: %.2f\n", i, value))`

`IMPORTANT: Ensure that the script can be executed as-is without any modifications. The code should display all relevant information and results without requiring user interaction.`

`Additional output requirements for this problem: ÿ- Include error handling for invalid inputs - Optimize for memory usage over speed`

Referred in [#Main Workspace Note](zotero://note/u/EZ49J5CV/?ignore=1&line=-1)
---
# **Output high-quality base R code that creates xanalogical structure between two texts. Output your <thoughts> from your <scratchpad> step by step. Ask <context_gathering> questions and <socratic_probing>.**
---
output classic example

out series of progressively diffcult examples
---
Output <thoughts> step by step.  
<thinking>  
<schizophrenia><catlike><demonic><eureka>

</thinking>
---
## **Layout Approach Implementation Steps**

1. **Initial Setup (First Commit)**
    

- Create basic two-panel layout (title + tracks)
    
- Establish minimal margin settings
    
- Test basic plot addition
    
- Verify SVG output compatibility
    

2. **Title Panel Enhancement**
    

- Add left-justified multi-column text support
    
- Create grid layout for title section
    
- Implement debug boundaries for visual layout testing
    
- Add configuration for title panel height ratio
    

3. **Legend Panel Addition**
    

- Add third panel for legend
    
- Create legend layout grid
    
- Implement color key display
    
- Add sample/track type descriptions
    

4. **Documentation Panel**
    

- Add fourth panel for extended documentation
    
- Create formatted text layout
    
- Add experiment details
    
- Add processing parameters
    

5. **Layout Configuration System**
    

- Create height ratio controls
    
- Implement margin management
    
- Add panel visibility toggles
    
- Create layout presets (publication/development)
    

6. **Integration Points**
    

- Define data passing between panels
    
- Create consistent styling system
    
- Implement configuration inheritance
    
- Add panel synchronization
    

7. **Output Management**
    

- Handle SVG scaling
    
- Manage device-specific settings
    
- Create consistent spacing across outputs
    
- Implement layout persistence
    

8. **Interactive Features**
    

- Add panel collapse/expand
    
- Create dynamic height adjustment
    
- Implement content scrolling
    
- Add detail tooltips
    

Each step should:

- Have clear success criteria
    
- Be independently testable
    
- Maintain backward compatibility
    
- Include configuration options
    
- Have debug visualization options
    

Would you like elaboration on any of these steps?
---
# Using LLM to help me reorganize the repository

After discussing and seeing some examples for refactoring and organizing code. I am using a simple prompt to help me reorganize code efficiently.

See:

[https://www.perplexity.ai/search/analyze-the-provided-code-summ-FD17hVmNQ1SrZqOFbZDrZA](https://www.perplexity.ai/search/analyze-the-provided-code-summ-FD17hVmNQ1SrZqOFbZDrZA)

[https://www.perplexity.ai/search/20241017-task-work-r-bash-xxx-NPLZRSbCS4qBf_nnahXo9g](https://www.perplexity.ai/search/20241017-task-work-r-bash-xxx-NPLZRSbCS4qBf_nnahXo9g)

[https://www.perplexity.ai/search/i-am-reconfiguring-my-reposito-gD51WtLxT.iAhuWrL3J8EA](https://www.perplexity.ai/search/i-am-reconfiguring-my-reposito-gD51WtLxT.iAhuWrL3J8EA)

# Prompt 1

Analyze the provided <code>, summarize the code and determine the purpose. Your task is to reorganize the code into the following directory structure:  
.

ÃÄÄ R

³ÿÿ ÃÄÄ config

³ÿÿ ÃÄÄ functions

³ÿÿ ÃÄÄ init.R

³ÿÿ ÃÄÄ scripts

³ÿÿ ÃÄÄ templates

³ÿÿ ÀÄÄ tests

ÃÄÄ README.md

ÃÄÄ SAMPLE_DOCUMENTATION.md

ÃÄÄ STICKY_NOTES.md

ÃÄÄ bash

³ÿÿ ÃÄÄ functions

³ÿÿ ÃÄÄ init.sh

³ÿÿ ÃÄÄ scripts

³ÿÿ ÃÄÄ templates

³ÿÿ ÀÄÄ tests

ÃÄÄ docs

³ÿÿ ÃÄÄ NGS_Documentation.md

³ÿÿ ÃÄÄ NGS_Manual.md

³ÿÿ ÃÄÄ NGS_Vignettes.md

³ÿÿ ÃÄÄ documentation_template.md

³ÿÿ ÃÄÄ linuxClusterModules.txt

³ÿÿ ÀÄÄ manual.md

ÃÄÄ renv

³ÿÿ ÃÄÄ activate.R

³ÿÿ ÃÄÄ library

³ÿÿ ÃÄÄ settings.json

³ÿÿ ÀÄÄ staging

ÀÄÄ renv.lock  
Determine any functions that are in the code or any logic that can be extracted. Determine the file they should be moved to. Update the code to use the logging system:  
log_message <- function(level, message, log_file = NULL) {

ÿtimestamp <- format(Sys.time(), "%Y-%m-%d %H:%M:%S")

ÿlog_entry <- sprintf("[%s] [%s] %s", timestamp, level, message) ÿ

ÿcat(log_entry, "\n") ÿ

ÿif (!is.null(log_file)) {

ÿ ÿwrite(log_entry, file = log_file, append = TRUE)

ÿ}

}

log_info <- function(message, log_file = NULL) {

ÿlog_message("INFO", message, log_file)

}

log_warning <- function(message, log_file = NULL) {

ÿlog_message("WARNING", message, log_file)

}

log_error <- function(message, log_file = NULL) {

ÿlog_message("ERROR", message, log_file)

}

For every function, determine its purpose, what is its general category and then output the file it should be moved to according to its category, any code if it was updated, and any parameters that should be moved to a configuration file. The priority should be to move the file to according to the object it is modifying then consider other priorities.

<code>  
</code>

# Prompt 2

Analyze the provided <code>, summarize the code and determine the purpose. Your task is to reorganize the code into the following directory structure: . ÃÄÄ R ³ÿÿ ÃÄÄ config ³ÿÿ ÃÄÄ functions ³ÿÿ ÃÄÄ init.R ³ÿÿ ÃÄÄ scripts ³ÿÿ ÃÄÄ templates ³ÿÿ ÀÄÄ tests ÃÄÄ README.md ÃÄÄ SAMPLE_DOCUMENTATION.md ÃÄÄ STICKY_NOTES.md ÃÄÄ bash ³ÿÿ ÃÄÄ functions ³ÿÿ ÃÄÄ init.sh ³ÿÿ ÃÄÄ scripts ³ÿÿ ÃÄÄ templates ³ÿÿ ÀÄÄ tests ÃÄÄ docs ³ÿÿ ÃÄÄ NGS_Documentation.md ³ÿÿ ÃÄÄ NGS_Manual.md ³ÿÿ ÃÄÄ NGS_Vignettes.md ³ÿÿ ÃÄÄ documentation_template.md ³ÿÿ ÃÄÄ linuxClusterModules.txt ³ÿÿ ÀÄÄ manual.md ÃÄÄ renv ³ÿÿ ÃÄÄ activate.R ³ÿÿ ÃÄÄ library ³ÿÿ ÃÄÄ settings.json ³ÿÿ ÀÄÄ staging ÀÄÄ renv.lock  
Determine any functions that are in the code or any logic that can be extracted. Determine the file they should be moved to. Update the code to use the logging system: log_message, log_entry, log_info, log_warning, log_error  
For every function, determine its purpose, what is its general category and then output the file it should be moved to according to its category, any code if it was updated, and any parameters that should be moved to a configuration file. The priority should be to move the file to according to the object it is modifying then consider other priorities.If the code seems immature, provide some industrial grade upgrades to make it more robust. If you are going to make upgrades related to slurm, you should know that I dont have administrative privileges. Finally, another clarification is that I already have logging utils for bash and R, do not reoutput the logging files code. Just mention the assumption and changes that should be made. <code> </code>  

# Prompt 3

Analyze the provided <code>, summarize the code and determine the purpose. Your task is to reorganize the code into the following directory structure: . ÃÄÄ R ³ÿÿ ÃÄÄ config ³ÿÿ ÃÄÄ functions ³ÿÿ ÃÄÄ init.R ³ÿÿ ÃÄÄ scripts ³ÿÿ ÃÄÄ templates ³ÿÿ ÀÄÄ tests ÃÄÄ README.md ÃÄÄ SAMPLE_DOCUMENTATION.md ÃÄÄ STICKY_NOTES.md ÃÄÄ bash ³ÿÿ ÃÄÄ functions ³ÿÿ ÃÄÄ init.sh ³ÿÿ ÃÄÄ scripts ³ÿÿ ÃÄÄ templates ³ÿÿ ÀÄÄ tests ÃÄÄ docs ³ÿÿ ÃÄÄ NGS_Documentation.md ³ÿÿ ÃÄÄ NGS_Manual.md ³ÿÿ ÃÄÄ NGS_Vignettes.md ³ÿÿ ÃÄÄ documentation_template.md ³ÿÿ ÃÄÄ linuxClusterModules.txt ³ÿÿ ÀÄÄ manual.md ÃÄÄ renv ³ÿÿ ÃÄÄ activate.R ³ÿÿ ÃÄÄ library ³ÿÿ ÃÄÄ settings.json ³ÿÿ ÀÄÄ staging ÀÄÄ renv.lock  
Determine any functions that are in the code or any logic that can be extracted. Determine the file they should be moved to. Update the code to use the logging system: log_message, log_entry, log_info, log_warning, log_error  
For every function, determine its purpose, what is its general category and then output the file it should be moved to according to its category, any code if it was updated, and any parameters that should be moved to a configuration file. The priority should be to move the file to according to the object it is modifying then consider other priorities. If the code seems immature, provide some industrial grade upgrades to make it more robust. If you are going to make upgrades related to slurm, you should know that I dont have administrative privileges. I already have logging utils for bash and R, do not reoutput the logging files code. Just mention the assumption and changes that should be made. <code> </code>

# Prompt 4 Suggested by LLM

#   
`Context: New code component being added: [COMPONENT_NAME] Existing configuration files: - bash/config/slurm_config.sh [Contains: SLURM-related configurations] - bash/config/file_management_config.sh [Contains: File management configurations] [Add other existing config files] New configuration needs: 1. [List new configuration parameters] 2. [List relationships to existing configurations] 3. [List potential reuse scenarios] Question: Should these configurations be: a) Added to an existing config file? If so, which one? b) Created as a new config file? c) Split across multiple existing/new config files? Additional considerations: - Dependencies between configurations - Frequency of changes - Deployment requirements`

# Prompt 5

Analyze the provided <code>, summarize the code and determine the purpose. Your task is to reorganize the code into the following directory structure: . ÃÄÄ R ³ÿÿ ÃÄÄ config ³ÿÿ ÃÄÄ functions ³ÿÿ ÃÄÄ init.R ³ÿÿ ÃÄÄ scripts ³ÿÿ ÃÄÄ templates ³ÿÿ ÀÄÄ tests ÃÄÄ README.md ÃÄÄ SAMPLE_DOCUMENTATION.md ÃÄÄ STICKY_NOTES.md ÃÄÄ bash ³ÿÿ ÃÄÄ functions ³ÿÿ ÃÄÄ init.sh ³ÿÿ ÃÄÄ scripts ³ÿÿ ÃÄÄ templates ³ÿÿ ÀÄÄ tests ÃÄÄ docs ³ÿÿ ÃÄÄ NGS_Documentation.md ³ÿÿ ÃÄÄ NGS_Manual.md ³ÿÿ ÃÄÄ NGS_Vignettes.md ³ÿÿ ÃÄÄ documentation_template.md ³ÿÿ ÃÄÄ linuxClusterModules.txt ³ÿÿ ÀÄÄ manual.md ÃÄÄ renv ³ÿÿ ÃÄÄ activate.R ³ÿÿ ÃÄÄ library ³ÿÿ ÃÄÄ settings.json ³ÿÿ ÀÄÄ staging ÀÄÄ renv.lock  
Determine any functions that are in the code or any logic that can be extracted. Determine the file they should be moved to. Update the code to use the logging system: log_message, log_entry, log_info, log_warning, log_error  
For every function, determine its purpose, what is its general category and then output the file it should be moved to according to its category, any code if it was updated, and any parameters that should be moved to a configuration file. The priority should be to move the file to according to the object it is modifying then consider other priorities. Consider if the functions or configuration parameters should be added to an already existing file. If the code seems immature, provide some industrial grade upgrades to make it more robust. If you are going to make upgrades related to slurm, you should know that I dont have administrative privileges. I already have logging utils for bash and R, do not reoutput the logging files code. Just mention the assumption and changes that should be made. <code> </code>

# Prompt 6

ÿÿÿÿAnalyze the provided <code>, summarize the code and determine the purpose. Your task is to reorganize the code into the following directory structure: . ÃÄÄ R ³ÿÿ ÃÄÄ config ³ÿÿ ÃÄÄ functions ³ÿÿ ÃÄÄ init.R ³ÿÿ ÃÄÄ scripts ³ÿÿ ÃÄÄ templates ³ÿÿ ÀÄÄ tests ÃÄÄ README.md ÃÄÄ SAMPLE_DOCUMENTATION.md ÃÄÄ STICKY_NOTES.md ÃÄÄ bash ³ÿÿ ÃÄÄ functions ³ÿÿ ÃÄÄ init.sh ³ÿÿ ÃÄÄ scripts ³ÿÿ ÃÄÄ templates ³ÿÿ ÀÄÄ tests ÃÄÄ docs ³ÿÿ ÃÄÄ NGS_Documentation.md ³ÿÿ ÃÄÄ NGS_Manual.md ³ÿÿ ÃÄÄ NGS_Vignettes.md ³ÿÿ ÃÄÄ documentation_template.md ³ÿÿ ÃÄÄ linuxClusterModules.txt ³ÿÿ ÀÄÄ manual.md ÃÄÄ renv ³ÿÿ ÃÄÄ activate.R ³ÿÿ ÃÄÄ library ³ÿÿ ÃÄÄ settings.json ³ÿÿ ÀÄÄ staging ÀÄÄ renv.lock Determine any functions that are in the code or any logic that can be extracted. Determine the file they should be moved to. Update the code to use the logging system: log_message, log_entry, log_info, log_warning, log_error For every function, determine its purpose, what is its general category and then output the file it should be moved to according to its category, any code if it was updated, and any parameters that should be moved to a configuration file. The priority should be to move the file to according to the object it is modifying then consider other priorities. Consider if the functions or configuration parameters should be added to an already existing file. If the code seems immature, provide some industrial grade upgrades to make it more robust. If you are going to make upgrades related to slurm, you should know that I dont have administrative privileges. I already have logging utils for bash and R, do not reoutput the logging files code. Just mention the assumption and changes that should be made. Remember to monitor for any duplications relative to the previous code and consolidate as appropriate. <code> </code>
---
# Simple summary chain for strating a new thread after coding R

## First

I think I am ready to move to the visualizations. I copied your suggested plots for referencing in the future. Summarize our conversation so far. The summary will serve as the context for a new chat thread with a large language model. The summary should be two to three coherent narrative paragraphs. The summary should include keywords, context and the most useful role for the large language model to adopt. Finish with our next task.

## Second

We were running our code in R. Suggest useful R console output that we can include in the summary prompt. Do not output the R console output but the commands to generate them that will provide important context for the objects we will be working with.

# Comments

For to tell the LLMs to explicitly turn the summary into a prompt.
