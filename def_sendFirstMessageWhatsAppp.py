import re
import os
import time
import random
import asyncio
import psycopg2

from Env_Config import Database_setting, GitHub_setting, Type_send_msg
from Env_template_message import template_message

from datetime import datetime, timedelta

from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.firefox.options import Options
from webdriver_manager.firefox import GeckoDriverManager

from concurrent.futures import ThreadPoolExecutor

os.environ['TOKEN_WEBDRIVER'] = GitHub_setting['Token_webdriver']

def TimeSendMessage(client_time_str, delay_time):
    client_time = datetime.strptime(client_time_str, "%d-%m-%Y %H-%M-%S")
    current_time = datetime.now()
    message_time = client_time + timedelta(minutes=delay_time)
    return current_time >= message_time

def replace_random_fields(message):
    # Шаблон для поиска текстов внутри фигурных скобок, кроме {ClientName}
    pattern = r"\{([^{}]*)\}"

    # Найдем все совпадения
    matches = re.findall(pattern, message)

    # Пройдемся по каждому совпадению
    for match in matches:
        # Если это не {ClientName}, заменим на случайное значение
        if "ClientName" not in match:
            # Разделим варианты внутри скобок по символу |
            options = match.split('|')
            # Выберем случайное значение
            random_choice = random.choice(options)
            # Заменим это в оригинальном сообщении
            message = message.replace(f"{{{match}}}", random_choice)

    return message

