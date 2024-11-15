# SystemControl
import datetime
import os
import random
import re
import shutil
import string
import threading
import time
from io import BytesIO

import jwt
import pandas as pd
from apscheduler.schedulers.asyncio import AsyncIOScheduler
# Flask
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask import send_file
from flask_admin import Admin
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from sqlalchemy import desc
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

# Local system
from Env_Config import Database_setting, Keys
# Database
from Models import (db, Users, List_CRMs, WhatsAppChat, SecretKeys, Clients, TemplateMessage, SendMessageClient,
                    ElectronicApplication, Admins, UserSubscription)
from def_AdminApp_setting import (setup_application, DashboardAdmin, AdminModelView, UsersModelView,
                                  UserSubscriptionModelView, ListCRMsModelView)
from def_CheckSubscriptionUser import CheckSubscriptionUser
from def_GetBranchesLink import send_email_order_link
from def_SendEmailApplication import send_email_application
from def_SendEmailCode import send_email_code
from def_SendOneManyClient import send_manyoneclient
# DefSystem
from def_WhatsAppAuthCode import whatsapp_authenticate
from def_getChatWhatsApp import get_ChatWhatsApp
from def_sendFirstMessageWhatsAppp import StartMessageStream_first
from def_sendLastMessageWhatsApp import StartMessageStream_last

application = Flask(__name__, template_folder = "templates", static_folder = 'static')
application.config[
    'SQLALCHEMY_DATABASE_URI'] = f"postgresql://{Database_setting['user']}:{Database_setting['password']}@{Database_setting['host']}/{Database_setting['database']}"
application.config['SECRET_KEY'] = 'k7GJQ9DjJrCz0W19'
application.secret_key = 'k7GJQ9DjJrCz0W19'

db.init_app(application)

login_manager = LoginManager()
login_manager.init_app(application)
login_manager.login_view = 'login_page'

scheduler = AsyncIOScheduler()


@login_manager.user_loader
def load_user(user_id):
    # Определение типа пользователя по модели
    user = Users.query.get(int(user_id))
    if not user:
        user = Admins.query.get(int(user_id))
    return user


def generate_confirmation_code(length = 6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k = length))


# Страница логина
@application.route("/admin/login", methods = ['POST', 'GET'])
def admin_login():
    if request.method == "POST":
        admin_login = request.form['admin_login']
        admin_password = request.form['admin_password']

        admin = Admins.query.filter_by(username = admin_login).first()

        if admin and admin.password == admin_password:  # Проверяем логин и пароль
            if admin.username == "General_admin":
                session['General_admin'] = True  # Устанавливаем флаг в сессии
                login_user(admin)  # Используем login_user из Flask-Login для админа
                return redirect(url_for("admin.index"))  # Перенаправляем на админку
        else:
            flash('Неправильный логин или пароль', 'error')

    return render_template("Admin_login_page.html")


@application.route("/", methods = ["GET", "POST"])
def home_page():
    return render_template("index.html")


@application.route("/GetElectronicApplication", methods = ['POST', 'GET'])
def get_electronic_application():
    if request.method == 'POST':
        full_name = request.form.get('full_name')
        email = request.form.get('email')
        phone_number = request.form.get('phone_number')
        name_company = request.form.get('company_name')
        description = request.form.get('description')

        print(full_name, email, phone_number, name_company, description)

        # Создаем новый объект заявки
        new_application = ElectronicApplication(
            full_name = full_name,
            email = email,
            phone_number = phone_number,
            name_company = name_company,
            description = description
        )

        try:
            # Добавляем новый объект в сессию и сохраняем в базе данных
            db.session.add(new_application)
            db.session.commit()
            # Отправки заявки на посты владельцу и пользователю
            send_email_application(full_name, email, phone_number, name_company, description)
        except Exception as e:
            db.session.rollback()  # Откатываем транзакцию в случае ошибки
            print(f'Error: {e}')

    return redirect(url_for("home_page"))


# Отправка заявки на почту
@login_required
@application.route("/GetBranchesLink", methods = ['POST', "GET"])
def get_branches_link():
    if request.method == "POST":
        user_id = current_user.id
        crm_id = request.form.get("crm_id")
        link = request.form.get("link")

        user = Users.query.filter_by(id = user_id).first()
        crm_system = List_CRMs.query.filter_by(id = crm_id, user_id = user_id).first()

        if user:
            if crm_system:
                name_branches = crm_system.title_branches
                fullname = user.full_name
                email = user.email

                thread = threading.Thread(target = send_email_order_link, args = (fullname, email, name_branches, link))
                thread.start()
                return redirect(url_for("dashboard_branches"))
    return redirect(url_for("dashboard_branches"))


