import json
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from pytz import timezone

from aiogram.fsm.storage.base import StorageKey

import logging
import asyncio
import datetime
import aiosqlite
from random import randint
from aiogram import Bot, Dispatcher, types, F, Router
from aiogram.types import InputMediaPhoto, Message, TelegramObject
from aiogram.filters.command import Command
from aiogram.enums.content_type import ContentType
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.utils.chat_action import ChatActionSender
from aiogram.utils.media_group import MediaGroupBuilder
import re

from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters.callback_data import CallbackData

from aiogram import BaseMiddleware
from typing import Callable, Any, Awaitable, Union, List, Callable, Dict, Optional

from hashtag import find_words
from config import BOT_TOKEN, chatid, tgChanel_id
from states import Registration, Hashtag, Time
from database import init_db, DB_NAME
from keyboards import TakeCallback, get_send_or_not_keyboard, get_confirm_keyboard, back_keyboard, new_hashtag_keyboard


moscow_tz = timezone('Europe/Moscow')
scheduler = AsyncIOScheduler(timezone=moscow_tz)

bot = Bot(token=BOT_TOKEN,
          default=DefaultBotProperties(parse_mode=ParseMode.HTML))

router = Router()
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

def get_admin_state(bot: Bot, dp: Dispatcher):
    return FSMContext(
        storage=dp.storage,
        key=StorageKey(bot_id=bot.id, chat_id=int(chatid), user_id=int(chatid))
    )


@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.reply("Напишите пожалуйста ваш тейк (НЕ НУЖНО добавлять оформление). Если обнаружите ошибку - напишите cюда (ссылку добав)\n\nДля создания был использован бот (будущий бот)")

manecen = '#тейк #другое | <a href="t.me/HateHoyoCfBot">бот для тейков</a>'




class AlbumMiddleware(BaseMiddleware):
    def __init__(self, latency: float = 0.2):
        self.latency = latency
        self.album_data: Dict[str, List[Message]] = {}

    async def __call__(self, handler, event: Message, data: Dict[str, Any]) -> Any:
        if not event.media_group_id:
            return await handler(event, data)
        try:
            if event.media_group_id not in self.album_data:
                self.album_data[event.media_group_id] = [event]
                await asyncio.sleep(self.latency)
                data["album"] = self.album_data.pop(event.media_group_id)
                return await handler(event, data)
            else:
                self.album_data[event.media_group_id].append(event)
        except Exception:
            return await handler(event, data)

router.message.middleware(AlbumMiddleware())



# ============== HASHTAGS ==============

@router.callback_query(TakeCallback.filter(F.action == "add_tag"))
async def add_hashtag_from_kb(callback: types.CallbackQuery, callback_data: TakeCallback):
    take_id = callback_data.take_id
    new_tag = callback_data.hashtag

    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT main_msg_id, original_text, finish_text, media_type FROM takes WHERE id = ?", (take_id,)) as cursor:
            row = await cursor.fetchone()
            if not row: return
            
            main_msg_id, orig_text, current_finish, media_type = row
            
            if new_tag in current_finish:
                await callback.answer(f"Тэг {new_tag} уже есть!")
                return

            parts = current_finish.split('|')
            if len(parts) > 1:
                updated_text = f"{parts[0].strip()} {new_tag} | {parts[1].strip()}"
            else:
                updated_text = f"{current_finish} {new_tag}"

            await db.execute("UPDATE takes SET finish_text = ? WHERE id = ?", (updated_text, take_id))
            await db.commit()

    try:
        if media_type != "text":
            await bot.edit_message_caption(
                chat_id=chatid, 
                message_id=main_msg_id, 
                caption=updated_text
            )
        else:
            await bot.edit_message_text(
                chat_id=chatid, 
                message_id=main_msg_id, 
                text=updated_text
            )
        await callback.answer(f"Добавлен {new_tag}")
    except Exception as e:
        logging.error(f"Error editing preview: {e}")
        await callback.answer("Ошибка обновления превью")

