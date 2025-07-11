import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.filters import Command
from aiogram import Bot, Dispatcher, Router, types
from aiogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from apscheduler.schedulers.asyncio import AsyncIOScheduler

TOKEN = "8161180643:AAG7BTHgmH6xGzAbTiJC5AsePUj5YmOJ2Rw"

bot = Bot(token=TOKEN)
dp = Dispatcher()
router = Router()
scheduler = AsyncIOScheduler()

# --- DATABASE SETUP ---

conn = sqlite3.connect("reminders.db")
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS reminders (
    user_id INTEGER,
    medicine_name TEXT,
    interval INTEGER,
    PRIMARY KEY(user_id, medicine_name)
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS click_counters (
    user_id INTEGER PRIMARY KEY,
    count INTEGER
)
""")

conn.commit()


# --- DB HELPERS ---

def add_reminder_db(user_id: int, medicine_name: str, interval: int):
    cursor.execute("""
    INSERT OR REPLACE INTO reminders (user_id, medicine_name, interval) VALUES (?, ?, ?)
    """, (user_id, medicine_name, interval))
    conn.commit()


def remove_reminder_db(user_id: int, medicine_name: str):
    cursor.execute("""
    DELETE FROM reminders WHERE user_id = ? AND medicine_name = ?
    """, (user_id, medicine_name))
    conn.commit()


def get_reminders_db(user_id: int):
    cursor.execute("""
    SELECT medicine_name, interval FROM reminders WHERE user_id = ?
    """, (user_id,))
    return cursor.fetchall()


def get_all_reminders():
    cursor.execute("""
    SELECT user_id, medicine_name, interval FROM reminders
    """)
    return cursor.fetchall()


def get_click_count(user_id: int):
    cursor.execute("SELECT count FROM click_counters WHERE user_id = ?", (user_id,))
    res = cursor.fetchone()
    return res[0] if res else 0


def set_click_count(user_id: int, count: int):
    cursor.execute("""
    INSERT INTO click_counters (user_id, count) VALUES (?, ?)
    ON CONFLICT(user_id) DO UPDATE SET count=excluded.count
    """, (user_id, count))
    conn.commit()


# --- SCHEDULER HELPERS ---

async def send_reminder(user_id: int, medicine_name: str):
    await bot.send_message(user_id, f"💊 Time to take your medicine: {medicine_name}")


def schedule_reminder(user_id: int, medicine_name: str, interval_minutes: int):
    job_id = f"{user_id}_{medicine_name}"
    scheduler.add_job(
        send_reminder,
        "interval",
        minutes=interval_minutes,
        args=[user_id, medicine_name],
        id=job_id,
        replace_existing=True,
    )


def remove_reminder(user_id: int, medicine_name: str):
    job_id = f"{user_id}_{medicine_name}"
    try:
        scheduler.remove_job(job_id)
    except Exception:
        pass


def load_all_reminders_to_scheduler():
    for user_id, medicine_name, interval in get_all_reminders():
        schedule_reminder(user_id, medicine_name, interval)


# --- INLINE KEYBOARD ---

def main_menu_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Set reminder", callback_data="set")],
        [InlineKeyboardButton(text="My reminders", callback_data="list")],
        [InlineKeyboardButton(text="Stop reminder", callback_data="stop")]
    ])


# --- HANDLERS ---

@router.message(Command("start"))
async def start(message: types.Message):
    # Скидаємо лічильник кліків при новому старті
    set_click_count(message.from_user.id, 0)
    await message.answer("👋 Hi! What do you want to do?", reply_markup=main_menu_keyboard())


@router.callback_query()
async def handle_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    count = get_click_count(user_id)

    # Збільшуємо лічильник на 1
    count += 1
    set_click_count(user_id, count)

    # Якщо 5 кліків — відповідаємо і скидаємо лічильник, повертаємо меню
    if count >= 5:
        await callback.message.answer("🎉 You clicked 5 times! Here's the main menu again.", reply_markup=main_menu_keyboard())
        set_click_count(user_id, 0)
        await callback.answer()
        return

    data = callback.data

    if data == "set":
        await callback.message.answer("Send me your reminder in format:\n`MedicineName interval_in_minutes`\nExample:\n`Aspirin 60`")
    elif data == "list":
        meds = get_reminders_db(user_id)
        if not meds:
            await callback.message.answer("❌ You don't have any reminders.")
        else:
            text = "💊 Your active reminders:\n"
            for med, interval in meds:
                text += f"- {med} every {interval} min\n"
            await callback.message.answer(text)
    elif data == "stop":
        meds = get_reminders_db(user_id)
        if not meds:
            await callback.message.answer("❌ No active reminders to stop.")
        else:
            buttons = [[InlineKeyboardButton(text=med, callback_data=f"del:{med}")] for med, _ in meds]
            markup = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback.message.answer("🛑 Select medicine to stop:", reply_markup=markup)
    elif data.startswith("del:"):
        med_name = data.split(":", 1)[1]
        remove_reminder(user_id, med_name)
        remove_reminder_db(user_id, med_name)
        await callback.message.answer(f"✅ Reminder for {med_name} has been stopped.")
    else:
        await callback.answer()  # To avoid hanging

    await callback.answer()


@router.message()
async def handle_set_command(message: Message):
    try:
        parts = message.text.strip().split(maxsplit=1)
        if len(parts) != 2:
            raise ValueError
        name = parts[0]
        interval = int(parts[1])
        user_id = message.from_user.id

        schedule_reminder(user_id, name, interval)
        add_reminder_db(user_id, name, interval)

        await message.answer(f"✅ Reminder set for {name} every {interval} minutes.", reply_markup=main_menu_keyboard())

        # Скидаємо лічильник кліків після успішної установки
        set_click_count(user_id, 0)

    except Exception:
        await message.answer("❌ Please use the format: `MedicineName 60`", reply_markup=main_menu_keyboard())


# --- MAIN ---

async def main():
    scheduler.start()
    load_all_reminders_to_scheduler()
    dp.include_router(router)
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
