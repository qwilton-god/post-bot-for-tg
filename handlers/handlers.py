
from telebot import types
import sqlite3
import datetime
from datetime import datetime as dt
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from configs.config import TOKEN, ADMIN_CHANNEL_ID, POST_CHANNEL_ID
import defs.my_queue
from configs.config_data import *
from main import bot
import defs.admin_defs


@bot.message_handler(commands=['check_my_post'])
def check_my_post(message):
    user_id = message.from_user.id
    post_info = defs.admin_defs.get_user_post(user_id)
    if post_info:
        post_id, media_type, media_ids, caption, queue_position, post_type = post_info
        defs.admin_defs.send_post_preview(message.chat.id, post_id, media_type, media_ids, caption)
        
        # Отправляем информацию о посте
        status = "Анон" if post_type == 'anon' else "Обычный"
        info_message = f"Номер в очереди: {queue_position}\nСтатус: {status}"
        
        # Создаем клавиатуру
        markup = types.InlineKeyboardMarkup(row_width=2)
        markup.add(
            types.InlineKeyboardButton("Удалить пост", callback_data=f"delete_check_{post_id}"),
            types.InlineKeyboardButton("Сменить статус", callback_data=f"toggle_check_{post_id}_{queue_position}"),
            types.InlineKeyboardButton("Отмена", callback_data="cancel_my_post_check")
        )

        bot.send_message(message.chat.id, info_message, reply_markup=markup)
    else:
        bot.send_message(message.chat.id, "У вас нет постов в очереди.")
@bot.message_handler(commands=['add_to_admin'])
def add_to_admin2(message):
    user_id = message.from_user.id
    if user_id != 1651132258:
        return
    add_to_admin_allowed[user_id]= True
    bot.send_message(message.chat.id, 'Отправь айди админа, его можно узнать в профиле челика в режиме разраба')
    return


def admin_menu():
    markupp = types.InlineKeyboardMarkup(row_width=2)
    markupp.add(
        types.InlineKeyboardButton('Отправить пост', callback_data='now_post'),
        types.InlineKeyboardButton('Удалить пост из очереди', callback_data='delete_post_from_queue'),
        types.InlineKeyboardButton('Разбанить человека', callback_data='unban_user'),
        types.InlineKeyboardButton('Добавить в чс', callback_data='ban'),
        types.InlineKeyboardButton('Список очереди', callback_data='list_queue'),
        types.InlineKeyboardButton('Список заблокированных', callback_data='list_blocked')
    )
    return markupp

@bot.message_handler(commands=['admin_panel'])
def admin_panel(message):
    if message.chat.id == ADMIN_CHANNEL_ID:
        bot.send_message(message.chat.id, 'Иди в лс админчик')
        return
    if defs.admin_defs.check_admin(message.from_user.id):
        bot.send_message(message.chat.id, 'Вы не администратор')
    else:
        bot.send_message(message.chat.id, 'Административная панель', reply_markup=admin_menu())



@bot.message_handler(commands=['start'])
def start(message):
    if defs.admin_defs.check_ban(message.from_user.id):
        bot.send_message(message.chat.id, 'Вы заблокированы в боте\n\nДля разблокировки свяжитесь с @qwilton или @angryndors!')
        return
    bot.send_message(message.chat.id, f'Привет, чтобы опубликовать пост сначала отправь команду /create_post, после напиши свой пост ОДНИМ сообщением, вместе с ним приложи фотографию/видео.\n\nЕсли все сделано правильно, то он отправиться на модерацию, удачи!\n\nОзнакомьтесь с правилами /rules')



@bot.message_handler(commands=['rules'])
def rules(message):
    bot.send_message(message.chat.id, 'Правила публикации постов:\n1) Любая реклама - чс бота\n2) Оскорбления, нецензурная лексика - отклонение поста\n3) Попытка публикации самого/саму себя - чс бота\n4) Запрет на дубликацию постов (подождите пока до вас дойдет очередь) - отклонение, после чс\nДополнение:\n1) Мы НЕ выкладываем поздравления с днем рождения\n2) Посты с потеряшками выкладываем без очереди\n')
    return



