# Telegram Task Management Bot

A production-ready Telegram bot for managing tasks with deadlines and employee assignments. Built with Python and SQLite, featuring an intuitive inline keyboard interface for seamless task management.

## Features

- **Task Creation**: Add tasks with descriptions, deadlines, and employee assignments
- **Task Filtering**: View all tasks, active tasks, completed tasks, or overdue tasks
- **Task Management**: Mark tasks as complete or delete them via interactive buttons
- **Smart Date Parsing**: Supports both full (`DD.MM.YYYY`) and short (`DD.MM.YY`) date formats
- **Employee Assignment**: Assign tasks to employees using usernames or names
- **Status Tracking**: Visual status indicators (✅ Completed, ⏰ Overdue, 🟢 In progress)
- **Automatic Sorting**: Tasks are automatically sorted by deadline
- **Persistent Storage**: All data stored in SQLite database

## Tech Stack

- **Python** 3.8+
- **python-telegram-bot** >= 22.5
- **python-dotenv** >= 1.2.0
- **SQLite3** (built-in)

## Installation

### Prerequisites

- Python 3.8 or higher
- pip package manager

### Setup Steps

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd tgBot
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Create a Telegram bot**:
   - Open Telegram and search for [@BotFather](https://t.me/BotFather)
   - Send `/newbot` command
   - Follow the instructions to create your bot
   - Copy the bot token you receive

4. **Configure environment variables**:
   - Create a `.env` file in the project root
   - Add your bot token:
     ```
     BOT_TOKEN=your_bot_token_here
     ```

5. **Run the bot**:
   ```bash
   python main.py
   ```

## Environment Variables

The bot requires the following environment variable:

| Variable | Description | Required |
|----------|-------------|----------|
| `BOT_TOKEN` | Telegram bot token from BotFather | Yes |

**Security Note**: The `.env` file is included in `.gitignore` to prevent accidentally committing sensitive tokens to version control. Never commit your bot token to a public repository.

## Usage

### Starting the Bot

After launching the bot, find it in Telegram and send `/start` to begin.

### Commands

| Command | Description |
|---------|-------------|
| `/start` or `/menu` | Show main menu with navigation buttons |
| `/help` | Display help information and available commands |
| `/add_task` | Show instructions for adding a new task |
| `/list_tasks` | Display task list with filtering options |
| `/complete_task [ID]` | Mark a task as completed (e.g., `/complete_task 1`) |
| `/delete_task [ID]` | Delete a task (e.g., `/delete_task 1`) |

### Adding Tasks

Send a message to the bot in the following format:

```
Задание: Подготовить отчет
Дедлайн: 25.12.2024
Сотрудник: @ivan_petrov
```

**Format Requirements**:
- `Задание:` - Task description (required)
- `Дедлайн:` - Deadline date (required)
- `Сотрудник:` - Employee username or name (optional)

**Date Formats Supported**:
- Full format: `DD.MM.YYYY` (e.g., `25.12.2024`)
- Short format: `DD.MM.YY` (e.g., `25.12.24`)

**Examples**:

```
Задание: Проверить код
Дедлайн: 10.01.2026
Сотрудник: @developer
```

```
Задание: Обновить документацию
Дедлайн: 15.01.26
```

You can also mention employees directly using `@username` in the message, and the bot will automatically detect and assign them.

### Task Management

The bot provides an interactive inline keyboard interface:

- **View Tasks**: Filter by all, active, completed, or overdue tasks
- **Complete Tasks**: Click "✅ Выполнить" button on any active task
- **Delete Tasks**: Click "🗑️ Удалить" button on any task
- **Navigation**: Use "◀️ Главное меню" to return to the main menu

## Database

The bot uses SQLite for data persistence. The database file (`tasks.db`) is automatically created on first run in the project root directory.

### Database Schema

**Table: `tasks`**

| Column | Type | Description |
|--------|------|-------------|
| `id` | INTEGER PRIMARY KEY | Auto-incrementing unique identifier |
| `task` | TEXT NOT NULL | Task description |
| `deadline` | TEXT NOT NULL | Deadline date in `DD.MM.YYYY` format |
| `employee` | TEXT NOT NULL | Employee username or name |
| `completed` | INTEGER NOT NULL DEFAULT 0 | Completion status (0 = incomplete, 1 = complete) |
| `created_at` | TEXT NOT NULL | Creation timestamp in `DD.MM.YYYY HH:MM` format |

### Database File

- **Location**: `tasks.db` (project root)
- **Auto-creation**: Created automatically on first run
- **Backup**: The database file is included in `.gitignore` to prevent committing user data

## Project Structure

```
tgBot/
├── main.py              # Main bot application
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (not in git)
├── tasks.db            # SQLite database (not in git)
├── .gitignore          # Git ignore rules
└── README.md           # This file
```

## Security Notes

- **Never commit sensitive data**: The `.env` file and `tasks.db` are excluded from version control via `.gitignore`
- **Protect your bot token**: Keep your `BOT_TOKEN` secure and never share it publicly
- **Database security**: The SQLite database contains user data and should be backed up regularly

## License

This project is open source and available for educational and commercial use.

## Contributing

Contributions, issues, and feature requests are welcome. Please feel free to submit a pull request or open an issue.
