from aiogram.fsm.state import State, StatesGroup


class SubscriptionStates(StatesGroup):
    choose_product = State()
    payment = State()
    confirmation = State()