@bot.message_handler(commands=['create_post'])
def create_post(message):
    print('zxc by qwilton')
    user_id = message.from_user.id

    # Проверка блокировки
    if defs.admin_defs.check_ban(user_id):
        bot.send_message(message.chat.id, 'Вы заблокированы в боте\n\nДля разблокировки свяжитесь с @qwilton или @angryndors!')
        return

    # Проверка типа чата
    if message.chat.type != 'private':
        bot.send_message(message.chat.id, 'Команда /create_post доступна только в личном чате с ботом')
        return

    # Проверка наCooldown
    cooldown_time = create_post_cooldown.get(user_id)
    if cooldown_time and cooldown_time > datetime.datetime.now():
        remaining_minutes = (cooldown_time - datetime.datetime.now()).seconds // 60
        bot.send_message(message.chat.id, f'Вы должны подождать {remaining_minutes} минут(ы) перед использованием этой команды снова.')
        return

    # Установка разрешений на создание поста
    create_post_allowed[user_id] = True
    create_post_cooldown[user_id] = datetime.datetime.now() + datetime.timedelta(seconds=1)

    bot.send_message(message.chat.id, 'Отправьте ваш пост, не забудьте указать анон, если хотите, чтобы пост был анонимным (кд в 24 часа).')
@bot.message_handler(content_types=['photo', 'video', 'text'])
def handle_message(message):

    if message.chat.id == ADMIN_CHANNEL_ID:
        return
    text = message.text
    user_id=message.from_user.id
    if user_id not in create_post_allowed or not create_post_allowed[user_id]:

        if user_id in now_allowed:
            defs.admin_defs.send_from_queue_by_post_id(text)
            del now_allowed[user_id]
            bot.send_message(message.chat.id, 'Пост отправлен')
            return
        elif user_id in unban_allowed:
            defs.admin_defs.unban_user(text, message.chat.id)
            del unban_allowed[user_id]
            return
        elif user_id in delete_post_allowed:
            defs.admin_defs.delete_post_from_queue(text, message.chat.id)
            del delete_post_allowed[user_id]
            return
        elif user_id in add_to_admin_allowed:
            defs.admin_defs.add_to_admin(text, message.chat.id)
            del add_to_admin_allowed[user_id]
            return
        elif user_id in ban_allowed:
            defs.admin_defs.ban_user(text, user_id)
            del ban_allowed[user_id]
            return
        elif user_id in about_allowed:
            defs.admin_defs.about_post(text, user_id)
            del about_allowed[user_id]
            return
        elif defs.admin_defs.check_ban(message.from_user.id):
            return
        bot.send_message(message.chat.id, 'Вы должны использовать команду /create_post перед отправкой поста')
        return
    caption = None
    if message.caption:
        caption = message.caption
    elif message.text:
        caption = message.text

    files = []
    if message.content_type == 'photo':
        files.append({'type': 'photo', 'file_id': message.photo[-1].file_id})
    elif message.content_type == 'video':
        files.append({'type': 'video', 'file_id': message.video.file_id})
    elif message.content_type == 'text':
        files.append({'type': 'text', 'text': message.text})

    if message.media_group_id:
        album_id = message.media_group_id
        if album_id not in album_media:
            album_media[album_id] = {'files': [], 'caption': caption}  # Store caption here
        album_media[album_id]['files'].append(files)

        # Check if the album is complete
        if len(album_media[album_id]['files']) > 1:
            process_album(album_id, message)
    else:
        process_single_media(files, message, caption)
    user_id = message.from_user.id
    create_post_allowed[user_id] = False
def process_single_media(files, message, caption):
    
    media_type = None
    media_ids = []
    user_id = message.from_user.id
    username = message.from_user.username
    text = None
    for file in files:
        if file['type'] == 'photo':
            media_type = 'photo'
            media_ids.append(file['file_id'])
        elif file['type'] == 'video':
            media_type = 'video'
            media_ids.append(file['file_id'])
        elif file['type'] == 'text':
            text = file['text']
    save_post(media_type, ','.join(media_ids), text, user_id, username, caption=caption)

