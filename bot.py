#!venv/bin/python
from aiogram.fsm.storage.base import StorageKey

import logging
import asyncio
import datetime
from random import randint
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.types import InputMediaPhoto, Message, TelegramObject
from aiogram.filters.command import Command
from aiogram.enums.content_type import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.chat_action import ChatActionSender
from aiogram.utils.media_group import MediaGroupBuilder
from aiogram.utils.keyboard import InlineKeyboardBuilder
import re

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from aiogram.fsm.storage.memory import MemoryStorage

from aiogram import BaseMiddleware
from typing import Callable, Any, Awaitable, Union, List, Callable, Dict

from hashtag import find_words
from config import BOT_TOKEN, chatid, tgChanel_id
from states import Registration, Hashtag, Time

# Объект бота
bot = Bot(token=BOT_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))
# Диспетчер для бота
router = Router()
dp = Dispatcher()
dp.include_router(router)
# Включаем логирование, чтобы не пропустить важные сообщения
logging.basicConfig(level=logging.INFO)
router = Router()


def get_admin_state(bot: Bot, dp: Dispatcher):
    return FSMContext(
        storage=dp.storage,
        key=StorageKey(bot_id=bot.id, chat_id=int(chatid), user_id=int(chatid))
    )


# Добавить возможность просто боту выкладывать тейк в Хейт Хойо кф (он спрашивает выкладывать или нет)
# Также бот будет спрашивать верные ли хэштеги стоят
# Хэндлер на команду /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.reply("Напишите пожалуйста ваш тейк (НЕ НУЖНО добавлять оформление). Если обнаружите ошибку - напишите cюда (ссылку добав)\n\nДля создания был использован бот (будущий бот)")

manecen = '#тейк #другое | <a href="t.me/@HateHoyoCfBot">бот для тейков</a>'




# Тест хэштегов

# Определяем состояния
class Form(StatesGroup):
    waiting_for_hashtags = State() # Состояние ожидания текста хэштегов


def get_send_or_not_keyboard():
    return types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Отправить", callback_data="send_or_plan_take")],
        [types.InlineKeyboardButton(text="Редактировать хэштеги",
                                    callback_data="change_hashtag")],
        [types.InlineKeyboardButton(text="Отклонить", callback_data="del_or_not_take")]
    ])

@dp.message(Command("random"))
async def cmd_random(message: types.Message):
    await message.answer("Отправлять тейк?",
                         reply_markup=get_send_or_not_keyboard())



# ============== HASHTAGS ==============
@dp.callback_query(F.data == "change_hashtag")
async def cmd_reg(callback: types.CallbackQuery, state: FSMContext):
    # !!! ПРОВЕРИТЬ ЧАТ АЙДИ
    msg_to_del = await bot.send_message(chat_id=chatid,
                           text="Напишите новый(е) хештег(и) (обязательно с #)")
    
    # if() # ПРОВЕРКУ ХЭШТЕГ ЕСТЬ ИЛИ НЕТ ДОБАВИТЬ
    await state.set_state(Hashtag.new_hashtag)
    await state.update_data(msg_to_del=msg_to_del.message_id)
    await callback.answer()

@dp.message(Hashtag.new_hashtag)
async def proccess_hashtag(message: types.Message, state: FSMContext):
    await state.update_data(new_hashtag=message.text)
    data = await state.get_data()
    
    media_type = data.get("media_type") 

    main_msg_id = data.get("main_msg_id")
    original_text = data.get("original_text")
    msg_to_del = data.get("msg_to_del")

    hashtags = data.get("new_hashtag")


    updated_text = f'{original_text}\n\n#тейк {hashtags} | <a href="t.me/@HateHoyoCfBot">бот для тейков</a>'
    
    try:
        if media_type == "photo" or media_type == "video" or media_type == "album":
            await message.bot.edit_message_caption(
                chat_id=message.chat.id, message_id=main_msg_id,
                caption=updated_text,
                parse_mode="HTML"
            )
        else:
            await message.bot.edit_message_text(
                chat_id=message.chat.id, message_id=main_msg_id,
                text=updated_text,
                parse_mode="HTML"
            )
        del_this_msg = await message.answer("Готово! Хэштеги обновлены.")
        await bot.delete_message(chat_id=message.chat.id,
                                 message_id=msg_to_del)
        await bot.delete_message(chat_id=message.chat.id,
                                 message_id=message.message_id)
        await asyncio.sleep(2)
        await bot.delete_message(chat_id=message.chat.id,
                                 message_id=del_this_msg.message_id)
    except Exception as e:
        await message.answer("Произошла ошибка при редактировании. Возможно, сообщение удалено.")
    
    await state.update_data(original_text=original_text,
                            finish_text=updated_text)
    
    # Сбрасываем состояние
    # await state.clear()



# ===========ФОТОГРАФИИ===========