@router.callback_query(TakeCallback.filter(F.action == "reset_tags"))
async def reset_hashtags(callback: types.CallbackQuery, callback_data: TakeCallback):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT main_msg_id, original_text, media_type FROM takes WHERE id = ?", (callback_data.take_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                main_msg_id, orig_text, media_type = row
                reset_text = f'{orig_text}\n\n#тейк | <a href="t.me/HateHoyoCfBot">бот для тейков</a>'
                await db.execute("UPDATE takes SET finish_text = ? WHERE id = ?", (reset_text, callback_data.take_id))
                await db.commit()
                
                try:
                    if media_type != "text":
                        await bot.edit_message_caption(chat_id=chatid, message_id=main_msg_id, caption=reset_text)
                    else:
                        await bot.edit_message_text(chat_id=chatid, message_id=main_msg_id, text=reset_text)
                except Exception: pass
    await callback.answer("Хэштеги сброшены")

@dp.callback_query(TakeCallback.filter(F.action == "new_hashtag"))
async def adding_new_hashtags(callback: types.CallbackQuery, callback_data: TakeCallback):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT finish_text, media_type, file_id FROM takes WHERE id = ?", (callback_data.take_id,)) as cursor:
            row = await cursor.fetchone()
            
            hashtag = "#генш" if callback_data.hashtag=="gensh" else "#другое" 
            if row:
                text, media_type, file_id = row
                await callback.message.edit_text("Тейк отправлен✅")
                await db.execute(f"UPDATE takes SET hashtag = 'sent' WHERE id = ?", (callback_data.take_id,))
                await db.commit()
            else:
                await callback.answer("Ошибка: тейк не найден в базе.")

@dp.message(Hashtag.new_hashtag)
async def proccess_hashtag(message: types.Message, state: FSMContext):
    await state.update_data(new_hashtag=message.text)
    data = await state.get_data()
    
    media_type = data.get("media_type") 

    main_msg_id = data.get("main_msg_id")
    original_text = data.get("original_text")
    msg_to_del = data.get("msg_to_del")

    hashtags = data.get("new_hashtag")


    updated_text = f'{original_text}\n\n#тейк {hashtags} | <a href="t.me/HateHoyoCfBot">бот для тейков</a>'
    
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


# ===========ФОТОГРАФИИ===========

@router.message(F.media_group_id)
async def handle_albums(message: Message, album: List[Message]):
    caption = album[0].caption or ""
    formatted = f'{caption}\n\n#тейк {find_words(caption) if caption else "#другое"} | <a href="t.me/HateHoyoCfBot">бот для тейков</a>'
    
    media_files = []
    builder = MediaGroupBuilder(caption=formatted)
    for msg in album:
        if msg.photo:
            media_files.append({'type': 'photo', 'file_id': msg.photo[-1].file_id})
            builder.add_photo(media=msg.photo[-1].file_id)
        elif msg.video:
            media_files.append({'type': 'video', 'file_id': msg.video.file_id})
            builder.add_video(media=msg.video.file_id)

    sent = await bot.send_media_group(chat_id=chatid, media=builder.build())
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO takes (user_id, main_msg_id, original_text, finish_text, media_type, file_id) VALUES (?, ?, ?, ?, ?, ?)",
            (message.from_user.id, sent[0].message_id, caption, formatted, "album", json.dumps(media_files))
        )
        t_id = cursor.lastrowid
        await db.commit()
    await bot.send_message(chat_id=chatid, text=f"Тейк #{t_id}. Отправить?", reply_markup=get_send_or_not_keyboard(t_id))

@router.message(F.photo)
async def handle_photo(message: Message):
    f_id = message.photo[-1].file_id
    caption = message.caption or ""
    formatted = f'{caption}\n\n#тейк {find_words(caption) if caption else "#другое"} | <a href="t.me/HateHoyoCfBot">бот для тейков</a>'
    
    sent = await bot.send_photo(chat_id=chatid, photo=f_id, caption=formatted)
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute("INSERT INTO takes (user_id, main_msg_id, original_text, finish_text, media_type, file_id) VALUES (?, ?, ?, ?, ?, ?)",
                                 (message.from_user.id, sent.message_id, caption, formatted, "photo", f_id))
        t_id = cursor.lastrowid
        await db.commit()
    await bot.send_message(chat_id=chatid, text=f"Тейк #{t_id}. Отправить?", reply_markup=get_send_or_not_keyboard(t_id))