@application.route("/Login", methods = ["GET", "POST"])
def login_page():
    if request.method == "POST":
        email = request.form.get('email')
        password = request.form.get('password')

        if not email or not password:
            flash('Email и пароль обязательны для ввода', 'error')
            return render_template("Login_page.html")

        user = Users.query.filter_by(email = email).first()
        if user and check_password_hash(user.password, password):
            login_user(user)  # Используем login_user из Flask-Login
            return redirect(url_for('dashboard_statistics'))
        else:
            flash('Неправильный email или пароль', 'error')

    return render_template("Login_page.html")


@application.route("/Registration", methods = ["GET", "POST"])
def registration_page():
    if request.method == "POST":
        full_name = request.form.get('full_name')
        phone_number = request.form.get('phone_number')
        company_name = request.form.get('company_name')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')

        if password != confirm_password:
            return render_template("Registration_page.html")

        if Users.query.filter_by(email = email).first():
            return render_template("Registration_page.html")

        # Создаем временную запись пользователя
        confirmation_code = generate_confirmation_code()
        session['registration_data'] = {
            'full_name': full_name,
            'phone_number': phone_number,
            'company_name': company_name,
            'email': email,
            'password': generate_password_hash(password),
            'confirmation_code': confirmation_code
        }

        # Отправляем письмо с кодом подтверждения (реализуйте эту функцию по необходимости)
        thread = threading.Thread(target = send_email_code, args = (email, confirmation_code))
        thread.start()

    return render_template("Registration_page.html")


@application.route("/ConfirmCode", methods = ["POST"])
def confirm_code():
    confirmation_code = request.form.get('confirmation_code')
    registration_data = session.get('registration_data')

    if not registration_data:
        return redirect('/Registration')

    if confirmation_code != registration_data['confirmation_code']:
        return render_template("Registration_page.html")

    # Сохраняем данные пользователя в базе данных
    new_user = Users(
        full_name = registration_data['full_name'],
        phone_number = registration_data['phone_number'],
        company_name = registration_data['company_name'],
        email = registration_data['email'],
        password = registration_data['password'],
        code_auth = confirmation_code
    )

    new_user_sub = UserSubscription(
        email = registration_data['email']
    )

    db.session.add(new_user)
    db.session.add(new_user_sub)
    db.session.commit()

    # Очищаем данные из сессии
    session.pop('registration_data', None)

    return redirect('/Login')


# Проверка на дубликат почты
@application.route("/check_email", methods = ["POST"])
def check_email():
    email = request.json.get("email")
    user = Users.query.filter_by(email = email).first()
    return jsonify({"exists": user is not None})


@application.route("/Dashboard_statistics", methods = ["GET"])
@login_required
def dashboard_statistics():
    # Получаем текущего пользователя по его id
    user = Users.query.filter_by(id = current_user.id).first()

    # Предполагается, что ФИО разделены пробелами
    full_name_parts = current_user.full_name.split()
    first_name = full_name_parts[1]  # Получаем имя (первый элемент)

    if user:
        # Проверяем статус подписки
        subscription = UserSubscription.query.filter_by(email = user.email).first()

        if subscription and not subscription.status_subscription:
            return render_template("DashBoard_statistics.html", subscription_expired = True, first_name = first_name)

    return render_template("DashBoard_statistics.html", first_name = first_name, subscription_expired = False)


@application.route("/Dashboard_branches")
@login_required
def dashboard_branches():
    # Получаем текущего пользователя по его id
    user = Users.query.filter_by(id = current_user.id).first()

    # Предполагается, что ФИО разделены пробелами
    full_name_parts = current_user.full_name.split()
    first_name = full_name_parts[1] if len(full_name_parts) > 1 else full_name_parts[0]

    # Проверяем статус подписки
    subscription = UserSubscription.query.filter_by(email = user.email).first()

    # Получение CRM-систем для текущего пользователя
    list_crm = List_CRMs.query.filter_by(user_id = current_user.id).all()

    # Обрабатываем поле whatsapp_Session и выделяем номера телефонов для каждой CRM
    crm_with_phones = []
    for crm in list_crm:
        whatsapp_session = crm.whatsapp_session
        if whatsapp_session:
            # Поиск номера телефона в строке
            phone_match = re.search(r"\+[\d\s-]+", whatsapp_session)
            if phone_match:
                # Убираем пробелы и дефисы из номера
                phone_number = re.sub(r"[\s-]", "", phone_match.group())
            else:
                phone_number = None

            crm_with_phones.append(
                {
                    'crm': crm,  # CRM объект
                    'phone_number': phone_number  # Найденный номер телефона или None
                }
            )
        else:
            crm_with_phones.append(
                {
                    'crm': crm,
                    'phone_number': None
                }
            )

    # Проверка подписки
    if subscription and not subscription.status_subscription:
        return render_template(
            "Dashboard_branches.html", crm_systems = crm_with_phones, subscription_expired = True,
            first_name = first_name
            )

    return render_template(
        "Dashboard_branches.html", crm_systems = crm_with_phones, subscription_expired = False, first_name = first_name
        )


