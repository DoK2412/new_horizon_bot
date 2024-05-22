from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Users(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    telegram_id: int
    telegram_teg: str
    registration_date: str
    active: bool = True
    rights: str
    user_name: str
    surname: str


class Calendar(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    day: int
    quantity_order: str
    actively: bool
    month: int


class Orders(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    creation_date: str
    active: bool
    job: str
    price: str
    refusal: bool
    rejection_reason: str
    number_phone: str
    order_date: str
    time: str
    closing_date: datetime


class Notebook(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int
    creation_date: str
    name: str
    text: str