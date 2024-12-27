import argparse
import time
import asyncio
from playsound import playsound
import json
from aioconsole import ainput
import questionary
import sys
import os


TITLE = "Stint Tracker"
SETTINGS_PATH = "/Users/mylesheller/Library/Mobile Documents/com~apple~CloudDocs/Git/stint-tracker/settings.json"
LOGS_PATH = "/Users/mylesheller/Library/Mobile Documents/com~apple~CloudDocs/Git/stint-tracker/logs.json"

hour = 60 * 60
day = hour * 24
week = day * 7
year = day * 365


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
    else:
        print(f"\r{' ' * 100}", end="")
    print(f"\r{text}", end="")


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


async def start_stint_async():
    with open(SETTINGS_PATH, "r") as file:
        settings = json.load(file)

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


def get_week_data(week_start, logs_list, is_first=False):
    daily_totals = []
    for i in range(7):
        day_start = week_start + (i * day)
        day_end = day_start + day
        day_logs = [log for log in logs_list if day_start <= log["start"] < day_end]
        daily_totals.append(sum(log["duration"] for log in day_logs))

    return {
        "daily_totals": daily_totals,
        "total": sum(daily_totals),
        "start": week_start,
        "is_first": is_first,
    }


def get_all_week_averages(logs_list):
    """Gets average daily totals across all weeks since first log"""


def get_recent_weeks_data(logs_list, num_weeks=None):
    """Gets week data for specified number of recent weeks, or all weeks if num_weeks is None"""
    if not logs_list:
        return []

    first_log = min(logs_list, key=lambda x: x["start"])

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
            log for log in logs_list if week_start <= log["start"] < week_start + week
        ]
        weeks_data.append(get_week_data(week_start, week_logs, not i))

    return weeks_data


def show_stats():
    with open(LOGS_PATH, "r") as file:
        logs: list = json.load(file)

    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Get all weeks data
    weeks_data = get_recent_weeks_data(logs)

    # Show last complete week if it exists
    if len(weeks_data) > 1:
        last_week = weeks_data[1]  # Index 1 because 0 is current week
        print("\n\n\nLast week:")
        for i, duration in enumerate(last_week["daily_totals"]):
            print(f"{days[i]}  -  {seconds_to_time(duration)}")
        print(f"\nLast week total: {seconds_to_time(last_week['total'])}")

    # Show current week
    this_week = weeks_data[0]
    current_weekday = time.localtime(time.time()).tm_wday
    print("\nThis week:")
    for i, duration in enumerate(this_week["daily_totals"]):
        if i <= current_weekday:
            print(
                f"{days[i]}  -  {seconds_to_time(duration)}{'  <-- Today' if i == current_weekday else ''}"
            )
    print(f"\nThis week total: {seconds_to_time(this_week['total'])}")


def main():
    def show_help():
        print(f"\n{TITLE} - Available commands:\n")
        for c in commands:
            print(f"{c['code']}{(6 - len(c['code'])) * ' '}{c['help']}")
        print()

    commands = [
        {"code": "l", "help": "Show summary", "func": show_stats, "type": "stats"},
        {
            "code": "lw",
            "help": "Show week avgs",
            "func": show_stats,
            "type": "stats",
        },
        {"code": "lt", "help": "Show treats", "func": show_stats, "type": "stats"},
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
