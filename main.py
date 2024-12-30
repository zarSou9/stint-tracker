import argparse
import time
import asyncio
from playsound import playsound
import json
from aioconsole import ainput
import questionary
import sys
import os
from rich.console import Console
from rich.table import box
from rich.table import Table
from typing import Literal
import shutil

"""
TO DO
- Add the amount of time I have to eat a treat after I finish the stint
- When showing stats I should be able to filter by which projects I was working on.
    - Be able to classify projects into different categories, and have the stats by default, show the default category
    - Also treats should be for specific categories of projects
    - Categories are essentially just new instances of the project, but I should be able to manage them with one script
- Add past weeks bar chart in summary which shows a row for the total time for each of the last max 10 weeks up to current week
- Verify week function - where you can specify a date or range of dates and gives you data accordingly
    - In the input it tells you the earliest date you can call to get week data
    - When lw is called just have a continuous input which can either take:
        - Single date - Show a single bar chart for each of the days in that week and then just a number for the total time spent
        - Date range - Shows a single bar chart with the total time spent for each of the weeks in the date range
    - This should be able to take any date from oldest log to current day. Just get the week for whatever the date is in
"""

TITLE = "Stint Tracker"

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

SETTINGS_PATH = os.path.join(SCRIPT_DIR, "data/settings.json")
LOGS_PATH = os.path.join(SCRIPT_DIR, "data/logs.json")
SUCCESS_PATH = os.path.join(SCRIPT_DIR, "sounds/success.mp3")


hour = 60 * 60
day = hour * 24
week = day * 7
year = day * 365
days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def time_to_seconds(time: str):
    """Converts YY:WW:DD:HH:MM:SS to seconds"""
    times = time.split(":")
    times.reverse()
    seconds = 0

    unit_to_seconds = [1, 60, hour, day, week, year]

    for i, t in enumerate(times):
        seconds += int(t) * unit_to_seconds[i]

    return seconds


def seconds_to_time(seconds: int):
    """Converts seconds to YY:WW:DD:HH:MM:SS format"""
    remaining = seconds
    units = []

    # Calculate each unit
    years = remaining // (year)
    remaining = remaining % (year)

    weeks = remaining // (week)
    remaining = remaining % (week)

    days = remaining // (day)
    remaining = remaining % (day)

    hours = remaining // (hour)
    remaining = remaining % (hour)

    minutes = remaining // 60
    seconds = remaining % 60

    # Build the time string
    if years > 0:
        units.append(str(years))
    if weeks > 0 or years > 0:
        units.append(str(weeks))
    if days > 0 or weeks > 0 or years > 0:
        units.append(str(days))
    if hours > 0 or days > 0 or weeks > 0 or years > 0:
        units.append(str(hours))
    if minutes > 0 or hours > 0 or days > 0 or weeks > 0 or years > 0:
        units.append(str(minutes).zfill(2))
    units.append(str(seconds).zfill(2))

    return ":".join(units).lstrip("0") if len(units) > 1 or int(units[0]) else "0"


def clear_print(text: str, lines_to_clear: int = 1):
    if lines_to_clear > 1:
        for _ in range(lines_to_clear - 1):
            print("\033[A\033[K", end="", flush=True)
    print(f"\033[K\r{' ' * 60}", end="", flush=True)
    print(f"\033[K\r{text}", end="", flush=True)


async def sleep_verbose(
    seconds,
    time_message="Time remaining",
    end="Done!",
    cancel_message="Timer canceled",
    return_on_cancel=False,
):
    print()
    try:
        end_time = time.time() + seconds
        while True:
            remaining = end_time - time.time()
            if round(remaining) <= 0:
                break
            clear_print(f"{time_message}: {seconds_to_time(round(remaining))}")
            try:
                await asyncio.sleep(1 + remaining - round(remaining))
            except asyncio.CancelledError:
                raise KeyboardInterrupt()
        clear_print(end)
        print()
    except KeyboardInterrupt:
        print()
        cancel_message and print(cancel_message)
        if return_on_cancel:
            return False
        exit()
    return True


