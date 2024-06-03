"""Файл предназначен для реализации класса пользователя"""

class User:
    user = dict()

    def __init__(self, chat_id):

        self.telegram_id = chat_id
        self.user_id = None
        self.date = None
        self.time = None
        self.number = None
        self.order_id = None
        self.statistics_start_date = None
        self.statistics_end_date = None
        self.user_rights_id = None


    @classmethod
    def get_user(cls, chat_id):
        if chat_id in cls.user.keys():
            return cls.user[chat_id]
        else:
            return cls.add_user(chat_id)

    @classmethod
    def add_user(cls, chat_id):
        cls.user[chat_id] = User(chat_id)
        return cls.user[chat_id]
