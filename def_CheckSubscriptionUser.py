import smtplib
import threading
import time

import psycopg2
from datetime import datetime, timedelta
from Env_Config import Database_setting, Email_setting

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def load_html_template(file_path):
    with open(file_path, "r", encoding="utf-8") as file:
        return file.read()

def send_email(to_email, subject, html_content):
    try:
        # Настройки SMTP сервера
        smtp_server = smtplib.SMTP("smtp.gmail.com", 587)
        smtp_server.starttls()
        smtp_server.login(Email_setting['Email_sender'], Email_setting['Email_token'])

        # Создание объекта сообщения
        msg = MIMEMultipart()
        msg["From"] = Email_setting['Email_sender']
        msg["To"] = to_email
        msg["Subject"] = subject

        msg.attach(MIMEText(html_content, "html"))

        # Отправка сообщения
        smtp_server.sendmail(Email_setting['Email_sender'], to_email, msg.as_string())

    except Exception as ex:
        print(f"ERROR | send_email: {ex}")
    finally:
        smtp_server.quit()

def CheckSubscriptionUser():
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
    except Exception as ex:
        print(f"ERROR | Activate «connect» & «cursor».\n{ex}")
        return  # Ранний выход при неудачном подключении

    """Проверка подписки, если истекает срок, уведомляем и отключаем."""
    """Запуск функции осуществить раз в час, чтобы не грузить сервер."""

    try:
        cursor.execute("SELECT * FROM user_subscription WHERE status_subscription = TRUE")
        for row_subscription in cursor.fetchall():
            email = row_subscription[1]
            data_beg_str = row_subscription[2]  # Строковое представление даты начала
            data_end_str = row_subscription[3]  # Строковое представление даты окончания
            status_subscription = row_subscription[4]
            status_send = row_subscription[5]

            # Преобразование строковых дат в объекты datetime
            data_end = datetime.strptime(data_end_str, "%d-%m-%Y").date()

            # Текущая дата
            current_date = datetime.now().date()

            # Вычисляем дату за 3 дня до окончания подписки
            three_days_before_end = data_end - timedelta(days=3)

            # Проверяем если подписка уже закончилась
            if current_date > data_end:
                try:
                    # Шаблон для завершенной подписки
                    expired_subscription_email = "templates/Email_EndSubscription.html"
                    html_expired = load_html_template(expired_subscription_email)

                    # Замена фраз
                    text_expired = "завершилась."
                    text_expired_details = "Пожалуйста, продлите подписку, чтобы продолжить использовать наши услуги."
                    html_expired = html_expired.replace("{{ текст_почты }}", email)
                    html_expired = html_expired.replace("{{ текст_окончания }}", text_expired)
                    html_expired = html_expired.replace("{{ текст_об_окончании }}", text_expired_details)

                    # Отправка уведомления
                    send_email(email, "Подписка завершена", html_expired)

                    # Обновление статусов в базе данных
                    cursor.execute("""UPDATE user_subscription SET status_subscription = FALSE, status_send = TRUE WHERE email = %s""", (email,))

                    cursor.execute('SELECT * FROM Users WHERE email = %s', (email,))
                    for user in cursor.fetchall():
                        user_id = user[0]

                        cursor.execute("""UPDATE List_crms SET Status_job = FALSE WHERE user_id = %s""", (user_id,))

                except Exception as ex:
                    print(f"ERROR | expired_subscription_email: {ex}")

            # Проверяем, если до окончания подписки осталось 3 дня или меньше
            elif current_date >= three_days_before_end and current_date <= data_end and status_send is False:
                try:
                    # Шаблон для подписки, заканчивающейся через 3 дня
                    three_days_email = "templates/Email_EndSubscription.html"
                    html_three_days = load_html_template(three_days_email)

                    # Замена фраз
                    text_three_days = "Закончится через 3 дня."
                    text_three_days_ends = "Успейте обновить подписку, чтобы не отключались боты"
                    html_three_days = html_three_days.replace("{{ текст_почты }}", email)
                    html_three_days = html_three_days.replace("{{ текст_окончания }}", text_three_days)
                    html_three_days = html_three_days.replace("{{ текст_об_окончании }}", text_three_days_ends)

                    # Отправка уведомления
                    send_email(email, "Уведомление о подписке", html_three_days)

                    cursor.execute("""UPDATE user_subscription SET status_send = TRUE WHERE email = %s""", (email,))

                except Exception as ex:
                    print(f"ERROR | three_days_email: {ex}")

    except Exception as ex:
        print(f"ERROR | check_main_status_subscription: {ex}")

    finally:
        connect.commit()
        connect.close()