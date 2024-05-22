import datetime


from telegram_bot_calendar import WYearTelegramCalendar


def get_year(bot, message, calendar_id=1):
    calendar, step = WYearTelegramCalendar(calendar_id=calendar_id,
                                           locale='ru', min_date=datetime.date.today()).build()
    bot.send_message(message.from_user.id,
                          'Укажите месяц.',
                          reply_markup=calendar)

def get_year_all(bot, message, calendar_id=1):
    calendar, step = WYearTelegramCalendar(calendar_id=calendar_id,
                                           locale='ru').build()
    bot.send_message(message.from_user.id,
                          'Укажите месяц.',
                          reply_markup=calendar)
