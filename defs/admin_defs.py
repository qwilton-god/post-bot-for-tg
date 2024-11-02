from telebot import types
import sqlite3
import time
from datetime import datetime as dt
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from configs.config import *
import defs.my_queue
from main import bot
from configs.config_data import *
import defs.posts
def about_post(post_id, user_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Проверяем, есть ли пост в очереди
    cursor.execute('SELECT * FROM queue WHERE post_id = ?', (post_id,))
    if cursor.fetchone() is None:
        bot.send_message(user_id, f'Пост с ID {post_id} не найден в очереди.')
        conn.close()
        return

    # Получаем данные о посте из таблицы posts
    cursor.execute('SELECT media_type, media_id, caption, username, text FROM posts WHERE id = ?', (post_id,))
    post_data = cursor.fetchone()

    # Получаем статус поста из таблицы queue
    cursor.execute('SELECT post_type FROM queue WHERE post_id = ?', (post_id,))
    queue_data = cursor.fetchone()

    if post_data and queue_data:
        media_type, media_ids, caption, username, text = post_data
        post_type = queue_data[0]  # Получаем тип поста из очереди
        status = 'Анон' if post_type == 'anon' else 'Дефолт'  # Определяем статус поста

        # Обработка медиа
        media_ids = media_ids.split(',')
        if media_type == 'photo':
            media = [InputMediaPhoto(media_id, caption) for media_id in media_ids]
            bot.send_media_group(user_id, media)
        elif media_type == 'video':
            media = [InputMediaVideo(media_id, caption) for media_id in media_ids]
            bot.send_media_group(user_id, media)
        elif media_type is None:
            bot.send_message(user_id, text)

        # Создаем разметку с кнопками
        markup = InlineKeyboardMarkup(row_width=3)
        markup.add(
            InlineKeyboardButton('Удалить', callback_data=f'about_delete_{post_id}'),
            InlineKeyboardButton('Опубликовать', callback_data=f'about_send_{post_id}'),
            InlineKeyboardButton('Сменить статус', callback_data=f'toggle_status_{post_id}'),  
            InlineKeyboardButton('Отмена', callback_data=f'about_remove')
        )
        
        # Отправляем сообщение с кнопками
        bot.send_message(user_id, f'Пост от @{username}, ID пользователя: {user_id}, Статус: {status}', reply_markup=markup)  
        return post_id

    conn.close()
def get_media_type(media_ids):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    media_type = None
    for media_id in media_ids:
        cursor.execute('SELECT media_type FROM posts WHERE media_id LIKE ?', ('%,' + media_id + ',',))
        media_type = cursor.fetchone()
        if media_type:
            break
    conn.close()
    return media_type[0] if media_type else None
def toggle_status(call):
    post_id = int(call.data.split('_')[2])
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    # Получаем текущий статус поста из очереди
    cursor.execute('SELECT post_type FROM queue WHERE post_id = ?', (post_id,))
    post_data = cursor.fetchone()

    if post_data:
        current_type = post_data[0]
        new_type = 'anon' if current_type == 'usual' else 'usual'  # Меняем статус на противоположный
        cursor.execute('UPDATE queue SET post_type = ? WHERE post_id = ?', (new_type, post_id))
        conn.commit()

        new_status_text = 'Анон' if new_type == 'anon' else 'Дефолт'

        # Получаем информацию о пользователе, который создал пост
        cursor.execute('SELECT username, user_id FROM posts WHERE id = ?', (post_id,))
        user_data = cursor.fetchone()

        if user_data:
            post_username, post_user_id = user_data

            # Обновляем сообщение с информацией о посте
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=f'Пост от @{post_username}, ID пользователя: {post_user_id}, Статус: {new_status_text}',
                reply_markup=call.message.reply_markup  # Сохраняем разметку кнопок
            )
        else:
            bot.send_message(call.from_user.id, f'Не удалось получить информацию о пользователе, который создал пост.')

    else:
        bot.send_message(call.from_user.id, f'Пост {post_id} не найден!')

    conn.close()  
def rufa(user_id):
    if user_id in delete_post_allowed:
        del delete_post_allowed[user_id]
    elif user_id in now_allowed:
        del now_allowed[user_id]
    elif user_id in unban_allowed:
        del unban_allowed[user_id]
    elif user_id in ban_allowed:
        del ban_allowed[user_id]
    elif user_id in about_allowed:
        del about_allowed[user_id]
    else:return

def list_blocked(call):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT user_id, username FROM blocked_users')
    rows = cursor.fetchall()
    
    if rows:
        message = "Список заблокированных пользователей:\n"
        for row in rows:
            user_id, username = row
            message += f"ID: {user_id}, Пользователь: @{username}\n"
    else:
        message = "Нет заблокированных пользователей."
    
    bot.send_message(call.message.chat.id, message)
    conn.close()
