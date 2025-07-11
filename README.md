# Telegram Medicine Reminder Bot

This is a Telegram bot that allows users to set, list, and stop medicine reminders with customizable intervals. The bot uses SQLite for persistent storage, ensuring that reminders are saved between restarts. APScheduler is used to schedule periodic notifications. Inline keyboard buttons provide an intuitive interface for users to interact with the bot. Additionally, a click counter feature tracks user interactions and responds after 5 clicks to improve user experience.

---

## Features

- Set reminders for medicines with user-defined intervals (in minutes)
- List all active reminders
- Stop specific reminders
- Persistent storage using SQLite database
- Scheduled notifications with APScheduler
- Inline keyboard navigation
- Click counter that responds after 5 interactions

---

## Technologies Used

- Python 3.8+
- aiogram (Telegram bot framework)
- SQLite3 for database
- APScheduler for scheduling tasks
- asyncio for asynchronous programming

---

## Installation and Usage

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/telegram-medicine-reminder-bot.git
   cd telegram-medicine-reminder-bot