def SendMessageClients_first(crm_id, user_id, whatsapp_session, new_clients_sorted, link):

    if len(new_clients_sorted) == 0:
        return

    try:
        # Подключение к базе данных
        # Убедитесь, что подключение к базе данных явно использует UTF-8
        connect = psycopg2.connect(
            user=Database_setting['user'],
            password=Database_setting['password'],
            host=Database_setting['host'],
            port=Database_setting['port'],
            database=Database_setting['database']
        )
        cursor = connect.cursor()
        print("Connect SUCCESS")
    except psycopg2.Error as db_ex:
        print(f"ERROR | Database connection: {db_ex}")
        return  # Прерываем выполнение, так как нет доступа к базе данных

    try:
        options = Options()
        options.add_argument("start-maximized")
        options.add_argument("disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--headless")
        options.log.level = "trace"
        options.add_argument(f"-profile")
        options.add_argument(f"{whatsapp_session}")

        service = Service(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)

        # Обработка каждого клиента
        for client in new_clients_sorted:
            client_name = client[3]
            client_phone = client[4]

            try:
                # Генерация уникальных сообщений для текущего клиента
                cursor.execute("SELECT message1 FROM templatemessage WHERE user_id = %s AND crm_id = %s", (user_id, crm_id))
                row_template_message = cursor.fetchone()

                if row_template_message:
                    message1 = replace_random_fields(row_template_message[0])

                    # Персонализация сообщений
                    message1_personalized = message1
                    message1_personalized = message1_personalized.replace("ClientName", client_name if client_name is not None else "")
                    message1_personalized = message1_personalized.replace("urls", link if link is not None else "")

                    if client_phone is not None:
                        original_phone = client_phone  # Сохраняем оригинальный номер

                        if client_phone.startswith("+"):
                            client_phone = client_phone[1:]
                        if client_phone.startswith("8"):
                            client_phone = "7" + client_phone[1:]

                        # Формирование URL для WhatsApp
                        try:
                            whatsapp_url = f"https://web.whatsapp.com/send/?phone={client_phone}&text&type=phone_number&app_absent=0"
                        except Exception as url_ex:
                            print(f"ERROR | URL formation: {url_ex}")
                            continue

                        # Открытие страницы и отправка сообщения
                        try:
                            driver.get(whatsapp_url)
                            WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[aria-placeholder="Введите сообщение"]')))

                            time.sleep(3)

                            try:
                                message_box = driver.find_element(By.CSS_SELECTOR, 'div[aria-placeholder="Введите сообщение"]')
                                message_box.click()

                                #Добавить ссылки на отправку
                                formatted_message = "\n".join([message1_personalized, template_message['StopMessage']])
                                for message_char in formatted_message:
                                    message_box.send_keys(message_char)
                                    time.sleep(0.01)

                                message_box.send_keys(Keys.ENTER)
                                time.sleep(5)

                                # Обновление статусов после отправления сообщения клиенту
                                try:
                                    time_prise = datetime.now().strftime("%d-%m-%Y %H-%M-%S")

                                    cursor.execute(f"UPDATE Clients SET whatsapp_status = TRUE WHERE phone_number = '{original_phone}'")
                                    cursor.execute(f"UPDATE Clients SET status_first_send = TRUE WHERE phone_number = '{original_phone}'")
                                    cursor.execute(f"UPDATE Clients SET status_last_send = FALSE WHERE phone_number = '{original_phone}'")
                                    cursor.execute(f"UPDATE Clients SET time_prise = '{time_prise}' WHERE phone_number = '{original_phone}'")
                                    connect.commit()
                                except psycopg2.Error as update_status_ex:
                                    print(f"ERROR | Cant update status for active client: {update_status_ex}")

                                #Запись в сообщения в бд после отправки #Время брать их HTML кода #Поиск времени по тексту сообщения.

                                # Запись сообщения в БД после отправки. Поиск времени и текста последнего сообщения.
                                try:
                                    # Получаем последнее отправленное сообщение и его время
                                    messages = driver.find_elements(By.CLASS_NAME, "message-out")
                                    if messages:
                                        last_message = messages[-1]  # Берем последнее сообщение
                                        copyable_text = last_message.find_element(By.CLASS_NAME, "copyable-text")
                                        last_message_date = copyable_text.get_attribute("data-pre-plain-text")

                                        pattern = r"\[\d{2}:\d{2},\s\d{2}\.\d{2}\.\d{4}\]\s.*:"

                                        #Чиста дата для дальнейшего сравнения в формате [время, дата] - как в HTML WH
                                        clean_date = re.sub(pattern, lambda x: x.group(0).split(']')[0] + ']', last_message_date)
                                        #Дата для сверки отправки
                                        real_date_message = datetime.now().strftime("%d-%m-%Y %H-%M-%S")
                                        cursor.execute("INSERT INTO sendmessageclient (user_id, crm_id, phone_number, message, send_date, type_sender, type_send, real_date_send) "
                                                       "VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
                                                       (user_id, crm_id, original_phone, formatted_message, clean_date, Type_send_msg['WH_sender'], Type_send_msg['WH_type'], real_date_message))
                                        connect.commit()
                                except Exception as ex:
                                    print(f"ERROR | Write message sent to client: {ex}")
                                finally:
                                    connect.commit()


                            except Exception as send_message_ex:
                                print(f"ERROR | Message sending: {send_message_ex}")

                        except Exception as open_url_ex:
                            print(f"ERROR | Cant open URL for WhatsApp: {open_url_ex}")
                            #Если не удалось открыть ссылку, то мы записываем данный номер, что он не действителен
                            try:
                                cursor.execute(f"UPDATE Clients SET phone_number = '{original_phone} + (Недействителен)' WHERE phone_number = '{original_phone}'")
                                cursor.execute(f"UPDATE Clients SET telegram_status = NULL WHERE phone_number = '{original_phone}'")
                                cursor.execute(f"UPDATE Clients SET whatsapp_status = NULL WHERE phone_number = '{original_phone}'")
                                cursor.execute(f"UPDATE Clients SET status_first_send = NULL WHERE phone_number = '{original_phone}'")
                                cursor.execute(f"UPDATE Clients SET status_last_send = NULL WHERE phone_number = '{original_phone}'")
                                cursor.execute(f"UPDATE Clients SET status_bot = NULL WHERE phone_number = '{original_phone}'")
                            except psycopg2.Error as update_ex:
                                print(f"ERROR | Cant update status for inactive client: {update_ex}")
                            finally:
                                connect.commit()
                                continue

            except Exception as message_ex:
                print(f"ERROR | Message generation: {message_ex}")

    finally:
        if driver:
            driver.quit()
        if connect:
            connect.commit()
            connect.close()

