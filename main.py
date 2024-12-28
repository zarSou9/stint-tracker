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
from rich.table import Table
from typing import Literal


"""
TO DO
- Add past weeks bar chart in summary which shows a row for the total time for each of the last max 10 weeks up to current week
- Add treat summary which insentivizes more treats, and shows progress towards each treat
- Add week functionality where you can specify a date or range of dates and gives you data accordingly
    - In the input it tells you the earliest date you can call to get week data
    - When lw is called just have a continuous input which can either take:
        - Single date - Show a single bar chart for each of the days in that week and then just a number for the total time spent
        - Date range - Shows a single bar chart with the total time spent for each of the weeks in the date range
    - This should be able to take any date from oldest log to current day. Just get the week for whatever the date is in
"""

TITLE = "Stint Tracker"
SETTINGS_PATH = "/Users/mylesheller/Library/Mobile Documents/com~apple~CloudDocs/Git/stint-tracker/settings.json"
LOGS_PATH = "/Users/mylesheller/Library/Mobile Documents/com~apple~CloudDocs/Git/stint-tracker/logs.json"

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
            print("\033[A\033[K", end="")
    print(f"\033[K\r{text}", end="", flush=True)


async def sleep_verbose(
    seconds,
    time_message="Time remaining",
    end="Done!",
    cancel_message="Timer canceled",
    return_on_cancel=False,
):
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
    stop_code="c",
    start_time=time.time(),
):
    async def get_input():
        while True:
            user_input = await ainput()
            if user_input.lower() == stop_code.lower():
                return True

    input_task = asyncio.create_task(get_input())
    print()
    try:
        while not input_task.done():
            elapsed_time = time.time() - start_time
            sys.stdout.write(
                f"\033[A\033[K\r{elapsed_message}: {seconds_to_time(round(elapsed_time))}\nEnter {stop_code} to {stop_message}: "
            )
            sys.stdout.flush()
            await asyncio.sleep(max(0.1, 1 - (elapsed_time - round(elapsed_time))))
    finally:
        if not input_task.done():
            input_task.cancel()

    # Final output
    sys.stdout.write(
        f"\r{end_message + ' - ' if end_message else ''}Final time: {seconds_to_time(round(time.time() - start_time))}\n"
    )
    sys.stdout.flush()


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
    selected: str = await questionary.select(
        "Select stint:",
        choices=[*settings["stint_options"], "Other"],
    ).ask_async()

    details = None
    if selected == "Other":
        selected = input("Describe the task: ")
        add_task = input("Add task to stint options? (y/n) ")
        if add_task.lower().find("y") != -1:
            settings["stint_options"].append(selected)
            save_json(settings)
    else:
        details = input("Add additional details (optional): ")

    start_time = time.time()

    await sleep_verbose(
        time_to_seconds(settings["min_stint_time"]),
        "Time until valid",
        "Stint valid!",
        "Stint canceled",
    )
    await asyncio.gather(
        asyncio.to_thread(playsound, "success.mp3"),
        stop_watch(
            stop_message="end the stint",
            end_message="Logging stint",
            stop_code="s",
            start_time=start_time,
        ),
    )

    with open(LOGS_PATH, "r") as file:
        logs: list = json.load(file)
    logs.append(
        {
            "task": selected,
            "details": details or None,
            "start": round(start_time),
            "duration": round(time.time() - start_time),
        }
    )
    save_json(logs, LOGS_PATH)


def start_stint():
    asyncio.run(start_stint_async())


def clear_console():
    if sys.platform.startswith("win"):
        _ = os.system("cls")
    else:
        _ = os.system("clear")


# Printing


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


def show_week(id: str):
    pass


def main():
    def show_help():
        print(f"\n{TITLE} - Available commands:\n")
        for c in commands:
            print(f"{c['code']}{(6 - len(c['code'])) * ' '}{c['help']}")
        print()

    commands = [
        {"code": "l", "help": "Show summary", "func": show_summary, "type": "stats"},
        {
            "code": "lw",
            "help": "Show week",
            "func": show_summary,
            "type": "stats",
        },
        {"code": "lt", "help": "Show treats", "func": show_summary, "type": "stats"},
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
