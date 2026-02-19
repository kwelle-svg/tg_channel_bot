from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData
from typing import Optional

class TakeCallback(CallbackData, prefix="take"):
    action: str
    take_id: int
    hashtag: Optional[str] = None

def get_send_or_not_keyboard(take_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="Отправить", callback_data=TakeCallback(action="confirm", take_id=take_id))
    builder.button(text="Редактировать хэштеги", callback_data=TakeCallback(action="edit", take_id=take_id))
    builder.button(text="Отклонить", callback_data=TakeCallback(action="delete", take_id=take_id))
    builder.adjust(1)
    return builder.as_markup()
    # return types.InlineKeyboardMarkup(inline_keyboard=[
    #     [types.InlineKeyboardButton(text="Отправить", callback_data="send_or_plan_take")],
    #     [types.InlineKeyboardButton(text="Редактировать хэштеги",
    #                                 callback_data="change_hashtag")],
    #     [types.InlineKeyboardButton(text="Отклонить", callback_data="del_or_not_take")]
    # ])

# Отправить или запланировать
# @dp.callback_query(F.data == "send_or_plan_take")
# async def send_or_plan_take(callback: types.CallbackQuery):
#     new_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
#         [types.InlineKeyboardButton(text="Сейчас", callback_data="send_take")],
#         [types.InlineKeyboardButton(text="Запланировать", callback_data="taking_time_from_user")],
#         [types.InlineKeyboardButton(text="Я передумала", callback_data="go_back")] # Добавляем кнопку назад
#     ])
#     await callback.message.edit_text("Когда отправить тейк?", reply_markup=new_keyboard)
#     await callback.answer()

def get_confirm_keyboard(take_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="Сейчас", callback_data=TakeCallback(action="send_now", take_id=take_id))
    builder.button(text="Запланировать", callback_data=TakeCallback(action="plan", take_id=take_id))
    builder.button(text="Назад", callback_data=TakeCallback(action="back", take_id=take_id))
    builder.adjust(2, 1)
    return builder.as_markup()


def back_keyboard(take_id: int):
    builder = InlineKeyboardBuilder()
    builder.button(text="Назад", callback_data=TakeCallback(action="back", take_id=take_id))
    # builder.adjust(2, 1)
    return builder.as_markup()

def new_hashtag_keyboard(take_id: int):
    builder = InlineKeyboardBuilder()
    tags = {
        "gensh": "#генш",
        "hsr": "#хср",
        "another": "#другое"
    }
    
    for cb_val, display_name in tags.items():
        builder.button(
            text=display_name, 
            callback_data=TakeCallback(action="add_tag", take_id=take_id, hashtag=display_name)
        )
    
    builder.button(text="Сбросить🔄", callback_data=TakeCallback(action="reset_tags", take_id=take_id))
    builder.button(text="Готово✅", callback_data=TakeCallback(action="back", take_id=take_id))
    
    builder.adjust(3, 2)
    return builder.as_markup()