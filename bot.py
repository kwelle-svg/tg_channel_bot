#!venv/bin/python
import logging
import asyncio
from random import randint
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.types import InputMediaPhoto
from aiogram.filters.command import Command
from aiogram.enums.content_type import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.chat_action import ChatActionSender
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re

from hashtag import find_words
from config import BOT_TOKEN

# Объект бота
bot = Bot(token=BOT_TOKEN)
# Диспетчер для бота
dp = Dispatcher()
# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)


# Добавить возможность просто боту выкладывать тейк в Хейт Хойо кф (он спрашивает выкладывать или нет)
# Также бот будет спрашивать верные ли хэштеги стоят
# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.reply("Напишите пожалуйста ваш тейк")

manecen = '#тейк #генш | <a href="t.me/@HateHoyoCfBot">бот для тейков</a>'


def get_send_or_not_keyboard():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Отправить", callback_data="send_or_plan_take")],
        [types.InlineKeyboardButton(text="Отклонить", callback_data="del_or_not_take")],
        [types.InlineKeyboardButton(text="Редактировать хэштеги", callback_data="change_hashtag")]
    ])

@dp.message(Command("random"))
async def cmd_random(message: types.Message):
    await message.answer("Отправлять тейк?", reply_markup=get_send_or_not_keyboard())


# Отправить или запланировать
@dp.callback_query(F.data == "send_or_plan_take")
async def send_or_plan_take(callback: types.CallbackQuery):
    new_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Сейчас", callback_data="send_take")],
        [types.InlineKeyboardButton(text="Запланировать", callback_data="planning_take")],
        [types.InlineKeyboardButton(text="Я передумала", callback_data="go_back")] # Добавляем кнопку назад
    ])
    await callback.message.edit_text("Когда отправить тейк?", reply_markup=new_keyboard)
    await callback.answer()

# Отправка тейка
@dp.callback_query(F.data == "send_take")
async def send_take(callback: types.CallbackQuery):
    await callback.message.answer("Тейк отправлен✅")

# Когда отправляем тейк
@dp.callback_query(F.data == "planning_take")
async def planning_take(callback: types.CallbackQuery):
    await callback.message.answer("Напишите время")
# Реализовать здесь планировку тейков

# Изменить Хэштеги
@dp.callback_query(F.data == "change_hashtag")
async def change_hashtag(callback: types.CallbackQuery):
    await callback.message.answer("Меняем хэштеги")


# Тейк отправлен + ЗАПЛАНИРОВАТЬ ВРЕМЯ
@dp.callback_query(F.data == "del_or_not_take")
async def del_or_not_take(callback: types.CallbackQuery):
    new_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Да", callback_data="del_take")],
        [types.InlineKeyboardButton(text="Я передумала", callback_data="go_back")] # Добавляем кнопку назад
    ])
    await callback.message.edit_text("Вы уверены?(тейк удалится)", reply_markup=new_keyboard)
    await callback.answer()

# Отклонить тейк
@dp.callback_query(F.data == "del_take")
async def del_take(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer("Тейк отклонен")

# Новый хэндлер для обработки кнопки "Назад"
@dp.callback_query(F.data == "go_back")
async def process_back(callback_query: types.CallbackQuery):
    # Редактируем сообщение, возвращая исходный текст и клавиатуру
    await callback_query.message.edit_text(
        text="Отправлять тейк?", 
        reply_markup=get_send_or_not_keyboard()
    )
    await callback_query.answer()





@dp.message(F.text)
async def echo_messages(message: types.Message):
    mess = message
    hshtg = find_words(mess.text)
    await bot.send_message(chat_id='936395572', text=f'{mess.text}\n\n #тейк {hshtg} | <a href="t.me/@HateHoyoCfBot">бот для тейков</a>', parse_mode='HTML')

media_groups = {}

# @dp.message(F.photo)
# async def handler(message: types.Message):
#     if not message.media_group_id:
#         await message.answer_photo(message.photo[-1].file_id)
#         return

#     group_id = message.media_group_id
#     media_groups.setdefault(group_id, []).append(message)

#     await asyncio.sleep(1)  # ждём остальные фото

#     if group_id not in media_groups:
#         return

#     album = [
#         types.InputMediaPhoto(media=m.photo[-1].file_id)
#         for m in media_groups[group_id]
#     ]

#     album = MediaGroupBuilder(caption="CaptionS")

#     await message.answer_media_group(album, caption=f'{message.caption}\n\n #тейк #генш | <a href="t.me/@HateHoyoCfBot">бот для тейков</a>', parse_mode='HTML')
#     media_groups.pop(group_id, None)




@dp.message(F.photo)
async def echo_photo_messages(message: types.Message):
    mess = message
    media_groups = {}
    if mess.media_group_id:
        media_groups.setdefault(mess.media_group_id, []).append(mess)
        await asyncio.sleep(2)
        album = [
            InputMediaPhoto(media=m.photo[-1].file_id)
            for m in media_groups[mess.media_group_id]
        ]
        await message.answer_media_group(album)
    else:
        await bot.send_photo(chat_id='936395572', photo=mess.photo[0].file_id, caption=f'{mess.caption}\n\n #тейк #генш | <a href="t.me/@HateHoyoCfBot">бот для тейков</a>', parse_mode='HTML')

@dp.message(F.video)
async def echo_video_messages(message: types.Message):
    mess = message
    await bot.send_video(chat_id='936395572', video=mess.video[0].file_id, caption=f'{mess.caption}\n\n #тейк #генш | <a href="t.me/@HateHoyoCfBot">бот для тейков</a>', parse_mode='HTML')




async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Запуск бота
    asyncio.run(main())