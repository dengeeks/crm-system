import time
import psycopg2
import selenium
from selenium import webdriver
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from webdriver_manager.firefox import GeckoDriverManager
from selenium.webdriver.common.by import By
import re  # Импортируем модуль для работы с регулярными выражениями
from Env_Config import Database_setting


def get_ChatWhatsApp(user_id, crm_id):
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
        print("SUCCESS | Active «connect» & «cursor»")
    except Exception as ex:
        print(f"ERROR | Activate «connect» & «cursor».\n{ex}")
        return  # Early exit if connection fails

    type_app = "WhatsApp"

    # Получаем информацию о сессии и номере телефона из базы данных
    cursor.execute(f"SELECT * FROM List_crms WHERE id = {crm_id} AND user_id = {user_id}")
    list_crms = cursor.fetchone()

    if list_crms:
        whatsapp_session = list_crms[5]

        # Настройки для Firefox Browser
        options = Options()
        options.log.level = "trace"
        options.add_argument(f"-profile")
        options.add_argument(f"{whatsapp_session}")

        # Установка и запуск Firefox
        service = Service(GeckoDriverManager().install())
        driver = webdriver.Firefox(service=service, options=options)

        # Инициализируем клиентов данной CRM системы
        cursor.execute(f"SELECT * FROM CLients WHERE user_id = {user_id} and crm_id = {crm_id} AND status_bot = TRUE")
        chat_dict = {}  # Словарь для хранения сообщений для каждого клиента

        for row_client in cursor.fetchall():
            if row_client:
                client_phone = row_client[4]

                if client_phone is not None:
                    original_phone = client_phone  # Сохраняем оригинальный номер

                    if client_phone.startswith("+"):
                        client_phone = client_phone[1:]
                    if client_phone.startswith("8"):
                        client_phone = "7" + client_phone[1:]

                whatsapp_url = f"https://web.whatsapp.com/send/?phone={client_phone}&text&type=phone_number&app_absent=0"
                driver.get(whatsapp_url)

                time.sleep(30)

                # Получаем элементы сообщений (message-out и message-in)
                messages = driver.find_elements(By.CSS_SELECTOR, "div.message-out, div.message-in")
                client_chat_text = ""  # Переменная для хранения сообщений текущего клиента

                for message in messages:
                    message_text = message.text
                    message_class = message.get_attribute("class")

                    # Получаем дату и время из вложенного элемента с атрибутом data-pre-plain-text
                    date_element = message.find_element(By.CSS_SELECTOR, "div.copyable-text")
                    pre_plain_text = date_element.get_attribute("data-pre-plain-text")
                    if pre_plain_text:
                        # Регулярное выражение для извлечения даты в формате "дд.мм.гггг"
                        match = re.search(r"\d{2}\.\d{2}\.\d{4}", pre_plain_text)
                        if match:
                            message_date = match.group(0)  # Получаем только дату "30.09.2024"
                        else:
                            message_date = "Не удалось извлечь дату"

                    # Формируем текст для каждого сообщения с датой после сообщения
                    if "message-out" in message_class:
                        client_chat_text += f"Вы: {message_text} ({message_date})\n"
                    elif "message-in" in message_class:
                        client_chat_text += f"{client_phone}: {message_text} ({message_date})\n"

                if not client_chat_text:
                    client_chat_text = "Не удалось получить сообщения"

                print(client_chat_text)

                # Сохраняем сообщения для клиента в словарь
                chat_dict[client_phone] = client_chat_text

        # Запись объединённых сообщений в базу данных (если нужно)
        try:
            for title, messages in chat_dict.items():
                cursor.execute(f"SELECT text_message FROM WhatsAppChat WHERE title_message = %s AND user_id = %s AND crm_id = %s",
                               (title, user_id, crm_id))
                row_chat = cursor.fetchone()

                if row_chat:
                    existing_messages = row_chat[0]
                    # Проверяем, есть ли новые сообщения
                    if messages.strip() != existing_messages.strip():
                        new_messages = messages.strip().split('\n')
                        existing_messages = existing_messages.strip().split('\n')
                        # Сравниваем и добавляем новые сообщения
                        for msg in new_messages:
                            if msg not in existing_messages:
                                existing_messages.append(msg)
                                print(f"Новое сообщение найдено и добавлено: {msg}")
                        updated_messages = "\n".join(existing_messages)
                        cursor.execute(
                            f"UPDATE WhatsAppChat SET text_message = %s WHERE user_id = %s AND crm_id = %s AND title_message = %s",
                            (updated_messages, user_id, crm_id, title))
                    else:
                        print("Сообщение уже существует в базе данных.")
                else:
                    cursor.execute(
                        "INSERT INTO WhatsAppChat (user_id, crm_id, title_message, text_message, type_app) VALUES (%s, %s, %s, %s, %s);",
                        (user_id, crm_id, title, messages, type_app))

            # Сохранение изменений
            connect.commit()

        except Exception as e:
            print(f"Database error: {e}")

        finally:
            driver.quit()
            if connect:
                cursor.close()
                connect.close()


# get_ChatWhatsApp(user_id=2, crm_id=2)  # Убедитесь, что передаете правильные user_id и crm_id
