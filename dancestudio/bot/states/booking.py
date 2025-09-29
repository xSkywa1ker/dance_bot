from aiogram.fsm.state import State, StatesGroup


class BookingStates(StatesGroup):
    choose_direction = State()
    choose_date = State()
    confirm_slot = State()
    ask_full_name = State()
    ask_age = State()
    reserve_or_confirm = State()
    payment = State()