@application.route('/update_time', methods = ['POST'])
def update_time():
    data = request.get_json()
    crm_id = data.get('crm_id')
    time_send = data.get('time_send')

    # Ищем CRM по ID
    crm = List_CRMs.query.get(crm_id)
    if crm:
        crm.time_send = time_send  # Обновляем время отправки
        db.session.commit()  # Сохраняем изменения в базе данных
        return jsonify(success = True)
    return jsonify(success = False)


@application.route("/Dashboard_MessageLog", methods = ['GET', 'POST'])
@login_required
def dashboard_messagelog():
    user = Users.query.filter_by(id = current_user.id).first()
    # Проверяем статус подписки
    subscription = UserSubscription.query.filter_by(email = current_user.email).first()
    subscription_expired = not subscription or not subscription.status_subscription

    # Предполагается, что ФИО разделены пробелами
    full_name_parts = current_user.full_name.split()
    first_name = full_name_parts[1] if len(full_name_parts) > 1 else full_name_parts[0]

    # Получаем список всех CRM для отображения в форме
    crms = List_CRMs.query.filter_by(user_id = user.id).all()

    # Инициализируем данные для передачи в шаблон
    data = []
    selected_branch_title = 'Не выбран филиал'  # Значение по умолчанию для названия филиала

    # Обработка POST-запроса для фильтрации данных
    if request.method == 'POST':
        crm_id = request.form.get('crm_id')

        if crm_id:
            # Получаем данные для выбранной CRM
            data = SendMessageClient.query.filter_by(crm_id = crm_id).order_by(desc(SendMessageClient.id)).all()

            # Находим название выбранного филиала
            selected_crm = List_CRMs.query.filter_by(id = crm_id).first()
            if selected_crm:
                selected_branch_title = selected_crm.title_branches

    return render_template(
        "Dashboard_MessageLog.html",
        first_name = first_name,
        crms = crms,
        data = data,
        selected_branch_title = selected_branch_title,
        subscription_expired = subscription_expired
        )


@application.route("/Dashboard_settings")
@login_required
def dashboard_settings():
    # Проверка статуса подписки
    subscription = UserSubscription.query.filter_by(email = current_user.email).first()
    subscription_expired = not subscription or not subscription.status_subscription

    # Предполагается, что ФИО разделены пробелами
    full_name_parts = current_user.full_name.split()
    first_name = full_name_parts[1] if len(full_name_parts) > 1 else full_name_parts[0]

    return render_template(
        "Dashboard_settings.html",
        first_name = first_name,
        subscription_expired = subscription_expired
        )


@application.route('/update_password', methods = ['POST'])
@login_required
def update_password():
    old_password = request.form.get('old_password')
    new_password = request.form.get('new_password')
    confirm_new_password = request.form.get('confirm_new_password')

    user = Users.query.get(current_user.id)

    if not check_password_hash(user.password, old_password):
        flash('Старый пароль неверный.', 'error')
        return redirect(url_for('dashboard_settings'))

    if new_password != confirm_new_password:
        flash('Новые пароли не совпадают.', 'error')
        return redirect(url_for('dashboard_settings'))

    user.password = generate_password_hash(new_password)
    db.session.commit()
    flash('Пароль успешно изменен.', 'success')
    return redirect(url_for('dashboard_settings'))


@application.route('/validate_old_password', methods = ['POST'])
@login_required
def validate_old_password():
    if request.content_type != 'application/json':
        return jsonify({"status": "error", "message": "Неправильный формат данных"}), 415

    data = request.get_json()
    old_password = data.get('old_password')

    if old_password is None:
        return jsonify({"status": "error", "message": "Не указан старый пароль"}), 400

    user = Users.query.get(current_user.id)

    if user and check_password_hash(user.password, old_password):
        return jsonify({"status": "success"})
    else:
        return jsonify({"status": "error", "message": "Старый пароль неверный."})


