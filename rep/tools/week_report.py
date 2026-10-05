"""The week's report: statistics, then the person's answers, in one file for
the next thread (rep/PLAN.md D56).

Run at the end of the week, `rep-week` (rep/shell/rep.sh), or
    uv run python tools/week_report.py [--days 7] [--no-questions]
It reads, never writes, rep's data: the events (what the person did), the
run log (what rep did, D55), the body forms and notes.md. It writes one file,
<data root>/reports/week-<today>.md, and prints its path.

The statistics follow PLAN.md section 8's cards (E1-E5); each card's
prediction is printed beside its number, and the person is asked about it.
Everything is computed from the same readers rep uses (storage, events), so
the report and rep cannot disagree about the data.
"""

import argparse
import os
import re
import statistics
import sys
from collections import Counter
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from rep import run_log
from rep.events import effective_events, parse_canonical_time, scheduling_day
from rep.library import check_library_files
from rep.machine import resolve_machine_context
from rep.memory_model import AGAIN
from rep.session import DEFAULT_PRESET
from rep.storage import LIBRARY_FILE_SUFFIX, load_events, read_library_files

# The body form's conversions (templates/body.md). A US standard drink is 14 g
# of alcohol; ethanol weighs 0.789 g per ml; a US fluid ounce is 29.5735 ml.
USUAL_STRENGTH_PERCENT = {"beer": 5.0, "cider": 5.0, "seltzer": 5.0, "wine": 12.0, "spirits": 40.0, "liquor": 40.0}
CAFFEINE_MILLIGRAMS_PER_OUNCE = {"brewed": 12.0, "coffee": 12.0, "espresso": 63.0, "tea": 6.0, "energy": 10.0, "decaf": 0.3}

QUESTIONS = [
    "What was the most annoying moment of the week?",
    "What did you avoid doing, and why?",
    "What would you cut from rep?",
    "What did you wish rep did?",
    "How ready do you feel for the permit test, 1 to 5, and did the drills change that?",
    "The body form: what did you skip, and what was unclear?",
    "Anything for the next thread that is not in your notes?",
]


def evening_order(clock_text: str, day_start_hour: int) -> int:
    """Minutes since the day's start, so 01:30 sorts after 23:00 (D44)."""
    hour_text, minute_text = clock_text.split(":")
    minutes = int(hour_text) * 60 + int(minute_text)
    return minutes + 1440 if int(hour_text) < day_start_hour else minutes


def median_text(values: list[float], unit: str) -> str:
    return "none" if values == [] else f"{statistics.median(values):.0f} {unit} (n={len(values)})"


