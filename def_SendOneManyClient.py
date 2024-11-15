import os
import re
import time
from datetime import datetime

import psycopg2
from selenium import webdriver
from selenium.webdriver import Keys
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager

from Env_Config import Database_setting, GitHub_setting, Type_send_msg

os.environ['TOKEN_WEBDRIVER'] = GitHub_setting['Token_webdriver']


def send_manyoneclient(user_id, crm_id, phone_numbers, message):
    try:
        # Подключение к базе данных
        connect = psycopg2.connect(
            user = Database_setting['user'],
            password = Database_setting['password'],
            host = Database_setting['host'],
            port = Database_setting['port'],
            database = Database_setting['database']
        )
        cursor = connect.cursor()
    except psycopg2.Error as db_ex:
        print(f"ERROR | Database connection: {db_ex}")
        return  # Прерываем выполнение, так как нет доступа к базе данных

    cursor.execute(
        f"SELECT whatsapp_session FROM List_crms WHERE user_id = %s AND id = %s AND status_job = %s",
        (user_id, crm_id, True)
    )
    check_list_crm = cursor.fetchone()

    if not check_list_crm:
        print("ERROR | CRM session not found.")
        return

    whatsapp_session = check_list_crm[0]
    options = Options()
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--headless")
    options.log.level = "trace"
    options.add_argument(f"-profile")
    options.add_argument(f"{whatsapp_session}")

    service = Service(executable_path = '/usr/local/bin/geckodriver')
    driver = webdriver.Firefox(service = service, options = options)
    try:

        try:

            for client_phone in phone_numbers:
                if client_phone is not None:
                    original_phone = client_phone  # Сохраняем оригинальный номер

                    if client_phone.startswith("+"):
                        client_phone = client_phone[1:]
                    if client_phone.startswith("8"):
                        client_phone = "7" + client_phone[1:]

                    # Отправка сообщений индивидуальным клиентам
                    try:
                        whatsapp_url = f"https://web.whatsapp.com/send/?phone={client_phone}&text&type=phone_number&app_absent=0"
                        driver.get(whatsapp_url)

                        WebDriverWait(driver, 20).until(
                            EC.presence_of_element_located(
                                (By.CSS_SELECTOR, 'div[aria-placeholder="Введите сообщение"]')
                                )
                            )

                        time.sleep(3)

                        try:
                            message_box = driver.find_element(
                                By.CSS_SELECTOR, 'div[aria-placeholder="Введите сообщение"]'
                                )
                            message_box.click()

                            for message_char in message:
                                message_box.send_keys(message_char)
                                time.sleep(0.01)

                            message_box.send_keys(Keys.ENTER)
                            time.sleep(5)

                            try:
                                # Получаем последнее отправленное сообщение и его время
                                messages = driver.find_elements(By.CLASS_NAME, "message-out")
                                if messages:
                                    last_message = messages[-1]  # Берем последнее сообщение
                                    copyable_text = last_message.find_element(By.CLASS_NAME, "copyable-text")
                                    last_message_date = copyable_text.get_attribute("data-pre-plain-text")

                                    pattern = r"\[\d{2}:\d{2},\s\d{2}\.\d{2}\.\d{4}\]\s.*:"

                                    # Чиста дата для дальнейшего сравнения в формате [время, дата] - как в HTML WH
                                    clean_date = re.sub(
                                        pattern, lambda x: x.group(0).split(']')[0] + ']', last_message_date
                                        )
                                    real_date_message = datetime.now().strftime("%d-%m-%Y %H-%M-%S")
                                    cursor.execute(
                                        "INSERT INTO sendmessageclient (user_id, crm_id, phone_number, message, send_date, type_sender, type_send, real_date_send) "
                                        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s);",
                                        (user_id, crm_id, original_phone, message, clean_date,
                                         Type_send_msg['WH_sender'], Type_send_msg['WH_type'], real_date_message)
                                    )

                            except Exception as ex:
                                print(f"ERROR | Write message sent to client: {ex}")
                            finally:
                                connect.commit()

                        except Exception as ex:
                            print(f"ERROR | Message box interaction: {ex}")
                            continue

                    except Exception as url_ex:
                        print(f"ERROR | URL formation: {url_ex}")
                        continue

        except Exception as ex:
            print(f"ERROR | Cannot open WhatsApp session: {ex}")
            return

    except Exception as ex:
        print(f"ERROR | Cannot send message to client: {ex}")
    finally:
        print(user_id)
        driver.quit()
        cursor.close()
        connect.close()