class AlbumMiddleware(BaseMiddleware):
    def __init__(self, latency: float = 0.2):
        self.latency = latency
        self.album_data: Dict[str, List[Message]] = {}

    async def __call__(self, handler, event: Message, data: Dict[str, Any]) -> Any:
        # If the message is not part of an album, just pass it through
        if not event.media_group_id:
            return await handler(event, data)

        try:
            # If this is the first message of an album, create a list
            if event.media_group_id not in self.album_data:
                self.album_data[event.media_group_id] = [event]
                # Wait for other messages to arrive
                await asyncio.sleep(self.latency)
                
                # After waiting, put the collected messages into 'album' data
                data["album"] = self.album_data.pop(event.media_group_id)
                return await handler(event, data)
            else:
                # If the album list already exists, just add this message to it
                self.album_data[event.media_group_id].append(event)
        except Exception:
            return await handler(event, data)


dp.message.middleware(AlbumMiddleware())

@dp.message(F.media_group_id)
async def handle_albums(message: Message, album: List[Message], state: FSMContext):
    adm_state = get_admin_state(bot, dp)
    
    caption = album[0].caption or ""
    formatted_caption = f'{caption + "\n\n" if caption else ""}#тейк {find_words(caption) if caption else "#другое"} | <a href="t.me/@HateHoyoCfBot">бот для тейков</a>'
    
    # Save file IDs for the channel later
    media_files = []
    builder = MediaGroupBuilder(caption=formatted_caption)
    
    for msg in album:
        if msg.photo:
            file_id = msg.photo[-1].file_id
            media_files.append({'type': 'photo', 'file_id': file_id})
            builder.add_photo(media=file_id)
        elif msg.video:
            file_id = msg.video.file_id
            media_files.append({'type': 'video', 'file_id': file_id})
            builder.add_video(media=file_id)

    # Send to ADMIN for preview
    sent = await bot.send_media_group(chat_id=chatid, media=builder.build())
    await bot.send_message(chat_id=chatid, text="Отправлять тейк?", reply_markup=get_send_or_not_keyboard())

    await adm_state.update_data(
        main_msg_id=sent[0].message_id,
        finish_text=formatted_caption,
        original_text=caption,
        media_type="album",
        media_files=media_files
    )

@dp.message(F.photo)
async def handle_single_photo(message: Message):
    adm_state = get_admin_state(bot, dp)
    
    file_id = message.photo[-1].file_id
    caption = message.caption or ""
    formatted_caption = f'{caption + "\n\n" if caption else ""}#тейк {find_words(caption) if caption else "#другое"} | <a href="t.me/@HateHoyoCfBot">бот для тейков</a>'
    
    sent = await bot.send_photo(chat_id=chatid, photo=file_id, caption=formatted_caption)
    await bot.send_message(chat_id=chatid, text="Отправлять тейк?", reply_markup=get_send_or_not_keyboard())
    
    await adm_state.update_data(
        main_msg_id=sent.message_id,
        original_text=caption,
        finish_text=formatted_caption,
        media_type="photo",
        file_id=file_id
    )

@dp.message(F.video)
async def echo_video_messages(message: types.Message, state: FSMContext):
    adm_state = get_admin_state(bot, dp)
    
    file_id = message.video.file_id
    caption = message.caption or ""
    formatted_caption = f'{caption + "\n\n" if caption else ""}#тейк {find_words(caption) if caption else "#другое"} | <a href="t.me/@HateHoyoCfBot">бот для тейков</a>'
    
    sent = await bot.send_video(chat_id=chatid, video=file_id, caption=formatted_caption)
    await bot.send_message(chat_id=chatid, text="Отправлять тейк?", reply_markup=get_send_or_not_keyboard())
    
    await adm_state.update_data(
        main_msg_id=sent.message_id,
        finish_text=formatted_caption,
        original_text=caption,
        media_type="video",
        file_id=file_id
    )

# ================= Клавиатура ======================
# Отправить или запланировать
@dp.callback_query(F.data == "send_or_plan_take")
async def send_or_plan_take(callback: types.CallbackQuery):
    new_keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="Сейчас", callback_data="send_take")],
        [types.InlineKeyboardButton(text="Запланировать", callback_data="taking_time_from_user")],
        [types.InlineKeyboardButton(text="Я передумала", callback_data="go_back")] # Добавляем кнопку назад
    ])
    await callback.message.edit_text("Когда отправить тейк?", reply_markup=new_keyboard)
    await callback.answer()

async def sending_take(state: FSMContext):
    data = await state.get_data()
    text = data.get("finish_text")
    media_type = data.get("media_type") # 'photo', 'video', 'album', or None (text)
    
    if media_type == "photo":
        await bot.send_photo(chat_id=tgChanel_id, photo=data.get("file_id"), caption=text)
    
    elif media_type == "video":
        await bot.send_video(chat_id=tgChanel_id, video=data.get("file_id"), caption=text)
    
    elif media_type == "album":
        # Reconstruct the album from saved file_ids
        media_list = data.get("media_files")
        builder = MediaGroupBuilder(caption=text)
        for item in media_list:
            if item['type'] == 'photo':
                builder.add_photo(media=item['file_id'])
            else:
                builder.add_video(media=item['file_id'])
        await bot.send_media_group(chat_id=tgChanel_id, media=builder.build())
    
    else:
        # Just text
        await bot.send_message(chat_id=tgChanel_id, text=text)
    
    await state.clear()