# def StartMessageStream_first():
#     while True:
#         new_clients = []
#
#         try:
#             connect = psycopg2.connect(
#                 user=Database_setting['user'],
#                 password=Database_setting['password'],
#                 host=Database_setting['host'],
#                 port=Database_setting['port'],
#                 database=Database_setting['database']
#             )
#             cursor = connect.cursor()
#         except Exception as ex:
#             print(f"ERROR | Activate «connect» & «cursor».\n{ex}")
#             return
#
#         try:
#             cursor.execute(f"SELECT * FROM List_crms WHERE status_job = TRUE")
#             crms = cursor.fetchall()
#
#             with ThreadPoolExecutor(max_workers=4) as executor:
#                 for row_listcrms in crms:
#                     crm_id = row_listcrms[0]
#                     user_id = row_listcrms[1]
#                     whatsapp_session = row_listcrms[5]
#                     delay_time = row_listcrms[8]
#                     #ССылка на сайт
#                     link = row_listcrms[10]
#
#                     cursor.execute(f"SELECT * FROM Clients WHERE user_id = %s AND crm_id = %s AND status_first_send = %s AND telegram_status = %s AND status_bot = %s", (user_id, crm_id, False, False, True))
#                     clients = cursor.fetchall()
#
#                     for client in clients:
#                         new_clients.clear()
#                         client_time = client[6]
#
#                         if TimeSendMessage(client_time, delay_time):
#                             new_clients.append(client)
#
#                     new_clients_sorted = sorted(new_clients, key=lambda x: x[0])
#
#                     # Запуск потоков для отправки сообщений
#                     executor.submit(SendMessageClients_first, crm_id, user_id, whatsapp_session, new_clients_sorted, link)
#
#                 # Ожидание завершения всех потоков
#                 executor.shutdown(wait=True)
#
#         except Exception as ex:
#             print(f"ERROR | {ex}")
#         finally:
#             connect.commit()

def StartMessageStream_first():
    while True:
        new_clients = []

        try:
            connect = psycopg2.connect(
                user=Database_setting['user'],
                password=Database_setting['password'],
                host=Database_setting['host'],
                port=Database_setting['port'],
                database=Database_setting['database']
            )
            cursor = connect.cursor()
        except Exception as ex:
            print(f"ERROR | Activate «connect» & «cursor».\n{ex}")
            return
        try:
            cursor.execute(f"SELECT * FROM List_crms WHERE status_job = TRUE")
            crms = cursor.fetchall()

            with ThreadPoolExecutor(max_workers=4) as executor:
                for row_listcrms in crms:
                    crm_id = row_listcrms[0]
                    user_id = row_listcrms[1]
                    delay_time = row_listcrms[8]
                    # Ссылка на сайт
                    link = row_listcrms[10]

                    cursor.execute(f"SELECT * FROM Clients WHERE user_id = %s AND crm_id = %s AND status_first_send = %s AND telegram_status = %s AND status_bot = %s",
                                   (user_id, crm_id, False, False, True))
                    clients = cursor.fetchall()

                    new_clients.clear()
                    for client in clients:
                        client_time = client[6]

                        if TimeSendMessage(client_time, delay_time):
                            new_clients.append(client)

                    # Проверка, что new_clients не пуст
                    if new_clients:
                        new_clients_sorted = sorted(new_clients, key=lambda x: x[0])

                        # Проверка, что new_clients_sorted не пуст и имеет хотя бы один элемент
                        if new_clients_sorted and new_clients_sorted[0][2] == crm_id:
                            cursor.execute(f"SELECT * FROM List_Crms WHERE user_id = %s AND id = %s", (user_id, crm_id))
                            whatsapp_session = cursor.fetchone()[5]

                            executor.submit(SendMessageClients_first, crm_id, user_id, whatsapp_session, new_clients_sorted, link)

        except Exception as ex:
            print(f"ERROR | {ex}")
        finally:
            connect.commit()