@application.route("/Dashboard_chats/WhatsApp")
@login_required
def dashboard_chats_whatsapp():
    full_name_parts = current_user.full_name.split()
    first_name = full_name_parts[1] if len(full_name_parts) > 1 else full_name_parts[0]

    crm_systems = List_CRMs.query.filter_by(user_id = current_user.id).all()

    # Проверяем статус подписки
    user = Users.query.filter_by(id = current_user.id).first()
    subscription = UserSubscription.query.filter_by(email = user.email).first()
    subscription_expired = subscription and not subscription.status_subscription

    return render_template(
        "Dashboard_chats_whatsapp.html", first_name = first_name, crm_systems = crm_systems,
        subscription_expired = subscription_expired
        )


@application.route("/get_chats/<int:crm_id>", methods = ["GET"])
@login_required
def get_chats_whatsapp(crm_id):
    print(crm_id)
    chats = WhatsAppChat.query.filter_by(user_id = current_user.id, crm_id = crm_id).all()
    chats_data = []
    for chat in chats:
        first_message = chat.text_message.split('\n', 1)[0] if chat.text_message else ''
        chats_data.append(
            {
                "id": chat.id,
                "title_message": chat.title_message,
                "text_message": first_message
            }
        )
    return jsonify(chats_data)


@application.route("/get_chat_messages/<int:chat_id>", methods = ["GET"])
@login_required
def get_chat_messages_whatsapp(chat_id):
    messages = WhatsAppChat.query.filter_by(id = chat_id).all()
    if not messages:
        return jsonify({"error": "No messages found"}), 404  # Добавляем обработку случая, когда сообщений нет
    messages_data = [{"text_message": message.text_message} for message in messages]
    return jsonify(messages_data)


@application.route("/Dashboard_chats/Telegram")
@login_required
def dashboard_chats_telegram():
    full_name_parts = current_user.full_name.split()
    first_name = full_name_parts[1] if len(full_name_parts) > 1 else full_name_parts[0]

    crm_systems = List_CRMs.query.filter_by(user_id = current_user.id).all()

    return render_template("Dashboard_chats_telegram.html", first_name = first_name, crm_systems = crm_systems)


@application.route("/refresh_chats", methods = ['POST'])
@login_required
def refresh_chats():
    user_id = current_user.id
    crm_id = request.form.get('crm_id')
    print(crm_id)
    # Проверяем статус подписки
    user = Users.query.filter_by(id = user_id).first()
    subscription = UserSubscription.query.filter_by(email = user.email).first()

    if not subscription or not subscription.status_subscription:
        return redirect(url_for("dashboard_chats_whatsapp"))

    # Устанавливаем статус выполнения задачи в сессии
    session[f'task_status_{user_id}_{crm_id}'] = 'in_progress'

    # Запускаем задачу в фоновом потоке
    thread = threading.Thread(target = get_ChatWhatsApp, args = (user_id, crm_id))
    thread.daemon = True
    thread.start()

    return redirect(url_for("dashboard_chats_whatsapp"))


@application.route('/Dashboard_SendManyClient', methods = ['GET', 'POST'])
def dashboard_sendmanyclient():
    full_name_parts = current_user.full_name.split()
    first_name = full_name_parts[1] if len(full_name_parts) > 1 else full_name_parts[0]

    # Получаем CRM системы, привязанные только к текущему пользователю
    crm_systems = List_CRMs.query.filter_by(user_id = current_user.id).all()
    return render_template('Dashboard_SendOneManyClient.html', crm_systems = crm_systems, first_name = first_name)


@application.route('/import_excel', methods = ['POST'])
def import_excel():
    crm_id = request.form['crm_id']  # Получаем ID филиала
    file = request.files['excel_file']  # Получаем файл

    if file:
        # Сохраните файл на сервере (по желанию)
        filename = secure_filename(file.filename)
        file_path = os.path.join('instance/Excel', filename)
        file.save(file_path)

        # Чтение данных из Excel с помощью pandas
        data = pd.read_excel(file_path)

        # Проход по каждой строке файла и запись данных в БД
        for index, row in data.iterrows():
            new_client = Clients(
                user_id = current_user.id,  # предположим, что у тебя есть текущий пользователь
                crm_id = crm_id,
                fullname_clients = row['ФИО клиента'],  # Названия колонок должны совпадать с Excel
                phone_number = row['Телефон клиента'],
                telegram_status = row['Статус Telegram'],
                status_first_send = None,
                status_last_send = None,
                whatsapp_status = row['Статус WhatsApp'],
                order_count = row['Кол-во заказов'],
                status_bot = row['Статус бота']
            )
            db.session.add(new_client)

        # Сохранение изменений в БД
        db.session.commit()

        flash('Файл успешно загружен и данные сохранены в БД!')
    else:
        flash('Ошибка: файл не выбран.')

    return redirect(url_for('dashboard_sendmanyclient'))


