# Stint Tracker

A command-line productivity tool that helps you track work sessions and maintain motivation through a customizable reward system.

## Features

- **Timed Work Sessions**: Start tracked work sessions with a minimum required duration
- **Flexible Task Categories**: Choose from preset tasks or add custom ones on the fly
- **Progress Tracking**:
  - Daily and weekly activity visualization
  - Running averages for each day of the week
  - High score tracking across multiple time intervals
- **Reward System**:
  - Earn treats for completing individual stints
  - Unlock special rewards for reaching time-based milestones
  - Track progress towards daily, weekly, and total-time achievement goals

## Commands

- `l` - Show activity summary with charts and statistics
- `lw` - Display detailed week view
- `lt` - View available treats and progress
- `s` - Start a new stint
- `c` - Clear console
- `h` - Show help menu

## Configuration

The app uses a `settings.json` file to manage:

- Minimum stint duration
- Available task categories
- Reward definitions including:
  - Individual stint rewards
  - Cumulative time rewards
  - High score interval rewards
  - Grace periods for claiming rewards

### Sample Settings Structure

```json
{
    "min_stint_time": "20:25",
    "stint_options": ["Task 1", "Task 2"],
    "treat": {
        "description": "Basic reward",
        "grace_period": "5:00"
    },
    "total_time_treats": [...],
    "high_score_intervals": [...]
}
```

## Installation

1. Clone the repository
2. Install required dependencies:

```bash
pip install playsound questionary rich
```

3. Configure your `settings.json` file
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

## Notes

- The timer will add a newline after each update if the terminal window is not wide enough

## Requirements

- Python 3.x
- Required packages: playsound, questionary, rich

## License

MIT License
