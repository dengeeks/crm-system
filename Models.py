from flask_login import UserMixin
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Admins(db.Model, UserMixin):

    __tablename__ = "admins"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.Text, nullable=True)
    password = db.Column(db.Text, nullable=False)
    role = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<Admin: {self.id}>'

class Users(db.Model, UserMixin):

    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(20), nullable=True)
    company_name = db.Column(db.String(100), nullable=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    code_auth = db.Column(db.String(100), nullable=True)  # Новое поле

    def __repr__(self):
        return f'<User {self.id}>'

#Список CRM систем пользователя
class List_CRMs(db.Model):

    __tablename__ = "list_crms"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)  # Внешний ключ к пользователю
    title_branches = db.Column(db.Text, nullable=False)
    description_branches = db.Column(db.Text, nullable=True)
    crm_system = db.Column(db.Text, nullable=True)  # Название CRM-системы
    whatsapp_session = db.Column(db.Text, nullable=True)  # Путь к сессии WhatsApp
    tg_token = db.Column(db.Text, nullable=True)  # Telegram Token
    link_tgbot = db.Column(db.Text, nullable=True)
    time_send = db.Column(db.Integer, nullable=True)
    status_job = db.Column(db.Boolean, default=False)
    url_website = db.Column(db.Text)

    def __repr__(self):
        return f'<List_CRMs {self.id}>'

class SecretKeys(db.Model):

    __tablename__ = "secretkeys"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    crm_id = db.Column(db.Integer, nullable=False)
    type_key = db.Column(db.Text, nullable=False)
    key_value = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<SecretKeys {self.id}>'

class WhatsAppChat(db.Model):

    __tablename__ = "whatsappchat"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    crm_id = db.Column(db.Integer, nullable=False)
    title_message = db.Column(db.Text, nullable=True)
    text_message = db.Column(db.Text, nullable=True)
    type_app = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<WhatsAppChat {self.id}>'

class Clients(db.Model):

    __tablename__ = "clients"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    crm_id = db.Column(db.Integer, nullable=False)
    fullname_clients = db.Column(db.Text, nullable=True)
    phone_number = db.Column(db.Text, nullable=True)
    telegram_id = db.Column(db.BigInteger, nullable=True)
    time_prise = db.Column(db.Text, nullable=True)
    telegram_status = db.Column(db.Boolean, default=False) #Если True значит не будет использовать WhatsApp
    whatsapp_status = db.Column(db.Boolean, default=False) #Если Tg_status False, значит отправляем.
    status_first_send = db.Column(db.Boolean, default=False) #Статус отправки сообщения на оценку
    status_last_send = db.Column(db.Boolean) #Статус отправки после оценки. После первого сообщения ставим статус False, чтобы случайно не отправить два раза!
    order_count = db.Column(db.Integer, nullable=True) #Счетчик заказов
    status_bot = db.Column(db.Boolean, default=True) #Вкл&Выкл получение сообщений

    def __repr__(self):
        return f'<Clients {self.id}>'

class TemplateMessage(db.Model):

    __tablename__ = "templatemessage"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, nullable=False)
    crm_id = db.Column(db.Integer, nullable=False)
    message1 = db.Column(db.Text, nullable=True)
    message2 = db.Column(db.Text, nullable=True)
    message3 = db.Column(db.Text, nullable=True)
    type_send = db.Column(db.Text, nullable=False)

    def __repr__(self):
        return f'<TemplateMessage {self.id}>'

class UserSubscription(db.Model):

    __tablename__ = "user_subscription"

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.Text, nullable=False)
    date_beg = db.Column(db.Text, nullable=True)
    date_end = db.Column(db.Text, nullable=True)
    status_subscription = db.Column(db.Boolean, default=False)
    status_send = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f'<UserSubscription {self.id}>'

class SendMessageClient(db.Model):

    __tablename__ = "sendmessageclient"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, nullable=False)
    crm_id = db.Column(db.Integer, nullable=False)
    phone_number = db.Column(db.Text, nullable=True)
    telegram_id = db.Column(db.BigInteger, nullable=True)
    message = db.Column(db.Text, nullable=True)
    send_date = db.Column(db.Text, nullable=True)
    type_sender = db.Column(db.Text, nullable=True)
    type_send = db.Column(db.Text, nullable=True)
    real_date_send = db.Column(db.Text, nullable=True)
    client_mark = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<SendMessageClient {self.id}>'

class ElectronicApplication(db.Model):

    __tablename__ = "electronicapplication"

    id = db.Column(db.Integer, primary_key=True)
    full_name = db.Column(db.Text, nullable=False)
    email = db.Column(db.Text, nullable=False)
    phone_number = db.Column(db.Text, nullable=False)
    name_company = db.Column(db.Text, nullable=False)
    description = db.Column(db.Text, nullable=True)

    def __repr__(self):
        return f'<ElectronicApplication {self.id}>'