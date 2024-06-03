import datetime
import requests
import re

from sqlmodel import Session, select

from database.connection_db import engin
from database.sql_requests import Users, Orders, Calendar

from setting import bot_token

from aiogram_calendar import SimpleCalendar
from servise.state import Form
from aiogram.types import ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton


async def get_calendar(callback, min_date, max_date):
    calendar = SimpleCalendar(locale='ru_RU.utf8', show_alerts=True)
    calendar.set_dates_range(datetime.datetime.strptime(str(min_date), '%Y-%m-%d'),
                             datetime.datetime.strptime(str(max_date), '%Y-%m-%d'))
    return calendar


async def start_calendar(callback):
    min_date = datetime.date.today()
    max_date = "{:%Y-%m-%d}".format(datetime.datetime.strptime('31.12.2030', '%d.%m.%Y'))
    await callback.message.answer('Укажите дату: ',
                                       reply_markup=await (
                                           await get_calendar(callback, min_date, max_date)).start_calendar())


async def ending_calendar(callback, callback_data):
    min_date = datetime.date.today()
    max_date = "{:%Y-%m-%d}".format(datetime.datetime.strptime('31.12.2030', '%d.%m.%Y'))
    calendar = await get_calendar(callback, min_date, max_date)
    selected, date = await calendar.process_selection(callback, callback_data)
    if selected and date:
        await callback.message.delete()
        date_list = [date.strftime('%d'), date.strftime('%m'), date.strftime('%Y')]
        date = f'{date_list[0]}.{date_list[1]}.{date_list[2]}'
        return date


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
    def __init__(self, callback=None, message=None, user=None):
        self.callback = callback
        self.message = message
        self.user = user

    async def check_user(self):
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

    async def authorization(self):
        date = datetime.datetime.now()
        with Session(engin) as session:
            add_useer = Users(telegram_id=self.callback.from_user.id,
                              telegram_teg=self.callback.from_user.username,
                              registration_date=date,
                              rights='user',
                              user_name=self.callback.from_user.first_name,
                              surname=self.callback.from_user.last_name)
            session.add(add_useer)
            session.commit()
            return True


