# Bash Coding Style: Simple & Incremental

## Code Structure
Write linear, procedural scripts without functions or abstractions:
- Inline all logic in execution order (top to bottom)
- Repeat code blocks rather than abstracting into functions
- Code should read like prose explanation
- Use comments to mark logical sections

## Naming Conventions
**Constants** (CAPS_SNAKE_CASE):
MAX_RETRIES=3
TIMEOUT_SECONDS=30
LOG_FILE_PATH="/var/log/script.log"

**Variables** (descriptive lowercase with underscores):
user_config_before_update="..."
error_count_total=0
temp_file_path="/tmp/processing_${timestamp}.txt"

**Include units when relevant**:
connection_timeout_ms=5000
file_size_bytes=1024
retry_delay_seconds=10

## Script Organization
1. **Configuration block** - All parameters at top
2. **Data loading** - Read files, set up environment
3. **Processing chunks** - Logical sections (5-30 lines each)
4. **Verification** - Echo/log results after major steps

Example:
```bash
# Configuration
MAX_ATTEMPTS=5
OUTPUT_DIR="/data/processed"

# Load input
input_files=$(find "$SOURCE_DIR" -name "*.dat")

# Process each file
for file in $input_files; do
    # Extract relevant data
    filtered_data=$(grep "ACTIVE" "$file")
    
    # Transform and save
    echo "$filtered_data" | awk '{print $2}' > "$OUTPUT_DIR/$(basename "$file")"
    
    # Verify
    echo "Processed: $file"
done
```

## Development Approach
- Write incrementally: suggest next small step, not complete solution
- Ask questions when approach is unclear
- Point out issues immediately as they arise
- Admit uncertainty rather than guessing
