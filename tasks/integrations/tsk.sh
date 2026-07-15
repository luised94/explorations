# tsk -- task, calendar & habit tracker
# Source this file or symlink it into my_config extensions.

# ============================================================================
# CONFIGURATION
# ============================================================================

# Absolute path to the script; the one place that knows where the code lives.
TSK_SCRIPT="$HOME/personal_repos/explorations/tasks/tasks.py"

# Data directory: set a default, but let an existing override win.
: "${TASKS_LOCAL_DIR:=$HOME/personal_repos/usb-repos/tasks}"
export TASKS_LOCAL_DIR

# ============================================================================
# PREFLIGHT CHECKS
# ============================================================================
# Warn once at source time on the abnormal path; silent when healthy so
# shell startup stays quiet.

if ! command -v uv >/dev/null 2>&1; then
    echo "tsk: warning: uv not found on PATH. tsk command will not work." >&2
fi

if [ ! -f "$TSK_SCRIPT" ]; then
    echo "tsk: warning: script not found at $TSK_SCRIPT" >&2
fi

# ============================================================================
# FUNCTION
# ============================================================================

# --no-project keeps uv from adopting a pyproject.toml in the current
# directory; tsk runs as a standalone script regardless of cwd. Both checks
# are cheap and re-run on every call to fail fast with a clear message.
tsk() {
    if ! command -v uv >/dev/null 2>&1; then
        echo "tsk: error: uv not found on PATH" >&2
        return 127
    fi
    if [ ! -f "$TSK_SCRIPT" ]; then
        echo "tsk: error: script not found at $TSK_SCRIPT" >&2
        return 127
    fi
    uv run --no-project "$TSK_SCRIPT" "$@"
}
