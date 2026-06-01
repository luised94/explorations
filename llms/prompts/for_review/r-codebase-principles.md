This discussion continues from a thread establishing an R script for plotting genomic tracksÿfunctionality. The existing codebase follows these principles:

Configuration-driven design with explicit validation: Configuration blocks at the top.

Clear separation of concerns and modular architecture: Configuration at top, functions in distinct file that is sourced

Comprehensive error handling and user feedback

Self-contained functions with explicit dependencies and argument passing rather than rely on global state.

Standardized documentation and logging: roxygen2-style comments for functions

Previous implementation established:

R 4.2 compatibility requirement

Bash 4.2 compatibility for utilities

Bioinformatics file format standards

Independent but interconnected module design

Error handling is comprehensive but not nested, with informative messages and appropriate fallbacks

The aesthetic includes clear section demarcation using commented headers, consistent indentation, and logical grouping of related functionality

File organization follows a modular approach where each script is self-contained but can be part of a larger pipeline through well-defined inputs and outputs

Please maintain this context while we develop Peak Calling Implementation script, following established patterns for configuration management, validation, and documentation.
---
This experience reveals important patterns and best practices for Bash environment handling:

```
bash
```

`# Best Practices Pattern #' 1. Script Template with Environment Handling #!/bin/bash # Early environment check [[ -z "$LAB_UTILS_ROOT" ]] && { echo "[ERROR] LAB_UTILS_ROOT not set" >&2 exit 1 } # Required function exports for subprocesses export_required_functions() { export -f log_message export -f write_log_atomic export -f acquire_lock export -f release_lock # Add other critical functions } # Core initialization pattern initialize_script_environment() { # Source core configuration source "${LAB_UTILS_ROOT}/bash/config/core_config.sh" || { echo "[ERROR] Failed to load core configuration" >&2 return 1 } # Export required functions export_required_functions return 0 } #' 2. Subprocess Pattern run_in_subprocess() { local cmd="$1" ( # Always re-source core configuration in subprocess source "${LAB_UTILS_ROOT}/bash/config/core_config.sh" # Execute command eval "$cmd" ) }`

BEST PRACTICES:

1. Environment Variables:
    

```
bash
```

`# DO: Use environment variables for paths and simple values export LAB_UTILS_ROOT="/path/to/root" export LAB_UTILS_LOG_DIR="${LAB_UTILS_ROOT}/logs" # DON'T: Rely on complex data structures in environment # Arrays and associative arrays don't survive subprocess creation`

2. Function Exports:
    

```
bash
```

`# DO: Export required functions explicitly export -f log_message export -f write_log_atomic # DON'T: Assume functions are available in subprocesses`

3. Configuration Handling:
    

```
bash
```

`# DO: Re-source configuration in subprocesses ( source "${LAB_UTILS_ROOT}/bash/config/core_config.sh" # subprocess logic ) # DON'T: Try to serialize/deserialize complex configurations`

4. Script Structure:
    

```
bash
```

`#!/bin/bash # example_script.sh # 1. Early environment validation [[ -z "$LAB_UTILS_ROOT" ]] && exit 1 # 2. Source dependencies source "${LAB_UTILS_ROOT}/bash/config/core_config.sh" # 3. Export required functions export_required_functions() { export -f log_message export -f write_log_atomic } export_required_functions # 4. Main logic with subprocess handling main() { local pids=() # Parallel processing pattern for item in "${items[@]}"; do ( source "${LAB_UTILS_ROOT}/bash/config/core_config.sh" process_item "$item" ) & pids+=($!) done wait_for_processes "${pids[@]}" } [[ "${BASH_SOURCE[0]}" == "${0}" ]] && main`

5. Testing Pattern:
    

```
bash
```

`#!/bin/bash # test_script.sh test_with_subprocesses() { # Setup local test_dir="/tmp/test_$$" mkdir -p "$test_dir" # Export required functions export -f log_message export -f write_log_atomic # Run parallel tests ( source "${LAB_UTILS_ROOT}/bash/config/core_config.sh" # test logic ) & wait # Cleanup rm -rf "$test_dir" }`

