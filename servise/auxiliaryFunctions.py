import datetime
import requests
import re


from sqlmodel import Session, select

from database.connection_db import engin
from database.sql_requests import Users, Orders, Calendar
from servise.calendar import get_year, get_year_all
from setting import list_time

from telebot import types
from setting import bot_token, list_commands_user, list_commands_admin



def publicity(id, job, date, number_phone, new_date=None, time=None, new_time=None, cancellation=False, add=False, transfer=False):
    """отправка сообщение админам"""
    id_admin = list()

    with Session(engin) as session:
        admin = session.exec(select(Users).where(Users.rights == 'admin')).all()
        for i_admin in admin:
            id_admin.append(i_admin.telegram_id)
    if cancellation:
        messeg = f'Заявка №: {str(id)} отменена заказчиком.\n\nСведения о заявке:\n\nЗаявка на : {date},\nНеобходимая работа: {job}, \nНомер заказчика: {str(number_phone)}'
    if add:
        messeg = f'Создана новая заявка на: {date}.\n\nСведения о заявке:\n\nНеобходимая работа: {job},\nЖелаемое время: {time},\nНомер заказчика: {str(number_phone)}'
    if transfer:
        messeg = f'Заказчик перенёс заявку.\n\nСведения о заявке:\n\nПеренесено с {date}, {time} на {new_date} {new_time},\nНеобходимая работа: {job},\nНомер заказчика: {str(number_phone)}'


    for i_id in id_admin:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={i_id}&text={messeg}"
        requests.get(url).json()


class WorcUser(object):
    def __init__(self, user):
        self.user = user

    def check_user(self):

        with (Session(engin) as session):
            user_view = session.exec(
                select(Users).where(Users.telegram_id == self.user.telegram_id)).first()
            if user_view is None:
                self.user.rights = 'not_registered'
            elif user_view.rights == 'admin':
                self.user.user_id_db = user_view.id
                self.user.rights = user_view.rights
            elif user_view.rights == 'user':
                self.user.user_id_db = user_view.id
                self.user.rights = user_view.rights

    def authorization(self):
        date = datetime.datetime.now()
        with Session(engin) as session:
            add_useer = Users(telegram_id=self.user.telegram_id,
                              telegram_teg=self.user.telegram_tag,
                              registration_date=str(date),
                              rights='user',
                              user_name=self.user.user_name,
                              surname=self.user.surname)
            session.add(add_useer)
            session.commit()
            return True