@login_required
@application.route("/export_clients_to_excel", methods = ["GET"])
def export_clients_to_excel():
    user_id = current_user.id

    # Получаем данные из таблиц
    crms = List_CRMs.query.filter_by(user_id = user_id).all()
    clients = Clients.query.filter_by(user_id = user_id).all()

    # Подготовка данных для экспорта
    data = []
    for crm in crms:
        for client in clients:
            if client.crm_id == crm.id:
                data.append(
                    {
                        "Название филиала": crm.title_branches,
                        "ФИО": client.fullname_clients,
                        "Номер телефона": client.phone_number,
                        "Telegram ID": client.telegram_id,
                        "Telegram статус": (
                            "Включен" if client.telegram_status else
                            "Отключен" if client.telegram_status is False else
                            "Отсутствует"
                        ),
                        "WhatsApp статус": (
                            "Включен" if client.whatsapp_status else
                            "Отключен" if client.whatsapp_status is False else
                            "Отсутствует"
                        ),
                        "Количество заказов": client.order_count,
                        "Статус рассылки": (
                            "Включен" if client.status_bot else
                            "Выключен"
                        )
                    }
                )

    # Создаем DataFrame и экспортируем в память (BytesIO)
    df = pd.DataFrame(data)
    output = BytesIO()
    with pd.ExcelWriter(output, engine = 'openpyxl') as writer:
        df.to_excel(writer, index = False)
    output.seek(0)

    # Отправляем файл пользователю для скачивания
    return send_file(
        output, as_attachment = True, download_name = "clients_export.xlsx",
        mimetype = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )


@application.route('/get_clients/<int:crm_id>', methods = ['GET'])
def get_clients(crm_id):
    # Получаем клиентов, связанных с конкретной CRM системой
    clients = Clients.query.filter_by(crm_id = crm_id).all()
    clients_data = [
        {
            'id': client.id,
            'fullname_clients': client.fullname_clients,
            'phone_number': client.phone_number,
            'telegram_status': client.telegram_status,
            'whatsapp_status': client.whatsapp_status,
            'status_bot': client.status_bot,
            'order_count': client.order_count
        } for client in clients
    ]
    return jsonify({'clients': clients_data})


@application.route('/send_manyoneclient', methods = ['POST'])
def send_message():
    data = request.json
    selected_clients = data.get('selected_clients')
    message = data.get('message')
    crm_id = data.get('crm_id')  # Получаем crm_id
    user_id = current_user.id

    # Запуск функции по отправке индивидуальных сообщений в отдельном потоке
    thread = threading.Thread(target = send_manyoneclient, args = (user_id, crm_id, selected_clients, message))
    thread.start()

    return jsonify({'status': 'success'})


@application.route("/Dashboard/TemplateMessage", methods = ['GET', 'POST'])
@login_required
def dashboard_template_message():
    # Проверка статуса подписки
    subscription = UserSubscription.query.filter_by(email = current_user.email).first()
    subscription_expired = not subscription or not subscription.status_subscription

    # Предполагается, что ФИО разделены пробелами
    full_name_parts = current_user.full_name.split()
    first_name = full_name_parts[1] if len(full_name_parts) > 1 else full_name_parts[0]

    # Получаем CRM системы для текущего пользователя
    crm_systems = List_CRMs.query.filter_by(user_id = current_user.id).all()

    # Обработка POST-запроса
    if request.method == 'POST':
        crm_id = request.form.get('crm_id')
        message1 = request.form.get('message1')
        message2 = request.form.get('message2')
        message3 = request.form.get('message3')
        type_send = request.form.get('send_type')

        if not subscription_expired:
            # Обновляем или добавляем сообщение шаблона
            template_message = TemplateMessage.query.filter_by(user_id = current_user.id, crm_id = crm_id).first()

            if template_message:
                template_message.message1 = message1
                template_message.message2 = message2
                template_message.message3 = message3
                template_message.type_send = type_send
            else:
                new_template_message = TemplateMessage(
                    user_id = current_user.id,
                    crm_id = crm_id,
                    message1 = message1,
                    message2 = message2,
                    message3 = message3,
                    type_send = type_send
                )
                db.session.add(new_template_message)

            db.session.commit()

        return redirect(url_for("dashboard_template_message"))

    return render_template(
        "Dashbaord_template_message.html",
        first_name = first_name,
        crm_systems = crm_systems,
        subscription_expired = subscription_expired
        )


