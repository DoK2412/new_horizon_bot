import asyncio


from setting import bot_token, bot_token_test
from user_data import User

from servise.auxiliaryFunctions import WorcUser, AdminPanel, UserPanel


from aiogram.types import ReplyKeyboardRemove, \
    InlineKeyboardMarkup, InlineKeyboardButton, Message
from aiogram import Bot, Dispatcher, types
from aiogram.filters import CommandStart
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode, ContentType
from aiogram import F
from aiogram.fsm.context import FSMContext
from aiogram_calendar import SimpleCalendarCallback
from aiogram.types import InputFile


from servise.state import Form


dp = Dispatcher()


@dp.message(CommandStart())
async def start_bot_worc(message):
    user = User.get_user(message.chat.id)
    await message.delete()
    await WorcUser(message=message, user=user).check_user()
    if user.rights == 'not_registered':
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text='Авторизация',
                                     callback_data='Авторизация')
            ]
        ])
        await message.answer('Для использования бота вам необходимо авторизоваться', reply_markup=keyboard)

    elif user.rights == 'user':
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [
                    InlineKeyboardButton(text='Подать заявку',
                                         callback_data='Подать заявку')
                ],
                [
                    InlineKeyboardButton(text='Отменить заявку',
                                         callback_data='Отменить заявку'),
                    InlineKeyboardButton(text='Перенос заявки',
                                         callback_data='Перенос заявки')
                ],
                [
                    InlineKeyboardButton(text='Просмотреть мои заявки',
                                         callback_data='Просмотреть мои заявки')
                ]
            ])
            await message.answer('Добро пожаловать в главное меню.', reply_markup=keyboard)

    elif user.rights == 'admin':

        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text='Просмотр заявок',
                                     callback_data='Просмотр заявок'),
                InlineKeyboardButton(text='Подать заявку',
                                     callback_data='Подать заявку')
            ],
            [
                InlineKeyboardButton(text='Статистика работ',
                                     callback_data='Статистика работ'),
                InlineKeyboardButton(text='Отметить заявку как выполненную',
                                     callback_data='Отметить заявку как выполненную')
            ],
            [
                InlineKeyboardButton(text='Отменить заявку',
                                     callback_data='Отмена заявки'),
                InlineKeyboardButton(text='Перенос заявки',
                                     callback_data='Корректировка сроков')
            ],
            [
                InlineKeyboardButton(text='Блокировка дня',
                                     callback_data='Блокировка дня'),
                InlineKeyboardButton(text='Разблокировка дня',
                                     callback_data='Разблокировка дня')
            ],
            [
                InlineKeyboardButton(text='Изменить права',
                                     callback_data='Изменить права'),
                InlineKeyboardButton(text='Изменить количество заявок',
                                     callback_data='Изменить количество заявок')
            ],
        ])
        await message.answer('Добро пожаловать в админ меню.', reply_markup=keyboard)


### Юзер запросы
@dp.callback_query(F.data == "Авторизация")
async def authorizations(callback: types.CallbackQuery):
    authorization = await WorcUser(callback=callback).authorization()
    if authorization:
        await start_bot_worc(callback.message)

    else:
        await callback.message.answer('В процессе авторизации произошла ошибка.\nПовторите попытку')
        await start_bot_worc(callback.message)


