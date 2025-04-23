"""
Post Bot - Telegram бот для управления постами и публикациями.
Главная точка входа в приложение.
"""
import threading
import sqlite3
import telebot
from configs.config import TOKEN, ADMIN_CHANNEL_ID, POST_CHANNEL_ID
from configs.config_data import DATABASE_NAME

# Инициализация экземпляра бота
bot = telebot.TeleBot(TOKEN)

# Инициализация базы данных
def initialize_database():
    """Создание таблиц базы данных, если они не существуют."""
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()

    # Таблица для хранения постов
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

    # Таблица для заблокированных пользователей
    cursor.execute('''CREATE TABLE IF NOT EXISTS blocked_users (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        username TEXT,
        is_blocked BOOLEAN DEFAULT FALSE,
        blocked_reason TEXT,
        block_date DATETIME
    )''')

    # Таблица для администраторов
    cursor.execute('''CREATE TABLE IF NOT EXISTS admins (
        id INTEGER PRIMARY KEY,
        user_id INTEGER,
        username TEXT,
        level INTEGER
    )''')

    # Таблица для очереди постов
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


# Импорт обработчиков и других модулей
from handlers.handlers import *
from handlers.callbacks_query import *
import defs.my_queue


if __name__ == '__main__':
    # Инициализация базы данных
    initialize_database()
    
    # Запуск планирования постов
    defs.my_queue.schedule_posts()
    defs.my_queue.check_queue_and_schedule()

    # Запуск планировщика в отдельном потоке
    scheduler_thread = threading.Thread(target=defs.my_queue.run_scheduler)
    scheduler_thread.daemon = True
    scheduler_thread.start()
    
    print("Бот запущен!")
    bot.infinity_polling()