import re
import os
import time
import random
import hashlib
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

from apscheduler.schedulers.asyncio import AsyncIOScheduler

scheduler = AsyncIOScheduler()

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

def TimeSendMessage(client_time_str, delay_time):
    client_time = datetime.strptime(client_time_str, "%d-%m-%Y %H-%M-%S")
    current_time = datetime.now()
    message_time = client_time + timedelta(minutes=delay_time)
    return current_time >= message_time


def SendMessageClients_last(crm_id, user_id, whatsapp_session, new_clients_sorted, link):
    if len(new_clients_sorted) == 0:
        return

    driver = None
    connect = None

    try:
        # Подключение к базе данных
        connect = psycopg2.connect(
            user=Database_setting['user'],
            password=Database_setting['password'],
            host=Database_setting['host'],
            port=Database_setting['port'],
            database=Database_setting['database']
        )
        cursor = connect.cursor()
    except psycopg2.Error as db_ex:
        print(f"ERROR | Database connection: {db_ex}")
        return  # Прерываем выполнение, так как нет доступа к базе данных

    try:
        options = Options()
        options.add_argument(f"-profile")
        options.add_argument(f"{whatsapp_session}")

        driver = webdriver.Firefox(options=options)

        # Отправка сообщения после оценивания
        for client in new_clients_sorted:
            client_name = client[3]
            client_phone = client[4]

            try:
                # Генерация уникальных сообщений для текущего клиента
                cursor.execute("SELECT message2, message3 FROM templatemessage WHERE user_id = %s AND crm_id = %s", (user_id, crm_id))
                row_template_message = cursor.fetchone()

                if row_template_message:
                    five_star = replace_random_fields(row_template_message[0])
                    low_star = replace_random_fields(row_template_message[1])

                    # Обработка переменной link
                    link = link if link is not None else ""
                    five_star = five_star.replace("urls", link)
                    low_star = low_star.replace("urls", link)

                    # Обработка переменной client_name
                    client_name = client_name if client_name is not None else ""
                    five_star = five_star.replace("ClientName", client_name)
                    low_star = low_star.replace("ClientName", client_name)

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

                        try:
                            driver.get(whatsapp_url)
                            WebDriverWait(driver, 30).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[aria-placeholder="Введите сообщение"]')))

                            time.sleep(3)

                            try:
                                cursor.execute(f"SELECT message, send_date, real_date_send FROM sendmessageclient WHERE phone_number "
                                               f"= %s AND user_id = %s AND crm_id = %s ORDER BY id DESC",
                                               (original_phone, user_id, crm_id))
                                row_send_message_db = cursor.fetchone()

                                send_date_message_client = row_send_message_db[1]
                                real_date_message_send = row_send_message_db[2]

                                # Получение всех сообщений в чате
                                rows = WebDriverWait(driver, 30).until(EC.presence_of_all_elements_located((By.CSS_SELECTOR, 'div[role="row"]')))
                                for i in range(len(rows)):
                                    row = rows[i]
                                    try:
                                        current_time = datetime.now().strftime("%d-%m-%Y %H-%M-%S")

                                        real_date_message_send = (datetime.strptime(real_date_message_send, "%d-%m-%Y %H-%M-%S") + timedelta(hours=24)).strftime("%d-%m-%Y %H-%M-%S")
                                        # Проверяем, является ли сообщение message-out
                                        message_out_elements = row.find_elements(By.CLASS_NAME, "message-out")
                                        if message_out_elements:
                                            for message_out in message_out_elements:
                                                try:
                                                    copyable_text = message_out.find_element(By.CLASS_NAME, "copyable-text")
                                                    if copyable_text:
                                                        last_message_date = copyable_text.get_attribute("data-pre-plain-text")
                                                        pattern = r"\[\d{2}:\d{2},\s\d{2}\.\d{2}\.\d{4}\]\s.*:"
                                                        clean_date = re.sub(pattern, lambda x: x.group(0).split(']')[0] + ']', last_message_date)
                                                        if send_date_message_client == clean_date:
                                                            print(clean_date, "Дата последнего нашего сообщения!")
                                                            # Переменная для хранения сообщений, которые будем выводить
                                                            output_message = ""
                                                            stop_detected = False  # Флаг для отслеживания "STOP"
                                                            grade_detected = False  # Флаг для отслеживания оценки
                                                            final_grade = ""  # Хранит последнюю правильную оценку
                                                            first_response = True  # Флаг для отслеживания первого ответа
                                                            incorrect_response_sent = False
                                                            # Проходим по всем строкам после текущего message-out
                                                            for j in range(i + 1, len(rows)):  # i + 1: начиная со следующей строки
                                                                next_row = rows[j]
                                                                message_in_elements = next_row.find_elements(By.CLASS_NAME, "message-in")

                                                                # Флаг для отслеживания отправленного сообщения о некорректной оценке

                                                                # Обрабатываем все входящие сообщения
                                                                for message_in in message_in_elements:
                                                                    text_message = message_in.text
                                                                    client_response = text_message.split("\n")[0]  # Очистка от даты!
                                                                    print(client_response, "Без даты")

                                                                    # Проверка на наличие слова "стоп" или "STOP" в любом ответе
                                                                    if re.search(r'\b(стоп|stop)\b', client_response, re.IGNORECASE):
                                                                        stop_detected = True  # Обнаружено "STOP", установим флаг

                                                                # Проверка оценки только в первом ответе
                                                                if first_response:
                                                                    # Убираем пробелы для удобства обработки
                                                                    client_response_cleaned = re.sub(r'\s+', '', client_response)
                                                                    print(client_response_cleaned, "Без пробелов")

                                                                    # Проверяем некорректные оценки (например, с запятыми)
                                                                    if re.search(r'\d[,\.]\d', client_response_cleaned):
                                                                        print("Некорректный формат оценки.")
                                                                    else:
                                                                        # Оставляем только цифры 1-5, игнорируя все остальное
                                                                        client_response_cleaned = re.sub(r'[^1-5]', '', client_response_cleaned)

                                                                        # Проверяем количество уникальных оценок
                                                                        unique_grades = set(client_response_cleaned)  # Множество уникальных оценок

                                                                        if len(unique_grades) > 1:
                                                                            final_grade = None
                                                                            print("Несколько оценок в одном сообщении.")
                                                                        elif len(unique_grades) == 1:
                                                                            grade = unique_grades.pop()  # Получаем единственную оценку
                                                                            final_grade = grade  # Сохраняем последнюю валидную оценку
                                                                            grade_detected = True  # Оценка найдена

                                                                            # Пример логики для ответа на оценки
                                                                            output_message += f"{five_star}" if grade == "5" else f"{low_star}"
                                                                            print(f"Оценка клиента: {grade}")

                                                                        # Установите флаг, чтобы больше не проверять оценки в следующих ответах
                                                                        first_response = False

                                                                # Если на текущий момент есть "STOP", отключаем клиента
                                                                if stop_detected:
                                                                    try:
                                                                        output_message += template_message['LastStopMessage']

                                                                        cursor.execute(f"UPDATE Clients SET status_bot = FALSE WHERE phone_number = '{original_phone}'")
                                                                        cursor.execute(f"UPDATE Clients SET time_prise = NULL WHERE phone_number = '{original_phone}'")
                                                                        cursor.execute(f"UPDATE Clients SET status_last_send = TRUE WHERE phone_number = '{original_phone}'")
                                                                        cursor.execute(f"UPDATE Clients SET phone_number = '{original_phone} + (Отключен)' WHERE phone_number = '{original_phone}'")
                                                                        connect.commit()
                                                                        print(f"Клиент {original_phone} отключён.")
                                                                    except Exception as ex:
                                                                        print(f"ERROR | STOP client emailing: {ex}")
                                                                    else:
                                                                        if stop_detected and not grade_detected:
                                                                            print("Отключаем клиента")
                                                                        # Если отключение не произошло, выводим оценку, если она была найдена
                                                                        else:
                                                                            # Если отключение не произошло, выводим оценку, если она была найдена
                                                                            if not grade_detected and not incorrect_response_sent and stop_detected is False:
                                                                                output_message += template_message['Repeat_message']  # Сообщение о некорректной оценке
                                                                                incorrect_response_sent = True  # Установить флаг, чтобы не отправлять повторно
                                                                                print("Повторное сообщение: некорректная оценка.")

                                                            # Отправляем сообщение клиенту
                                                            if output_message:
                                                                WebDriverWait(driver, 20).until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[aria-placeholder="Введите сообщение"]')))

                                                                message_box = driver.find_element(By.CSS_SELECTOR, 'div[aria-placeholder="Введите сообщение"]')
                                                                message_box.click()

                                                                for message_text in output_message:
                                                                    message_box.send_keys(message_text)
                                                                    time.sleep(0.01)

                                                                message_box.send_keys(Keys.ENTER)
                                                                time.sleep(5)
                                                                # Запись сообщения в БД после отправки. Поиск времени и текста последнего сообщения.
                                                                try:
                                                                    # Получаем последнее отправленное сообщение и его время
                                                                    messages = driver.find_elements(By.CLASS_NAME, "message-out")
                                                                    if messages:
                                                                        last_message = messages[-1]  # Берем последнее сообщение
                                                                        copyable_text = last_message.find_element(By.CLASS_NAME, "copyable-text")
                                                                        last_message_date = copyable_text.get_attribute("data-pre-plain-text")

                                                                        pattern = r"\[\d{2}:\d{2},\s\d{2}\.\d{2}\.\d{4}\]\s.*:"

                                                                        # Чиста дата для дальнейшего сравнения в формате [время, дата] - как в HTML WH
                                                                        clean_date = re.sub(pattern, lambda x: x.group(0).split(']')[0] + ']',last_message_date)
                                                                        # Дата для сверки отправки
                                                                        real_date_message = datetime.now().strftime("%d-%m-%Y %H-%M-%S")
                                                                        cursor.execute("INSERT INTO sendmessageclient (user_id, crm_id, phone_number, message, send_date, type_sender, type_send, real_date_send, client_mark)"
                                                                            "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s);",
                                                                            (user_id, crm_id, original_phone, output_message, clean_date, Type_send_msg['WH_sender'], Type_send_msg['WH_type'], real_date_message, final_grade))
                                                                        connect.commit()
                                                                except Exception as ex:
                                                                    print(f"ERROR | Write message sent to client: {ex}")
                                                                finally:
                                                                    connect.commit()

                                                                if output_message != template_message['Repeat_message']:
                                                                    try:
                                                                        cursor.execute(f"UPDATE Clients SET status_last_send = TRUE WHERE phone_number = '{original_phone}'")
                                                                        cursor.execute(f"UPDATE Clients SET time_prise = Null WHERE phone_number = '{original_phone}'")
                                                                        connect.commit()
                                                                    except psycopg2.Error as update_status_ex:
                                                                        print(f"ERROR | Cant update status for active client: {update_status_ex}")

                                                except Exception as message_out_ex:
                                                    print(f"ERROR | Process message out: {message_out_ex}")
                                                    continue
                                    except Exception as row_ex:
                                        print(f"ERROR | Process row: {row_ex}")
                                        continue
                            except Exception as ex:
                                print(f"ERROR | {ex}")
                        except Exception as ex:
                            print(f"ERROR | {ex}")
            except Exception as client_ex:
                print(f"ERROR | Process client {client_phone}: {client_ex}")
                continue

    except Exception as ex:
        print(f"ERROR | General: {ex}")

    finally:
        if driver:
            driver.quit()  # Закрываем драйвер
        if connect:
            cursor.close()
            connect.close()  # Закрываем соединение с базой данных


def StartMessageStream_last():
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
                    whatsapp_session = row_listcrms[5]
                    delay_time = 1 #одна минута
                    link = row_listcrms[10]

                    cursor.execute(f"SELECT * FROM Clients WHERE user_id = %s AND crm_id = %s AND status_last_send = %s AND telegram_status = %s AND status_bot = %s", (user_id, crm_id, False, False, True))
                    clients = cursor.fetchall()

                    for client in clients:
                        new_clients.clear()
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

                            executor.submit(SendMessageClients_last, crm_id, user_id, whatsapp_session, new_clients_sorted, link)
        except Exception as ex:
            print(f"ERROR | {ex}")
        finally:
            connect.commit()