async def stop_watch(
    elapsed_message="Elapsed time",
    stop_message="cancel",
    end_message: str | None = None,
    start_time=time.time(),
):
    print("\n")
    try:
        while True:
            elapsed_time = time.time() - start_time
            clear_print(
                f"{elapsed_message}: {seconds_to_time(round(elapsed_time))}\nPress ^C to {stop_message}: ",
                lines_to_clear=2,
            )
            try:
                await asyncio.sleep(max(0.1, 1 - (elapsed_time - round(elapsed_time))))
            except asyncio.CancelledError:
                raise KeyboardInterrupt()
    except KeyboardInterrupt:
        print()
        clear_print(
            f"{end_message + ' - ' if end_message else ''}Final time: {seconds_to_time(round(time.time() - start_time))}\n"
        )
    return round(time.time() - start_time)


def save_json(obj, path=SETTINGS_PATH):
    with open(path, "w") as file:
        json.dump(obj, file, indent=2)


def get_json(path=SETTINGS_PATH, default={}):
    try:
        with open(path, "r") as file:
            return json.load(file)
    except FileNotFoundError:
        with open(path, "w") as file:
            json.dump(default, file)
        return default


def get_logs() -> list[dict]:
    return get_json(LOGS_PATH, [])


async def start_stint_async():
    settings = get_json()
    logs = get_logs()

    selected: str = await questionary.select(
        "Select stint:",
        choices=[*settings["stint_options"], "Other"],
    ).ask_async()

    if selected == "Other":
        selected = input("Describe the task: ")
        add_task = input("Add task to stint options? (y/n) ")
        if add_task.lower().find("y") != -1:
            settings["stint_options"].append(selected)
            save_json(settings)

    # Show last stint info for same task if available
    last_stint = next((log for log in reversed(logs) if log["task"] == selected), None)
    if last_stint and last_stint.get("notes"):
        print()
        print_pretty(f"Notes from last time: {last_stint['notes']}")

    start_time = time.time()

    await sleep_verbose(
        time_to_seconds(settings["min_stint_time"]),
        "Time until valid",
        "Stint valid!",
        "Stint canceled",
    )
    try:
        await asyncio.gather(
            asyncio.to_thread(playsound, SUCCESS_PATH),
            stop_watch(
                stop_message="end the stint",
                end_message="Logging stint",
                start_time=start_time,
            ),
        )
    except asyncio.CancelledError:
        pass

    notes = input("\nNotes to future self (optional): ").strip()

    with open(LOGS_PATH, "r") as file:
        logs: list = json.load(file)
    logs.append(
        {
            "task": selected,
            "start": round(start_time),
            "duration": round(time.time() - start_time),
            "notes": notes or None,
        }
    )
    save_json(logs, LOGS_PATH)
    print("Stint Saved!\n")


def start_stint():
    try:
        asyncio.run(start_stint_async())
    except KeyboardInterrupt:
        pass


def clear_console():
    if sys.platform.startswith("win"):
        _ = os.system("cls")
    else:
        _ = os.system("clear")


# Printing


def print_pretty(text: str, indent: int = 2, padding: int = 2):
    """Prints text wrapped to terminal width with proper indentation and padding."""
    terminal_width = shutil.get_terminal_size().columns
    max_width = terminal_width - indent - padding

    words = text.split()
    current_line = []
    current_length = 0

    for word in words:
        word_length = len(word)
        if current_length + word_length + len(current_line) <= max_width:
            current_line.append(word)
            current_length += word_length
        else:
            print(" " * indent + " ".join(current_line))
            current_line = [word]
            current_length = word_length

    if current_line:
        print(" " * indent + " ".join(current_line))