def main() -> int:
    argument_parser = argparse.ArgumentParser(description="The week's statistics and the person's answers, in one file.")
    argument_parser.add_argument("--days", type=int, default=7, help="how many scheduling days, ending today (default 7)")
    argument_parser.add_argument("--no-questions", action="store_true", help="statistics only")
    parsed_arguments = argument_parser.parse_args()
    day_count: int = parsed_arguments.days
    asking: bool = not parsed_arguments.no_questions

    machine_context = resolve_machine_context(data_root_flag=None, environment=os.environ, home_directory=Path.home())
    data_root = machine_context["data_root"]
    day_start_hour = DEFAULT_PRESET["day_start_hour"]
    today = scheduling_day(datetime.now(timezone.utc), day_start_hour)
    first_day = (date.fromisoformat(today) - timedelta(days=day_count - 1)).isoformat()
    window_days = [(date.fromisoformat(first_day) + timedelta(days=offset)).isoformat() for offset in range(day_count)]

    library_read = read_library_files(data_root / "library")
    library_check = check_library_files([(library_file["path"], library_file["text"]) for library_file in library_read["files"]])
    deck_by_item_id = {
        located_item["item"]["id"]: Path(located_item["path"]).name.removesuffix(LIBRARY_FILE_SUFFIX)
        for located_item in library_check["located_items"]
    }
    automatic_check_item_ids = {
        located_item["item"]["id"] for located_item in library_check["located_items"] if located_item["item"]["check"] != "self"
    }
    events = load_events(data_root / "events")["events"]
    effective = effective_events(events)
    live_events = [event for event in effective["ordered_events"] if event["id"] not in effective["undone_event_ids"]]

    def event_day(event_at: str) -> str:
        return scheduling_day(parse_canonical_time(event_at), day_start_hour)

    report: list[str] = [
        f"# rep week report, {first_day} to {today}",
        "",
        "> For the next thread: read with PLAN.md section 8 (the cards) and",
        "> STATUS.md. Every number is computed by rep/tools/week_report.py from",
        "> the events, the run log, the body forms and notes.md; the person's",
        "> answers follow the numbers. Rank the feedback into fixes, and fill in",
        "> each card's Result and Decision.",
        "",
        f"data root: {data_root}  ({machine_context['data_root_source']})",
        f"library: {library_check['item_count']} items in {len(library_read['files'])} decks; events: {len(events)}",
        "",
    ]
    card_findings: list[tuple[str, str, str]] = []  # (card, observed, prediction)

    # --- E1 capture: item_stamped per day and per deck ---
    stamped_by_day = Counter(event_day(event["at"]) for event in live_events if event["kind"] == "item_stamped")
    stamped_by_deck = Counter(
        deck_by_item_id.get(event["item"], "(not in the library)")
        for event in live_events if event["kind"] == "item_stamped" and event_day(event["at"]) in window_days
    )  # fmt: skip
    capture_days = [stamped_by_day[day] for day in window_days]
    report += ["## E1 capture", "", "| day | items captured |", "|---|---|"]
    report += [f"| {day} | {stamped_by_day[day]} |" for day in window_days]
    report += ["", "by deck: " + (", ".join(f"{deck} {count}" for deck, count in stamped_by_deck.most_common()) or "none"), ""]
    card_findings.append(("E1 capture", f"{sum(1 for count in capture_days if count >= 5)} of {day_count} days with 5 or more captured", "at least 5 items on each reading day"))

    # --- sessions: kind, duration, time of day (E2, E3, R3) ---
    session_starts = {event["id"]: event for event in live_events if event["kind"] == "session_start" and event_day(event["at"]) in window_days}
    session_ends = {event["session"]: event for event in live_events if event["kind"] == "session_end"}
    durations_minutes: list[float] = []
    local_hours: Counter[int] = Counter()
    completed_scheduled_days: set[str] = set()
    session_rows: list[str] = []
    for session_id, session_start in session_starts.items():
        started_at = parse_canonical_time(session_start["at"])
        offset_text = session_start.get("utc_offset")
        if offset_text is not None:
            offset_sign = -1 if offset_text.startswith("-") else 1
            offset = timedelta(hours=int(offset_text[1:3]), minutes=int(offset_text[4:6])) * offset_sign
            local_hours[(started_at + offset).hour] += 1
        session_end = session_ends.get(session_id)
        minutes = None if session_end is None else (parse_canonical_time(session_end["at"]) - started_at).total_seconds() / 60
        if minutes is not None:
            durations_minutes.append(minutes)
        kind = "drill " + session_start["selection"] if "selection" in session_start else "scheduled"
        reason = "abandoned" if session_end is None else session_end["reason"]
        if session_end is not None and session_end["reason"] == "completed" and "selection" not in session_start:
            completed_scheduled_days.add(event_day(session_start["at"]))
        planned = len(session_start.get("plan", []))
        session_rows.append(f"| {event_day(session_start['at'])} | {kind} | {planned} | {reason} | {'-' if minutes is None else f'{minutes:.1f}'} |")
    report += ["## Sessions", "", "| day | kind | items planned | ended | minutes |", "|---|---|---|---|---|", *sorted(session_rows), ""]
    report += [f"median minutes: {median_text(durations_minutes, 'min')}"]
    report += ["start hour (local): " + (", ".join(f"{hour:02d}h {count}" for hour, count in sorted(local_hours.items())) or "unknown"), ""]

    # --- attempts in the window: grading (E2), reviews (E4), latency (E5) ---
    window_attempts = [event for event in live_events if event["kind"] == "attempt" and event["day"] in window_days]
    automatic_attempts = [attempt for attempt in window_attempts if attempt["rating"] is not None]
    corrected = [attempt for attempt in automatic_attempts if attempt["id"] in effective["amended_ratings"]]
    ungraded = [attempt for attempt in window_attempts if effective["amended_ratings"].get(attempt["id"], attempt["rating"]) is None]
    correction_percent = 0.0 if automatic_attempts == [] else 100 * len(corrected) / len(automatic_attempts)
    report += ["## Grading (E2)", ""]
    report += [f"attempts: {len(window_attempts)}; graded by rep (exact, numeric): {len(automatic_attempts)}, of which corrected on a sheet: {len(corrected)} ({correction_percent:.0f}%)"]
    report += [f"left without a grade: {len(ungraded)}", ""]
    card_findings.append(("E2 commit before reveal", f"{correction_percent:.0f}% of automatic grades corrected; median session {median_text(durations_minutes, 'min')}", "under 15% amended; median session under 15 minutes"))
    card_findings.append(("E3 consistency", f"{len(completed_scheduled_days)} of {day_count} days with a completed scheduled session", "sessions on at least 5 of 7 days"))

    # E4: a review is an attempt with an earlier graded review at least one
    # day before (E7, E8's rule); passing is any grade but again.
    last_graded_day: dict[str, str] = {}
    review_outcomes_by_bucket: dict[str, list[bool]] = {}
    passing_latencies_by_item: dict[str, list[int]] = {}
    for event in live_events:
        if event["kind"] != "attempt":
            continue
        rating = effective["amended_ratings"].get(event["id"], event["rating"])
        if rating is None:
            continue
        previous_day = last_graded_day.get(event["item"])
        if previous_day is not None and event["day"] in window_days:
            elapsed_days = (date.fromisoformat(event["day"]) - date.fromisoformat(previous_day)).days
            if elapsed_days >= 1:
                bucket = "1" if elapsed_days == 1 else "2-3" if elapsed_days <= 3 else "4-7" if elapsed_days <= 7 else "8-15" if elapsed_days <= 15 else "16+"
                review_outcomes_by_bucket.setdefault(bucket, []).append(rating != AGAIN)
        if rating != AGAIN and event["day"] in window_days:
            passing_latencies_by_item.setdefault(event["item"], []).append(event["latency_milliseconds"])
        last_graded_day[event["item"]] = event["day"]
    report += ["## Reviews (E4)", "", "| days since last review | reviews | passed |", "|---|---|---|"]
    for bucket in ("1", "2-3", "4-7", "8-15", "16+"):
        outcomes = review_outcomes_by_bucket.get(bucket, [])
        report.append(f"| {bucket} | {len(outcomes)} | {'-' if outcomes == [] else f'{100 * sum(outcomes) / len(outcomes):.0f}%'} |")
    all_outcomes = [outcome for outcomes in review_outcomes_by_bucket.values() for outcome in outcomes]
    report.append("")
    card_findings.append(("E4 calibration", "no reviews yet" if all_outcomes == [] else f"{100 * sum(all_outcomes) / len(all_outcomes):.0f}% passed of {len(all_outcomes)} reviews", "near 90% (needs a few hundred reviews)"))
    slowest = sorted(
        ((statistics.median(latencies) / 1000, item_id) for item_id, latencies in passing_latencies_by_item.items()), reverse=True
    )[:10]
    report += ["## Slow correct answers (E5)", "", "| median seconds | item | deck | typed by rep's check |", "|---|---|---|---|"]
    report += [f"| {seconds:.1f} | {item_id} | {deck_by_item_id.get(item_id, '-')} | {'yes' if item_id in automatic_check_item_ids else 'no'} |" for seconds, item_id in slowest]
    report.append("")
    card_findings.append(("E5 automaticity", "slowest passing item: " + ("none" if slowest == [] else f"{slowest[0][1]} at {slowest[0][0]:.1f} s"), "slow items are candidates for more practice"))

    # --- body forms (R1, R3, R5) ---
    report += ["## Body", "", "| day | bed | wake | sleep h | quality | standard drinks | last drink | caffeine mg | last coffee | flags |", "|---|---|---|---|---|---|---|---|---|---|"]
    form_days = 0
    for day in window_days:
        form_path = data_root / "body" / f"{day}.md"
        if not form_path.exists():
            report.append(f"| {day} | | | | | | | | | no form |")
            continue
        form_days += 1
        fields: dict[str, list[str]] = {}
        for line in form_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("#") or ":" not in line:
                continue
            key, value = line.split(":", 1)
            fields.setdefault(key.strip(), []).append(value.strip())
        flags: list[str] = []
        bed_text = (fields.get("bed") or [""])[0]
        wake_text = (fields.get("wake") or [""])[0]
        sleep_hours = ""
        time_pattern = re.compile(r"^(\d{1,2}):(\d{2})$")
        bed_match, wake_match = time_pattern.match(bed_text), time_pattern.match(wake_text)
        if bed_match and wake_match:
            bed_minutes = int(bed_match[1]) * 60 + int(bed_match[2])
            wake_minutes = int(wake_match[1]) * 60 + int(wake_match[2])
            sleep_hours = f"{((wake_minutes - bed_minutes) % 1440) / 60:.1f}"
            if 600 <= bed_minutes < 1080:
                flags.append(f"bed {bed_text}: daytime? midnight is 00:00")
        elif bed_text or wake_text:
            flags.append("bed or wake not HH:MM")
        standard_drinks = 0.0
        last_drink = ""
        for drink_text in fields.get("drink", []):
            parts = drink_text.split()
            numbers = [float(part) for part in parts[1:] if re.fullmatch(r"\d*\.?\d+", part)]
            words = [part.lower() for part in parts[1:] if not re.fullmatch(r"\d*\.?\d+", part)]
            if parts == [] or numbers == []:
                flags.append(f"drink '{drink_text}' unreadable")
                continue
            if re.fullmatch(r"\d{1,2}:\d{2}", parts[0]) and (last_drink == "" or evening_order(parts[0], day_start_hour) > evening_order(last_drink, day_start_hour)):
                last_drink = parts[0]
            # The person's first entry was "drink: 3:00 .5": 3 a.m. in 24-hour
            # time, likely meant as 3 p.m. Shown, not corrected.
            if re.fullmatch(r"\d{1,2}:\d{2}", parts[0]) and evening_order(parts[0], day_start_hour) >= 1440:
                flags.append(f"drink at {parts[0]}: after midnight? 3 p.m. is 15:00")
            if len(numbers) >= 2:
                standard_drinks += numbers[0] * 29.5735 * numbers[1] / 100 * 0.789 / 14
            elif words != [] and words[0] in USUAL_STRENGTH_PERCENT:
                standard_drinks += numbers[0] * 29.5735 * USUAL_STRENGTH_PERCENT[words[0]] / 100 * 0.789 / 14
                flags.append(f"{words[0]} strength estimated")
            else:
                standard_drinks += numbers[0]  # the first template: a count of standard drinks
                flags.append(f"drink '{drink_text}' read as standard drinks")
        caffeine = 0.0
        last_coffee = ""
        for coffee_text in fields.get("coffee", []):
            parts = coffee_text.split()
            numbers = [float(part) for part in parts[1:] if re.fullmatch(r"\d*\.?\d+", part)]
            words = [part.lower() for part in parts[1:] if not re.fullmatch(r"\d*\.?\d+", part)]
            if parts == [] or numbers == []:
                flags.append(f"coffee '{coffee_text}' unreadable")
                continue
            if re.fullmatch(r"\d{1,2}:\d{2}", parts[0]) and (last_coffee == "" or evening_order(parts[0], day_start_hour) > evening_order(last_coffee, day_start_hour)):
                last_coffee = parts[0]
            if words == []:
                caffeine += numbers[0] * 95  # the first template: cups of brewed coffee
                flags.append(f"coffee '{coffee_text}' read as cups")
            elif words[0] in CAFFEINE_MILLIGRAMS_PER_OUNCE:
                caffeine += numbers[0] * CAFFEINE_MILLIGRAMS_PER_OUNCE[words[0]]
            else:
                caffeine += numbers[0] * CAFFEINE_MILLIGRAMS_PER_OUNCE["brewed"]
                flags.append(f"coffee kind '{words[0]}' read as brewed")
        quality = (fields.get("quality") or [""])[0]
        report.append(
            f"| {day} | {bed_text} | {wake_text} | {sleep_hours} | {quality} | {standard_drinks:.1f} | {last_drink} | {caffeine:.0f} | {last_coffee} | {'; '.join(flags)} |"
        )
    report.append("")

    # --- the run log: what rep did (D55) ---
    runs = [
        run_record for run_record in run_log.read_runs(machine_context["state_directory"] / "runs.jsonl")
        if scheduling_day(datetime.fromisoformat(run_record["at"]), day_start_hour) in window_days
    ]  # fmt: skip
    report += ["## What rep did (run log)", "", "| command | runs | failed | median ms | slowest ms |", "|---|---|---|---|---|"]
    for command, command_count in Counter(str(run_record["command"]) for run_record in runs).most_common():
        command_runs = [run_record for run_record in runs if str(run_record["command"]) == command]
        command_durations = [float(run_record["duration_milliseconds"]) for run_record in command_runs]
        failed = sum(1 for run_record in command_runs if run_record["error"] is not None or run_record["exit_code"] not in (0, 1))
        report.append(f"| {command} | {command_count} | {failed} | {statistics.median(command_durations):.0f} | {max(command_durations):.0f} |")
    phase_times: dict[str, list[float]] = {}
    for run_record in runs:
        for phase_name, milliseconds in run_record["phases"].items():
            phase_times.setdefault(f"{run_record['command']}/{phase_name}", []).append(float(milliseconds))
    report += ["", "phases, median ms: " + (", ".join(f"{name} {statistics.median(times):.1f}" for name, times in sorted(phase_times.items())) or "none")]
    for run_record in [run_record for run_record in runs if run_record["error"] is not None][-5:]:
        report += ["", f"error in `{run_record['command']}` at {run_record['at']}:", "```", str(run_record["error"]).rstrip(), "```"]
    report.append("")

    # --- the person's notes for these days, as written ---
    notes_path = data_root / "notes.md"
    report += ["## Notes (notes.md, as written)", ""]
    if notes_path.exists():
        keeping = False
        for line in notes_path.read_text(encoding="utf-8", errors="replace").splitlines():
            if line.startswith("## "):
                keeping = line[3:].strip() in window_days
            if keeping:
                report.append(line)
    else:
        report.append("(no notes.md)")
    report.append("")

    # --- the cards, then the questions ---
    report += ["## Cards: observed against predicted", ""]
    answers: list[tuple[str, str]] = []
    if asking:
        print(f"rep week report, {first_day} to {today}. Enter skips any question; Ctrl-D stops asking.\n")
    try:
        for card, observed, prediction in card_findings:
            report += [f"- {card}: {observed}. Predicted: {prediction}."]
            if asking:
                print(f"{card}\n  observed:  {observed}\n  predicted: {prediction}")
                answers.append((f"{card}: what explains this?", input("  what explains this? ").strip()))
        if asking:
            print()
            for question in QUESTIONS:
                answers.append((question, input(f"{question}\n  ").strip()))
    except EOFError:
        print("\n(stopped asking)")
    report += ["", "## The person's answers", ""]
    report += [f"- {question}\n  {answer or '(skipped)'}" for question, answer in answers] or ["(not asked: --no-questions)"]
    report += ["", f"body forms: {form_days} of {day_count} days. Generated {datetime.now(timezone.utc).isoformat(timespec='seconds')}."]

    report_path = data_root / "reports" / f"week-{today}.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(report) + "\n", encoding="utf-8")
    print(report_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