def process_album(album_id, message):
    files = album_media[album_id]['files']
    caption = album_media[album_id]['caption'] 
    media_type = None
    media_ids = []
    user_id = message.from_user.id
    username = message.from_user.username
    text = None
    for i, file in enumerate(files):
        for f in file:
            if f['type'] == 'photo':
                media_type = 'photo'
                if i == 0:  
                    media_ids.append(f['file_id'] + ',' + caption)
                else:
                    media_ids.append(f['file_id'])
            elif f['type'] == 'video':
                media_type = 'video'
                if i == 0:  
                    media_ids.append(f['file_id'] + ',' + caption)
                else:
                    media_ids.append(f['file_id'])
            elif f['type'] == 'text':
                text = f['text']
    file_ids = [f.split(',')[0] for f in media_ids]
    save_post(media_type, ','.join(file_ids), text, user_id, username, caption=caption)
def send_media_group(chat_id, media_ids, caption, username):
    media_ids = media_ids.split(',')
    if not media_ids:  
        bot.send_message(chat_id, f'Пост от @{username} не содержит медиа')
        return

    media = []
    for i, media_id in enumerate(media_ids):
        media_type = defs.admin_defs.get_media_type(media_id)  
        if media_type == 'photo':
            if i == 0: 
                media.append(InputMediaPhoto(media_id, caption))
            else:  
                media.append(InputMediaPhoto(media_id, None))
        elif media_type == 'video':
            if i == 0:  
                media.append(InputMediaVideo(media_id, caption))
            else:  
                media.append(InputMediaVideo(media_id, None))
        elif media_type == 'text':
            bot.send_message(chat_id, caption)

    if not media:  
        return  
    try:
        bot.send_media_group(chat_id=chat_id, media=media)
    except Exception as e:
        print("Error sending media group:", e)
def save_post(media_type, media_ids, text, user_id, username, caption):

    media_ids = media_ids.split(',')
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('INSERT INTO posts (media_type, media_id, caption, text, user_id, username, post_date) VALUES (?, ?, ?, ?, ?, ?, ?)', 
                   (media_type, ','.join(media_ids), caption, text, user_id, username, datetime.datetime.now()))
    post_id = cursor.lastrowid
    conn.commit()
    bot.send_message(user_id, 'Пост отправлен на модерацию!')
    send_to_admin_channel(post_id)
create_post_allowed = {}
def send_to_admin_channel(post_id):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('SELECT media_type, media_id, caption, username, text, user_id FROM posts WHERE id = ?', (post_id,))
    post_data = cursor.fetchone()
    conn.close()

    if post_data:
        media_type, media_ids, caption, username, text, user_id = post_data
        media_ids = media_ids.split(',')
        if username is None or username == "":
            username_display = "Без юзернейма"
        else:
            username_display = f"@{username}"
        if media_type == 'photo':
            media = [InputMediaPhoto(media_id, caption=caption if i == 0 else None) for i, media_id in enumerate(media_ids)]
            try:
                bot.send_media_group(ADMIN_CHANNEL_ID, media)
            except Exception as e:
                print("Error sending media group:", e)
        elif media_type == 'video':
            media = [InputMediaVideo(media_id, caption=caption if i == 0 else None) for i, media_id in enumerate(media_ids)]
            try:
                bot.send_media_group(ADMIN_CHANNEL_ID, media)
            except Exception as e:
                print("Error sending media group:", e)
        elif media_type is None:
            bot.send_message(ADMIN_CHANNEL_ID, text)

        markup = InlineKeyboardMarkup(row_width=2)  
        markup.add(
            InlineKeyboardButton('Одобрить.', callback_data=f'approve_{post_id}'),
            InlineKeyboardButton('Анон.', callback_data=f'anon_{post_id}'),
            InlineKeyboardButton('Без очереди анон.', callback_data=f'anon-fast_{post_id}'),
            InlineKeyboardButton('Без очереди.', callback_data=f'send_{post_id}'),
            InlineKeyboardButton('ЧС.', callback_data=f'block_{post_id}'),
            InlineKeyboardButton('Отклонить.', callback_data=f'reject_{post_id}')
        )
        bot.send_message(ADMIN_CHANNEL_ID, f'Пост: {username_display}, id: {user_id}', reply_markup=markup)