@application.route("/client_bot_management", methods = ['POST', 'GET'])
def client_bot_management():
    if request.method == 'POST':
        data = request.get_json()  # Получаем данные в формате JSON
        phone_number = data.get('phoneNumber')
        status = data.get('status')

        print(status)

        # Преобразование статуса в boolean
        if status == "true":
            status = True
        elif status == "false":
            status = False

        # Поиск клиента по номеру телефона
        client = Clients.query.filter_by(phone_number = phone_number).first()

        if client:
            client.status_bot = status
            db.session.commit()
            return jsonify({'success': True, 'message': 'Client status updated'})
        else:
            return jsonify({'success': False, 'message': 'Client not found'})

    return render_template('btn_off_on.html')


@application.route("/get_messages/<int:crm_id>", methods = ['GET'])
@login_required
def get_messages(crm_id):
    # Ищем шаблон сообщения для текущего пользователя и выбранного филиала (crm_id)
    template_message = TemplateMessage.query.filter_by(user_id = current_user.id, crm_id = crm_id).first()

    if template_message:
        # Если шаблон найден, возвращаем его данные
        return jsonify(
            {
                'message1': template_message.message1,
                'message2': template_message.message2,
                'message3': template_message.message3,
                'type_send': template_message.type_send
            }
        )
    else:
        # Если шаблон не найден, возвращаем пустые значения
        return jsonify(
            {
                'message1': '',
                'message2': '',
                'message3': '',
                'type_send': ''
            }
        )


@application.route('/get_crm_id', methods = ['GET'])
def get_crm_id():
    user_id = request.args.get('user_id')  # Получаем user_id из GET-параметров

    # Поиск CRM-системы по user_id
    list_crm_record = List_CRMs.query.filter_by(user_id = user_id).first()

    if list_crm_record:
        return jsonify({'crm_id': list_crm_record.id}), 200
    else:
        return jsonify({'error': 'CRM record not found'}), 404


@application.route('/generate_word/<int:crm_id>')
@login_required
def generate_word(crm_id):
    user_id = current_user.id
    # Найти CRM-систему по id и user_id
    crm_system = List_CRMs.query.filter_by(id = crm_id, user_id = user_id).first()

    if crm_system:
        # Проверить, существует ли уже ключ для этого пользователя и CRM
        existing_key = SecretKeys.query.filter_by(user_id = user_id, crm_id = crm_id).first()

        if existing_key:
            # Если ключ уже существует, вернуть его
            return jsonify(word = existing_key.key_value)

        # Генерация случайного слова (например, 8 символов из букв латинского алфавита)
        random_word = ''.join(random.choices(string.ascii_letters, k = 8))  # Генерирует случайное слово из 8 букв

        # Генерация случайного числа
        random_number = random.randint(1000, 9999)  # Генерирует случайное число от 1000 до 9999

        # Формирование токена с добавлением случайного слова и числа
        token = f"{user_id}_{crm_id}_{crm_system.crm_system}_{random_word}{random_number}"

        # Кодирование токена с использованием jwt
        encode_token = jwt.encode({'token': token}, application.secret_key, algorithm = 'HS256')

        # Сохранение сгенерированного токена в базу данных
        new_key = SecretKeys(
            user_id = user_id,
            crm_id = crm_id,
            type_key = Keys['SecretWebhook'],  # предполагается, что это id CRM или тип ключа
            key_value = encode_token
        )

        # Добавление и коммит изменений в базе данных
        db.session.add(new_key)
        db.session.commit()

        # Вернуть сгенерированный ключ
        return jsonify(word = encode_token)

    else:
        return jsonify(error = 'CRM system not found'), 404


"""Теперь это функция просто добавляет филиал"""


@application.route('/add_branches', methods = ['POST', 'GET'])
@login_required
def add_branches():
    if request.method == 'POST':
        # Получение данных из формы
        crm_system = request.form.get('crm-system')
        title_branches = request.form.get('Title_branches')
        description_branches = request.form.get("Description_branches")
        telegram_token = request.form.get('Telegram_bot')

        user_id = current_user.id

        new_crm_system = List_CRMs(
            user_id = user_id,
            title_branches = title_branches,
            description_branches = description_branches,
            crm_system = crm_system
        )

        db.session.add(new_crm_system)
        db.session.commit()

        return redirect(url_for("dashboard_branches"))

    return redirect(url_for("dashboard_branches"))