class AdminPanel(object):

    bot = None
    user = None
    message = None
    def __init__(self, user, bot, message):
        self.user = user
        self.bot = bot
        self.message = message

    def replacement_rights(self):
        AdminPanel.bot = self.bot
        AdminPanel.user = self.user
        AdminPanel.message = self.message

        with (Session(engin) as session):
            user_view = session.exec(
                select(Users)).all()
            self.bot.send_message(self.message.chat.id, "Выберите и введите id пользователя и укажите права (admin/user) через пробел")

            for user in user_view:
                self.bot.send_message(self.message.chat.id, f"id: {user.id},\nИмя: {user.user_name},\nФамилия: {user.surname}, \nПрава: {user.rights}.")
            self.bot.register_next_step_handler(self.message, AdminPanel.update_rights)

    def update_rights(self):
        if self.text in list_commands_admin:
            AdminPanel.redirection(self)
        else:
            data_us = self.text.split()
            if len(data_us) < 2 or data_us[1] not in ['admin', 'user']:
                AdminPanel.bot.send_message(self.from_user.id,
                                            "Указаны неверные права.\nПовторите ввод.")
                AdminPanel.bot.register_next_step_handler(AdminPanel.message, AdminPanel.update_rights)
            else:
                with Session(engin) as session:
                    user_view = session.exec(
                        select(Users).where(Users.id == data_us[0])).one()
                    if user_view.telegram_id == self.from_user.id:
                        AdminPanel.bot.send_message(self.from_user.id,
                                                    "Вы не можете изменить права себе.")
                        AdminPanel.bot.register_next_step_handler(AdminPanel.message, AdminPanel.update_rights)
                    else:
                        user_view.rights = data_us[1]
                        session.add(user_view)
                        session.commit()
                        session.refresh(user_view)
                        AdminPanel.bot.send_message(self.from_user.id,
                                              "Права изменены.")

    def change_number_orders(self, date=None, month=True):
        """изменение количества заказов в день"""
        AdminPanel.bot = self.bot
        AdminPanel.user = self.user
        AdminPanel.message = self.message
        if month:
            get_year(self.bot, self.message)
        if date:
            self.user.day = date.strftime("%d.%m.%Y")
            self.bot.send_message(self.message.from_user.id, f"Введите количество услуг на {self.user.day}")
            self.bot.register_next_step_handler(self.message.message, AdminPanel.save_orders)

    def save_orders(self):

        with Session(engin) as session:
            day = session.exec(select(Calendar).where(Calendar.day == AdminPanel.user.day)).one()
            quantity_order = day.quantity_order
            day.quantity_order = str(self.text)
            session.add(day)
            session.commit()
            session.refresh(day)
        AdminPanel.bot.send_message(self.from_user.id,
                                          f"Количество заказов на {AdminPanel.user.day} изменено c {quantity_order} на {day.quantity_order} .")

    def bloc_day(self, date=None):
        """блокировка дня"""
        if date:
            days = date.strftime("%d.%m.%Y")
            with Session(engin) as session:
                day = session.exec(select(Calendar).where(Calendar.day == days)).one()
                day.actively = False
                session.add(day)
                session.commit()
                session.refresh(day)

            AdminPanel.bot.send_message(self.message.from_user.id,
                                              f"День {days} заблокирован.")

    def unblocking_day(self):
        with Session(engin) as session:
            day = session.exec(select(Calendar).where(Calendar.actively == False)).all()
            if len(day) == 0:
                self.bot.send_message(self.message.from_user.id, "У вас нет заблокированных дней.")
            else:
                markup = types.InlineKeyboardMarkup()
                self.user.bloc_day = True
                for i in day:
                    markup.add(types.InlineKeyboardButton(text=i.day,
                                                          callback_data=i.day))

                self.bot.send_message(self.message.from_user.id, "Выберите дату из списка заблокированных:", reply_markup=markup)

    def completion_unblocking_day(self, days):
        with Session(engin) as session:
            day = session.exec(select(Calendar).where(Calendar.day == days)).one()
            day.actively = True
            session.add(day)
            session.commit()
            session.refresh(day)
        self.bot.send_message(self.message.from_user.id,
                                    f"День {days} разблокирован.\nЗаказов на день {day.quantity_order}")


    def viewing_applications(self):
        with Session(engin) as session:
            orders = session.exec(select(Orders).where(Orders.active == True)).all()
        if len(orders) == 0:
            self.bot.send_message(self.message.from_user.id, "Нет активных заявок.")
        else:
            dict_orders = dict()
            for order in orders:
                if order.order_date in dict_orders:
                    dict_orders[order.order_date].append([order.id, order.time, order.job, order.number_phone])
                else:
                    dict_orders[order.order_date] = list()
                    dict_orders[order.order_date].append([order.id, order.time, order.job, order.number_phone])
            dict_orders = dict(sorted(dict_orders.items()))

            for key_order, values_order in dict_orders.items():
                values_order.sort(key=lambda x: x[0])
                self.bot.send_message(self.message.from_user.id, f"~~===Заявки на {key_order}===~~")
                for i in values_order:
                    self.bot.send_message(self.message.from_user.id, f"Заявка №: {i[0]},\nВид работ: {i[2]},\nВремя: {i[1]}\nНомер заказчика: {i[3]}.")

    def fulfillment_request(self):
        AdminPanel.bot = self.bot
        AdminPanel.user = self.user
        AdminPanel.message = self.message

        self.bot.send_message(self.message.from_user.id, f"Введите номер выполненной заявки и стоимость выполнения через пробел.")
        AdminPanel(self.user, self.bot, self.message).viewing_applications()
        self.bot.register_next_step_handler(self.message, AdminPanel.closing_application)

    def closing_application(self):
        if self.text in list_commands_admin:
            AdminPanel.redirection(self)
        else:
            date = datetime.date.today()
            order_data = self.text.split()
            with Session(engin) as session:
                order = session.exec(select(Orders).where(Orders.id == order_data[0])).one()
                order.active = False
                if len(order_data) == 2:
                    order.price = int(order_data[1])
                else:
                    order.price = 0
                order.closing_date = date
                session.add(order)
                session.commit()
                session.refresh(order)
                id_user = session.exec(select(Users.telegram_id).where(Users.id == order.user_id)).one()

                messeg = f'Мастер перевел Ваш заказ № {order.id} - "{order.job}" в статус исполнено.'
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={id_user}&text={messeg}"
                requests.get(url).json()

                AdminPanel.bot.send_message(AdminPanel.message.from_user.id, f"Заявка № {order.id} переведена в статус исполнена.")

    def cancellation_application(self):

        AdminPanel.bot = self.bot
        AdminPanel.user = self.user
        AdminPanel.message = self.message

        self.bot.send_message(self.message.from_user.id,
                              f"Введите номер Завки которую хотите отменить.")
        AdminPanel(self.user, self.bot, self.message).viewing_applications()
        self.bot.register_next_step_handler(self.message, AdminPanel.obtaining_reason_refusal)


    def obtaining_reason_refusal(self):
        if self.text in list_commands_admin:
            AdminPanel.redirection(self)
        else:
            AdminPanel.user.id_application_refusal = self.text
            AdminPanel.bot.send_message(AdminPanel.message.from_user.id,
                                  f"Введите причину отказа от заявки.")
            AdminPanel.bot.register_next_step_handler(AdminPanel.message, AdminPanel.completion_failure)

    def completion_failure(self):
        if self.text in list_commands_admin:
            AdminPanel.redirection(self)
        else:
            with Session(engin) as session:
                order = session.exec(select(Orders).where(Orders.id == AdminPanel.user.id_application_refusal)).one()
                order.active = False
                order.refusal = True
                order.rejection_reason = self.text
                session.add(order)
                session.commit()
                session.refresh(order)
                id_user = session.exec(select(Users.telegram_id).where(Users.id == order.user_id)).one()

                messeg = f'Мастер отменил Ваш заказ № {order.id} - "{order.job}".\nПричина отказа: {self.text}'
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={id_user}&text={messeg}"
                requests.get(url).json()

                AdminPanel.bot.send_message(AdminPanel.message.from_user.id,
                                            f"Заявка № {order.id} отменена.")

    def transfer_application(self):
        AdminPanel.bot = self.bot
        AdminPanel.user = self.user
        AdminPanel.message = self.message

        self.bot.send_message(self.message.from_user.id,
                              f"Введите номер заявки которую хотите перенести.")
        AdminPanel(self.user, self.bot, self.message).viewing_applications()
        self.bot.register_next_step_handler(self.message, AdminPanel.transfer_date)

    def transfer_date(self, month=True, date=None):
        if month:
            AdminPanel.user.transfer_date = True
            AdminPanel.user.id_transfer_request = self.text
            get_year(AdminPanel.bot, AdminPanel.message)
        if date:
            AdminPanel.user.day = date.strftime("%d.%m.%Y")
            with Session(engin) as session:
                day = session.exec(select(Calendar).where(Calendar.day == AdminPanel.user.day)).one()
                order = session.exec(select(Orders).where(Orders.order_date == AdminPanel.user.day, Orders.active == True)).all()
                if day.quantity_order <= len(order):
                    self.bot.send_message(self.message.from_user.id, "К сожалению на этот день нет свободных мест.")
                elif len(order) == 0:
                    markup = types.InlineKeyboardMarkup()

                    for time in list_time:
                        markup.add(types.InlineKeyboardButton(text=time,
                                                              callback_data=time))
                    self.bot.send_message(self.message.from_user.id,
                                          "Выберите доапазон времени:\nВремя возможно скореектировать с мастером в зависимости от загруженности.",
                                          reply_markup=markup)
                elif len(order) > 0 and len(order) < day.quantity_order:
                    for i_order in order:
                        if i_order.time in list_time:
                            list_time.remove(i_order.time)
                            continue
                    markup = types.InlineKeyboardMarkup()
                    for time in list_time:
                        markup.add(types.InlineKeyboardButton(text=time,
                                                              callback_data=time))

                    self.bot.send_message(self.message.from_user.id,
                                          "Выберите доапазон времени:\nВремя возможно скореектировать с мастером в зависимости от загруженности.",
                                          reply_markup=markup)

    def completion_transfer(self):
        if self.text in list_commands_user:
            UserPanel.redirection(self)
        else:
            with Session(engin) as session:
                order = session.exec(select(Orders).where(Orders.id == AdminPanel.user.id_transfer_request)).one()
                date = order.order_date
                time = order.time
                order.order_date = AdminPanel.user.day
                order.time = AdminPanel.user.time



                session.add(order)
                session.commit()
                session.refresh(order)
                id_user = session.exec(select(Users.telegram_id).where(Users.id == order.user_id)).one()

                messeg = f'Мастер изменил сроки исполнения заказа № {order.id} - {order.job}.\nДата изменена с {date} на {order.order_date},\n Время изменено с {time} на {order.time}'
                url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={id_user}&text={messeg}"
                requests.get(url).json()

                AdminPanel.bot.send_message(AdminPanel.message.from_user.id,
                                            f"Заявка № {order.id} перенесена.")

    def first_day_statistics(self, month=True, date=None):
        AdminPanel.bot = self.bot
        AdminPanel.user = self.user
        AdminPanel.message = self.message
        if month:
            self.user.statistics_one = True
            self.bot.send_message(self.message.from_user.id, "Введите дату начала выборки.")
            get_year_all(self.bot, self.message)
        if date:
            self.bot.delete_message(self.message.from_user.id, self.message.message.message_id)
            self.user.day_one_statistics = date
            AdminPanel.two_day_statistics(self, month=True,  date=None)

    def two_day_statistics(self, month=True, date=None):
        if month:
            self.bot.send_message(self.message.from_user.id, "Введите дату окончания выборки.")
            self.user.statistics_two = True
            get_year_all(self.bot, self.message, calendar_id=2)
        if date:
            self.user.day_two_statistics = date
            AdminPanel.display_statistics(self)

    def display_statistics(self):

        with Session(engin) as session:
            order = session.exec(select(Orders).where(Orders.closing_date >= self.user.day_one_statistics, Orders.closing_date <= self.user.day_two_statistics)).all()
            price = 0
        for i in order:
            if isinstance(i.price, int):
                price += i.price
            else:
                price += 0
        self.bot.send_message(self.message.from_user.id, f"В период с {self.user.day_one_statistics} до {self.user.day_two_statistics} заработано: {price}")

    def redirection(self):

        if self.text == 'Изменить права':
            AdminPanel(AdminPanel.user, AdminPanel.bot, AdminPanel.message).replacement_rights()
        elif self.text == 'Изменить количество заявок':
            AdminPanel.user.calendar = 1
            AdminPanel(AdminPanel.user, AdminPanel.bot, AdminPanel.message).change_number_orders()
        elif self.text == 'Блокировка дня':
            AdminPanel.user.calendar = 2
            AdminPanel(AdminPanel.user, AdminPanel.bot, AdminPanel.message).change_number_orders()
        elif self.text == 'Разблокировка дня':
            AdminPanel(AdminPanel.user, AdminPanel.bot, AdminPanel.message).unblocking_day()
        elif self.text == 'Просмотр заявок':
            AdminPanel(AdminPanel.user, AdminPanel.bot, AdminPanel.message).viewing_applications()
        elif self.text == 'Отметить заявку как выполненную':
            AdminPanel(AdminPanel.user, AdminPanel.bot, AdminPanel.message).fulfillment_request()
        elif self.text == 'Отменить заявку':
            AdminPanel(AdminPanel.user, AdminPanel.bot, AdminPanel.message).cancellation_application()
        elif self.text == 'Перенос заявки':
            AdminPanel(AdminPanel.user, AdminPanel.bot, AdminPanel.message).transfer_application()
        elif self.text == 'Статистика работ':
            AdminPanel(AdminPanel.user, AdminPanel.bot, AdminPanel.message).first_day_statistics()

