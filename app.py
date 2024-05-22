import telegram_bot_calendar
from telebot import TeleBot, types

from setting import bot_token, bot_token_test
from user_data import User

from servise.auxiliaryFunctions import WorcUser, AdminPanel, UserPanel
from servise.returnText import text_user, not_registered_text, admin_text
from telegram_bot_calendar import WYearTelegramCalendar

import datetime
import time


bot = TeleBot(bot_token)


@bot.message_handler(commands=['start'])
def start_bot_worc(message):
    user = User.get_user(message.chat.id, message.chat.username, message.from_user.first_name, message.from_user.last_name)
    WorcUser(user).check_user()
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    if user.rights == 'not_registered':
        button_1 = types.KeyboardButton('Авторизация')
        markup.add(button_1)
        bot.send_message(message.chat.id, not_registered_text, reply_markup=markup)

    elif user.rights == 'user':
        button_1 = types.KeyboardButton('Подать заявку')
        button_2 = types.KeyboardButton('Отменить заявку')
        button_3 = types.KeyboardButton('Перенос заявки')
        button_4 = types.KeyboardButton('Просмотреть мои заявки')

        markup.add(button_1, button_2, button_3)
        markup.add(button_4)
        bot.send_message(message.chat.id, text_user, reply_markup=markup)

        markup.add(button_3)
    elif user.rights == 'admin':
        button_1 = types.KeyboardButton('Просмотр заявок')
        button_2 = types.KeyboardButton('Изменить количество заявок')
        button_3 = types.KeyboardButton('Статистика работ')
        button_4 = types.KeyboardButton('Отметить заявку как выполненную')
        button_5 = types.KeyboardButton('Отменить заявку')
        button_6 = types.KeyboardButton('Перенос заявки')
        button_7 = types.KeyboardButton('Блокировка дня')
        button_8 = types.KeyboardButton('Разблокировка дня')
        button_9 = types.KeyboardButton('Изменить права')

        markup.add(button_1, button_6)
        markup.add(button_2, button_3)
        markup.add(button_4, button_5)
        markup.add(button_7, button_8)
        markup.add(button_9)
        bot.send_message(message.chat.id, admin_text, reply_markup=markup)


@bot.message_handler(content_types=['text'])
def bot_message(message):
    user = User.get_user(message.chat.id, message.chat.username, message.from_user.first_name, message.from_user.last_name)
    WorcUser(user).check_user()

    if user.rights == 'not_registered':
        result = WorcUser(user).authorization()
        if result:
            bot.send_message(message.chat.id, "Авторизация пройдена успешно.")
            start_bot_worc(message)
        else:
            bot.send_message(message.chat.id, "Во время авторизации произошла ошибка.\n"
                                              "Повторите попытку.")
            start_bot_worc(message)

    elif user.rights == 'user':
        if message.text == 'Подать заявку':
            user.adding_order = True
            UserPanel(user, bot, message).date_applications()
        elif message.text == 'Отменить заявку':
            UserPanel(user, bot, message).cancellation_application()
        elif message.text == 'Просмотреть мои заявки':
            UserPanel(user, bot, message).viewing_application()
        elif message.text == 'Перенос заявки':
            UserPanel(user, bot, message).transfer_application()


    elif user.rights == 'admin':
        if message.text == 'Изменить права':
            AdminPanel(user, bot, message).replacement_rights()
        elif message.text == 'Изменить количество заявок':
            user.calendar = 1
            AdminPanel(user, bot, message).change_number_orders()
        elif message.text == 'Блокировка дня':
            user.calendar = 2
            AdminPanel(user, bot, message).change_number_orders()
        elif message.text == 'Разблокировка дня':
            AdminPanel(user, bot, message).unblocking_day()
        elif message.text == 'Просмотр заявок':
            AdminPanel(user, bot, message).viewing_applications()
        elif message.text == 'Отметить заявку как выполненную':
            AdminPanel(user, bot, message).fulfillment_request()
        elif message.text == 'Отменить заявку':
            AdminPanel(user, bot, message).cancellation_application()
        elif message.text == 'Перенос заявки':
            AdminPanel(user, bot, message).transfer_application()
        elif message.text == 'Статистика работ':
            AdminPanel(user, bot, message).first_day_statistics()


@bot.callback_query_handler(func=WYearTelegramCalendar.func(calendar_id=1))
def processing_day_month(message):
    user = User.get_user(message.from_user.id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
    if user.statistics_one:
        result, key, step = WYearTelegramCalendar(calendar_id=1, locale='ru').process(
        message.data)
    else:
        result, key, step = WYearTelegramCalendar(calendar_id=1, locale='ru', min_date=datetime.date.today()).process(
        message.data)

    bot.edit_message_text('Выберите дату.',
                          message.message.chat.id,
                          message.message.message_id,
                          reply_markup=key)
    if user.calendar == 1:
        bot.register_next_step_handler(message.message, AdminPanel(user, bot, message).change_number_orders(date=result, month=False))
    elif user.calendar == 2:
        bot.register_next_step_handler(message.message, AdminPanel(user, bot, message).bloc_day(date=result))
    if user.transfer_date:
        bot.register_next_step_handler(message.message, AdminPanel(user, bot, message).transfer_date(date=result, month=False))
    if user.statistics_one:
        bot.register_next_step_handler(message.message, AdminPanel(user, bot, message).first_day_statistics(date=result, month=False))
    if user.adding_order:
        bot.register_next_step_handler(message.message, UserPanel(user, bot, message).add_order(date=result))
    if user.transfer:
        bot.register_next_step_handler(message.message, UserPanel(user, bot, message).add_new_date(date=result))


@bot.callback_query_handler(func=WYearTelegramCalendar.func(calendar_id=2))
def processing_day_month(message):
    user = User.get_user(message.from_user.id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
    result, key, step = WYearTelegramCalendar(calendar_id=2, locale='ru').process(
        message.data)
    bot.edit_message_text('Выберите дату.',
                          message.message.chat.id,
                          message.message.message_id,
                          reply_markup=key)
    if user.statistics_two:
        bot.register_next_step_handler(message.message, AdminPanel(user, bot, message).two_day_statistics(date=result, month=False))


@bot.callback_query_handler(func=lambda call: True)
def entry_database(message):
    user = User.get_user(message.from_user.id, message.from_user.username, message.from_user.first_name, message.from_user.last_name)
    if user.bloc_day:
        user.bloc_day = False
        AdminPanel(user, bot, message).completion_unblocking_day(message.data)
    elif user.adding_order:
        user.adding_order = False
        user.time = message.data
        UserPanel(user, bot, message).passing_number_phone()
    elif user.transfer:
        user.transfer = False
        user.time = message.data
        UserPanel(user, bot, message).completion_transfer()
    elif user.transfer_date:
        user.transfer_date = False
        user.time = message.data
        AdminPanel(user, bot, message).completion_transfer()


if __name__ == '__main__':
    while True:
        try:
            bot.polling(none_stop=True, timeout=90)
        except Exception as e:
            print(datetime.datetime.now(), e)
            time.sleep(2)
            continue

