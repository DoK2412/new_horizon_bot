from aiogram.fsm.state import State, StatesGroup


class Form(StatesGroup):
    number = State()                        # состояние получения номера телефона юзер
    job = State()                           # состояние получения необходимой работы юзер
    cancellation_order = State()            # состояние отмены заявки юзер
    transfer = State()                      # состояние переноса заявки юзер
    calendar_1 = State()                    # состояние календаря подачи заявки юзер
    calendar_2 = State()                    # состояние календаря переноса заявки админ
    calendar_3 = State()                    # состояние календаря для изменения количества заявок админ
    calendar_4 = State()                    # состояние календаря для статистики первого админ
    calendar_5 = State()                    # состояние календаря для статистики второго админ
    calendar_6 = State()                    # состояние календаря для блокировки дня
    number_applications = State()           # состояние изменения количества заявок админ
    cancellation_application = State()      # состояние на отмену заявки админ
    reason_cancellation = State()           # состояние для причины отмены админ
    user_rights_id = State()                # состояние для получения id пользователя под смену прав
    user_rights = State()                   # состояние для получения типа прав пользователя
    admin_transfer_order = State()          # состояние для переноса заявки админ
    calendar_7 = State()                    # состояние для выбора дня переноса заявки
    completed_application = State()         # состояние для id выполненой заявки
    amount = State()                        # смостояние для получения суммы за работу


