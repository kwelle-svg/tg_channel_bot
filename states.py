from aiogram.fsm.state import StatesGroup, State


class Registration(StatesGroup):
    # Определяем два состояния
    name = State()
    email = State()


class Hashtag(StatesGroup):
    new_hashtag = State()
    # Добавить выход


class Time(StatesGroup):
    send_time = State()
    # Добавить выход