@dp.message(F.video)
async def echo_video_messages(message: Message):
    file_id = message.video.file_id
    caption = message.caption or ""
    formatted_caption = f'{caption + "\n\n" if caption else ""}#тейк {find_words(caption) if caption else "#другое"} | <a href="t.me/HateHoyoCfBot">бот для тейков</a>'
    
    sent = await bot.send_video(chat_id=chatid, video=file_id, caption=formatted_caption)
    
    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO takes (user_id, main_msg_id, original_text, finish_text, media_type, file_id) VALUES (?, ?, ?, ?, ?, ?)",
            (message.from_user.id, sent.message_id, caption, formatted_caption, "video", file_id)
        )
        take_id = cursor.lastrowid
        await db.commit()

    await bot.send_message(chat_id=chatid, text=f"Тейк #{take_id}. Отправлять?", reply_markup=get_send_or_not_keyboard(take_id))

# ================= Клавиатура ======================

async def sending_take(take_id: int, plan_msg_id: int = None):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT finish_text, media_type, file_id, main_msg_id FROM takes WHERE id = ?", (take_id,)) as cursor:
            row = await cursor.fetchone()
            if not row:
                logging.error(f"Тейк {take_id} не найден!")
                return
            text, media_type, file_id, main_msg_id = row

        try:
            if media_type == "photo":
                await bot.send_photo(chat_id=tgChanel_id, photo=file_id, caption=text)
            elif media_type == "video":
                await bot.send_video(chat_id=tgChanel_id, video=file_id, caption=text)
            elif media_type == "album":
                media_list = json.loads(file_id)
                builder = MediaGroupBuilder(caption=text)
                for item in media_list:
                    if item['type'] == 'photo':
                        builder.add_photo(media=item['file_id'])
                    else:
                        builder.add_video(media=item['file_id'])
                await bot.send_media_group(chat_id=tgChanel_id, media=builder.build())
            else:
                await bot.send_message(chat_id=tgChanel_id, text=text)
            
            try:
                await bot.edit_message_text(
                    chat_id=chatid,
                    message_id=main_msg_id + 1, 
                    text=f"✅ Тейк #{take_id} успешно отправлен",
                    reply_markup=None
                )
            except Exception as e:
                logging.warning(f"Не удалось обновить кнопки для тейка {take_id}: {e}")

            if plan_msg_id:
                try:
                    await bot.delete_message(chat_id=chatid, message_id=plan_msg_id)
                except: pass

            await db.execute("DELETE FROM takes WHERE id = ?", (take_id,))
            await db.commit()
            logging.info(f"Тейк {take_id} отправлен и удален.")
        except Exception as e:
            logging.error(f"Ошибка отправки: {e}")
            

async def how_much_time(current_time, when_send) -> int:
    hours_of_current_time = int(current_time[:2])*60*60
    minutes_of_current_time = int(current_time[3:5])*60
    seconds_of_current_time = int(current_time[6:])
    int_current_time = hours_of_current_time+minutes_of_current_time+seconds_of_current_time
    print(when_send[:2], when_send[3:5])
    if(when_send[-2:] == "+1"):
        hours_of_when_send = (24+int(when_send[:2]))*60*60
    else:
        hours_of_when_send = int(when_send[:2])*60*60
    minutes_of_when_send = int(when_send[3:5])*60
    int_when_send = hours_of_when_send+minutes_of_when_send
    print(int_when_send-int_current_time)
    return int_when_send-int_current_time


@router.message(Time.send_time)
async def planning_take(message: types.Message, state: FSMContext):
    data = await state.get_data()
    take_id = data.get("take_id")
    msg_to_edit_id = data.get("msg_to_edit_id")
    
    try:
        time_parts = datetime.datetime.strptime(message.text.strip(), "%H:%M")
        now_msk = datetime.datetime.now(moscow_tz)
        
        run_date = now_msk.replace(
            hour=time_parts.hour, 
            minute=time_parts.minute, 
            second=0, microsecond=0
        )

        if run_date < now_msk:
            run_date += datetime.timedelta(days=1)

        scheduler.add_job(
            sending_take,
            trigger='date',
            run_date=run_date,
            args=[take_id],
            id=f"take_{take_id}"
        )

        await bot.edit_message_text(
            chat_id=message.chat.id,
            message_id=msg_to_edit_id,
            text=f"✅ Тейк #{take_id} запланирован!\n⏰ Отправка: {run_date.strftime('%d.%m %H:%M')} (МСК)"
        )

        scheduler.add_job(
            sending_take,
            trigger='date',
            run_date=run_date,
            args=[take_id, msg_to_edit_id],
            id=f"take_{take_id}",
            replace_existing=True
        )

        await bot.delete_message(chat_id=message.chat.id, message_id=message.message_id)
        await state.clear()
    except ValueError:
        await message.answer("❌ Неверный формат. Нужно ЧЧ:ММ (например, 15:30)")