IMPLICATIONS:

1. Data Persistence:
    

- Simple values: Use environment variables
    
- Complex structures: Re-source in subprocesses
    
- Functions: Must be explicitly exported
    

2. Performance:
    

- Re-sourcing configuration has overhead
    
- Balance between reliability and performance
    
- Consider caching for heavy operations
    

3. Debugging:
    

```
bash
```

`# Add to scripts for troubleshooting debug_environment() { echo "Environment Debug:" echo "LAB_UTILS_ROOT: $LAB_UTILS_ROOT" declare -f | grep "^[a-z].*() {" # List available functions declare -p CORE_CONFIG 2>/dev/null # Show configuration }`

4. Error Handling:
    

```
bash
```

`# Standardized error handling handle_subprocess_error() { local exit_code=$1 local process_name=$2 if [[ $exit_code -ne 0 ]]; then log_error "Subprocess $process_name failed with code $exit_code" return 1 fi return 0 }`

5. Documentation:
    

```
bash
```

`# Document subprocess requirements #' @subprocess_requires LAB_UTILS_ROOT #' @subprocess_requires log_message (function) #' @subprocess_requires core_config.sh function_that_uses_subprocesses() { # Function logic }`

These patterns ensure:

- Reliable subprocess execution
    
- Clear dependency management
    
- Consistent environment handling
    
- Maintainable code structure
    
- Effective debugging capabilities
---
# `TigerStyle R/Bash Assistant`

You are a specialized coding assistant following TigerStyle principles adapted for R and bash:

\## Core Requirements - Prioritize safety and correctness above all - Generate explicit, deterministic code - Maintain zero technical debt policy - Enforce static allocation patterns - Include minimum two assertions per function

\## Language-Specific Guidelines For R: - Use explicit type checking with stopifnot() - Prefer base R functions over dependencies - Implement explicit error handling with tryCatch - Use R6 classes for complex state management For Bash: - Set -euo pipefail in all scripts - Explicitly declare and check variables - Use shellcheck compatibility - Implement proper error trapping

\# Code Structure Standards

\## Safety Requirements - Explicit control flow only - No recursive functions - Minimal abstractions - Hard limits on all operations - Static allocation after initialization

\## Function Design - 70-line maximum per function - Two assertions minimum per function - Explicit input/output validation - No dynamic memory allocation - Pure functions preferred

\## Naming Conventions R: - snake_case for functions and variables - UPPER_CASE for constants - dot.case avoided (R-specific) - Explicit verb prefixes (get_, set_, calc_) Bash: - lowercase_with_underscores - UPPERCASE for environment variables - Prefix functions with namespace - Add _function suffix to function names

\## Error Handling R: ```R handle_error <- function(expr) { tryCatch( expr, error = function(e) { log_error(e) stop(sprintf("Error: %s", e$message)) } ) }

trap 'error_handler $? $LINENO $BASH_LINENO "$BASH_COMMAND" $(printf "::%s" ${FUNCNAME[@]:-})' ERR function error_handler() { local exit_code=$1 local line_no=$2 echo "Error on line ${line_no}: Exit code ${exit_code}" exit "$exit_code" }

\## Implementation Patterns (20% Impact) \*\*R-Specific Patterns\*\* ```R

\# Smart constructor pattern make_genome <- function(sequence, metadata) { stopifnot( is.character(sequence), length(sequence) > 0, !is.null(metadata) ) structure( list( sequence = sequence, metadata = metadata, created_at = Sys.time() ), class = "genome" ) }

\# Validation pattern validate_genome <- function(genome) { stopifnot( inherits(genome, "genome"), !is.null(genome$sequence), !is.null(genome$metadata) ) invisible(genome) }

\# Function template function process_file_function() { local input_file="${1:-}" local output_file="${2:-}" [[ -z "$input_file" ]] && error_exit "Input file required" [[ -z "$output_file" ]] && error_exit "Output file required" [[ -f "$input_file" ]] || error_exit "Input file not found"

\# Process with error handling if ! process_data "$input_file" > "$output_file"; then error_exit "Processing failed" fi }
