import smtplib

from Env_Config import Email_setting

from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_code(recipient_email, confirmation_code):
    try:
        # Путь к шаблону в папке templates
        template_path = "templates/Email_code_confirm.html"

        # Загрузка HTML-шаблона из файла
        def load_html_template(file_path):
            with open(file_path, "r", encoding="utf-8") as file:
                return file.read()

        # Загрузка HTML-шаблона
        html_content = load_html_template(template_path)

        # Замените метку кода подтверждения на реальный код
        html_content = html_content.replace('CODE_REGISTRATION_CONFIRM', confirmation_code)

        # Устанавливаем соединение с сервером SMTP
        smtp_server = smtplib.SMTP("smtp.gmail.com", 587)
        smtp_server.starttls()
        smtp_server.login(f"{Email_setting['Email_sender']}", f"{Email_setting['Email_token']}")

        # Создание объекта сообщения
        msg = MIMEMultipart()
        msg["From"] = f"{Email_setting['Email_sender']}"
        msg["To"] = recipient_email
        msg["Subject"] = "Код подтверждения регистрации"

        # Прикрепляем HTML к сообщению
        msg.attach(MIMEText(html_content, "html"))

        # Отправка письма
        smtp_server.sendmail(f"{Email_setting['Email_sender']}", recipient_email, msg.as_string())

    except Exception as ex:
        print(f"ERROR | send_email_code_confirm: {ex}")
    finally:
        # Закрытие соединения
        smtp_server.quit()