def print_week(times: list[int], limit_first=False, limit_today=False):
    current_weekday = time.localtime(time.time()).tm_wday
    print_days = not limit_first
    for i, duration in enumerate(times):
        if duration:
            print_days = True
        if print_days and (not limit_today or i <= current_weekday):
            print(
                f"{days[i]}  -  {seconds_to_time(duration)}{'  <-- Today' if i == current_weekday and limit_today else ''}"
            )


def print_bar_chart(values, labels=None, max_width=50, title=None, show_values=True):
    """Prints a horizontal bar chart using Unicode block characters

    Args:
        values: List of numerical values
        labels: List of labels (optional)
        max_width: Maximum width of the bars in characters
        title: Chart title (optional)
        show_values: Whether to show numerical values at end of bars
    """
    if not values:
        return

    BLOCK = "█"
    max_val = max(values)

    labels = labels or [str(i + 1) for i in range(len(values))]
    label_width = max(len(str(label)) for label in labels)

    if title:
        print(f"\n{title}")

    for i, value in enumerate(values):
        if max_val == 0:
            bar_width = 0
        else:
            bar_width = int((value / max_val) * max_width)

        label = f"{labels[i]:>{label_width}}"

        value_display = f" {seconds_to_time(value)}" if show_values else ""

        print(f"{label} | {BLOCK * bar_width}{value_display}")


def print_rich_bar_chart(
    values,
    labels=None,
    max_width=50,
    title=None,
    justify_labels: Literal["left", "right"] = "left",
    start_at_label: int | None = None,
):
    console = Console()
    table = Table(title=title, show_header=False, box=None)

    max_val = max(values)

    for i, value in enumerate(values):
        if labels:
            if justify_labels == "left":
                idx = max(i, start_at_label) if start_at_label else i
            else:
                idx = (
                    (
                        min(len(labels), start_at_label)
                        if start_at_label
                        else len(labels)
                    )
                    - len(values)
                    + 1
                    + i
                )
            label = labels[max(min(idx, len(labels) - 1), 0)]
        else:
            label = str(i + 1)

        bar_width = int((value / max_val) * max_width) if max_val > 0 else 0
        table.add_row(
            f"{label:>3}",
            "│",
            "█" * bar_width,
            f"{seconds_to_time(value)}",
        )
    print()
    console.print(table)


def get_week_data(week_start, logs_list, is_first=False, is_last=False):
    daily_totals = []

    add_day = not is_first
    for i in range(time.localtime(time.time()).tm_wday + 1 if is_last else 7):
        day_start = week_start + (i * day)
        day_end = day_start + day
        day_logs = [log for log in logs_list if day_start <= log["start"] < day_end]
        total = sum(log["duration"] for log in day_logs)
        add_day = add_day or total
        add_day and daily_totals.append(total)

    return {
        "daily_totals": daily_totals,
        "total": sum(daily_totals),
        "start": week_start,
        "date": time.strftime("%Y-%m-%d", time.localtime(week_start)),
        "is_first": is_first,
        "is_last": is_last,
    }


def get_weeks_data(logs=get_logs(), num_weeks=None):
    """Gets week data for specified number of recent weeks, or all weeks if num_weeks is None"""
    if not logs:
        return []

    first_log = min(logs, key=lambda x: x["start"])

    now = time.time()
    today_start = time.mktime(time.localtime(now)[:3] + (0, 0, 0, 0, 0, -1))
    current_weekday = time.localtime(now).tm_wday
    current_week_start = today_start - (current_weekday * day)

    first_weekday = time.localtime(first_log["start"]).tm_wday
    first_week_start = time.mktime(
        time.localtime(first_log["start"])[:3] + (0, 0, 0, 0, 0, -1)
    ) - (first_weekday * day)

    total_weeks = max(1, int((current_week_start - first_week_start) / week) + 1)
    weeks_to_fetch = min(total_weeks, num_weeks) if num_weeks else total_weeks

    weeks_data = []
    for i in range(weeks_to_fetch):
        week_start = current_week_start - (i * week)
        week_logs = [
            log for log in logs if week_start <= log["start"] < week_start + week
        ]
        weeks_data.append(
            get_week_data(week_start, week_logs, i >= weeks_to_fetch - 1, i == 0)
        )
    weeks_data.reverse()
    return weeks_data


