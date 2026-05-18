
# .perplexity_coding_standard.md

\# Repository Structure and Coding Standards ## Directory Organization

\*\*Core Layers\*\*

\- meta/: Code generation and templates

\- core/: Domain implementation

\- infrastructure/: Technical components

\- interface/: External APIs

\- aspects/: Cross-cutting concerns

\- pipeline/: Processing workflows

\## Naming Conventions

\*\*File Naming Pattern\*\*

\- Format: <domain>_<action>.<extension>

\- Example: genome_processor.R, data_validator.sh

\*\*Function Categories\*\*

\- Processors: transform_data(), process_sequence()

\- Handlers: manage_resource(), handle_error() - Utilities: validate_input(), verify_result() ## Code Organization \*\*Implementation Hierarchy\*\* 1. Domain logic (core/) 2. Technical infrastructure (infrastructure/) 3. External interfaces (interface/) 4. Cross-cutting concerns (aspects/) \*\*Configuration Management\*\* - Separate static and dynamic configurations - Use hierarchical organization - Keep environment-specific settings isolated ## Meta-Programming Guidelines \*\*Code Generation\*\* - Use templates for repetitive patterns - Generate boilerplate code - Maintain consistent structure \*\*Documentation Requirements\*\* - Include function purpose - Document domain context - Specify input/output contracts ## Testing Strategy \*\*Test Categories\*\* - Unit tests: Pure functions - Integration tests: Component interaction - Property tests: Invariants - Performance tests: Benchmarks ## Error Handling \*\*Recovery Pattern\*\* ```R with_recovery <- function(f) { function(...) { tryCatch( f(...), error = handle_error, warning = handle_warning ) } }

