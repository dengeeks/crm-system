import smtplib
from Env_Config import Email_setting
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

def send_email_application(full_name, email, phone_number, name_company, description):
    # Инициализация SMTP сервера
    smtp_server = smtplib.SMTP("smtp.gmail.com", 587)
    smtp_server.starttls()
    smtp_server.login(f"{Email_setting['Email_sender']}", f"{Email_setting['Email_token']}")

    if description is None:
        description = "Описание отсутствует"

    # Отправка письма основателю
    try:
        msg = MIMEMultipart()
        msg["From"] = f"{Email_setting['Email_sender']}"
        msg['To'] = f"{Email_setting['Email_sender']}"
        msg["Subject"] = "Новая заявка на подключение"

        # Загрузка и подготовка HTML шаблона для основателя
        html_founder = "templates/Email_application_founder.html"
        with open(html_founder, 'r', encoding="utf-8") as file_founder:
            html_content_founder = file_founder.read()

        # Замена значений в HTML-шаблоне
        html_content_founder = html_content_founder.replace("{{ full_name }}", full_name)
        html_content_founder = html_content_founder.replace("{{ email }}", email)
        html_content_founder = html_content_founder.replace("{{ phone_number }}", phone_number)
        html_content_founder = html_content_founder.replace("{{ name_company }}", name_company)
        html_content_founder = html_content_founder.replace("{{ description }}", description)

        # Прикрепление HTML содержимого
        msg.attach(MIMEText(html_content_founder, "html"))

        # Отправка письма
        smtp_server.sendmail(f"{Email_setting['Email_sender']}", f"{Email_setting['Email_sender']}", msg.as_string())
    except Exception as ex:
        print(f"ERROR | html_founder: {ex}")

    # Отправка письма пользователю
    try:
        msg = MIMEMultipart()
        msg["From"] = f"{Email_setting['Email_sender']}"
        msg['To'] = email
        msg["Subject"] = "Ваша заявка успешно отправлена"

        # Загрузка и подготовка HTML шаблона для пользователя
        html_user = "templates/Email_application_user.html"
        with open(html_user, 'r', encoding="utf-8") as file_user:
            html_content_user = file_user.read()

        # Замена значений в HTML-шаблоне
        html_content_user = html_content_user.replace("Full_name", full_name)

        # Прикрепление HTML содержимого
        msg.attach(MIMEText(html_content_user, "html"))

        # Отправка письма
        smtp_server.sendmail(f"{Email_setting['Email_sender']}", email, msg.as_string())
    except Exception as ex:
        print(f"ERROR | html_user: {ex}")
    finally:
        smtp_server.quit()