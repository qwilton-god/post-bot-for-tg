
import telebot
from telebot import types
import sqlite3
import time
from datetime import datetime as dt
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from configs.config import *
from configs.config_data import DATABASE_NAME
bot = telebot.TeleBot(TOKEN, parse_mode=None)


def check_user_in_queue(user_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM queue WHERE user_id = ?', (user_id,))
    exists = cursor.fetchone() is not None  # Проверяем, есть ли запись
    conn.close()
    return exists 
def send_to_post_channel(post_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT media_type, media_id, caption, username, text FROM posts WHERE id = ?', (post_id,))
    post_data = cursor.fetchone()
    conn.close()
    if post_data:
        media_type, media_ids, caption, username, text = post_data
        media_ids = media_ids.split(',')

        if media_type == 'photo':
            media = [InputMediaPhoto(media_id, caption=caption if i == 0 else None) for i, media_id in enumerate(media_ids)]
            try:
                bot.send_media_group(POST_CHANNEL_ID, media)
            except Exception as e:
                print("Error sending media group:", e)
        elif media_type == 'video':
            media = [InputMediaVideo(media_id, caption=caption if i == 0 else None) for i, media_id in enumerate(media_ids)]
            try:
                bot.send_media_group(POST_CHANNEL_ID, media)
            except Exception as e:
                print("Error sending media group:", e)
        elif media_type is None:
            bot.send_message(POST_CHANNEL_ID, text)

def send_from_queue():
    try:
        conn = sqlite3.connect(DATABASE_NAME)
        cursor = conn.cursor()
        cursor.execute('SELECT post_id, post_type FROM queue ORDER BY post_date ASC LIMIT 1')
        row = cursor.fetchone()
        if row:
            post_id, post_type = row
            cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
            post_data = cursor.fetchone()
            if post_data:
                if post_type == 'usual':
                    try:
                        send_post_usual(post_id)
                        cursor.execute('DELETE FROM queue WHERE post_id = ?', (post_id,))
                        conn.commit()
                    except Exception as e:
                        print("Error sending post from queue (usual):", e)
                        retry_delay = 1
                        for i in range(5):  # Retry up to 5 times
                            time.sleep(retry_delay)
                            try:
                                send_post_usual(post_id)
                                cursor.execute('DELETE FROM queue WHERE post_id = ?', (post_id,))
                                conn.commit()
                                break
                            except Exception as e:
                                print("Error sending post from queue (usual, retry {}): {}".format(i+1, e))
                                retry_delay *= 2  # Exponential backoff
                elif post_type == 'anon':
                    try:
                        send_to_post_channel(post_id)
                        cursor.execute('DELETE FROM queue WHERE post_id = ?', (post_id,))
                        conn.commit()
                    except Exception as e:
                        print("Error sending post from queue (anon):", e)
                        retry_delay = 1
                        for i in range(5):  # Retry up to 5 times
                            time.sleep(retry_delay)
                            try:
                                send_to_post_channel(post_id)
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
def send_post_usual(post_id):
    conn = sqlite3.connect(DATABASE_NAME)
    cursor = conn.cursor()
    cursor.execute('SELECT media_type, media_id, caption, username, text FROM posts WHERE id = ?', (post_id,))
    post_data = cursor.fetchone()
    conn.close()
    if post_data:
        media_type, media_ids, caption, username, text = post_data
        media_ids = media_ids.split(',')

        if media_type == 'photo':
            media = [InputMediaPhoto(media_id, caption=f"{caption}\n\nАвтор поста: @{username}" if i == 0 else None) for i, media_id in enumerate(media_ids)]
            try:
                bot.send_media_group(POST_CHANNEL_ID, media)
            except Exception as e:
                print("Error sending media group:", e)
        elif media_type == 'video':
            media = [InputMediaVideo(media_id, caption=f"{caption}\n\nАвтор: @{username}" if i == 0 else None) for i, media_id in enumerate(media_ids)]
            try:
                bot.send_media_group(POST_CHANNEL_ID, media)
            except Exception as e:
                print("Error sending media group:", e)
        elif media_type is None:
            bot.send_message(POST_CHANNEL_ID, f"{text}\n\nАвтор: @{username}")