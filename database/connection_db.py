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


engin = create_engine(JobDB().create(),
                      pool_pre_ping=True,
                      connect_args={
                          "keepalives": 1,
                          "keepalives_idle": 30,
                          "keepalives_interval": 10,
                          "keepalives_count": 5,
                      })