def list_queue(call):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    count = defs.my_queue.count_posts_in_queue()
    cursor.execute('SELECT post_id, user_id FROM queue ORDER BY post_date ASC')
    rows = cursor.fetchall()
    
    if rows:
        message = f"Всего постов: {count}\n"
        
        for row in rows:
            post_id, user_id = row
            message += f"Пост ID: {post_id}, Пользователь ID: {user_id}\n"

        button = types.InlineKeyboardButton(text="Подробнее о посте...", callback_data="about_posts")
        markup = types.InlineKeyboardMarkup().add(button) 

        bot.send_message(call.message.chat.id, message, reply_markup=markup)  
    else:
        message = "Очередь пуста."
        bot.send_message(call.message.chat.id, message)
    
    conn.close()
def add_to_admin(user_id, chat_id):
    if not user_id.isdigit():
        bot.send_message(chat_id, 'ID пользователя должен состоять только из цифр.')
        return

    with sqlite3.connect('database.db') as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM admins WHERE user_id = ?", (user_id,))
        if cursor.fetchone() is not None:
            bot.send_message(chat_id, f'Пользователь с ID {user_id} уже находится в списке администрации.')
            return

        cursor.execute("INSERT INTO admins (id, user_id) VALUES (NULL, ?)", (user_id,))
        conn.commit()
        bot.send_message(chat_id, f'Пользователь с ID {user_id} был добавлен в список администрации.')
def ban_user(user_id, chat_id):
    if not user_id.isdigit():
        bot.send_message(chat_id, 'ID пользователя должен состоять только из цифр.')
        return
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    
    # Проверяем, есть ли пользователь в таблице заблокированных пользователей
    cursor.execute('SELECT * FROM blocked_users WHERE user_id = ?', (user_id,))
    if cursor.fetchone():
        bot.send_message(chat_id, f'Пользователь с ID {user_id} уже заблокирован.')
    else:
        # Добавляем пользователя в таблицу заблокированных пользователей
        cursor.execute('INSERT INTO blocked_users (user_id) VALUES (?)', (user_id,))
        conn.commit()
        bot.send_message(chat_id, f'Пользователь с ID {user_id} был заблокирован.')
    
    conn.close()
def delete_post_from_queue(post_id, chat_id): 
    if not post_id.isdigit(): 
        bot.send_message(chat_id, 'ID пользователя должен состоять только из цифр.') 
        return 
    conn = sqlite3.connect('database.db') 
    cursor = conn.cursor() 

    cursor.execute('SELECT * FROM queue WHERE post_id = ? ', (post_id,)) 
    if cursor.fetchone(): 
        cursor.execute('DELETE FROM queue WHERE post_id = ? ', (post_id,)) 
        conn.commit() 
        bot.send_message(chat_id, f'Пост с ID {post_id} был удален из очереди.') 
    else: 
        bot.send_message(chat_id, f'Пост с ID {post_id} не найден в очереди.') 

    conn.close()
def send_from_queue_by_post_id(post_id):
    print(post_id)
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute('SELECT post_type FROM queue WHERE post_id = ?', (post_id,))
        row = cursor.fetchone()
        if row:
            post_type = row[0]
            cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
            post_data = cursor.fetchone()
            if post_data:
                if post_type == 'usual':
                    try:
                        defs.posts.send_post_usual(post_id)
                        cursor.execute('DELETE FROM queue WHERE post_id = ?', (post_id,))
                        conn.commit()
                    except Exception as e:
                        print("Error sending post from queue (usual):", e)
                        retry_delay = 1
                        for i in range(5):  # Retry up to 5 times
                            time.sleep(retry_delay)
                            try:
                                defs.posts.send_post_usual(post_id)
                                cursor.execute('DELETE FROM queue WHERE post_id = ?', (post_id,))
                                conn.commit()
                                break
                            except Exception as e:
                                print("Error sending post from queue (usual, retry {}): {}".format(i+1, e))
                                retry_delay *= 2  # Exponential backoff
                elif post_type == 'anon':
                    try:
                        defs.posts.send_to_post_channel(post_id)
                        cursor.execute('DELETE FROM queue WHERE post_id = ?', (post_id,))
                        conn.commit()
                    except Exception as e:
                        print("Error sending post from queue (anon):", e)
                        retry_delay = 1
                        for i in range(5):  # Retry up to 5 times
                            time.sleep(retry_delay)
                            try:
                                defs.posts.send_to_post_channel(post_id)
                                cursor.execute('DELETE FROM queue WHERE post_id = ?', (post_id,))
                                conn.commit()
                                break
                            except Exception as e:
                                print("Error sending post from queue (anon, retry {}): {}".format(i+1, e))
                                retry_delay *= 2  # Exponential backoff
    except sqlite3.Error as e:
        print("Error connecting to database:", e)
    finally:
        conn.close()