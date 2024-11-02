# main.py
import telebot
from configs.config import TOKEN, ADMIN_CHANNEL_ID, POST_CHANNEL_ID
import sqlite3
import threading

# Создаем экземпляр бота
bot = telebot.TeleBot(TOKEN)

# Инициализируем базу данных
conn = sqlite3.connect('database.db')
cursor = conn.cursor()

# Создаем необходимые таблицы
cursor.execute('''CREATE TABLE IF NOT EXISTS posts (
    id INTEGER PRIMARY KEY,
    media_type TEXT,
    media_id TEXT,
    caption TEXT,
    text TEXT,
    user_id INTEGER,
    username TEXT,
    post_date DATETIME,
    approved BOOLEAN DEFAULT FALSE,
    rejected BOOLEAN DEFAULT FALSE
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS blocked_users (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    username TEXT,
    is_blocked BOOLEAN DEFAULT FALSE,
    blocked_reason TEXT,
    block_date DATETIME
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
    id INTEGER PRIMARY KEY,
    user_id INTEGER,
    username TEXT,
    level INTEGER
)''')

cursor.execute('''CREATE TABLE IF NOT EXISTS queue (
    post_id INTEGER PRIMARY KEY,
    user_id INTEGER,
    username TEXT,
    post_date DATETIME,
    post_type TEXT,
    author_id INTEGER
)''')

conn.commit()
conn.close()


from handlers.handlers import *
from handlers.callbacks_query import *
import defs.my_queue

if __name__ == '__main__':

    defs.my_queue.schedule_posts()
    defs.my_queue.check_queue_and_schedule()

    scheduler_thread = threading.Thread(target=defs.my_queue.run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    # Запускаем бота
    print("Bot started!")
    bot.infinity_polling()