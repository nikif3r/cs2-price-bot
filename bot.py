import os
import asyncio
import logging
from datetime import datetime

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command

API_TOKEN = os.getenv("BOT_TOKEN")

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher()

USERS = {}

async def fetch_price_rub(item_name: str) -> float:
    base = abs(hash(item_name)) % 5000 + 500
    return float(base) + 0.41

def get_user_data(user_id: int):
    if user_id not in USERS:
        USERS[user_id] = {"items": {}}
    return USERS[user_id]

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "Привет! Я бот для отслеживания цен скинов.\n"
        "Команды:\n"
        "/add — добавить предмет\n"
        "/list — список отслеживаемых\n"
    )

@dp.message(Command("add"))
async def cmd_add(message: types.Message):
    await message.answer("Отправь название предмета.")
    dp.message.register(handle_add_item, lambda m: m.from_user.id == message.from_user.id)

async def handle_add_item(message: types.Message):
    user = get_user_data(message.from_user.id)
    name = message.text.strip()
    if name in user["items"]:
        await message.answer("Этот предмет уже отслеживается.")
        return
    price = await fetch_price_rub(name)
    user["items"][name] = {
        "last_price": price,
        "history": [(datetime.utcnow().date().isoformat(), price)]
    }
    await message.answer(f"Добавил:\n{name}\nТекущая цена: {price:.2f} ₽")

@dp.message(Command("list"))
async def cmd_list(message: types.Message):
    user = get_user_data(message.from_user.id)
    if not user["items"]:
        await message.answer("Ты ещё ничего не отслеживаешь.")
        return
    text = "Отслеживаемые предметы:\n\n"
    for name, data in user["items"].items():
        text += f"- {name}: {data['last_price']:.2f} ₽\n"
    await message.answer(text)

async def daily_check():
    while True:
        now = datetime.utcnow()
        if now.hour == 9:
            for user_id, data in USERS.items():
                items = data["items"]
                if not items:
                    continue
                text = "Ежедневный отчёт:\n\n"
                for name, info in items.items():
                    old_price = info["last_price"]
                    new_price = await fetch_price_rub(name)
                    info["last_price"] = new_price
                    info["history"].append((now.date().isoformat(), new_price))
                    diff = new_price - old_price
                    diff_pct = (diff / old_price * 100) if old_price else 0
                    sign = "+" if diff >= 0 else ""
                    text += (
                        f"{name}\n"
                        f"Текущая: {new_price:.2f} ₽\n"
                        f"Вчера: {old_price:.2f} ₽\n"
                        f"Изменение: {sign}{diff:.2f} ₽ ({sign}{diff_pct:.2f}%)\n\n"
                    )
                try:
                    await bot.send_message(user_id, text)
                except:
                    pass
            await asyncio.sleep(3600)
        await asyncio.sleep(300)

async def main():
    asyncio.create_task(daily_check())
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