class UserPanel(object):

    bot = None
    user = None
    message = None
    check = 0
    def __init__(self, user, bot, message):
        self.user = user
        self.bot = bot
        self.message = message


    def date_applications(self, date=None, month=True):
        """запись услуги"""
        if month:
            get_year(self.bot, self.message)

    def add_order(self, date=None):
        if date:

            UserPanel.bot = self.bot
            UserPanel.user = self.user
            UserPanel.message = self.message

            self.bot.delete_message(self.message.from_user.id, self.message.message.message_id)

            self.user.day = date.strftime("%d.%m.%Y")
            self.user.adding_order = True
            with Session(engin) as session:
                time_user = list_time.copy()
                day = session.exec(select(Calendar).where(Calendar.day == self.user.day)).one()
                order = session.exec(select(Orders).where(Orders.order_date == self.user.day, Orders.active == True)).all()
                if day.quantity_order <= len(order):
                    self.bot.send_message(self.message.from_user.id, "К сожалению на этот день нет свободных мест.")
                elif len(order) == 0:
                    markup = types.InlineKeyboardMarkup()

                    for time in list_time:
                        markup.add(types.InlineKeyboardButton(text=time,
                                                              callback_data=time))
                    self.bot.send_message(self.message.from_user.id, "Выберите доапазон времени:\nВремя возможно скореектировать с мастером в зависимости от загруженности.",
                                          reply_markup=markup)
                elif len(order) > 0 and len(order) < day.quantity_order:
                    for i_order in order:
                        if i_order.time in time_user:
                            time_user.remove(i_order.time)
                            continue
                    markup = types.InlineKeyboardMarkup()
                    for time in time_user:
                        markup.add(types.InlineKeyboardButton(text=time,
                                                              callback_data=time))

                    self.bot.send_message(self.message.from_user.id,
                                          "Выберите доапазон времени:\nВремя возможно скореектировать с мастером в зависимости от загруженности.",
                                          reply_markup=markup)
                time_user = ['09:00-10:00', '10:30-11:30', '12:00-13:00', '13:30-14:30', '15:00-16:00', '16:30-17:30',
                             '18:00-19:00']

    def passing_number_phone(self):
        UserPanel.bot.send_message(UserPanel.message.from_user.id, "Опишите какую работу необходимо выполнить.")
        UserPanel.bot.register_next_step_handler(self.message.message, UserPanel.add_number_phone)

    def add_number_phone(self):
        if self.text in list_commands_user:
            UserPanel.redirection(self)
        else:
            UserPanel.user.job = self.text
            UserPanel.bot.send_message(UserPanel.message.from_user.id, "Введите Ваш номер телефона для связи с Вами.\nФормат нометра 89996662229")
            UserPanel.bot.register_next_step_handler(self, UserPanel.description_work)

    def description_work(self):
        if self.text in list_commands_user:
            UserPanel.redirection(self)
        else:
            if re.match(r'^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$', self.text) and self.text.isnumeric():
                date = datetime.datetime.now()

                with Session(engin) as session:
                    add_useer = Orders(user_id=UserPanel.user.user_id_db,
                                       creation_date=str(date),
                                       job=UserPanel.user.job,
                                       active=True,
                                       number_phone=self.text,
                                       refusal=False,
                                       order_date=UserPanel.user.day,
                                       time=UserPanel.user.time)
                    session.add(add_useer)
                    session.commit()

                publicity(None, self.text, UserPanel.user.day, UserPanel.user.number, time=UserPanel.user.time, add=True)
                UserPanel.bot.send_message(UserPanel.message.from_user.id, "Заявка принята, мастер свяжется с вами в ближайшее время.")
            else:
                UserPanel.bot.send_message(UserPanel.message.from_user.id, "Номер телефона введен не верно.\nПовторите ввод.")
                UserPanel.add_number_phone(self)


    def cancellation_application(self):
        UserPanel.bot = self.bot
        UserPanel.user = self.user
        UserPanel.message = self.message

        with Session(engin) as session:
            order = session.exec(select(Orders).where(Orders.user_id == self.user.user_id_db, Orders.active == True)).all()
            self.bot.send_message(self.message.from_user.id, "Введите номер заявки для отмены ")
            for i_order in order:
                self.bot.send_message(self.message.from_user.id, f"Номер заявки: {i_order.id},\nДата: {i_order.order_date},\nНеобходимая работа: {i_order.job}, \nЗаявленное время: {i_order.time}")
            self.bot.register_next_step_handler(self.message, UserPanel.cancellation_application_db)


    def cancellation_application_db(self):
        if self.text in list_commands_user:
            UserPanel.redirection(self)
        else:
            with Session(engin) as session:
                cancellation = session.exec(select(Orders).where(Orders.id == self.text)).one()
                cancellation.active = False
                session.add(cancellation)
                session.commit()
                session.refresh(cancellation)
                publicity(cancellation.id, cancellation.job, cancellation.order_date, cancellation.number_phone, cancellation=True)
                UserPanel.bot.send_message(UserPanel.message.from_user.id, "Заявка отменена.")

    def viewing_application(self):
        with Session(engin) as session:
            order = session.exec(select(Orders).where(Orders.user_id == self.user.user_id_db, Orders.active == True)).all()
            if len(order) == 0:
                self.bot.send_message(self.message.from_user.id, "У вас нет заявок.")
            else:
                self.bot.send_message(self.message.from_user.id, "Ваши активнае заявки.")
                for i_order in order:
                    self.bot.send_message(self.message.from_user.id, f"Номер заявки: {i_order.id},\nДата: {i_order.order_date},\nНеобходимая работа: {i_order.job}")

    def transfer_application(self):
        UserPanel.bot = self.bot
        UserPanel.user = self.user
        UserPanel.message = self.message

        with Session(engin) as session:
            order = session.exec(
                select(Orders).where(Orders.user_id == self.user.user_id_db, Orders.active == True)).all()
            self.bot.send_message(self.message.from_user.id, "Укажите номер заявки необходимую перенести.")
            for i_order in order:
                self.bot.send_message(self.message.from_user.id,
                                      f"Номер заявки: {i_order.id},\nДата: {i_order.order_date},\nНеобходимая работа: {i_order.job}")
            self.bot.register_next_step_handler(self.message, UserPanel.new_date)

    def new_date(self):
        if self.text in list_commands_user:
            UserPanel.redirection(self)
        else:
            UserPanel.user.transfer = True
            UserPanel.user.user_id_rights = self.text
            UserPanel(UserPanel.user, UserPanel.bot, UserPanel.message).date_applications()

    def add_new_date(self, date=None):
        if date:
            UserPanel.user.day = date.strftime("%d.%m.%Y")
            with Session(engin) as session:
                day = session.exec(select(Calendar).where(Calendar.day == UserPanel.user.day)).one()
                order = session.exec(select(Orders).where(Orders.order_date == UserPanel.user.day, Orders.active == True)).all()
                if day.quantity_order <= len(order):
                    self.bot.send_message(self.message.from_user.id, "К сожалению на этот день нет свободных мест.")
                elif len(order) == 0:
                    markup = types.InlineKeyboardMarkup()

                    for time in list_time:
                        markup.add(types.InlineKeyboardButton(text=time,
                                                              callback_data=time))
                    self.bot.send_message(self.message.from_user.id,
                                          "Выберите доапазон времени:\nВремя возможно скореектировать с мастером в зависимости от загруженности.",
                                          reply_markup=markup)
                elif len(order) > 0 and len(order) < day.quantity_order:
                    for i_order in order:
                        if i_order.time in list_time:
                            list_time.remove(i_order.time)
                            continue
                    markup = types.InlineKeyboardMarkup()
                    for time in list_time:
                        markup.add(types.InlineKeyboardButton(text=time,
                                                              callback_data=time))

                    self.bot.send_message(self.message.from_user.id,
                                          "Выберите доапазон времени:\nВремя возможно скореектировать с мастером в зависимости от загруженности.",
                                          reply_markup=markup)

    def completion_transfer(self):

        with Session(engin) as session:
            order = session.exec(select(Orders).where(Orders.id == UserPanel.user.user_id_rights)).one()
            date = order.order_date
            time = order.time
            order.order_date = UserPanel.user.day
            order.time = UserPanel.user.time
            session.add(order)
            session.commit()
            session.refresh(order)
            publicity(None, order.job, date, order.number_phone, new_date=UserPanel.user.day, time=time, new_time=UserPanel.user.time,  transfer=True)
            UserPanel.bot.send_message(UserPanel.message.from_user.id, "Заявка перенесена.")


    def redirection(self):

        if self.text == 'Подать заявку':
            UserPanel.user.adding_order = True
            UserPanel(UserPanel.user, UserPanel.bot, UserPanel.message).date_applications()
        elif self.text == 'Отменить заявку':
            UserPanel(UserPanel.user, UserPanel.bot, UserPanel.message).cancellation_application()
        elif self.text == 'Просмотреть мои заявки':
            UserPanel(UserPanel.user, UserPanel.bot, UserPanel.message).viewing_application()
        elif self.text == 'Перенос заявки':
            UserPanel(UserPanel.user, UserPanel.bot, UserPanel.message).transfer_application()


