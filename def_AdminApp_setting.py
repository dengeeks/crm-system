from flask import redirect, url_for, session
from flask_admin import Admin, expose
from flask_admin.base import AdminIndexView
from flask_admin.contrib.sqla import ModelView

from Models import (db, Admins, Users, ElectronicApplication, UserSubscription,
                    List_CRMs  # Импортируйте модели и базу данных
                    )


class MyAdminIndexView(AdminIndexView):
    @expose('/')
    def index(self):
        if 'General_admin' in session:  # Проверка, авторизован ли пользователь
            return super(MyAdminIndexView, self).index()
        else:
            return redirect(url_for('admin_login'))  # Перенаправление на страницу логина


class DashboardAdmin(AdminIndexView):
    @expose('/')
    def index(self):
        return self.render('Admin_HomePage.html')  # Указываем шаблон из папки templates_admin


class AdminModelView(ModelView):
    def is_accessible(self):
        return 'General_admin' in session  # Доступ только для авторизованного админа


class UsersModelView(AdminModelView):
    # Убираем поле password из отображения в списках и формах
    column_exclude_list = ['password', 'code_auth']

    def create_form(self, obj = None):
        form = super(UsersModelView, self).create_form(obj)
        if 'password' in form._fields:
            del form._fields['password']  # Убираем поле из формы создания
        if 'code_auth' in form._fields:
            del form._fields['code_auth']  # Убираем поле из формы создания
        return form

    def edit_form(self, obj = None):
        form = super(UsersModelView, self).edit_form(obj)
        if 'password' in form._fields:
            del form._fields['password']  # Убираем поле из формы редактирования
        if 'code_auth' in form._fields:
            del form._fields['code_auth']
        return form


class ListCRMsModelView(AdminModelView):
    # Переопределяем метод для отображения user_email вместо user_id
    column_list = ['user_email', 'title_branches', 'description_branches', 'crm_system', 'whatsapp_session',
                   'link_tgbot', 'time_send', 'status_job', 'url_website']

    def _get_user_email(user_id):
        user = Users.query.get(user_id)
        return user.email if user else 'Unknown'

    # Добавляем кастомное поле для отображения email
    def _get_user_email_column(view, context, model, name):
        return ListCRMsModelView._get_user_email(model.user_id)

    column_formatters = {
        'user_email': _get_user_email_column
    }

    column_labels = {
        'title_branches': 'Название филиалов',
        'description_branches': 'Описание филиалов',
        'crm_system': 'Система CRM',
        'link_tgbot': 'TG бот',
        'time_send': 'Время отправки',
        'status_job': 'Статус работы',
        'url_website': 'Ссылка на сайт'
    }

    # Исключаем поле tg_token из отображения
    column_exclude_list = ['tg_token']

    # Убедитесь, что url_website включен в form_columns
    form_columns = ['title_branches', 'description_branches', 'crm_system', 'whatsapp_session', 'link_tgbot',
                    'time_send', 'status_job', 'url_website']  # Добавьте сюда url_website

    form_labels = {
        'title_branches': 'Название филиала',
        'description_branches': 'Описание филиала',
        'crm_system': 'Система CRM',
        'whatsapp_session': 'Сессия WhatsApp',
        'link_tgbot': 'TG бот',
        'time_send': 'Время отправки',
        'status_job': 'Статус работы',
        'url_website': 'Ссылка на сайт'  # Убедитесь, что у вас есть метка для url_website
    }


class UserSubscriptionModelView(AdminModelView):
    column_labels = {
        'email': 'Почта',
        'date_beg': 'Дата подписки',
        'date_end': 'Конец подписки',
        'status_subscription': 'Статус подписки',
        'status_send': 'Статус отправки'
    }


def setup_application(application):
    # Создаем все таблицы и администратора при первом запуске
    def create_admin_and_setup():
        if not Admins.query.filter_by(username = "General_admin").first():
            hashed_password = "General_admin_password"  # Храните пароль в безопасном месте и не в коде!
            new_admin = Admins(username = "General_admin", password = hashed_password, role = "General_admin")
            db.session.add(new_admin)
            db.session.commit()

    # Настраиваем админ-панель
    admin = Admin(application, template_mode = 'bootstrap4', index_view = DashboardAdmin())
    admin.add_view(AdminModelView(Admins, db.session))
    admin.add_view(UsersModelView(Users, db.session))
    admin.add_view(AdminModelView(ElectronicApplication, db.session))
    admin.add_view(UserSubscriptionModelView(UserSubscription, db.session))  # Используем кастомный ModelView
    admin.add_view(ListCRMsModelView(List_CRMs, db.session))
    # Создаем все таблицы и администратора при первом запуске