class AdminPanel(object):

    def __init__(self, user= None, callback= None, message= None):
        self.callback = callback
        self.message = message
        self.user = user

    async def viewing_applications(self):
        """Получение всех заявок от пользователя"""
        with Session(engin) as session:
            orders = session.exec(select(Orders).where(Orders.active == True)).all()
        if len(orders) == 0:
            await self.callback.message.answer("Нет активных заявок.")
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
                await self.callback.message.answer(f"~~===Заявки на {key_order}===~~")
                for i in values_order:
                    await self.callback.message.answer(f"Заявка №: {i[0]},\nВид работ: {i[2]},\nВремя: {i[1]}\nНомер заказчика: {i[3]}.")

    async def change_number_orders(self, state):
        """отправляем календарь пользователю"""
        await state.set_state(Form.calendar_3)
        await start_calendar(self.callback)

    async def date_changing_applications(self, callback_data, state):
        """Получения даты для смены количества заявок"""
        date = await ending_calendar(self.callback, callback_data)
        if date:
            self.user.date = date
            await state.clear()

            await state.set_state(Form.number_applications)
            await self.callback.message.answer(
                "Введите количество заявок на день.",
                reply_markup=ReplyKeyboardRemove(),
            )

    async def creating_quantity_database(self, state):
        """Запись в базу данных изменения количества заявок на день"""
        with Session(engin) as session:
            day = session.exec(select(Calendar).where(Calendar.day == self.user.date)).one()
            quantity_order = day.quantity_order
            day.quantity_order = str(self.message.text)
            session.add(day)
            session.commit()
            session.refresh(day)
        await state.clear()
        await self.message.answer(f"Количество заказов на {self.user.date} изменено c {quantity_order} на {self.message.text} .")

    async def statistics_calendar_first(self, state):
        """начало получеия первой даты статистики"""
        await state.set_state(Form.calendar_4)
        await start_calendar(self.callback)

    async def starting_points(self, callback_data, state):
        """получение даты начала статистики"""
        date = await ending_calendar(self.callback, callback_data)
        if date:
            date = date.split('.')
            date = datetime.datetime.strptime(f'{date[2]}{date[1]}{date[0]}', '%Y%m%d').date()
            self.user.statistics_start_date = date
            await state.clear()
            await state.set_state(Form.calendar_5)
            await AdminPanel(callback=self.callback, user=self.user).statistics_calendar_second(state)

    async def statistics_calendar_second(self, state):
        """начало получения второй даты статистики"""
        await state.set_state(Form.calendar_5)
        await start_calendar(self.callback)

    async def end_points(self, callback_data, state):
        """Получение даты окончания статистики"""
        date = await ending_calendar(self.callback, callback_data)
        if date:
            date = date.split('.')
            date = datetime.datetime.strptime(f'{date[2]}{date[1]}{date[0]}', '%Y%m%d').date()
            self.user.statistics_end_date = date
            await state.clear()
            with Session(engin) as session:
                order = session.exec(select(Orders).where(Orders.closing_date >= self.user.statistics_start_date, Orders.closing_date <= self.user.statistics_end_date)).all()
                price = 0
            for i in order:
                if isinstance(i.price, int):
                    price += i.price
                else:
                    price += 0
            await self.callback.message.answer(f"В период с {self.user.statistics_start_date} до {self.user.statistics_end_date} заработано: {price}")

    async def cancellation_application(self, state):
        with Session(engin) as session:
            orders = session.exec(select(Orders).where(Orders.active == True)).all()
        if len(orders) == 0:
            await self.callback.message.answer("Нет активных заявок.")
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
                await self.callback.message.answer(f"~~===Заявки на {key_order}===~~")
                for i in values_order:
                    await self.callback.message.answer(f"Заявка №: {i[0]},\nВид работ: {i[2]},\nВремя: {i[1]}\nНомер заказчика: {i[3]}.")
            await state.set_state(Form.cancellation_application)
            await self.callback.message.answer(
                "Введите номер заявки для отмены.",
                reply_markup=ReplyKeyboardRemove(),
            )

    async def reason_cancellation(self, state):
        await state.clear()
        self.user.order_id = self.message.text
        await state.set_state(Form.reason_cancellation)
        await self.message.answer("Введите причину отмены заказа")

    async def entry_cancellatio_database(self, state):
        await state.clear()

        with Session(engin) as session:
            order = session.exec(select(Orders).where(Orders.id == self.user.order_id)).one()
            order.active = False
            order.refusal = True
            order.rejection_reason = self.message.text
            session.add(order)
            session.commit()
            session.refresh(order)
            id_user = session.exec(select(Users.telegram_id).where(Users.id == order.user_id)).one()

            messeg = f'Мастер отменил Ваш заказ № {order.id} - "{order.job}".\nПричина отказа: {self.message.text}'
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={id_user}&text={messeg}"
            requests.get(url).json()

            await self.message.answer(f"Заявка № {order.id} отменена.")

    async def blocking(self, state):
        """выбор дня для блокировки"""
        await state.set_state(Form.calendar_6)
        await start_calendar(self.callback)

    async def end_blocking(self, callback_data, state):
        await state.clear()
        date = await ending_calendar(self.callback, callback_data)
        if date:
            with Session(engin) as session:
                day = session.exec(select(Calendar).where(Calendar.day == date)).one()
                day.actively = False
                session.add(day)
                session.commit()
                session.refresh(day)
            await self.callback.message.answer(f"День {date} заблокирован.")

    async def unlock(self):
        with Session(engin) as session:
            day = session.exec(select(Calendar).where(Calendar.actively == False)).all()
            if len(day) == 0:
                await self.callback.message.answer("У вас нет заблокированных дней.")
            else:
                keyboard = InlineKeyboardMarkup(inline_keyboard=[])
                for i_day in day:
                    keyboard.inline_keyboard.append([
                        InlineKeyboardButton(text=i_day.day,
                                             callback_data=f'Разблокировка {i_day.day}')
                    ])
                await self.callback.message.answer(
                    "Выберите диапазон времени",
                    reply_markup=keyboard,
                )

    async def adding_database(self):
        """разблокировка дня в базе"""
        with Session(engin) as session:
            day = session.exec(select(Calendar).where(Calendar.day == self.callback.data[14:])).one()
            day.actively = True
            session.add(day)
            session.commit()
            session.refresh(day)
        await self.callback.message.answer(f"День {self.callback.data[14:]} разблокирован.\nЗаказов на день {day.quantity_order}")

    async def change_rights(self, state):
        """вавод пользователей бота"""
        await state.set_state(Form.user_rights_id)
        with (Session(engin) as session):
            user_view = session.exec(
                select(Users)).all()
            await self.callback.message.answer("Выберите и введите id пользователя")

            for user in user_view:
                await self.callback.message.answer(f"id: {user.id},\nИмя: {user.user_name},\nФамилия: {user.surname}, \nПрава: {user.rights}.")

    async def rights_request(self, state):
        await state.clear()
        await state.set_state(Form.user_rights)
        self.user.user_rights_id = self.message.text
        await self.message.answer("Введите права пользователя user/admin")

    async def changing_rights_database(self, state):
        await state.clear()
        if self.message.text in ['admin', 'user']:
            with Session(engin) as session:
                user_view = session.exec(
                    select(Users).where(Users.id == self.user.user_rights_id)).one()
                if user_view.id == self.user.user_id_db:
                    await self.message.answer("Вы не можете изменить права себе.")
                else:
                    user_view.rights = self.message.text
                    session.add(user_view)
                    session.commit()
                    session.refresh(user_view)
                    await self.message.answer("Права изменены.")
        else:
            await self.message.answer("Вы ввели не верные права, повторите ввод")
            await AdminPanel(message=self.message, user=self.user).changing_rights_database(state)

    async def transfer_of_application(self, state):
        with Session(engin) as session:
            orders = session.exec(select(Orders).where(Orders.active == True)).all()
        if len(orders) == 0:
            await self.callback.message.answer("Нет активных заявок.")
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
                await self.callback.message.answer(f"~~===Заявки на {key_order}===~~")
                for i in values_order:
                    await self.callback.message.answer(
                        f"Заявка №: {i[0]},\nВид работ: {i[2]},\nВремя: {i[1]}\nНомер заказчика: {i[3]}.")
            await AdminPanel(callback=self.callback, user=self.user).date_transfer(state)

    async def date_transfer(self, state):
        """выбор дня для переноса"""
        await state.set_state(Form.calendar_7)
        await start_calendar(self.callback)

    async def time_application(self, callback_data, state):
        await state.clear()
        date = await ending_calendar(self.callback, callback_data)
        if date:
            self.user.date = date
            time_user = ['09:00-10:00', '10:30-11:30', '12:00-13:00', '13:30-14:30', '15:00-16:00', '16:30-17:30',
                         '18:00-19:00']

            with Session(engin) as session:
                day = session.exec(select(Calendar).where(Calendar.day == self.user.date)).one()
                order = session.exec(
                    select(Orders).where(Orders.order_date == self.user.date, Orders.active == True)).all()
                if day.quantity_order <= len(order):
                    await self.callback.message.answer("К сожалению на этот день нет свободных мест.")
                elif len(order) == 0:
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
                    for time in time_user:
                        keyboard.inline_keyboard.append([
                            InlineKeyboardButton(text=time,
                                                 callback_data=f'Смена {time}')
                        ])
                    await self.callback.message.answer(
                        "Выберите диапазон времени",
                        reply_markup=keyboard,
                    )
                elif len(order) > 0 and len(order) < day.quantity_order:
                    for i_order in order:
                        if i_order.time in time_user:
                            time_user.remove(i_order.time)
                            continue
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
                    for time in time_user:
                        keyboard.inline_keyboard.append([
                            InlineKeyboardButton(text=time,
                                                 callback_data=f'Смена {time}')
                        ])
                    time_user = ['09:00-10:00', '10:30-11:30', '12:00-13:00', '13:30-14:30', '15:00-16:00',
                                 '16:30-17:30',
                                 '18:00-19:00']
                    await self.callback.message.answer(
                        "Выберите диапазон времени",
                        reply_markup=keyboard,
                    )

    async def time_receipt(self, state):
        await state.clear()
        self.user.time = self.callback.data[6:]
        await state.set_state(Form.admin_transfer_order)
        await self.callback.message.answer(
            "Введите номер заявки необходимую перенести")

    async def write_db(self, state):
        await state.clear()
        self.user.order_id = self.message.text
        with Session(engin) as session:
            order = session.exec(select(Orders).where(Orders.id == self.user.order_id)).one()
            date = order.order_date
            time = order.time
            order.order_date = self.user.date
            order.time = self.user.time
            session.add(order)
            session.commit()
            session.refresh(order)
            id_user = session.exec(select(Users.telegram_id).where(Users.id == order.user_id)).one()

            messeg = f'Мастер изменил сроки исполнения заказа № {order.id} - {order.job}.\nДата изменена с {date} на {order.order_date},\nВремя изменено с {time} на {order.time}'
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={id_user}&text={messeg}"
            requests.get(url).json()

            await self.message.answer(f"Заявка № {order.id} перенесена.")

    async def cancel_the_application(self, state):
        with Session(engin) as session:
            orders = session.exec(select(Orders).where(Orders.active == True)).all()
        if len(orders) == 0:
            await self.callback.message.answer("Нет активных заявок.")
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
                await self.callback.message.answer(f"~~===Заявки на {key_order}===~~")
                for i in values_order:
                    await self.callback.message.answer(
                        f"Заявка №: {i[0]},\nВид работ: {i[2]},\nВремя: {i[1]}\nНомер заказчика: {i[3]}.")
            await state.set_state(Form.completed_application)
            await self.callback.message.answer("Введите id выполенной заявки")

    async def receiving_amount(self, state):
        await state.clear()
        self.user.order_id = self.message.text
        await state.set_state(Form.amount)
        await self.message.answer("Введите суммы полученную за выполнение работ")

    async def entry_the_db_completed_orders(self, state):
        await state.clear()
        date = datetime.date.today()
        with Session(engin) as session:
            order = session.exec(select(Orders).where(Orders.id == self.user.order_id)).one()
            order.active = False
            order.price = self.message.text
            order.closing_date = date
            session.add(order)
            session.commit()
            session.refresh(order)
            id_user = session.exec(select(Users.telegram_id).where(Users.id == order.user_id)).one()

            messeg = f'Мастер перевел Ваш заказ № {order.id} - "{order.job}" в статус исполнено.'
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage?chat_id={id_user}&text={messeg}"
            requests.get(url).json()

        await self.message.answer(f"Заявка № {order.id} переведена в статус исполнена.")