def get_total_duration(logs=get_logs()):
    return sum(log["duration"] for log in logs)


def show_all_week_averages(logs=get_logs()):
    weeks_data = get_weeks_data(logs)

    daily_sums = [0] * 7
    daily_counts = [0] * 7

    for week in weeks_data:
        offset = (
            (
                (time.localtime(time.time()).tm_wday + 1 if week["is_last"] else 7)
                - len(week["daily_totals"])
            )
            if week["is_first"]
            else 0
        )
        for i, total in enumerate(week["daily_totals"]):
            daily_sums[i + offset] += total
            daily_counts[i + offset] += 1

    averages = [
        round((daily_sums[i] / daily_counts[i])) if daily_counts[i] > 0 else 0
        for i in range(7)
    ]
    print_rich_bar_chart(averages, labels=days, title="Daily Averages")

    print(f"\nWeeks analyzed: {len(weeks_data)}")


def get_running_max(lst: list[int], run_num=1, return_current_run=False):
    max_value = 0
    running_value = 0
    running_num = 0
    for value in lst:
        if running_num < run_num:
            running_num += 1
            running_value += value

        if running_num >= run_num:
            max_value = max(max_value, running_value)
            running_num = 0
            running_value = 0

    if return_current_run:
        return {
            "max_value": max_value,
            "last_run": running_value if running_num else sum(lst[-run_num:]),
        }
    return max_value


def get_high_score(logs=get_logs(), unit: Literal["day", "week"] = "day", amount=1):
    weeks_data = get_weeks_data(logs)

    scores = []
    for week_data in weeks_data:
        if unit == "day":
            scores.extend(week_data["daily_totals"])
        else:
            scores.append(sum(week_data["daily_totals"]))

    result = get_running_max(scores, amount, True)

    return {
        "current": result["last_run"],
        "high_score": result["max_value"],
    }


def show_high_scores(logs=get_logs(), settings=get_json()):
    intervals = json.loads(json.dumps(settings["high_score_intervals"]))
    intervals.reverse()
    for interval in intervals:
        result = get_high_score(logs, interval["unit"], interval["amount"])
        print_rich_bar_chart(
            title=f'{interval["amount"]} {interval["unit"].capitalize()} High Score',
            values=[result["high_score"], result["current"]],
            labels=["High", "Current"],
        )


def show_summary():
    logs = get_logs()
    settings = get_json()

    weeks_data = get_weeks_data(logs, 2)

    show_all_week_averages(logs)

    print()
    show_high_scores(logs, settings)

    print()
    titles = ["This", "Last"][: len(weeks_data)]
    titles.reverse()
    for i, week_data in enumerate(weeks_data):
        print_rich_bar_chart(
            week_data["daily_totals"],
            labels=days,
            title=f"{titles[i]} Week's Activity",
            justify_labels="right",
            start_at_label=(
                time.localtime(time.time()).tm_wday if week_data["is_last"] else None
            ),
        )

    print(f"\nTotal duration: {seconds_to_time(get_total_duration(logs))}\n")