@dp.callback_query(F.data == "Подать заявку")
async def apply(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await UserPanel(callback=callback, user=user).date_applications(state)


@dp.callback_query(Form.calendar_1, SimpleCalendarCallback.filter())
async def process_simple_calendar(callback, callback_data, state: FSMContext):
    user = User.get_user(callback.message.chat.id)
    await UserPanel(callback=callback, user=user).get_day_and_month(callback_data, state)


@dp.callback_query(F.data[:5] == "Время")
async def receiving_note(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    user.time = callback.data[6:]
    await state.set_state(Form.hotel)
    await callback.message.answer(
        "Введите название отеля",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.callback_query(F.data == "Пропустить")
async def skip(callback: types.CallbackQuery, state: FSMContext):
    await state.set_state(Form.job)
    await callback.message.answer(
        "Опишите необходимую работу.",
        reply_markup=ReplyKeyboardRemove(),
    )


@dp.callback_query(F.data == "Фото")
async def skip(callback: types.CallbackQuery,  state: FSMContext):
    await callback.message.delete()
    await state.set_state(Form.photo)
    await callback.message.answer(
        "Загрузите одну или несколько фотографий.")


@dp.message(Form.photo)
async def echo_photo_message(message: Message, state: FSMContext, bot: Bot):
    user = User.get_user(message.chat.id)
    if message.photo is not None:

        # Получаем список фотографий в сообщении
        photos = message.photo

        # Перебираем фотографии и обрабатываем их
        for photo in photos:
            if message.photo[-1].file_id in user.list_photo:
                continue
            else:
                user.list_photo.append(message.photo[-1].file_id)
        await state.set_state(Form.job)
        if user.switch is False:
            user.list_video = list()
            user.switch = True
            await message.answer(
                "Опишите необходимую работу.",
                reply_markup=ReplyKeyboardRemove(),
            )
    else:
        await message.answer(
            "Вы прислали не фото. Повторите отправку.")


@dp.callback_query(F.data == "Видео")
async def video(callback: types.CallbackQuery,  state: FSMContext):
    await callback.message.delete()
    await state.set_state(Form.video)
    await callback.message.answer(
        "Загрузите одно или несколько видео.")


@dp.message(Form.video)
async def echo_video_message(message: Message, state: FSMContext):
    user = User.get_user(message.chat.id)
    if message.video is not None:
        # Получаем список фотографий в сообщении
        videos = message.video

        # Перебираем фотографии и обрабатываем их
        for video in videos:
            if message.video.file_id in user.list_video:
                continue
            else:
                user.list_video.append(message.video.file_id)

        await state.set_state(Form.job)
        if user.switch is False:
            user.switch = True
            user.list_photo = list()
            await message.answer(
                "Опишите необходимую работу.",
                reply_markup=ReplyKeyboardRemove(),
            )
    else:
        await message.answer(
            "Вы прислали не видео. Повторите отправку.")


@dp.message(Form.hotel)
async def hotel(message: Message, state: FSMContext):
    await message.delete()
    user = User.get_user(message.chat.id)
    await UserPanel(message=message, user=user).check_number(state)


@dp.message(Form.job)
async def job(message: Message, state: FSMContext):
    await message.delete()
    user = User.get_user(message.chat.id)
    user.switch = False
    await UserPanel(message=message, user=user).work_record(state)


@dp.callback_query(F.data == "Отменить заявку")
async def cancellation(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await UserPanel(callback=callback, user=user).get_application_id(state)


@dp.message(Form.cancellation_order)
async def cancellation_order(message: Message, state: FSMContext):
    await message.delete()
    user = User.get_user(message.chat.id)
    await UserPanel(message=message, user=user).cancellation_application(state)


@dp.callback_query(F.data == "Перенос заявки")
async def transfer(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await UserPanel(callback=callback, user=user).transfer_application(state)


@dp.message(Form.transfer)
async def cancellation_order(message: Message, state: FSMContext):
    await message.delete()
    user = User.get_user(message.chat.id)
    await UserPanel(message=message, user=user).date_selection(state)


@dp.callback_query(Form.calendar_2, SimpleCalendarCallback.filter())
async def process_simple_calendar(callback, callback_data, state: FSMContext):
    user = User.get_user(callback.message.chat.id)
    await UserPanel(callback=callback, user=user).transfer_time(callback_data, state)


@dp.callback_query(F.data[:7] == "Перенос")
async def receiving_note(callback: types.CallbackQuery):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    user.time = callback.data[7:]
    await UserPanel(callback=callback, user=user).completion_transfer()


@dp.callback_query(F.data == "Просмотреть мои заявки")
async def my_applications(callback: types.CallbackQuery):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await UserPanel(callback=callback, user=user).current_applications()


###Админ запросы
@dp.callback_query(F.data == "Просмотр заявок")
async def view_applications(callback: types.CallbackQuery):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).viewing_applications()


@dp.callback_query(F.data == "Изменить количество заявок")
async def change_number_order(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).change_number_orders(state)


@dp.callback_query(Form.calendar_3, SimpleCalendarCallback.filter())
async def date_changing_application(callback, callback_data, state: FSMContext):
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).date_changing_applications(callback_data, state)


@dp.message(Form.number_applications)
async def change_number_order(message: Message, state: FSMContext):
    """получение количества заявок на день"""
    await message.delete()
    user = User.get_user(message.chat.id)
    await AdminPanel(message=message, user=user).creating_quantity_database(state)


@dp.callback_query(F.data == "Статистика работ")
async def statistics_calendar_1(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).statistics_calendar_first(state)


@dp.callback_query(Form.calendar_4, SimpleCalendarCallback.filter())
async def starting_point(callback, callback_data, state: FSMContext):
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).starting_points(callback_data, state)


@dp.callback_query(Form.calendar_5, SimpleCalendarCallback.filter())
async def starting_point(callback, callback_data, state: FSMContext):
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).end_points(callback_data, state)


@dp.callback_query(F.data == "Отмена заявки")
async def cancellation_application(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).cancellation_application(state)


@dp.message(Form.cancellation_application)
async def cancellation(message: Message, state: FSMContext):
    """получение id заявки на отмену"""
    await message.delete()
    user = User.get_user(message.chat.id)
    await AdminPanel(message=message, user=user).reason_cancellation(state)


@dp.message(Form.reason_cancellation)
async def cancellation(message: Message, state: FSMContext):
    """получение причины отмены заказа"""
    await message.delete()
    user = User.get_user(message.chat.id)
    await AdminPanel(message=message, user=user).entry_cancellatio_database(state)


@dp.callback_query(F.data == "Блокировка дня")
async def blocking_day(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).blocking(state)


@dp.callback_query(Form.calendar_6, SimpleCalendarCallback.filter())
async def starting_point(callback, callback_data, state: FSMContext):
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).end_blocking(callback_data, state)