class UserPanel(object):

    def __init__(self, callback=None, message=None, user=None):
        self.callback = callback
        self.message = message
        self.user = user

    async def date_applications(self, state):
        """запись услуги"""
        await state.set_state(Form.calendar_1)
        min_date = datetime.date.today()
        max_date = "{:%Y-%m-%d}".format(datetime.datetime.strptime('31.12.2030', '%d.%m.%Y'))
        await self.callback.message.answer('Укажите дату: ',
                                           reply_markup=await (
                                               await get_calendar(self.callback, min_date, max_date)).start_calendar())

    async def get_day_and_month(self, callback_data, state):
        min_date = datetime.date.today()
        max_date = "{:%Y-%m-%d}".format(datetime.datetime.strptime('31.12.2030', '%d.%m.%Y'))
        calendar = await get_calendar(self.callback, min_date, max_date)
        selected, date = await calendar.process_selection(self.callback, callback_data)
        if selected and date:
            await state.clear()
            await self.callback.message.delete()
            date_list = [date.strftime('%d'), date.strftime('%m'), date.strftime('%Y')]
            self.user.date = f'{date_list[0]}.{date_list[1]}.{date_list[2]}'
            time_user = ['09:00-10:00', '10:30-11:30', '12:00-13:00', '13:30-14:30', '15:00-16:00', '16:30-17:30',
                         '18:00-19:00']

            with Session(engin) as session:
                day = session.exec(select(Calendar).where(Calendar.day == self.user.date)).one()
                order = session.exec(select(Orders).where(Orders.order_date == self.user.date, Orders.active == True)).all()
                if day.quantity_order <= len(order):
                    await self.callback.message.answer("К сожалению на этот день нет свободных мест.")
                elif len(order) == 0:
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
                    for time in time_user:
                        keyboard.inline_keyboard.append([
                            InlineKeyboardButton(text=time,
                                                 callback_data=f'Время {time}')
                        ])
                    await self.callback.message.answer(
                        "Выберите диапазон времени",
                        reply_markup=keyboard,
                    )
                elif len(order) > 0 and len(order) < day.quantity_order:
                    for i_order in order:
                        if i_order.time in time_user:
                            time_user.remove(i_order.time)
                            continue
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
                    for time in time_user:
                        keyboard.inline_keyboard.append([
                            InlineKeyboardButton(text=time,
                                                 callback_data=f'Время {time}')
                        ])
                    time_user = ['09:00-10:00', '10:30-11:30', '12:00-13:00', '13:30-14:30', '15:00-16:00', '16:30-17:30',
                                 '18:00-19:00']
                    await self.callback.message.answer(
                        "Выберите диапазон времени",
                        reply_markup=keyboard,
                    )
    async def check_number(self, state):
        if re.match(r'^((8|\+7)[\- ]?)?(\(?\d{3}\)?[\- ]?)?[\d\- ]{7,10}$', self.message.text) and self.message.text.isnumeric():
            self.user.number = self.message.text
            await state.clear()
            await state.set_state(Form.job)
            await self.message.answer(
                "Опишите необходимую работу.",
                reply_markup=ReplyKeyboardRemove(),
            )
        else:
            await self.message.answer(
                "Номер телефон определне не верно, повторите ввод",
                reply_markup=ReplyKeyboardRemove(),
            )

    async def work_record(self, state):
        await state.clear()
        date = datetime.datetime.now()
        with Session(engin) as session:
            add_useer = Orders(user_id=self.user.user_id_db,
                               creation_date=date,
                               job=self.message.text,
                               active=True,
                               number_phone=self.user.number,
                               refusal=False,
                               order_date=self.user.date,
                               time=self.user.time)
            session.add(add_useer)
            session.commit()

        publicity(None, self.message.text, self.user.date, self.user.number, time=self.user.time, add=True)
        await self.message.answer("Заявка принята, мастер свяжется с вами в ближайшее время.")

    async def get_application_id(self, state):
        with Session(engin) as session:
            order = session.exec(select(Orders).where(Orders.user_id == self.user.user_id_db, Orders.active == True)).all()
            if len(order) > 0:
                await state.set_state(Form.cancellation_order)
                await self.callback.message.answer("Введите номер заявки для отмены.")
                for i_order in order:
                    await self.callback.message.answer(f"Номер заявки: {i_order.id},\nДата: {i_order.order_date},\nНеобходимая работа: {i_order.job}, \nЗаявленное время: {i_order.time}")
            else:
                await self.callback.message.answer("У вас нет актуальных заявок.")

    async def cancellation_application(self, state):
        await state.clear()
        with Session(engin) as session:
            cancellation = session.exec(select(Orders).where(Orders.id == self.message.text)).one()
            cancellation.active = False
            session.add(cancellation)
            session.commit()
            session.refresh(cancellation)
            publicity(cancellation.id, cancellation.job, cancellation.order_date, cancellation.number_phone, cancellation=True)
            await self.message.answer("Заявка отменена.")

    async def transfer_application(self, state):
        with Session(engin) as session:
            order = session.exec(select(Orders).where(Orders.user_id == self.user.user_id_db, Orders.active == True)).all()
            if len(order) > 0:
                for i_order in order:
                    await self.callback.message.answer(
                        f"Номер заявки: {i_order.id},\nДата: {i_order.order_date},\nНеобходимая работа: {i_order.job}, \nЗаявленное время: {i_order.time}")
                    await state.set_state(Form.transfer)
                    await self.callback.message.answer(
                        "Введите номер заявки необходимую перенести",
                        reply_markup=ReplyKeyboardRemove(),
                    )
            else:
                await self.callback.message.answer("У вас нет актуальных заявок.")

    async def date_selection(self, state):
        self.user.order_id = self.message.text
        await state.clear()
        await state.set_state(Form.calendar_2)
        min_date = datetime.date.today()
        max_date = "{:%Y-%m-%d}".format(datetime.datetime.strptime('31.12.2030', '%d.%m.%Y'))
        await self.message.answer('Укажите дату: ',
                                           reply_markup=await (
                                               await get_calendar(self.callback, min_date, max_date)).start_calendar())

    async def current_applications(self):
            with Session(engin) as session:
                order = session.exec(select(Orders).where(Orders.user_id == self.user.user_id_db, Orders.active == True)).all()
                if len(order) > 0:
                    await self.callback.message.answer("Введите номер заявки для отмены.")
                    for i_order in order:
                        await self.callback.message.answer(
                            f"Номер заявки: {i_order.id},\nДата: {i_order.order_date},\nНеобходимая работа: {i_order.job}, \nЗаявленное время: {i_order.time}")
                else:
                    await self.callback.message.answer("У вас нет актуальных заявок.")

    async def transfer_time(self, callback_data, state):
        min_date = datetime.date.today()
        max_date = "{:%Y-%m-%d}".format(datetime.datetime.strptime('31.12.2030', '%d.%m.%Y'))
        calendar = await get_calendar(self.callback, min_date, max_date)
        selected, date = await calendar.process_selection(self.callback, callback_data)
        if selected and date:
            await state.clear()
            await self.callback.message.delete()
            date_list = [date.strftime('%d'), date.strftime('%m'), date.strftime('%Y')]
            self.user.date = f'{date_list[0]}.{date_list[1]}.{date_list[2]}'
            time_user = ['09:00-10:00', '10:30-11:30', '12:00-13:00', '13:30-14:30', '15:00-16:00', '16:30-17:30',
                         '18:00-19:00']

            with Session(engin) as session:
                day = session.exec(select(Calendar).where(Calendar.day == self.user.date)).one()
                order = session.exec(
                    select(Orders).where(Orders.order_date == self.user.date, Orders.active == True)).all()
                if day.quantity_order <= len(order):
                    await self.callback.message.answer("К сожалению на этот день нет свободных мест.")
                elif len(order) == 0:
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
                    for time in time_user:
                        keyboard.inline_keyboard.append([
                            InlineKeyboardButton(text=time,
                                                 callback_data=f'Перенос {time}')
                        ])
                    await self.callback.message.answer(
                        "Выберите диапазон времени",
                        reply_markup=keyboard,
                    )
                elif len(order) > 0 and len(order) < day.quantity_order:
                    for i_order in order:
                        if i_order.time in time_user:
                            time_user.remove(i_order.time)
                            continue
                    keyboard = InlineKeyboardMarkup(inline_keyboard=[])
                    for time in time_user:
                        keyboard.inline_keyboard.append([
                            InlineKeyboardButton(text=time,
                                                 callback_data=f'Перенос {time}')
                        ])
                    time_user = ['09:00-10:00', '10:30-11:30', '12:00-13:00', '13:30-14:30', '15:00-16:00',
                                 '16:30-17:30', '18:00-19:00']
                    await self.callback.message.answer(
                        "Выберите диапазон времени",
                        reply_markup=keyboard,
                    )

    async def completion_transfer(self):
        with Session(engin) as session:
            order = session.exec(select(Orders).where(Orders.id == self.user.order_id)).one()
            date = order.order_date
            time = order.time
            order.order_date = self.user.date
            order.time = self.user.time
            session.add(order)
            session.commit()
            session.refresh(order)
            publicity(None, order.job, date, order.number_phone, new_date=self.user.date, time=time, new_time=self.user.time,  transfer=True)
            await self.callback.message.answer("Заявка перенесена.")