# Отправка тейка
@dp.callback_query(F.data == "send_take")
async def send_take(callback: types.CallbackQuery, state: FSMContext):
    await sending_take(state=state)
    await callback.message.delete()
    await callback.message.answer("Тейк отправлен✅")


async def how_much_time(current_time, when_send) -> int:
    hours_of_current_time = int(current_time[:2])*60*60
    minutes_of_current_time = int(current_time[3:5])*60
    seconds_of_current_time = int(current_time[6:])
    int_current_time = hours_of_current_time+minutes_of_current_time+seconds_of_current_time
    print(when_send[:2], when_send[3:5])
    if(when_send[-2:] == "+1"): # Сделать ограничение в 86400 сек (24 часа)
        hours_of_when_send = (24+int(when_send[:2]))*60*60
    else:
        hours_of_when_send = int(when_send[:2])*60*60
    minutes_of_when_send = int(when_send[3:5])*60
    int_when_send = hours_of_when_send+minutes_of_when_send
    print(int_when_send-int_current_time)
    return int_when_send-int_current_time


@dp.callback_query(F.data == "taking_time_from_user")
async def taking_time(callback: types.CallbackQuery, state: FSMContext):
    # Можно в выводимое сообщение добавить настоящее нынешнее время
    current_time = str(datetime.datetime.now())[11:16]
    current_date = str(datetime.datetime.now())[:10]
    print(str(datetime.datetime.now())[:11])
    msg_to_edit = await bot.send_message(chat_id=chatid,
    text=f"Напишите время\n(в формате {current_time} или {current_time} +1 для отправки на следующий день)")

    # if # ПРОВЕРКУ ФОРМАТА ВРЕМЕНИ ДОБАВИТЬ
    await state.set_state(Time.send_time)
    await state.update_data(msg_to_edit=msg_to_edit)
    await callback.answer()

# Когда отправляем тейк
@dp.message(Time.send_time)
async def planning_take(message: types.Message, state: FSMContext):
    # if message.text== # Проверку короче
    await state.update_data(send_time=message.text)
    data = await state.get_data()

    what_time = data.get("send_time")

    try:
        await bot.delete_message(chat_id=chatid, message_id=message.message_id)
        await data.get("msg_to_edit").edit_text(text=f"Тейк отправится в {what_time}")
    except Exception as e:
        await message.answer("Ошибка, сообщение возможно удалено.")
    # Сделать, чтобы пользователь отправлял время только в формате\
    # 15.02.2026 12:10 (при этом день не обязателен, а время - да)
    # А также, чтобы время было больше текущего
    
    current_time = str(datetime.datetime.now())
    try:
        seconds = await how_much_time(current_time=current_time[11:19], when_send=what_time)
        await asyncio.sleep(seconds)
        
        await data.get("msg_to_edit").edit_text(text=f"Тейк отправлен!✅")
        await sending_take(state=state)
    except Exception as e:
        await message.answer("Произошла ошибка при редактировании. Возможно, указан неверный формат времени.")

# Отклонить тейк
@dp.callback_query(F.data == "del_or_not_take")
async def del_or_not_take(callback: types.CallbackQuery):
    await callback.message.answer("Тейк отклонен❌")
    await callback.message.delete()


# Новый хэндлер для обработки кнопки "Назад"
@dp.callback_query(F.data == "go_back")
async def process_back(callback_query: types.CallbackQuery):
    # Редактируем сообщение, возвращая исходный текст и клавиатуру
    await callback_query.message.edit_text(
        text="Отправлять тейк?", 
        reply_markup=get_send_or_not_keyboard()
    )
    await callback_query.answer()



async def hashtag_or_not(message: str) -> bool:
    if message[0] != "#":
        return False
    for i in len(message):
        if not(message[i] == " " and i != len(message)
           and message[i+1] == "#"):
            return False
    return True





@dp.message(F.text)
async def echo_messages(message: types.Message, state: FSMContext):
    adm_state = get_admin_state(bot, dp)

    mess = message
    hshtg = find_words(mess.text)
    base_text=f'{mess.text}'
    formatted_text = f'{base_text}\n\n#тейк {hshtg} | <a href="t.me/@HateHoyoCfBot">бот для тейков</a>'

    sent_message = await bot.send_message(chat_id=chatid, text=formatted_text)
    await bot.send_message(chat_id=chatid, text="Отправлять тейк?",
                           reply_markup=get_send_or_not_keyboard())
    
    await adm_state.update_data(
        main_msg_id=sent_message.message_id,
        original_text=base_text,
        finish_text=formatted_text,
        media_type=None
    )
    

# ДОБАВИТЬ ОБРАБОТЧИК ДЛЯ ВСЕХ ОСТАВШИХСЯ СООБЩЕНИЙ
@dp.message()
async def other_msgs(message: types.Message):
    await message.reply(text=f"Мы принимаем только текст/фото/видео")


async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    # Запуск бота
    asyncio.run(main())