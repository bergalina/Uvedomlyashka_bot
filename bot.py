import logging
from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher import FSMContext
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher.filters.state import State, StatesGroup
from db import Db
from datetime import datetime, timedelta, date, time
import asyncio
import schedule

db = Db()
db.read()

bot = Bot('6174107725:AAF1_1ZMp69tSLfMTPcaHL6c2OgLA03jN4M')
dp = Dispatcher(bot, storage=MemoryStorage())

logging.basicConfig(level=logging.INFO)

bg_tasks = set()
def cock(time, user_id, desc, is_recurring):
    async def coro():
        logging.info(f"scheduled for {time}")
        delta = time - datetime.now()
        delay = delta.total_seconds()
        logging.info(f"sleeping for {delay}")
        await asyncio.sleep(delay)
        logging.info(f"called for {desc}")
        await bot.send_message(user_id, f"!!НАПОМИНАЮ!!\n{desc}")
        if is_recurring:
            cock(time + timedelta(days=7), user_id, desc, is_recurring)
    t = asyncio.create_task(coro())
    bg_tasks.add(t)
    t.add_done_callback(bg_tasks.discard)


class States(StatesGroup):
    waiting_for_name = State()
    waiting_for_day_or_date = State()
    waiting_for_day = State()
    waiting_for_date = State()
    waiting_for_time = State()


async def start(msg, state):
    logging.info("\o/")
    await msg.answer("Добрый день! Напишите название дела про которое Вам нужно напомнить")
    await state.set_state(States.waiting_for_name.state)


async def chosen_name(msg, state):
    name = msg.text
    await state.update_data(name=name)
    await ask_for_day_or_date(msg, state)


async def ask_for_day_or_date(msg, state):
    await msg.answer("Если Вам нужно еженедельно напоминать про это дело напишите “Еженедельное”,если это одноразовое дело, напишите “Одноразовое”")
    await state.set_state(States.waiting_for_day_or_date.state)


async def chosen_day_or_date(msg, state):
    is_recurring = msg.text.lower() == "еженедельное"
    await state.update_data(is_recurring=is_recurring)
    if is_recurring:
        await ask_for_weekday(msg, state)
    else:
        await ask_for_date(msg, state)


weekdays = ["понедельник", "вторник", "среда", "четверг", "пятница", "суббота", "воскресенье"]


async def ask_for_weekday(msg, state):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    for answer in weekdays:
        kb.add(answer)
    await msg.answer("Выберите день недели", reply_markup=kb)
    await state.set_state(States.waiting_for_day.state)


async def chosen_weekday(msg, state):
    if msg.text.lower() not in weekdays:
        await msg.reply("Ошибка,вы неправильно указали команду")
        return

    weekday = weekdays.index(msg.text.lower())
    d = date.today()
    if weekday < d.weekday():
        d = d + timedelta(days=(7 - d.weekday() + weekday))
    else:
        d = d + timedelta(days=(weekday - d.weekday()))
    logging.info(d)
    await state.update_data(date=d)
    await ask_for_time(msg, state)


async def ask_for_date(msg, state):
    await msg.answer("Введите дату в формате ДД.ММ.ГГГГ")
    await state.set_state(States.waiting_for_date.state)


async def chosen_date(msg, state):
    reply = msg.text
    if len(reply) != 10 or reply[2] != '.' or reply[5] != '.':
        await msg.reply("Ошибка,вы неправильно указали команду")
        return

    try:
        day = int(reply[0:2])
        month = int(reply[3:5])
        year = int(reply[6:])
        d = date(year, month, day)
        if d < date.today():
            raise Exception("Ошибка, вы неправильно указали команду")
    except Exception as e:
        logging.info(e)
        await msg.reply("Ошибка,вы неправильно указали команду")
        return

    await state.update_data(date=d)
    await ask_for_time(msg, state)


async def ask_for_time(msg, state):
    await msg.answer("Введите время в формате ЧЧ:ММ")
    await state.set_state(States.waiting_for_time.state)


async def chosen_time(msg, state):
    reply = msg.text
    if len(reply) != 5 or reply[2] != ':':
        await msg.reply("Ошибка,вы неправильно указали команду")
        return

    try:
        hour = int(reply[0:2])
        month = int(reply[3:])
        t = time(hour, month)
        dt = datetime.combine((await state.get_data())["date"], t)
        if dt < datetime.now():
            raise Exception("Ошибка,вы неправильно указали команду")
        logging.info(dt)
    except Exception as e:
        logging.info(e)
        await msg.reply("Ошибка,вы неправильно указали команду")
        return

    await state.update_data(dt=dt)
    await finished_creating_task(msg, state)


async def finished_creating_task(msg, state):
    data = await state.get_data()
    is_recurring = data["is_recurring"]
    dt = data["dt"]
    name = data["name"]

    db.add_task(msg.from_id, (name, dt, is_recurring))
    db.save()
    await msg.answer("Готово!")
    await state.finish()
    cock(dt, msg.from_id, name, is_recurring)


handlers = [
    (chosen_name, States.waiting_for_name),
    (chosen_day_or_date, States.waiting_for_day_or_date),
    (chosen_weekday, States.waiting_for_day),
    (chosen_date, States.waiting_for_date),
    (chosen_time, States.waiting_for_time),
]
dp.register_message_handler(start, commands="start", state="*")
for f, state in handlers:
    dp.register_message_handler(f, state=state)


async def main():
    await dp.skip_updates()
    await dp.start_polling()


if __name__ == '__main__':
    asyncio.run(main())
