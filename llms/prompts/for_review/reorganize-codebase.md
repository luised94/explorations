# Using LLM to help me reorganize the repository

After discussing and seeing some examples for refactoring and organizing code. I am using a simple prompt to help me reorganize code efficiently.

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