[Wisdom from lab_utils repository restructure thread](zotero://note/u/KZESDHY6/)
---
# `.perplexity_system_validator_1.0.0.md`  
You are a senior technical lead with expertise in software engineering and project management. Your communication style should be:

\- Direct and technically precise

\- Slightly irreverent but professional

\- Focus on delivering complete, production-ready solutions

\# Repository Analysis Protocol

\## Validation Checks

\- Structure compliance

\- Naming conventions

\- Code organization

\- Impact analysis

\- Vim command generation

\## Analysis Requirements

\- Verify against standards - Generate impact reports - Provide actionable commands - Predict downstream effects

\## Response Format 1. Compliance Status 2. Required Changes 3. Impact Analysis 4. Vim Commands

SOLUTION DELIVERY

\- Complete, copy-paste ready code

\- No comments, only self-documenting code

\- Extensive console logging for debugging

\- All edge cases handled

VERIFICATION QUESTIONS

\- 3 critical questions about edge cases

\- 2 questions about scalability/maintenance

\- 1 question about future improvements
---
# .perplexity_system_validator_1.0.1.md

You are a senior technical lead with expertise in software engineering and project management focused on maintaining industrial-grade code quality and robust architecture. Your communication style should be direct and technically precise, delivering complete, production-ready solutions.

\## Core Requirements

\- Analyze repository structure and suggest improvements- Prioritize safety and correctness above all - Generate explicit, deterministic code - Maintain zero technical debt policy ÿ- Explicit control flow only - No recursive functions - Minimal abstractions - 70-line maximum per function - Explicit input/output validation - Pure functions preferred - Enforce explicit error handling patterns

\## Naming Conventions

R: - snake_case for functions and variables - UPPER_CASE for constants - dot.case avoided (R-specific) - Explicit verb prefixes (get_, set_, calc_) - Use explicit type checking with stopifnot() - Prefer base R functions over dependencies

Bash: - lowercase_with_underscores - UPPERCASE for environment variables - Prefix functions with namespace - Add _function suffix to function names - Explicitly declare and check variables

\*\*File Pattern\*\* - Format: <domain>_<action>.<extension> - Domain: Primary concept (genome, experiment) - Action: Primary operation (process, analyze) - Extension: Implementation (.R, .sh) \*\*Function Categories\*\* - Processors: transform_data(), process_sequence() - Validators: validate_input(), verify_result() - Handlers: manage_resource(), handle_error()

\## Validation Checks

\- Structure compliance, Naming conventions, Code organization, Impact analysis, Remove duplication ÿ

\- Separate static and dynamic configurations - Use hierarchical organization - Keep environment-specific settings isolated

\## Analysis Requirements

\- Verify against standards - Generate impact reports - Provide actionable commands - Predict downstream effects on other repository files.

\## Response Format

1\. Compliance Status 2. Required Changes 3. Impact Analysis 4. Complete, copy-paste ready self-documenting code 5. Verification Context-Gathering Questions, next step file follow up based on dependency analysis

\## Integration Process

1\. Collect structured feedback 2. Analyze usage patterns 3. Identify improvement areas 4. Prioritize enhancements 5. Implement changes 6. Verify improvements

# References

[\# Repository Analysis and Enhancement System You are a specialized repository assistant focused on maintaining industria](zotero://note/u/S38INSPC/)

[TigerStyle R/Bash Assistant](zotero://note/u/H6J7RR26/)
---
`Verify this perplexity space is properly configured by: 1. Confirm access to reference files: - Echo first line of reference_guidelines.md - Echo directory structure from reference_standards.md 2. Validate core capabilities: - Generate a simple function following standards - Apply error handling patterns - Implement logging 3. Test response format: - Provide analysis summary - List prioritized issues - Show concrete steps - Include validation tests Please demonstrate access to reference materials and ability to follow core standards by implementing a simple logging function in both R and bash.`
---
# 001_Perplexity space for whole repository editing

I am trying to set up a space to provide entire project context, guidelines, system prompt and prompt sets to Claude3.5 through the perplexity web interface.

Used claude3.5 and perplexity to see if helped but did not include a control without search.  
Thread name:  
__20241025_Task_Work_R/bash/labutils/PerSpace_XXX: Using perplexity spaces to help me rework my lab_utils systematically. Revisit.

## Protocol

use tree -I renv to generate directory structure.

Set system prompt

## **Usage Workflow**

**Step 1: Initial Query**

Analyze the following file: {file_content} Required: 1. Standards compliance 2. Impact analysis 3. Vim commands

**Step 2: Follow-up Actions**

Apply suggested changes: 1. File modifications 2. Directory updates 3. Downstream adjustments  

# Prompt 1

I used a large language model to help me restructure my configuration repository. I decide to go through all of the files without rigorously testing along the way. I now I have to make sure the repository is coherent and functional. I do have a deadline so we have to remain focused. The code will be used between my local computer and ÿa linux cluster environment. Your task is to help me go through the repository, anticipate common problems, detect any duplications or errors, output high-quality industrial grade code, etcetera. I would like to setup the project such that the root is ~/lab_utils but I should be able to run my scripts from anywhere for the bash and the R scripts. I am using renv for package management in the case of R. I have included the directory structure in the linux cluster for reference. the data folder contains the directories for each sequencing experiment and it is a symbolic link. Our project should be simple, but robust, efficient maintainable and structured since it will used for a publication. We first have to setup functional scripts to setup an experiment. Lets start with the init.R file and the init_config.R Reference files: perplexity_conding_standard.md: coding standards to follow. repository_aggregate.md: Entire text for the relevant files in the code repository. treestructure_norenv.txt: Directory structure of the code repository. linux_cluster_directory.txt: Directory structure of the linux cluster environment. Analyze the following file: /R/init.R #!/usr/bin/env Rscript #' Project Initialization initialize_project <- function() { ÿ ÿ# Setup error handling ÿ ÿoptions(error = function() { ÿ ÿ ÿ ÿcat("Error occurred in initialization\n") ÿ ÿ ÿ ÿif (interactive()) recover() ÿ ÿ}) ÿ ÿtryCatch({ ÿ ÿ ÿ ÿ# Load basic configuration ÿ ÿ ÿ ÿsource("config/init_config.R") ÿ ÿ ÿ ÿ# Check environment ÿ ÿ ÿ ÿcheck_environment() ÿ ÿ ÿ ÿ# Load priority scripts first ÿ ÿ ÿ ÿload_priority_scripts() ÿ ÿ ÿ ÿ# Load remaining function scripts ÿ ÿ ÿ ÿload_directory_scripts(CONFIG$PATHS$FUNCTIONS) ÿ ÿ ÿ ÿ# Load script directories ÿ ÿ ÿ ÿfor (dir in c(CONFIG$PATHS$SCRIPTS, CONFIG$PATHS$CONFIG)) { ÿ ÿ ÿ ÿ ÿ ÿload_directory_scripts(dir) ÿ ÿ ÿ ÿ} ÿ ÿ ÿ ÿlog_info("Project initialization completed successfully") ÿ ÿ}, error = function(e) { ÿ ÿ ÿ ÿcat("Critical initialization error:", e$message, "\n") ÿ ÿ ÿ ÿif (interactive()) { ÿ ÿ ÿ ÿ ÿ ÿrecover() ÿ ÿ ÿ ÿ} else { ÿ ÿ ÿ ÿ ÿ ÿquit(status = 1) ÿ ÿ ÿ ÿ} ÿ ÿ}) } initialize_project() ./R/config/init_config.R #' Initialization Configuration CONFIG <- list( ÿ ÿINITIALIZATION = list( ÿ ÿ ÿ ÿPATHS = list( ÿ ÿ ÿ ÿ ÿ ÿBASE = "R", ÿ ÿ ÿ ÿ ÿ ÿFUNCTIONS = "functions", ÿ ÿ ÿ ÿ ÿ ÿSCRIPTS = "scripts", ÿ ÿ ÿ ÿ ÿ ÿCONFIG = "config", ÿ ÿ ÿ ÿ ÿ ÿTEMPLATES = "templates" ÿ ÿ ÿ ÿ), ÿ ÿ ÿ ÿPATTERNS = list( ÿ ÿ ÿ ÿ ÿ ÿR_FILES = "\\.R$", ÿ ÿ ÿ ÿ ÿ ÿCONFIG_FILES = "^[^.].\\*\\.R$", ÿ ÿ ÿ ÿ ÿ ÿEXCLUDE = c("^\\.", "^_", "test_", "example_") ÿ ÿ ÿ ÿ), ÿ ÿ ÿ ÿLOAD_ORDER = list( ÿ ÿ ÿ ÿ ÿ ÿPRIORITY = c( ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ"logging_utils.R", ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ"environment_utils.R", ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ"validation_utils.R" ÿ ÿ ÿ ÿ ÿ ÿ), ÿ ÿ ÿ ÿ ÿ ÿOPTIONAL = c( ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ"analysis_utils.R", ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ"visualization_utils.R" ÿ ÿ ÿ ÿ ÿ ÿ) ÿ ÿ ÿ ÿ) ÿ ÿ), ÿ ÿENVIRONMENT = list( ÿ ÿ ÿ ÿREQUIRED_VARS = c( ÿ ÿ ÿ ÿ ÿ ÿ"HOME", ÿ ÿ ÿ ÿ ÿ ÿ"R_LIBS_USER", ÿ ÿ ÿ ÿ ÿ ÿ"WINDOWS_USER" ÿ ÿ ÿ ÿ), ÿ ÿ ÿ ÿPATHS = list( ÿ ÿ ÿ ÿ ÿ ÿUSER_LIB = "~/R/library", ÿ ÿ ÿ ÿ ÿ ÿRENV = "renv" ÿ ÿ ÿ ÿ) ÿ ÿ) ) #' Initialization Configuration CONFIG <- list( ÿ ÿPATHS = list( ÿ ÿ ÿ ÿBASE = "R", ÿ ÿ ÿ ÿFUNCTIONS = "functions", ÿ ÿ ÿ ÿSCRIPTS = "scripts", ÿ ÿ ÿ ÿCONFIG = "config", ÿ ÿ ÿ ÿTEMPLATES = "templates" ÿ ÿ), ÿ ÿLOAD_ORDER = list( ÿ ÿ ÿ ÿPRIORITY = c( ÿ ÿ ÿ ÿ ÿ ÿ"logging_utils.R", ÿ ÿ ÿ ÿ ÿ ÿ"environment_utils.R", ÿ ÿ ÿ ÿ ÿ ÿ"validation_utils.R" ÿ ÿ ÿ ÿ), ÿ ÿ ÿ ÿOPTIONAL = c( ÿ ÿ ÿ ÿ ÿ ÿ"analysis_utils.R", ÿ ÿ ÿ ÿ ÿ ÿ"visualization_utils.R" ÿ ÿ ÿ ÿ) ÿ ÿ), ÿ ÿPATTERNS = list( ÿ ÿ ÿ ÿR_FILES = "\\.R$", ÿ ÿ ÿ ÿEXCLUDE = c("^\\.", "^_", "test_", "example_") ÿ ÿ), ÿ ÿENVIRONMENT = list( ÿ ÿ ÿ ÿREQUIRED_VARS = c( ÿ ÿ ÿ ÿ ÿ ÿ"HOME", ÿ ÿ ÿ ÿ ÿ ÿ"R_LIBS_USER", ÿ ÿ ÿ ÿ ÿ ÿ"WINDOWS_USER" ÿ ÿ ÿ ÿ) ÿ ÿ) ) Required: 1\. Analysis and summary of purpose 2\. Standards compliance 3\. Impact analysis 4\. Complete standard-compliance upgrade code 5\. Potential downstream effect prediction and next step follow up instructions on specific files

## Prompt 2

`Maintain awareness of: - Active files - Current context - Previous interactions - System state - Pending actions`

Reference files: perplexity_conding_standard.md: coding standards to follow. repository_aggregate.md: Entire text for the relevant files in the code repository. treestructure_norenv.txt: Directory structure of the code repository. linux_cluster_directory.txt: Directory structure of the linux cluster environment. dir_tree_output.txt: Directory structure of the code repository in the linux cluster environment.  
User feedback:

Before moving on to the logging, environment and validate files, we have to fix certain things. From now on, **we must always explicitly declare arguments with clear parameter names. In this case, the configuration settings should be passed to the functions.**

Reanalyze and upgrade the init_config.R and init.R files to follow standards. Assign more descriptive less ambiguous names to the files. Label one of the functions clearly as the main function. For example, instead of initialize_project, do initialize_project_main.

# **Required:**

# **1\. Analysis and summary of purpose 2. Standards compliance 3. Impact analysis 4. Complete standard-compliance upgrade code 5. Potential downstream effect prediction and next step follow up instructions on specific files**  

## References

[.perplexity_coding_standard.md](zotero://note/u/IXP4R54S/)

[.perplexity_system_validator.md](zotero://note/u/KZT32P5U/?line=2)

[https://www.perplexity.ai/search/i-am-trying-to-use-the-new-per-lMQKoiKaTKmSGzplckOgNw](https://www.perplexity.ai/search/i-am-trying-to-use-the-new-per-lMQKoiKaTKmSGzplckOgNw)

dropbox/projects_prompts/001.
