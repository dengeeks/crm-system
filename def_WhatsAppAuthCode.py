# BaseLibrary
import os
import shutil
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

import psycopg2
# Selenium
from selenium import webdriver
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.firefox.options import Options
from selenium.webdriver.firefox.service import Service
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.firefox import GeckoDriverManager

from Env_Config import Database_setting, Email_setting


# Система создания профиля в FireFox и подключения WhatsApp
def whatsapp_authenticate(user_id, crm_id, phone_number, whatsapp_session):
    # Подключение к бд и проверка на сессию
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
        print("SUCCESS | Active «connect» & «cursor»")
    except Exception as ex:
        print(f"ERROR | Activate «connect» & «cursor».\n{ex}")
        return  # Early exit if connection fails

    # Проверка на профиль, если есть, то мы удаляем его из папки и перезаписываем в бд.
    try:
        cursor.execute(f"SELECT * FROM List_crms WHERE user_id = {user_id} AND id = {crm_id}")
        check_list_crm = cursor.fetchone()

        if check_list_crm:
            whatsapp_session_db = check_list_crm[5]

            if whatsapp_session_db is not None:
                if os.path.exists(whatsapp_session_db):
                    shutil.rmtree(whatsapp_session_db)

            # Создание папки
            os.makedirs(whatsapp_session, exist_ok = True)

            cursor.execute(
                f"UPDATE List_crms SET whatsapp_session = '{whatsapp_session}' WHERE user_id = {user_id} AND id = {crm_id}"
            )
    except Exception as ex:
        print(f"ERROR | remove and replace whatsapp session: {ex}")
    finally:
        connect.commit()

    # Создайте объект Options
    options = Options()
    options.add_argument("start-maximized")
    options.add_argument("disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--headless")
    options.log.level = "trace"
    options.add_argument(f"-profile")
    options.add_argument(f"{whatsapp_session}")
    # Создайте объект Service с использованием GeckoDriverManager
    # service = Service(GeckoDriverManager().install())

    service = Service(executable_path = '/usr/local/bin/geckodriver')

    # Инициализируйте WebDriver с Service и Options
    driver = webdriver.Firefox(service = service, options = options)

    try:
        # Открыть WhatsApp Web
        driver.get("https://web.whatsapp.com/")
        print("открытие ссылки")

        # Подождать некоторое время, чтобы страница загрузилась и ты мог авторизоваться вручную
        time.sleep(30)  # Увеличь время, если нужно больше времени для авторизации

        # Найти кнопку по CSS-селектору и кликнуть на неё
        element = driver.find_element(
            By.XPATH,
            "//div[@class='x1c4vz4f xs83m0k xdl72j9 x1g77sc7 xeuugli x2lwn1j xozqiw3 x1oa3qoh x12fk4p8 x1sy10c2']"
        )
        element.click()
        print("Нажата кнопка")

        # Подождать некоторое время, пока загрузится следующая страница
        time.sleep(20)  # Увеличь время, если нужно больше времени для загрузки

        # Найти текстовое поле по CSS-селектору и ввести номер телефона
        input_field = driver.find_element(By.TAG_NAME, 'input')
        input_field.clear()  # Если нужно очистить предварительное значение

        # Ввести новый номер телефона
        input_field.send_keys(phone_number)
        print("Ввод номера телефона")

        # Подождать некоторое время, чтобы убедиться, что введенный номер принят
        time.sleep(10)  # Можно настроить в зависимости от скорости работы страницы

        # Клик по пустой области, чтобы деактивировать выпадающий список
        body = driver.find_element(By.TAG_NAME, 'body')
        ActionChains(driver).move_to_element(body).click().perform()

        # Подождать, чтобы элемент "Далее" стал кликабельным и нажать на него
        next_button = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//div[contains(text(), 'Next') or contains(text(), 'Далее')]"))
        )
        next_button.click()
        time.sleep(20)

        # Найти элемент с кодом активации по атрибуту aria-details
        activation_code_element = WebDriverWait(driver, 20).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "[aria-details='link-device-phone-number-code-screen-instructions']")
            )
        )

        # Извлечь значение атрибута data-link-code
        activation_code = activation_code_element.get_attribute("data-link-code")

        # Отправить на почту и запустить таймер который через 5 минут ожидания
        # Получение почты пользователя
        try:
            cursor.execute(f"SELECT * FROM Users WHERE id = {user_id}")
            check_user_db = cursor.fetchone()

            if check_user_db:
                email_user = check_user_db[4]

                send_activation_code_to_email(email_user, activation_code)


        except Exception as ex:
            print(f"ERROR | get_email_user: {ex}")
        finally:
            connect.commit()

        time.sleep(300)  # Ожидание 5 минутЮ до закрытия браузера

    except Exception as ex:
        print(f"Не удалось выполнить действие: {ex}")
        driver.quit()
    finally:
        connect.commit()
        connect.close()
        driver.quit()


# Отправка пользователю на почту кода активации
def send_activation_code_to_email(email_user, activation_code):
    smtp_server = smtplib.SMTP("smtp.gmail.com", 587)
    smtp_server.starttls()
    smtp_server.login(f"{Email_setting['Email_sender']}", f"{Email_setting['Email_token']}")

    try:
        msg = MIMEMultipart()
        msg["From"] = f"{Email_setting['Email_sender']}"
        msg['To'] = email_user
        msg['Subject'] = "Код подтверждения WhatsApp"

        html_whatsapp_code = "templates/Email_code_WhatsApp.html"

        with open(html_whatsapp_code, 'r', encoding = "utf-8") as file_html:
            html_whatsapp_code = file_html.read()

        html_whatsapp_code = html_whatsapp_code.replace(
            "{{ code }}", ", ".join(activation_code)
        )  # Преобразуем список в строку
        html_whatsapp_code = html_whatsapp_code.replace("{{ time }}", "5")

        msg.attach(MIMEText(html_whatsapp_code, "html"))

        smtp_server.sendmail(f"{Email_setting['Email_sender']}", email_user, msg.as_string())

    except Exception as ex:
        print(f"ERROR | send_email: {ex}")
    finally:
        smtp_server.quit()
