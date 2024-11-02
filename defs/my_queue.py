
from telebot import types
import sqlite3
import datetime
import json
import schedule
import time
import pytz
import threading
import requests
import defs.posts
from datetime import datetime as dt
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from configs.config import TOKEN, ADMIN_CHANNEL_ID, POST_CHANNEL_ID
def make_request(method_url, params):
    retry_count = 0
    max_retries = 5
    retry_delay = 5

    while retry_count < max_retries:
        try:
            response = requests.post(method_url, json=params, timeout=25)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.ReadTimeout:
            retry_count += 1
            time.sleep(retry_delay)
            retry_delay *= 2  # Экспоненциальное увеличение задержки
    raise Exception(f"Failed to make request after {max_retries} retries")


moscow_tz = pytz.timezone('Europe/Moscow')
def count_posts_in_queue():
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        
        # Выполняем SQL-запрос для подсчета количества постов в очереди
        cursor.execute('SELECT COUNT(*) FROM queue')
        count = cursor.fetchone()[0]  # Извлекаем результат
        return count
    except sqlite3.Error as e:
        print("Ошибка базы данных:", e)
        return None
    finally:
        conn.close()
def send_posts():
    defs.posts.send_from_queue()
    
hourly_job = None
bi_hourly_job = None
thirty_min_job = None

def check_queue_and_schedule():
    global hourly_job, bi_hourly_job, thirty_min_job
    # Удаление старых задач 
    if hourly_job:
        schedule.cancel_job(hourly_job)
    if bi_hourly_job:
        schedule.cancel_job(bi_hourly_job)
    if thirty_min_job:
        schedule.cancel_job(thirty_min_job)

    post_count = count_posts_in_queue()
    if post_count is not None:
        if post_count > 30:
            thirty_min_job = schedule.every(30).minutes.do(send_posts)
            print("Посты будут отправляться каждые 30 минут.")
        elif post_count > 8:
            hourly_job = schedule.every(1).hours.do(send_posts)
            print("Посты будут отправляться каждый час.")
        else:
            bi_hourly_job = schedule.every(2).hours.do(send_posts)
            print("Посты будут отправляться каждые 2 часа.")

def cancel_job():
    global hourly_job, bi_hourly_job, thirty_min_job
    print('Расписание отключено')
    if hourly_job:
        schedule.cancel_job(hourly_job)
    if bi_hourly_job:
        schedule.cancel_job(bi_hourly_job)
    if thirty_min_job:
        schedule.cancel_job(thirty_min_job)

def schedule_posts():
    # Запускаем проверку в 9:00
    schedule.every().day.at("09:00").do(check_queue_and_schedule)
    schedule.every().day.at("09:00").do(defs.posts.send_from_queue)
    schedule.every().day.at("23:00").do(cancel_job)
    schedule.every().day.at("23:00").do(defs.posts.send_from_queue)

def run_scheduler():
    while True:
        schedule.run_pending()
        time.sleep(1)  # Задержка между проверками