@router.callback_query(TakeCallback.filter(F.action == "plan"))
async def plan_callback(callback: types.CallbackQuery, callback_data: TakeCallback, state: FSMContext):
    now_msk = datetime.datetime.now(moscow_tz)
    msg = await callback.message.answer(
        f"Введите время для тейка #{callback_data.take_id} (ЧЧ:ММ).\n"
        f"Сейчас в Москве: {now_msk.strftime('%H:%M')}"
    )
    await state.set_state(Time.send_time)
    await state.update_data(msg_to_edit_id=msg.message_id, take_id=callback_data.take_id)
    await callback.answer()

@router.callback_query(TakeCallback.filter(F.action == "send_now"))
async def process_send_now(callback: types.CallbackQuery, callback_data: TakeCallback):
    await callback.message.edit_text("Тейк отправлен в канал! ✅")
    await sending_take(callback_data.take_id)

@router.callback_query(TakeCallback.filter(F.action == "delete"))
async def process_delete(callback: types.CallbackQuery, callback_data: TakeCallback):
    async with aiosqlite.connect(DB_NAME) as db:
        await db.execute("DELETE FROM takes WHERE id = ?", (callback_data.take_id,))
        await db.commit()
    await callback.message.edit_text("Тейк отклонен❌")

@router.callback_query(TakeCallback.filter(F.action == "edit"))
async def process_edit(callback: types.CallbackQuery, callback_data: TakeCallback):
    await callback.message.edit_text(
        "Выберите новый(е) хештег(и)",
        reply_markup=new_hashtag_keyboard(callback_data.take_id)
    )

@router.callback_query(TakeCallback.filter(F.action == "back"))
async def process_back(callback: types.CallbackQuery, callback_data: TakeCallback):
    async with aiosqlite.connect(DB_NAME) as db:
        async with db.execute("SELECT finish_text, media_type, file_id FROM takes WHERE id = ?", (callback_data.take_id,)) as cursor:
            row = await cursor.fetchone()
        if row:
            text, media_type, file_id = row
            await callback.message.edit_text(
            text="Отправлять тейк?",
            reply_markup=get_send_or_not_keyboard(take_id=callback_data.take_id)
            )
            await db.execute("UPDATE takes SET status = 'sent' WHERE id = ?", (callback_data.take_id,))
            await db.commit()
        else:
            await callback.answer("Ошибка: тейк не найден в базе.") 

# ===============================================

@dp.callback_query(TakeCallback.filter(F.action == "confirm"))
async def process_confirm_step(callback: types.CallbackQuery, callback_data: TakeCallback):
    await callback.message.edit_text(
        "Когда отправить тейк?", 
        reply_markup=get_confirm_keyboard(callback_data.take_id)
    )

# ===============================================

@router.message(F.text, F.chat.type=="private")
async def echo_messages(message: types.Message):
    hshtg = find_words(message.text)
    formatted = f'{message.text}\n\n#тейк {hshtg} | <a href="t.me/HateHoyoCfBot">бот для тейков</a>'
    sent = await bot.send_message(chat_id=chatid, text=formatted)

    async with aiosqlite.connect(DB_NAME) as db:
        cursor = await db.execute(
            "INSERT INTO takes (user_id, main_msg_id, original_text, finish_text, media_type) VALUES (?, ?, ?, ?, ?)",
            (message.from_user.id, sent.message_id, message.text, formatted, "text")
        )
        t_id = cursor.lastrowid
        await db.commit()
    await bot.send_message(chat_id=chatid, text=f"Тейк #{t_id}. Отправить?", reply_markup=get_send_or_not_keyboard(t_id))

@router.message(F.chat.type=="private")
async def other_msgs(message: types.Message):
    await message.reply("Мы принимаем только текст/фото/видео")

async def main():
    await init_db()
    dp.include_router(router)
    scheduler.start()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