"""Ранее /activate - теперь будет перезаписывать и активиировать сессию WH"""


@application.route('/connect_whatsapp', methods = ['POST'])
@login_required
def activate():
    if request.method == "POST":
        data = request.get_json()
        crm_id = data.get('crm_id')
        user_id = current_user.id
        phone = data.get('phone')

        random_number = random.randint(0, 99999)

        whatsapp_session = f"instance/Profile_whatsapp/{user_id}_{phone}_{random_number}"

        # Запуск функции в другом потоке
        thread = threading.Thread(target = whatsapp_authenticate, args = (user_id, crm_id, phone, whatsapp_session))
        thread.start()

        # Получение пользователя из базы данных
        user = session.get(Users, int(user_id))

        # Возвращаем ответ
        return jsonify({"success": True})


@application.route('/disconnect_whatsapp', methods = ['POST'])
def disconnect_whatsapp():
    data = request.json
    crm_id = data.get('crm_id')

    if not crm_id:
        return jsonify({'status': 'error', 'message': 'CRM ID is required'}), 400

    try:
        # Обновление таблицы clients
        clients = Clients.query.filter_by(crm_id = crm_id).all()
        for client in clients:
            client.time_prise = None
            client.whatsapp_status = True
            client.status_first_send = True
            client.status_last_send = True

        db.session.commit()

        # Обновление таблицы list_crms
        crm = List_CRMs.query.filter_by(id = crm_id).first()

        if crm:
            # Получение пути к сессии WhatsApp
            whatsapp_session = crm.whatsapp_session

            if whatsapp_session:
                # Удаление папки, если она существует
                if os.path.exists(whatsapp_session):
                    shutil.rmtree(whatsapp_session)
                else:
                    return jsonify({'status': 'error', 'message': 'WhatsApp session folder does not exist'}), 404

            # Очистка поля whatsapp_session и обновление статуса CRM
            crm.whatsapp_session = None
            crm.status_job = False
            db.session.commit()

            return jsonify(
                {
                    'status': 'success',
                    'message': 'WhatsApp disconnected successfully'
                }
            ), 200
        else:
            return jsonify({'status': 'error', 'message': 'CRM not found'}), 404
    except Exception as e:
        db.session.rollback()
        return jsonify({'status': 'error', 'message': str(e)}), 500


@application.route("/restart_bot", methods = ['POST'])
@login_required
def restart_bot():
    # Получаем ID CRM системы из формы
    crm_id = request.form.get("crm_id")

    # Проверяем статус подписки
    user = Users.query.filter_by(id = current_user.id).first()
    subscription = UserSubscription.query.filter_by(email = user.email).first()

    if not subscription or not subscription.status_subscription:
        # Если подписка истекла, перенаправляем на страницу без выполнения кода
        return redirect(url_for("dashboard_branches"))

    # Выполняем запуск бота
    crm_record = List_CRMs.query.filter_by(id = crm_id, user_id = current_user.id).first()

    if crm_record:
        crm_record.status_job = True
        db.session.commit()

    """перезапуск телеграм бота"""
    # telegram_token = request.form.get("telegram_token")
    # user_id = current_user.id

    # # Остановка предыдущего бота, если он существует
    # if (telegram_token, user_id) in active_bots:
    #     stop_event = bot_stop[telegram_token, user_id]
    #     stop_event.set()  # Сообщаем боту остановиться
    #     active_bots[telegram_token, user_id].join()  # Ждем завершения потока
    #     print("Previous bot stopped.")
    #
    # # Создание нового события для нового бота
    # stop_event = threading.Event()
    # bot_stop[telegram_token, user_id] = stop_event
    # bot_thread = threading.Thread(target=RunBotCore, args=(telegram_token, user_id, stop_event))
    # bot_thread.start()
    # active_bots[telegram_token, user_id] = bot_thread

    return redirect(url_for("dashboard_branches"))


