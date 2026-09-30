# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""bendlab: build a Bend prompt from the installed compiler, and run model
submissions against the compiler.

    uv run bendlab.py prompt     write prompt.md from live `bend` output
    uv run bendlab.py run        run every work/<model_id>/ submission

Standard library only. The workflow and the reasons behind it are in
README.md; the rules the task prompt relies on are in rules-card.md.
"""

import argparse
import difflib
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

# Every path resolves from this file, never from the working directory or a
# hardcoded home path. The v1 shell harness hardcoded an absolute path, so
# running it from a git worktree read and wrote the main checkout instead.
PROJECT_DIRECTORY = Path(__file__).resolve().parent
WORK_DIRECTORY = PROJECT_DIRECTORY / "work"
RUNS_DIRECTORY = PROJECT_DIRECTORY / "runs"
PROMPT_FILE = PROJECT_DIRECTORY / "prompt.md"
PROMPTS_FILE = PROJECT_DIRECTORY / "prompts.md"
RULES_CARD_FILE = PROJECT_DIRECTORY / "rules-card.md"
HISTORY_FILE = PROJECT_DIRECTORY / "history.tsv"

SUBMISSION_FILE_NAMES = ["playground.bend", "LAWS.bend", "PROOF.bend"]

# PROOF.bend first: it imports playground.bend, so when both fail they report
# the same first error, and the proof run is the one that also checks the laws.
COMMAND_FILE_NAMES = ["PROOF.bend", "playground.bend"]

# The task prompt asks for these marker lines before each figure. Without
# them a figure boundary has to be guessed from blank lines, and a Mandelbrot
# row can legitimately be entirely blank.
EXPECTED_FIGURE_MARKERS = ["mandelbrot", "sierpinski"]

INSTALL_COMMAND = "curl -fsSL https://bend-lang.com/install.sh | sh"

# The compiler prints this update notice on every run. It is not part of any
# document or program output, so it is removed before hashing or measuring.
UPDATE_BANNER_PATTERN = re.compile(r"^bend \S+ is available: run bend update\s*$")

# Stable identifiers for the compiler's error messages. The raw wording can
# change between compiler versions (2.0.32 reworked error display), and a
# histogram across attempts must count one broken rule as one class wherever
# it breaks. Order matters: the first pattern that matches wins.
ERROR_CLASS_PATTERNS = [
    ("consumed more than once", "E-AFFINE"),
    ("decreasing self-call", "E-TERMINATION"),
    ("unfilled law", "E-UNFILLED-LAW"),
    ("match on a parameter or field", "E-SCRUTINEE"),
    ("scrutinee", "E-SCRUTINEE"),
    ("a defined name", "E-UNDEFINED"),
    ("expected : a term", "E-PARSE"),
    ("'def', 'type' or 'law'", "E-PARSE"),
    ("expected : a pattern", "E-PARSE"),
    ("expected : an import", "E-PARSE"),
]

HISTORY_COLUMNS = [
    "run_at", "materials", "model_id", "attempt", "repair_strategy",
    "bend_version", "command", "exit_code", "error_id", "error_site",
    "figures", "outcome", "done_automatic", "source",
]


def run_command(command_words, working_directory, timeout_seconds):
    # stdin from /dev/null: a main that reads input would otherwise block until
    # the timeout. NO_COLOR keeps terminal escapes out of recorded output.
    environment = dict(os.environ, NO_COLOR="1")
    start_seconds = time.monotonic()
    try:
        completed = subprocess.run(
            command_words, cwd=working_directory, stdin=subprocess.DEVNULL,
            capture_output=True, text=True, timeout=timeout_seconds,
            env=environment)
        elapsed_milliseconds = int((time.monotonic() - start_seconds) * 1000)
        return {"exit_code": completed.returncode, "stdout": completed.stdout,
                "stderr": completed.stderr, "timed_out": False,
                "milliseconds": elapsed_milliseconds}
    except subprocess.TimeoutExpired as timeout_error:
        # subprocess.run kills the child on timeout; record it as its own
        # outcome so it is never mistaken for a compiler error.
        return {"exit_code": None,
                "stdout": timeout_error.stdout or "",
                "stderr": timeout_error.stderr or "",
                "timed_out": True, "milliseconds": timeout_seconds * 1000}


def require_bend(install_requested):
    bend_path = shutil.which("bend")
    if bend_path:
        return bend_path
    if not install_requested:
        print("bend is not on PATH. Install it with:\n\n    " + INSTALL_COMMAND
              + "\n\nor re-run with --install-bend. Installation is opt-in "
              "because it pipes a remote script into sh and always fetches the "
              "newest compiler, which silently changes what is under test.",
              file=sys.stderr)
        sys.exit(2)
    print("installing bend: " + INSTALL_COMMAND, file=sys.stderr)
    subprocess.run(INSTALL_COMMAND, shell=True, check=False)
    bend_path = shutil.which("bend")
    if not bend_path:
        print("bend installed but is still not on PATH. Open a new shell (the "
              "installer may have edited your shell profile) and re-run.",
              file=sys.stderr)
        sys.exit(2)
    return bend_path


def read_template(template_name):
    # prompts.md is the single source of every message a model receives, so
    # two attempts with the same strategy name always received the same words.
    prompts_text = PROMPTS_FILE.read_text()
    template_match = re.search(
        r"<!-- template: " + re.escape(template_name) + r" -->\n(.*?)\n<!-- end -->",
        prompts_text, re.S)
    if not template_match:
        print("prompts.md has no template named '" + template_name + "'.",
              file=sys.stderr)
        sys.exit(2)
    return template_match.group(1)


def main():
    argument_parser = argparse.ArgumentParser(
        description="Build a Bend prompt and run model submissions.")
    subcommand_parsers = argument_parser.add_subparsers(dest="command", required=True)

    prompt_parser = subcommand_parsers.add_parser(
        "prompt", help="write prompt.md from live `bend` output")
    prompt_parser.add_argument(
        "--with-shaders", action="store_true",
        help="include `bend guide shaders` (off by default: every model that "
             "answered said it pulled a text-output task the wrong way)")
    prompt_parser.add_argument("--install-bend", action="store_true")

    run_parser = subcommand_parsers.add_parser(
        "run", help="run every work/<model_id>/ submission")
    run_parser.add_argument(
        "model_ids", nargs="*",
        help="only these work/ subdirectories (default: all of them)")
    run_parser.add_argument(
        "--strategy",
        help="the message that actually produced this attempt, when it was "
             "not the one the previous run suggested")
    run_parser.add_argument(
        "--force", action="store_true",
        help="record a new attempt even when the files and compiler are unchanged")
    run_parser.add_argument("--timeout", type=int, default=60)
    run_parser.add_argument("--install-bend", action="store_true")

    parsed_arguments = argument_parser.parse_args()
    bend_path = require_bend(parsed_arguments.install_bend)
    version_result = run_command([bend_path, "version"], PROJECT_DIRECTORY, 30)
    version_lines = (version_result["stdout"] + version_result["stderr"]).strip().splitlines()
    bend_version = version_lines[0].strip() if version_lines else "bend (unknown version)"

    if parsed_arguments.command == "prompt":
        # The documents are fetched from the compiler at the moment the prompt
        # is built. Frozen copies went stale within days: 2.0.16 to 2.0.32 took
        # about two weeks, and a model must read the docs of the compiler that
        # will judge its code.
        document_commands = [("bend guide", ["guide"])]
        if parsed_arguments.with_shaders:
            document_commands.append(("bend guide shaders", ["guide", "shaders"]))
        document_commands.append(("bend base", ["base"]))

        document_sections = []
        header_lines = []
        fingerprint_hasher = hashlib.sha256()
        for document_label, command_words in document_commands:
            document_result = run_command([bend_path] + command_words, PROJECT_DIRECTORY, 120)
            document_text = "\n".join(
                line for line in document_result["stdout"].splitlines()
                if not UPDATE_BANNER_PATTERN.match(line))
            # Fail loudly rather than build a prompt missing a document: a
            # renamed or removed guide topic would otherwise vanish silently.
            if document_result["exit_code"] != 0 or not document_text.strip():
                print("`" + document_label + "` failed or printed nothing (exit "
                      + str(document_result["exit_code"]) + "). Not writing a "
                      "prompt with a missing document.", file=sys.stderr)
                sys.exit(1)
            fingerprint_hasher.update(document_text.encode())
            document_digest = hashlib.sha256(document_text.encode()).hexdigest()
            header_lines.append("- `" + document_label + "`: sha256 " + document_digest[:16]
                                + ", " + str(len(document_text.splitlines())) + " lines")
            document_sections.append(
                "===== BEGIN `" + document_label + "` (verbatim output of "
                + bend_version + ") =====\n" + document_text
                + "\n===== END `" + document_label + "` =====")

        rules_card_text = RULES_CARD_FILE.read_text()
        task_text = read_template("task")
        fingerprint_hasher.update(rules_card_text.encode())
        fingerprint_hasher.update(task_text.encode())
        header_lines.append("- rules-card.md: sha256 "
                            + hashlib.sha256(rules_card_text.encode()).hexdigest()[:16])
        header_lines.append("- task (prompts.md): sha256 "
                            + hashlib.sha256(task_text.encode()).hexdigest()[:16])
        # The fingerprint covers content only, not the timestamp, so the same
        # materials built twice get the same fingerprint. It is how a run knows
        # which materials a model saw, with no manual tagging.
        materials_fingerprint = fingerprint_hasher.hexdigest()[:16]

        prompt_text = (
            "# Bend reference material and task\n\n"
            "Generated " + datetime.now().astimezone().isoformat(timespec="seconds")
            + " by bendlab.py from the compiler installed on this machine. Text "
            "between BEGIN and END lines is verbatim command output, not "
            "edited.\n\n"
            "- compiler: " + bend_version + "\n"
            + "\n".join(header_lines) + "\n"
            "- materials fingerprint: " + materials_fingerprint + "\n\n"
            + "\n\n".join(document_sections) + "\n\n"
            "===== BEGIN rules card (evidence-graded; see its grades) =====\n"
            + rules_card_text.rstrip() + "\n===== END rules card =====\n\n"
            + task_text.rstrip() + "\n")
        PROMPT_FILE.write_text(prompt_text)
        print("wrote " + str(PROMPT_FILE.relative_to(PROJECT_DIRECTORY)))
        print("compiler: " + bend_version)
        print("materials fingerprint: " + materials_fingerprint)
        print("about " + str(len(prompt_text) // 4) + " tokens (characters / 4)")
        return

    # ---- run ---------------------------------------------------------------

    if not WORK_DIRECTORY.is_dir():
        print("No work/ directory. Save each model's three files into "
              "work/<model_id>/ first.", file=sys.stderr)
        sys.exit(2)

    materials_fingerprint = "unknown"
    prompt_bend_version = None
    if PROMPT_FILE.is_file():
        prompt_header = PROMPT_FILE.read_text()[:4000]
        fingerprint_match = re.search(r"materials fingerprint: (\w+)", prompt_header)
        version_match = re.search(r"^- compiler: (.+)$", prompt_header, re.M)
        if fingerprint_match:
            materials_fingerprint = fingerprint_match.group(1)
        if version_match:
            prompt_bend_version = version_match.group(1).strip()

    # Read-only git context. The status is scoped to this directory because it
    # lives inside a larger repository whose other projects are not our state.
    git_head = run_command(["git", "rev-parse", "--short", "HEAD"], PROJECT_DIRECTORY, 30)
    git_status = run_command(["git", "status", "--porcelain", "--", "."], PROJECT_DIRECTORY, 30)
    git_description = "not a git repository"
    if git_head["exit_code"] == 0:
        git_description = git_head["stdout"].strip() + (
            " (uncommitted changes in this directory)" if git_status["stdout"].strip() else "")

    requested_model_ids = parsed_arguments.model_ids
    model_directories = sorted(
        directory for directory in WORK_DIRECTORY.iterdir()
        if directory.is_dir() and (not requested_model_ids or directory.name in requested_model_ids))

    run_timestamp = datetime.now().astimezone().isoformat(timespec="seconds")
    report_lines = [
        "# bendlab run " + run_timestamp, "",
        "- compiler: " + bend_version,
        "- materials fingerprint: " + materials_fingerprint,
        "- git: " + git_description, ""]
    if prompt_bend_version and prompt_bend_version != bend_version:
        report_lines += [
            "**WARNING: prompt.md was built with " + prompt_bend_version
            + " but the installed compiler is " + bend_version
            + ". The model read documentation for a different compiler "
            "than the one judging its code. Rebuild with `uv run bendlab.py prompt`.**", ""]
    summary_rows = []
    history_rows = []

    for model_directory in model_directories:
        model_id = model_directory.name
        missing_file_names = [file_name for file_name in SUBMISSION_FILE_NAMES
                              if not (model_directory / file_name).is_file()]
        if missing_file_names:
            summary_rows.append([model_id, "-", "skipped: missing " + ", ".join(missing_file_names), "", ""])
            continue

        submission_texts = {file_name: (model_directory / file_name).read_text()
                            for file_name in SUBMISSION_FILE_NAMES}
        submission_hasher = hashlib.sha256()
        for file_name in SUBMISSION_FILE_NAMES:
            submission_hasher.update(file_name.encode() + b"\0" + submission_texts[file_name].encode())
        submission_digest = submission_hasher.hexdigest()

        model_runs_directory = RUNS_DIRECTORY / model_id
        previous_attempt_directories = sorted(
            directory for directory in model_runs_directory.glob("a[0-9][0-9]")
            if (directory / "run.json").is_file()) if model_runs_directory.is_dir() else []
        previous_record = None
        if previous_attempt_directories:
            previous_record = json.loads((previous_attempt_directories[-1] / "run.json").read_text())

        # A new attempt is recorded only when the files or the compiler
        # changed. Re-running the harness must not invent attempts; a model
        # that hands back identical files after a repair message shows up as
        # "unchanged", which is itself a result.
        if (previous_record and not parsed_arguments.force
                and previous_record["submission_digest"] == submission_digest
                and previous_record["bend_version"] == bend_version):
            summary_rows.append([model_id, previous_record["attempt"],
                                 "unchanged since " + previous_record["attempt"], "", ""])
            continue

        attempt_number = len(previous_attempt_directories)
        attempt_name = "a" + str(attempt_number).zfill(2)
        attempt_directory = model_runs_directory / attempt_name
        attempt_directory.mkdir(parents=True, exist_ok=False)
        # Snapshot before running, and run the snapshot rather than work/, so
        # the recorded result always has the exact source that produced it
        # beside it, even after work/ is overwritten by the next paste.
        for file_name in SUBMISSION_FILE_NAMES:
            (attempt_directory / file_name).write_text(submission_texts[file_name])

        if parsed_arguments.strategy:
            repair_strategy = parsed_arguments.strategy
        elif attempt_number == 0:
            repair_strategy = "oneshot"
        else:
            repair_strategy = previous_record.get("suggested_next_strategy", "unknown")

        command_records = []
        for file_name in COMMAND_FILE_NAMES:
            command_result = run_command([bend_path, file_name], attempt_directory,
                                         parsed_arguments.timeout)
            combined_output = command_result["stdout"] + command_result["stderr"]
            cleaned_output = "\n".join(line for line in combined_output.splitlines()
                                       if not UPDATE_BANNER_PATTERN.match(line))
            (attempt_directory / (file_name + ".out.txt")).write_text(cleaned_output + "\n")

            command_passed = (command_result["exit_code"] == 0 and not command_result["timed_out"]
                              and (file_name != "PROOF.bend" or "All terms check." in cleaned_output))
            error_id = ""
            error_site = ""
            error_location = ""
            if not command_passed:
                error_id = "E-TIMEOUT" if command_result["timed_out"] else "E-OTHER"
                lowered_output = cleaned_output.lower()
                for error_pattern, pattern_error_id in ERROR_CLASS_PATTERNS:
                    if error_pattern.lower() in lowered_output:
                        error_id = pattern_error_id
                        break
                # The rule lives in the "observed" parenthetical; the "expected"
                # line only names the offending variable, which differs at every
                # site. Bullets may be "-" or "*" (pasted through a markdown view).
                observed_match = re.search(r"^[-*] observed\s*:\s*(.+?)\s*$", cleaned_output, re.M)
                location_match = re.search(r"^Location:\s*(\S+)", cleaned_output, re.M)
                line_match = re.search(r"^\s*(\d+)\s*>\|", cleaned_output, re.M)
                if observed_match:
                    error_site = re.sub(r"\s*\(.*\)$", "", observed_match.group(1))
                elif location_match:
                    error_site = location_match.group(1)
                if location_match or line_match:
                    error_location = ((location_match.group(1) if location_match else "?")
                                      + ":" + (line_match.group(1) if line_match else "?"))
            command_records.append({
                "command": "bend " + file_name, "exit_code": command_result["exit_code"],
                "milliseconds": command_result["milliseconds"],
                "timed_out": command_result["timed_out"], "passed": command_passed,
                "error_id": error_id, "error_site": error_site,
                "error_location": error_location, "output_file": file_name + ".out.txt"})

        # ---- figure measurement ----
        figures = []
        playground_record = command_records[COMMAND_FILE_NAMES.index("playground.bend")]
        if playground_record["passed"]:
            render_lines = [line.rstrip("\r") for line in
                            (attempt_directory / "playground.bend.out.txt").read_text().splitlines()]
            marker_pattern = re.compile(r"^== ([A-Za-z][A-Za-z0-9 _-]*) ==\s*$")
            figure_blocks = []
            if any(marker_pattern.match(line) for line in render_lines):
                current_name = None
                current_lines = []
                for line in render_lines + ["== end-of-output =="]:
                    marker_match = marker_pattern.match(line)
                    if marker_match:
                        if current_name is not None:
                            # Only exactly-empty lines are trimmed: a row of
                            # spaces is a real figure row (a Mandelbrot row can
                            # be all background), an empty line is IO.print's.
                            while current_lines and current_lines[-1] == "":
                                current_lines.pop()
                            while current_lines and current_lines[0] == "":
                                current_lines.pop(0)
                            figure_blocks.append((current_name.strip().lower(), current_lines, True))
                        current_name = marker_match.group(1)
                        current_lines = []
                    elif current_name is not None:
                        current_lines.append(line)
            else:
                # Fallback for output without markers (all of i00). Blank-line
                # grouping splits a figure at any all-blank row, so these
                # numbers are approximate and flagged as unmarked.
                current_lines = []
                for line in render_lines + [""]:
                    if line.strip():
                        current_lines.append(line)
                    else:
                        if len(current_lines) >= 3:
                            figure_blocks.append(("unmarked-" + str(len(figure_blocks) + 1),
                                                  current_lines, False))
                        current_lines = []
            for figure_name, figure_lines, figure_is_marked in figure_blocks:
                if not figure_lines:
                    figures.append({"name": figure_name, "marked": figure_is_marked,
                                    "rows": 0, "columns": 0, "never_filled_columns": 0,
                                    "blank_right_columns": 0})
                    continue
                figure_width = max(len(line) for line in figure_lines)
                padded_lines = [line.ljust(figure_width) for line in figure_lines]
                never_filled_columns = [column for column in range(figure_width)
                                        if all(line[column] == " " for line in padded_lines)]
                blank_right_columns = 0
                for column in range(figure_width - 1, -1, -1):
                    if column not in never_filled_columns:
                        break
                    blank_right_columns += 1
                figures.append({"name": figure_name, "marked": figure_is_marked,
                                "rows": len(figure_lines), "columns": figure_width,
                                "never_filled_columns": len(never_filled_columns),
                                "blank_right_columns": blank_right_columns})

        # ---- automatic part of the definition of done ----
        # Inductive-law heuristic: a proof def that names itself in its own
        # body (an induction hypothesis) or rewrites with %. It is a heuristic:
        # confirm by reading. It exists because two of five i00 models passed
        # the checker with laws that each close in one reduction step.
        proof_text = submission_texts["PROOF.bend"]
        proof_def_matches = list(re.finditer(r"^def ([A-Za-z0-9_.]+)\(", proof_text, re.M))
        inductive_proof_names = []
        for match_index, def_match in enumerate(proof_def_matches):
            body_end = (proof_def_matches[match_index + 1].start()
                        if match_index + 1 < len(proof_def_matches) else len(proof_text))
            next_top_level = re.search(r"^(law|type) ", proof_text[def_match.end():body_end], re.M)
            if next_top_level:
                body_end = def_match.end() + next_top_level.start()
            proof_body = proof_text[def_match.end():body_end]
            if (def_match.group(1) + "(") in proof_body or re.search(r"^\s*%", proof_body, re.M):
                inductive_proof_names.append(def_match.group(1))

        figure_names = [figure["name"] for figure in figures]
        sierpinski_figures = [figure for figure in figures if figure["name"] == "sierpinski"]
        done_checks = {
            "proof_passes": command_records[0]["passed"],
            "renders": playground_record["passed"],
            "figures_marked": all(marker in figure_names for marker in EXPECTED_FIGURE_MARKERS),
            "sierpinski_no_dead_columns": (sierpinski_figures[0]["never_filled_columns"] == 0
                                           if sierpinski_figures else None),
            "inductive_law_heuristic": bool(inductive_proof_names),
        }
        done_automatic = all(check_value is True for check_value in done_checks.values())

        # ---- next message ----
        failing_records = [record for record in command_records if not record["passed"]]
        current_error_ids = {record["error_id"] for record in failing_records}
        previous_error_ids = set()
        if previous_record:
            previous_error_ids = {record["error_id"] for record in previous_record["commands"]
                                  if record["error_id"]}
        if not failing_records:
            # Compiles and renders: the next step is the self-audit, which is
            # the only thing that reached the silent defects in i00.
            suggested_next_strategy = "audit"
        elif current_error_ids & previous_error_ids:
            # Same rule broken twice in a row: the model is repairing the
            # reported line only. Medium took eight rounds this way in i00.
            suggested_next_strategy = "sweep"
        else:
            suggested_next_strategy = "enumerate"

        paste_output = ""
        for record in failing_records:
            record_output = (attempt_directory / record["output_file"]).read_text().rstrip()
            # PROOF.bend imports playground.bend, so both runs usually report
            # the same error; paste the second only when it says something new.
            if paste_output and record["error_site"] == failing_records[0]["error_site"] \
                    and record["error_id"] == failing_records[0]["error_id"]:
                continue
            paste_output += "$ " + record["command"] + "\n" + record_output + "\n\n"
        paste_text = read_template(suggested_next_strategy).replace(
            "{compiler_output}", paste_output.rstrip()).replace(
            "{error_history}", ", ".join(sorted(current_error_ids | previous_error_ids)))
        (attempt_directory / "paste.md").write_text(paste_text.rstrip() + "\n")

        # ---- diff against the previous attempt ----
        diff_lines = []
        if previous_attempt_directories:
            for file_name in SUBMISSION_FILE_NAMES:
                previous_text = (previous_attempt_directories[-1] / file_name).read_text()
                diff_lines += list(difflib.unified_diff(
                    previous_text.splitlines(keepends=True),
                    submission_texts[file_name].splitlines(keepends=True),
                    fromfile=previous_attempt_directories[-1].name + "/" + file_name,
                    tofile=attempt_name + "/" + file_name))
            (attempt_directory / "diff-from-previous.patch").write_text("".join(diff_lines))
        diff_added = sum(1 for line in diff_lines if line.startswith("+") and not line.startswith("+++"))
        diff_removed = sum(1 for line in diff_lines if line.startswith("-") and not line.startswith("---"))

        run_record = {
            "schema": 1, "run_at": run_timestamp, "model_id": model_id,
            "attempt": attempt_name, "repair_strategy": repair_strategy,
            "materials": materials_fingerprint, "bend_version": bend_version,
            "git": git_description, "submission_digest": submission_digest,
            "commands": command_records, "figures": figures,
            "done_checks": done_checks, "done_automatic": done_automatic,
            "inductive_proofs": inductive_proof_names,
            "suggested_next_strategy": suggested_next_strategy,
            # Filled by hand: whether a law is non-vacuous and whether the fork
            # tree is balanced cannot be decided by this script.
            "done_manual": {"laws_non_vacuous": None, "fork_balanced": None, "notes": None},
        }
        (attempt_directory / "run.json").write_text(json.dumps(run_record, indent=2) + "\n")

        figures_compact = "|".join(
            figure["name"] + ":" + str(figure["rows"]) + "x" + str(figure["columns"])
            + ":" + str(figure["never_filled_columns"]) + "/" + str(figure["blank_right_columns"])
            for figure in figures)
        for record in command_records:
            history_rows.append({
                "run_at": run_timestamp, "materials": materials_fingerprint,
                "model_id": model_id, "attempt": attempt_name,
                "repair_strategy": repair_strategy, "bend_version": bend_version,
                "command": record["command"],
                "exit_code": "timeout" if record["timed_out"] else str(record["exit_code"]),
                "error_id": record["error_id"], "error_site": record["error_site"],
                "figures": figures_compact if record["command"] == "bend playground.bend" else "",
                "outcome": "pass" if record["passed"] else "fail",
                "done_automatic": "pass" if done_automatic else "fail",
                "source": "bendlab.py"})

        # Both commands usually report the same first error (PROOF.bend
        # imports playground.bend); list each distinct error once.
        distinct_errors = []
        for record in failing_records:
            error_text = record["error_id"] + " " + record["error_site"]
            if error_text not in distinct_errors:
                distinct_errors.append(error_text)
        status_text = ("done (automatic checks)" if done_automatic
                       else "compiles and renders" if not failing_records
                       else ", ".join(distinct_errors))
        summary_rows.append([model_id, attempt_name, status_text, repair_strategy,
                             "runs/" + model_id + "/" + attempt_name + "/paste.md"])

        report_lines += ["## " + model_id + " " + attempt_name, "",
                         "- produced by: " + repair_strategy,
                         "- files changed since previous attempt: +" + str(diff_added)
                         + " / -" + str(diff_removed) + " lines" if previous_attempt_directories
                         else "- first attempt"]
        for record in command_records:
            report_lines.append("- `" + record["command"] + "`: "
                                + ("pass" if record["passed"] else
                                   "FAIL " + record["error_id"] + " at " + (record["error_site"] or "?")
                                   + " (" + (record["error_location"] or "no location") + ")")
                                + ", " + str(record["milliseconds"]) + " ms")
        for figure in figures:
            report_lines.append("- figure " + figure["name"] + ": " + str(figure["rows"]) + " rows x "
                                + str(figure["columns"]) + " columns, "
                                + str(figure["never_filled_columns"]) + " never-filled columns, "
                                + str(figure["blank_right_columns"]) + " blank on the right"
                                + ("" if figure["marked"] else " (unmarked: approximate)"))
        report_lines.append("- done checks: " + ", ".join(
            check_name + "=" + ("?" if check_value is None else "yes" if check_value else "NO")
            for check_name, check_value in done_checks.items()))
        report_lines.append("- inductive proofs (heuristic): "
                            + (", ".join(inductive_proof_names) or "none"))
        report_lines.append("- next message: " + suggested_next_strategy + ", in `runs/"
                            + model_id + "/" + attempt_name + "/paste.md`")
        # Escalation is a suggestion; the person decides. Put it where it will
        # be seen instead of burying it in run.json.
        if suggested_next_strategy == "sweep":
            report_lines.append("- **same error class as the previous attempt ("
                                + ", ".join(sorted(current_error_ids & previous_error_ids))
                                + "): the sweep message asks for every site of the rule before any fix**")
        report_lines.append("")

    if history_rows:
        write_header = not HISTORY_FILE.is_file()
        with HISTORY_FILE.open("a") as history_handle:
            if write_header:
                history_handle.write("\t".join(HISTORY_COLUMNS) + "\n")
            for history_row in history_rows:
                history_handle.write("\t".join(history_row[column] for column in HISTORY_COLUMNS) + "\n")

    summary_table = ["| model | attempt | status | produced by | next message |",
                     "|---|---|---|---|---|"]
    summary_table += ["| " + " | ".join(row) + " |" for row in summary_rows]
    # The first six report lines are the header block ending in a blank line;
    # markdown needs that blank line before a table or it renders as text.
    report_text = "\n".join(report_lines[:6] + summary_table + [""] + report_lines[6:]) + "\n"
    RUNS_DIRECTORY.mkdir(exist_ok=True)
    (RUNS_DIRECTORY / "latest-report.md").write_text(report_text)
    print("\n".join(summary_table))
    print("\nreport: runs/latest-report.md")


if __name__ == "__main__":
    main()
