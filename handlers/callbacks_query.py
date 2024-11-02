from telebot import types
import sqlite3
import datetime
from datetime import datetime as dt
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, InputMediaPhoto, InputMediaVideo
from configs.config import *
import defs.my_queue
from main import bot
import defs.admin_defs
import defs.posts
from configs.config_data import *
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()

    try:
        # Проверяем, что данные начинаются с нужной строки и извлекаем post_id
        if call.data.startswith(('approve_', 'anon_', 'reject_', 'send_', 'anon-fast_', 'block_')):
            post_id = int(call.data.split('_')[1])
        else:
            post_id = None


        if call.data.startswith('approve_'):
            cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
            post = cursor.fetchone()
            if post:
                author_id = post[5]  
                cursor.execute('UPDATE posts SET approved = TRUE WHERE id = ?', (post_id,))
                cursor.execute('INSERT INTO queue (post_id, user_id, username, post_date, post_type, author_id) VALUES (?, ?, ?, ?, ?, ?)',  
                               (post_id, call.from_user.id, call.from_user.username, datetime.datetime.now(), 'usual', author_id))
                cursor.execute('SELECT user_id FROM posts WHERE id = ?', (post_id,))
                conn.commit() 
                author_id = cursor.fetchone()[0]
                bot.send_message(author_id, f'Ваш пост был одобрен и поставлен в очередь!\n\nПодробнее о посте /check_my_post')
                bot.send_message(ADMIN_CHANNEL_ID, f'Пост {post_id} одобрен не анонимно!')
            else:
                bot.send_message(call.from_user.id, f'Пост {post_id} не найден!')
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            conn.close()
            return
        
        
        elif call.data.startswith('anon_'):
            cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
            post = cursor.fetchone()
            if post:
                author_id = post[5]  
                cursor.execute('UPDATE posts SET approved = TRUE WHERE id = ?', (post_id,))
                cursor.execute('INSERT INTO queue (post_id, user_id, username, post_date, post_type, author_id) VALUES (?, ?, ?, ?, ?, ?)', 
                            (post_id, call.from_user.id, call.from_user.username, datetime.datetime.now(), 'anon', author_id))
                conn.commit() 
                bot.send_message(author_id, f'Ваш пост был одобрен и поставлен в очередь!\n\nПодробнее о посте/check_my_post')
                bot.send_message(ADMIN_CHANNEL_ID, f'Пост {post_id} был поставлен в очередь и будет отправлен анонимно!')
            else:
                bot.send_message(call.from_user.id, f'Пост {post_id} не найден!')
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            conn.close()
            return

        
        elif call.data.startswith('reject_'):
            cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
            if cursor.fetchone():
                newmark = InlineKeyboardMarkup(row_width=3)
                newmark.add(
                    InlineKeyboardButton('Реклама', callback_data=f'r_reason_{post_id}_adver'),
                    InlineKeyboardButton('Дублированный пост', callback_data=f'r_reason_{post_id}_duplicate'),
                    InlineKeyboardButton('Нецензурная брань', callback_data=f'r_reason_{post_id}_profanity'),
                    InlineKeyboardButton('Неадекватный пост', callback_data=f'r_reason_{post_id}_neadecvat'),              
                    InlineKeyboardButton('Выкладывание самого себя', callback_data=f'r_reason_{post_id}_selfpost'),
                    InlineKeyboardButton('Рофл пост', callback_data=f'r_reason_{post_id}_other'),
                    InlineKeyboardButton('Отмена', callback_data=f'cancel_reject_{post_id}')
                )
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=newmark)
            conn.close()
            return
        elif call.data.startswith('r_reason_'):
            post_id = call.data.split('_')[2]
            reason_code = call.data.split('_')[3]
            if post_id:
                reason_text = rej_reasons.get(reason_code, 'Неизвестная причина')

                bot.send_message(ADMIN_CHANNEL_ID, f'Пост {post_id} отклонен по причине: {reason_text}!')

                cursor.execute('SELECT user_id FROM posts WHERE id = ?', (post_id,))
                author_id = cursor.fetchone()[0]
                bot.send_message(author_id, f'Ваш пост {post_id} был отклонен по причине: {reason_text} .\n\nПожалуйста, ознакомьтесь с правилами и попробуйте снова.')

                cursor.execute('DELETE FROM posts WHERE id = ?', (post_id,))
                conn.commit()
            else:
                bot.send_message(call.from_user.id, f'Пост {post_id} не найден!')
            
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            conn.close()
            return

        elif call.data.startswith('cancel_reject_'):
            post_id = call.data.split('_')[2]
            markup = InlineKeyboardMarkup(row_width=2)  
            markup.add(
                InlineKeyboardButton('Одобрить.', callback_data=f'approve_{post_id}'),
                InlineKeyboardButton('Анон.', callback_data=f'anon_{post_id}'),
                InlineKeyboardButton('Без очереди анон.', callback_data=f'anon-fast_{post_id}'),
                InlineKeyboardButton('Без очереди.', callback_data=f'send_{post_id}'),
                InlineKeyboardButton('ЧС.', callback_data=f'block_{post_id}'),
                InlineKeyboardButton('Отклонить.', callback_data=f'reject_{post_id}')
            )

            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=markup)
            conn.close()
            return
        
        
        elif call.data.startswith('send_'):
            cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
            if cursor.fetchone():
                defs.posts.send_post_usual(post_id)
                cursor.execute('DELETE FROM queue WHERE post_id = ?', (post_id,))
                conn.commit()
                cursor.execute('SELECT user_id FROM posts WHERE id = ?', (post_id,))
                author_id = cursor.fetchone()[0]
                conn.commit()
                bot.send_message(author_id, f'Ваш пост был отправлен без очереди.')
                bot.send_message(ADMIN_CHANNEL_ID, f'Пост {post_id} одобрен!')

                bot.send_message(ADMIN_CHANNEL_ID, f'Пост {post_id} отправлен без очереди!')
            else:
                bot.send_message(call.from_user.id, f'Пост {post_id} не найден!')
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            conn.close()
            return
        
        
        elif call.data.startswith('anon-fast'):
            cursor.execute('SELECT * FROM posts WHERE id = ?', (post_id,))
            if cursor.fetchone():
                defs.posts.send_to_post_channel(post_id)
                cursor.execute('DELETE FROM queue WHERE post_id = ?', (post_id,))
                cursor.execute('SELECT user_id FROM posts WHERE id = ?', (post_id,))
                author_id = cursor.fetchone()[0]
                conn.commit()
                bot.send_message(author_id, 'Ваш пост был отправлен без очереди.')
                bot.send_message(ADMIN_CHANNEL_ID, f'Пост {post_id} отправлен без очереди!')
            else:
                bot.send_message(call.from_user.id, f'Пост {post_id} не найден!')
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            conn.close()
            return
        
        
        elif call.data.startswith('block_'):
            cursor.execute('SELECT user_id, username FROM posts WHERE id = ?', (post_id,))
            user_data = cursor.fetchone()
            if user_data:
                user_id, username = user_data
                cursor.execute('INSERT INTO blocked_users (user_id, username, is_blocked, blocked_reason, block_date) VALUES (?, ?, ?, ?, ?)', 
                               (user_id, username, True, 'ЧС', datetime.datetime.now()))
                conn.commit()
                bot.send_message(ADMIN_CHANNEL_ID, f'Пользователь @{username} заблокирован!')
                bot.send_message(user_id, 'Вы были заблокированы в боте\n\nДля разблокировки свяжитесь с @qwilton или @angryndors')
            else:
                bot.send_message(call.from_user.id, f'Пост {post_id} не найден!')
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            conn.close()
            return
        
        
        
        
        elif call.data.startswith('now_post'):
            user_id=call.from_user.id
            defs.admin_defs.rufa(call.from_user.id)
            now_allowed[call.from_user.id] = True
            bot.send_message(call.message.chat.id, 'Введите номер поста для отправки.')
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            return
        elif call.data.startswith('delete_post_from_queue'):
            user_id=call.from_user.id
            defs.admin_defs.rufa(call.from_user.id)
            delete_post_allowed[call.from_user.id] = True  
            bot.send_message(call.message.chat.id, 'Введите номер поста для удаления.')
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            return
        elif call.data.startswith('unban_user'):
            user_id=call.from_user.id
            defs.admin_defs.rufa(call.from_user.id)
            unban_allowed[call.from_user.id] = True
            bot.send_message(call.message.chat.id, 'Введите ID пользователя для разбана.')
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            return
        elif call.data.startswith('ban'):
            user_id=call.from_user.id
            defs.admin_defs.rufa(call.from_user.id)
            ban_allowed[call.from_user.id] = True
            bot.send_message(call.message.chat.id, 'Введите ID пользователя для добавления его в чс.')
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            return
        elif call.data.startswith('list_queue'):
            defs.admin_defs.list_queue(call)
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            return
        elif call.data.startswith('list_blocked'):
            defs.admin_defs.list_blocked(call)
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            return
        
        elif call.data.startswith('about_posts'):
            user_id=call.from_user.id
            defs.admin_defs.rufa(user_id)
            about_allowed[user_id] = True
            bot.send_message(user_id, 'Введите id поста для подробностей о нем')
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            return
        
        
        elif call.data.startswith('about_send_'):
            post_id = int(call.data.split('_')[2])
            defs.admin_defs.send_from_queue_by_post_id(post_id)
            bot.send_message(call.from_user.id, 'Пост был успешно отправлен.')
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            return
        elif call.data.startswith('about_delete_'):
            post_id = str(call.data.split('_')[2])
            defs.admin_defs.delete_post_from_queue(post_id, chat_id=call.message.chat.id)
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            return
        elif call.data.startswith('about_remove'):
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            return
        elif call.data.startswith('toggle_status_'):
            defs.admin_defs.toggle_status(call)
            return
        
        
        elif call.data.startswith('delete_check_'):
            post_id = str(call.data.split('_')[2])
            defs.admin_defs.delete_post_from_queue(post_id, chat_id=call.message.chat.id)
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            return
        elif call.data.startswith('toggle_check_'):
            defs.admin_defs.toggle_status_personal(call)
            return
        elif call.data == 'cancel_my_post_check':
            bot.edit_message_reply_markup(chat_id=call.message.chat.id, message_id=call.message.message_id, reply_markup=None)
            return
    except ValueError:
        bot.send_message(call.message.chat.id, "Ошибка: неверный формат данных. Пожалуйста, проверьте команду.")
    except sqlite3.Error as e:
        print("Ошибка базы данных:", e)
        bot.send_message(call.message.chat.id, "Ошибка базы данных. Пожалуйста, попробуйте позже.")
    finally:
        conn.close()
        