def show_week(logs=get_logs()):
    if not logs:
        print("\nNo logs found.")
        return

    # Get earliest date from logs
    earliest_date = time.strftime(
        "%Y-%m-%d", time.localtime(min(log["start"] for log in logs))
    )

    print(f"\nEnter a date (YYYY-MM-DD) or date range (YYYY-MM-DD:YYYY-MM-DD)")
    print(f"Earliest available date: {earliest_date}")
    date_input = input("> ").strip()

    if not date_input:
        return

    try:
        if ":" in date_input:
            # Handle date range
            start_date, end_date = date_input.split(":")
            start_timestamp = time.mktime(time.strptime(start_date, "%Y-%m-%d"))
            end_timestamp = time.mktime(time.strptime(end_date, "%Y-%m-%d"))

            if start_timestamp > end_timestamp:
                start_timestamp, end_timestamp = end_timestamp, start_timestamp

            # Adjust to start of weeks
            start_weekday = time.localtime(start_timestamp).tm_wday
            start_timestamp -= start_weekday * day

            # Get all weeks in range
            weeks_data = []
            current_timestamp = start_timestamp
            while current_timestamp <= end_timestamp:
                week_logs = [
                    log
                    for log in logs
                    if current_timestamp <= log["start"] < current_timestamp + week
                ]
                if week_logs:
                    weeks_data.append(
                        get_week_data(
                            current_timestamp,
                            week_logs,
                            is_first=current_timestamp == start_timestamp,
                            is_last=current_timestamp + week > end_timestamp,
                        )
                    )
                current_timestamp += week

            if not weeks_data:
                print("\nNo data found for this date range.")
                return

            # Show weekly totals bar chart
            print_rich_bar_chart(
                [week["total"] for week in weeks_data],
                labels=[week["date"] for week in weeks_data],
                title="Weekly Totals",
            )
            print(
                f"\nTotal time: {seconds_to_time(sum(week['total'] for week in weeks_data))}"
            )

        else:
            # Handle single date
            timestamp = time.mktime(time.strptime(date_input, "%Y-%m-%d"))
            weekday = time.localtime(timestamp).tm_wday
            week_start = timestamp - (weekday * day)

            week_logs = [
                log for log in logs if week_start <= log["start"] < week_start + week
            ]

            if not week_logs:
                print("\nNo data found for this week.")
                return

            week_data = get_week_data(week_start, week_logs)
            print_rich_bar_chart(
                week_data["daily_totals"],
                labels=days,
                title=f"Week of {week_data['date']}",
            )
            print(f"\nTotal time: {seconds_to_time(week_data['total'])}")

    except ValueError:
        print("\nInvalid date format. Please use YYYY-MM-DD.")


def show_logs(logs=get_logs()):
    if not logs:
        print("\nNo logs found.")
        return

    # Get unique tasks from logs
    tasks = sorted(set(log["task"] for log in logs))

    # Let user select task
    selected = questionary.select(
        "Select task to view:",
        choices=[*tasks, "All tasks"],
    ).ask()

    # Filter logs by selected task
    filtered_logs = (
        logs
        if selected == "All tasks"
        else [log for log in logs if log["task"] == selected]
    )
    if not filtered_logs:
        print("\nNo logs found for this task.")
        return

    # Ask for number of logs to show
    max_logs = len(filtered_logs)
    while True:
        try:
            num_logs = input(
                f"\nHow many recent logs to show? (1-{max_logs}, or press Enter for all): "
            ).strip()
            if not num_logs:  # Show all if empty
                break
            num_logs = int(num_logs)
            if 1 <= num_logs <= max_logs:
                filtered_logs = sorted(
                    filtered_logs, key=lambda x: x["start"], reverse=True
                )[:num_logs]

                break
            print(f"Please enter a number between 1 and {max_logs}")
        except ValueError:
            print("Please enter a valid number")

    # Group logs by date
    logs_by_date = {}
    for log in filtered_logs:
        date = time.strftime("%Y-%m-%d", time.localtime(log["start"]))
        if date not in logs_by_date:
            logs_by_date[date] = []
        logs_by_date[date].append(log)

    # Print logs grouped by date
    console = Console()
    for date in sorted(logs_by_date.keys()):
        weekday = time.strftime("%A", time.strptime(date, "%Y-%m-%d"))
        table = Table(title=f"{weekday}, {date}", show_header=True, box=box.ROUNDED)

        table.add_column("Time", justify="left", style="cyan")
        table.add_column("Duration", justify="right", style="green")
        if selected == "All tasks":
            table.add_column("Task", style="yellow")
        table.add_column("Notes", style="white")

        daily_total = 0
        for log in sorted(logs_by_date[date], key=lambda x: x["start"]):
            time_str = time.strftime("%I:%M %p", time.localtime(log["start"]))
            duration_str = seconds_to_time(log["duration"])
            daily_total += log["duration"]

            row = [
                time_str,
                duration_str + "\n",
                *([log["task"]] if selected == "All tasks" else []),
                log["notes"] + "\n" if log["notes"] else "",
            ]
            table.add_row(*row)

        table.add_row(
            "Total:",
            seconds_to_time(daily_total),
            *([""] if selected == "All tasks" else []),
            "",
            style="bold",
        )

        print()
        console.print(table)