@dp.callback_query(F.data == "Разблокировка дня")
async def unlock_day(callback: types.CallbackQuery):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).unlock()


@dp.callback_query(F.data[:13] == "Разблокировка")
async def adding_unlock_database(callback: types.CallbackQuery):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).adding_database()


@dp.callback_query(F.data == "Изменить права")
async def unlock_day(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).change_rights(state)


@dp.message(Form.user_rights_id)
async def get_user_id(message: Message, state: FSMContext):
    """получение id пользователя для назначения прав"""
    await message.delete()
    user = User.get_user(message.chat.id)
    await AdminPanel(message=message, user=user).rights_request(state)


@dp.message(Form.user_rights)
async def get_user_rights(message: Message, state: FSMContext):
    """получение прав для пользователя"""
    await message.delete()
    user = User.get_user(message.chat.id)
    await AdminPanel(message=message, user=user).changing_rights_database(state)


@dp.callback_query(F.data == "Корректировка сроков")
async def transfer_application(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).transfer_of_application(state)


@dp.callback_query(Form.calendar_7, SimpleCalendarCallback.filter())
async def application_time(callback, callback_data, state: FSMContext):
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).time_application(callback_data, state)


@dp.callback_query(F.data[:5] == "Смена")
async def time_of_receipt(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).time_receipt(state)


@dp.message(Form.admin_transfer_order)
async def write_to_transfer_db(message: Message, state: FSMContext):
    """получение id заказа для переноса и запись в базу данных"""
    await message.delete()
    user = User.get_user(message.chat.id)
    await AdminPanel(message=message, user=user).write_db(state)


@dp.callback_query(F.data == "Отметить заявку как выполненную")
async def unlock_day(callback: types.CallbackQuery, state: FSMContext):
    await callback.message.delete()
    user = User.get_user(callback.message.chat.id)
    await AdminPanel(callback=callback, user=user).cancel_the_application(state)


@dp.message(Form.completed_application)
async def write_to_transfer_db(message: Message, state: FSMContext):
    """получение id выполненной заявки"""
    await message.delete()
    user = User.get_user(message.chat.id)
    await AdminPanel(message=message, user=user).receiving_amount(state)


@dp.message(Form.amount)
async def write_to_transfer_db(message: Message, state: FSMContext):
    """получение суммы за работу"""
    await message.delete()
    user = User.get_user(message.chat.id)
    await AdminPanel(message=message, user=user).entry_the_db_completed_orders(state)


async def main():
    bot = Bot(token=bot_token, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())

