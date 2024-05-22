from sqlmodel import create_engine

import setting


class JobDB(object):

    def __init__(self):
        self.user: str = setting.DataBase["user_db"]
        self.password: str = setting.DataBase["password_db"]
        self.db_name: str = setting.DataBase["name_db"]
        self.host: str = setting.DataBase["host_db"]
        self.port: int = setting.DataBase["port_db"]
        self.cursor = None


    def create(self):
        return f'postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.db_name}'


engin = create_engine(JobDB().create())

