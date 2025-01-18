# Stint Tracker

Gamify your life with a command-line productivity tool that helps you track work sessions and maintain motivation through a customizable reward system.

## Features

- **Timed Work Sessions**: Start tracked work sessions with a minimum required duration
- **Project Management**: Choose from customizable project list and leave notes for your next work session
- **Progress Tracking**:
  - Daily and weekly activity visualization
  - Running averages for each day of the week
  - High score tracking across multiple time intervals
- **Reward System**:
  - Earn treats for completing individual stints
  - Unlock special rewards for reaching time-based milestones
  - Track progress towards daily, weekly, and total-time achievement goals

## Setup

1. Clone the repository
2. Install required dependencies:

```bash
pip install playsound questionary rich
```

3. Configure your `data/settings.json` file in accordance with `data/settings.example.json`
4. Run the application:

```bash
python main.py
```

## Usage

1. Start the application
2. Use command `s` to begin a new stint
3. Select or enter your task
4. Complete the minimum required time
5. Continue working until you're ready to end the stint
6. Use other commands to track your progress and view statistics

## Commands

- `l` - Show activity summary with charts and statistics
- `lw` - Display detailed week view
- `lt` - View progress towards treats
- `ll` - View recent stint logs
- `t` - View and redeem available treats
- `s` - Start a new stint
- `c` - Clear console
- `h` - Show help menu

## Configuration

The app uses a `data/settings.json` file to manage:

- Minimum stint duration
- Available projects
- Time of day past which stints won't be tracked: `end_stint_at`
- Reward definitions including:
  - Individual stint rewards
  - Cumulative time rewards
  - High score interval rewards
  - Grace periods for claiming rewards

## Notes

- Time is represted in the following format: YY:WW:DD:HH:MM:SS
- The timer will add a newline after each update if the terminal window is not wide enough

## Requirements

- Python 3.x
- Required packages: playsound, questionary, rich

## License

MIT License