def show_treats(logs=get_logs(), settings=get_json()):
    console = Console()
    print("\nTreat Summary\n")

    # Get total duration in hours for relevant periods
    total_hours = get_total_duration(logs) / 3600

    # Show total time treats
    if settings.get("total_time_treats"):
        table = Table(title="Total Time Treats", show_header=True)
        table.add_column("Hours Required")
        table.add_column("Progress")
        table.add_column("Treat")

        for treat in sorted(settings["total_time_treats"], key=lambda x: x["hours"]):
            progress = min(100, (total_hours / treat["hours"]) * 100)
            progress_bar = (
                f"[{'=' * int(progress/2)}{' ' * (50-int(progress/2))}] {progress:.1f}%"
            )
            table.add_row(
                str(treat["hours"]), progress_bar, treat["treat"]["description"]
            )
        console.print(table)
        print()

    # Show high score treats
    for interval in settings.get("high_score_intervals", []):
        if not interval.get("treats"):
            continue

        scores = get_high_score(logs, interval["unit"], interval["amount"])
        current_hours = scores["current"] / 3600

        title = f"{interval['amount']} {interval['unit'].capitalize()}"
        if interval["amount"] > 1:
            title += "s"
        table = Table(title=f"{title} Treats", show_header=True)
        table.add_column("Hours Required")
        table.add_column("Progress")
        table.add_column("Treat")

        for treat in sorted(interval["treats"], key=lambda x: x["hours"]):
            progress = min(100, (current_hours / treat["hours"]) * 100)
            progress_bar = (
                f"[{'=' * int(progress/2)}{' ' * (50-int(progress/2))}] {progress:.1f}%"
            )
            table.add_row(
                str(treat["hours"]), progress_bar, treat["treat"]["description"]
            )
        console.print(table)
        print()

    # Show basic treat if it exists
    if settings.get("treat"):
        print(f"Basic treat: {settings['treat']['description']}")
        print(f"(Available after completing a stint)")


def main():
    def show_help():
        print(f"\n{TITLE} - Available commands:\n")
        for c in commands:
            print(f"{c['code']}{(6 - len(c['code'])) * ' '}{c['help']}")
        print()

    commands = [
        {"code": "l", "help": "Show summary", "func": show_summary, "type": "stats"},
        {"code": "lw", "help": "Show week", "func": show_week, "type": "stats"},
        {"code": "lt", "help": "Show treats", "func": show_treats, "type": "stats"},
        {"code": "ll", "help": "Show logs", "func": show_logs, "type": "stats"},
        {"code": "s", "help": "Start stint", "func": start_stint, "type": "other"},
        {"code": "c", "help": "Clear console", "func": clear_console, "type": "other"},
        {
            "code": "h",
            "help": "Help",
            "func": show_help,
            "type": "other",
        },
    ]
    parser = argparse.ArgumentParser(description=TITLE, add_help=False)
    for command in commands:
        parser.add_argument(
            f"-{command['code']}", action="store_true", help=command["help"]
        )
    args = parser.parse_args()

    cmd = "h"
    for command in commands:
        if getattr(args, command["code"]):
            cmd = command["code"]
            break

    try:
        while True:
            for c in commands:
                if c["code"] == cmd:
                    c["func"]()
                    break
            cmd = input()
    except KeyboardInterrupt:
        print()
        exit()


if __name__ == "__main__":
    main()