@application.route('/stop_bot', methods = ['POST'])
@login_required
def stop_bot():
    # Получаем ID CRM системы из формы
    crm_id = request.form.get("crm_id")

    # Проверяем статус подписки
    user = Users.query.filter_by(id = current_user.id).first()
    subscription = UserSubscription.query.filter_by(email = user.email).first()

    if not subscription or not subscription.status_subscription:
        # Если подписка истекла, перенаправляем на страницу без выполнения кода
        return redirect(url_for("dashboard_branches"))

    # Выполняем остановку бота
    crm_record = List_CRMs.query.filter_by(id = crm_id, user_id = current_user.id).first()

    if crm_record:
        crm_record.status_job = False
        db.session.commit()

    """Остановка телеграм бота"""
    # telegram_token = request.form.get("telegram_token")
    # user_id = current_user.id
    #
    # if (telegram_token, user_id) in bot_stop:
    #     stop_event = bot_stop[(telegram_token, user_id)]
    #     stop_event.set()  # Устанавливаем сигнал для остановки

    return redirect(url_for("dashboard_branches"))  # Redirect after stopping


# Webhook CRM систем
@application.route('/webhook', methods = ['POST'])
def webhook():
    metadata = request.get_json()
    metadata_key = metadata['Key']
    client_name = metadata['User']['Full_name']
    client_phone = metadata['User']['Phone']
    key = jwt.decode(metadata_key, application.secret_key, algorithms = 'HS256')
    token = key['token']

    user_id = token.split("_")[0]
    crm_id = token.split("_")[1]
    crm_system = token.split("_")[2]
    time_prise = datetime.datetime.now().strftime("%d-%m-%Y %H-%M-%S")
    # Приведение номера клиента к единому формату без лишних символов
    formatted_client_phone = client_phone.split(" ")[0]  # Берем только основную часть номера до пробела

    # Проверка существования типа отправки и клиента в базе
    check_send_type = TemplateMessage.query.filter_by(crm_id = crm_id, user_id = user_id).first()
    client = Clients.query.filter_by(user_id = user_id, crm_id = crm_id).filter(
        Clients.phone_number.like(f"{formatted_client_phone}%")
        ).first()

    # Если клиент найден, обновляем его данные
    if client:
        # Обновление статуса в зависимости от типа отправки
        if check_send_type:
            if check_send_type.type_send == "multiple":
                client.status_first_send = False
                client.status_last_send = None
                client.time_prise = time_prise
                client.fullname_clients = client_name
                client.order_count += 1  # Для single просто увеличиваем счетчик
            elif check_send_type.type_send == "single":
                client.order_count += 1  # Для single просто увеличиваем счетчик
    else:
        # Если клиент не найден, создаем новую запись
        new_client = Clients(
            user_id = user_id,
            crm_id = crm_id,
            fullname_clients = client_name,
            phone_number = client_phone,
            time_prise = time_prise,
            order_count = 1,
            status_first_send = False,  # Новым клиентам присваиваем базовые значения
            status_last_send = None
        )
        db.session.add(new_client)

    # Сохраняем изменения в базе
    db.session.commit()

    return jsonify(
        {
            'status': 'ok',
            'client_data': {
                'name': client_name,
                'phone': client_phone,
                'time': time_prise
            }
        }
    )


@application.route("/logout")
def logout():
    logout_user()
    session.clear()
    return redirect(url_for("home_page"))


# Страница выхода
@application.route('/admin/logout')
def admin_logout():
    session.pop('General_admin', None)  # Удаление данных из сессии
    return redirect(url_for('admin_login'))


def CheckSubscription_Background():
    while True:
        CheckSubscriptionUser()
        time.sleep(1)


def start_CheckSubscription_Background():
    thread = threading.Thread(target = CheckSubscription_Background)
    thread.daemon = True
    thread.start()


def start_WhatsAppEmailing_background():
    thread = threading.Thread(target = StartMessageStream_first)
    thread.daemon = True
    thread.start()


def start_WhatsAppEmailing_background_last_message():
    thread = threading.Thread(target = StartMessageStream_last)
    thread.daemon = True
    thread.start()


admin = Admin(application, template_mode = 'bootstrap4', index_view = DashboardAdmin())
admin.add_view(AdminModelView(Admins, db.session))
admin.add_view(UsersModelView(Users, db.session))
admin.add_view(AdminModelView(ElectronicApplication, db.session))
admin.add_view(UserSubscriptionModelView(UserSubscription, db.session))  # Используем кастомный ModelView
admin.add_view(ListCRMsModelView(List_CRMs, db.session))
if __name__ == "__main__":
    start_CheckSubscription_Background()
    start_WhatsAppEmailing_background()
    start_WhatsAppEmailing_background_last_message()
    # setup_application(application)
    application.run(debug = True, use_reloader = False)
