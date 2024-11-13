import datetime
import os
import random
import re

import psycopg2

from aiogram.dispatcher import FSMContext

from Env_Config import Database_setting, Telegram_setting

import asyncio
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, ContentType
from aiogram.dispatcher.filters.state import StatesGroup, State


def RunBotCore(telegram_token, user_id, stop_event):
    new_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(new_loop)

    bot = Bot(token=telegram_token)
    storage = MemoryStorage()
    dp = Dispatcher(bot, storage=storage)

    class ClientPhone(StatesGroup):
        clients_phone = State()

    try:
        connect = psycopg2.connect(user=Database_setting['user'],
                                   password=Database_setting['password'],
                                   host=Database_setting['host'],
                                   port=Database_setting['port'],
                                   database=Database_setting['database'])
        cursor = connect.cursor()
        print("SUCCESS | Active «connect» & «cursor»")
    except Exception as ex:
        print(f"ERROR | Activate «connect» & «cursor».\n{ex}")

    async def format_phone_number(phone_number):
        if phone_number is None:
            return None
        phone_number = re.sub(r'\D', '', phone_number)
        if phone_number.startswith('8'):
            phone_number = '7' + phone_number[1:]
        elif phone_number.startswith('7'):
            pass
        return phone_number

    @dp.message_handler(commands=['start'])
    async def command_start(message: types.Message):
        try:
            cursor.execute(f"SELECT * FROM List_crms WHERE user_id = {user_id} AND tg_token = '{telegram_token}'")
            row_crm = cursor.fetchone()

            if row_crm:
                crm_id = row_crm[0]

                cursor.execute(f"SELECT * FROM templatemessage WHERE user_id = {user_id} AND crm_id = {crm_id}")
                row_templatemessage = cursor.fetchone()

                if row_templatemessage:
                    message1 = row_templatemessage[3]
                    message2 = row_templatemessage[4]
                    message3 = row_templatemessage[5]
                    message4 = row_templatemessage[6]
                    message5 = row_templatemessage[7]
                    urls = row_templatemessage[8].split("|")

                    message_db = random.SystemRandom().choice([message1, message2, message3, message4, message5])

                    keyboard = InlineKeyboardMarkup(row_width=1)
                    for url in urls:
                        keyboard.add(InlineKeyboardButton(text=url, url=url))

                    keyboard_get_contact = ReplyKeyboardMarkup(resize_keyboard=True)
                    button = KeyboardButton(text="Отправить контакт")
                    keyboard_get_contact.add(button)

                    cursor.execute(f"SELECT * FROM Clients WHERE telegram_id = {message.from_user.id} AND user_id = {user_id} AND crm_id = {crm_id}")
                    row_clients = cursor.fetchone()

                    if row_clients is None:
                        fullname_clients = message.from_user.username
                        phone_number = None
                        telegram_id = message.from_user.id
                        time_prise = datetime.datetime.now().strftime("%d-%m-%Y %H-%M-%S")
                        telegram_status = False
                        whatsapp_status = False
                        status_send = True

                        try:
                            cursor.execute(
                                "INSERT INTO Clients (user_id, crm_id, fullname_clients, phone_number, telegram_id, time_prise, telegram_status, whatsapp_status, status_send)"
                                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);", (
                                    user_id, crm_id, fullname_clients, phone_number, telegram_id, time_prise,
                                    telegram_status, whatsapp_status, status_send
                                ))
                            connect.commit()
                        except Exception as ex:
                            print(f"ERROR | Insert into Clients db: {ex}")

                        message_db = message_db.replace("{ClientName}", fullname_clients)
                        await bot.send_message(chat_id=message.chat.id, text=message_db, reply_markup=keyboard)
                        await bot.send_message(chat_id=message.from_user.id,
                                               text="Отправьте нам свой номер телефона, чтобы получать уведомления",
                                               reply_markup=keyboard_get_contact)

                    elif row_clients is not None:
                        cursor.execute(f"SELECT * FROM Clients WHERE telegram_id = {message.from_user.id}")

                        row_clients = cursor.fetchone()

                        if row_clients:
                            fullname_clients = row_clients[3]
                            message_db = message_db.replace("{ClientName}", fullname_clients)
                            await bot.send_message(chat_id=message.chat.id, text=message_db, reply_markup=keyboard)
                            await bot.send_message(chat_id=message.from_user.id,
                                                   text="Отправьте нам свой номер телефона, чтобы получать уведомления",
                                                   reply_markup=keyboard_get_contact)

        except Exception as ex:
            print(f"ERROR | command_start: {ex}")
        finally:
            connect.commit()

    @dp.message_handler(content_types=ContentType.ANY)
    async def any_message(message: types.Message):
        await message.reply(message.text)

    @dp.message_handler(content_types=['text'])
    async def command_text(message: types.Message):
        if message.text == "Отправить контакт":
            keyboard_get_contact = ReplyKeyboardMarkup(resize_keyboard=True)
            button = KeyboardButton(text="Отправить контакт", request_contact=True)
            keyboard_get_contact.add(button)
            await message.answer("Нажмите кнопку, отправить контакт, для получения уведомлений", reply_markup=keyboard_get_contact)
            await ClientPhone.clients_phone.set()

    @dp.message_handler(content_types=ContentType.CONTACT, state=ClientPhone.clients_phone)
    async def get_client_phone(message: types.Message, state: FSMContext):
        telegram_id = message.from_user.id
        contact = message.contact
        phone = contact.phone_number
        await state.update_data(get_client_phone=phone)
        data = await state.get_data()
        get_client_phone = data['get_client_phone']

        try:
            cursor.execute(f"SELECT * FROM List_crms WHERE user_id = {user_id} AND tg_token = '{telegram_token}'")
            row_crm = cursor.fetchone()

            if row_crm:
                crm_id = row_crm[0]

                cursor.execute(f"SELECT * FROM Clients WHERE user_id = {user_id} AND crm_id = {crm_id}")
                row_clients = cursor.fetchall()

                for row_client in row_clients:
                    client_phone_db = await format_phone_number(row_client[4])
                    client_phone_live = await format_phone_number(get_client_phone)

                    if client_phone_db and client_phone_live and client_phone_db == client_phone_live:
                        cursor.execute(f"DELETE FROM Clients WHERE telegram_id = %s AND phone_number IS NULL", (telegram_id,))
                        cursor.execute(f"UPDATE Clients SET telegram_id = %s WHERE phone_number = %s", (telegram_id, get_client_phone))
                        cursor.execute(f"UPDATE Clients SET time_Prise = %s WHERE phone_number = %s", (None, get_client_phone))
                        cursor.execute(f"UPDATE Clients SET telegram_status = TRUE WHERE phone_number = %s", (get_client_phone,))
                        cursor.execute(f"UPDATE Clients SET whatsapp_status = FALSE WHERE phone_number = %s", (get_client_phone,))
                        cursor.execute(f"UPDATE Clients SET status_send = %s WHERE phone_number = %s", (True, get_client_phone))
                    else:
                        cursor.execute(f"UPDATE Clients SET phone_number = %s WHERE telegram_id = %s", (get_client_phone, telegram_id))
                        cursor.execute(f"UPDATE Clients SET telegram_status = %s WHERE telegram_id = %s", (True, telegram_id))
                        cursor.execute(f"UPDATE Clients SET whatsapp_status = %s WHERE telegram_id = %s", (False, telegram_id))
                        cursor.execute(f"UPDATE Clients SET status_Send = %s WHERE telegram_id = %s", (True, telegram_id))

                await message.answer("Спасибо! За предоставленный контакт, теперь уведомления будут приходить в телеграм!")

        except Exception as ex:
            print(f"ERROR | get_contact_phone: {ex}")
        finally:
            await state.finish()
            connect.commit()

    async def bot_polling():
        await dp.start_polling()

    async def run():
        polling_task = asyncio.create_task(bot_polling())

        while not stop_event.is_set():
            await asyncio.sleep(0.5)

        polling_task.cancel()
        try:
            await polling_task
        except asyncio.CancelledError:
            print("Bot polling was cancelled.")

        dp.stop_polling()

    try:
        new_loop.run_until_complete(run())
    finally:
        new_loop.run_until_complete(new_loop.shutdown_asyncgens())
        new_loop.close()