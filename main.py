import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

API_TOKEN = '8887345234:AAHdutf6-R_OIi5TyTbKCFXGXeeAqeetkXU'

logging.basicConfig(level=logging.INFO)
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

class GameState(StatesGroup):
    playing = State()

def generate_all_numbers():
    numbers = []
    for a in range(10):
        for b in range(10):
            if b == a: continue
            for c in range(10):
                if c in (a, b): continue
                for d in range(10):
                    if d in (a, b, c): continue
                    numbers.append(f"{a}{b}{c}{d}")
    return numbers

ALL_NUMBERS = generate_all_numbers()

def get_bulls_cows(candidate, target):
    match = sum(1 for char in candidate if char in target)
    exact = sum(1 for i in range(4) if candidate[i] == target[i])
    return match, exact

def get_best_move(possible):
    if not possible: return None
    if len(possible) <= 2: return possible[0]
    search_space = ALL_NUMBERS if len(possible) <= 600 else possible
    best_move = possible[0]
    min_max_group = 99999
    for candidate in search_space:
        counts = {}
        for target in possible:
            m, e = get_bulls_cows(candidate, target)
            key = f"{m}_{e}"
            counts[key] = counts.get(key, 0) + 1
        max_group = max(counts.values())
        if max_group < min_max_group:
            min_max_group = max_group
            best_move = candidate
    return best_move

@dp.message(Command("start", "reset"))
async def start_game(message: types.Message, state: FSMContext):
    await state.set_state(GameState.playing)
    await state.update_data(possible=ALL_NUMBERS.copy())
    text = (
        "🎮 **Бот для взлома Быков и Коров готов!**\n\n"
        "1. Сделай первый ход в игре: `1234`\n"
        "2. Отправь мне результат в формате: `ход есть место`\n"
        "   *(Например: `1234 2 1`)*\n\n"
        "Для сброса игры напиши /reset"
    )
    await message.answer(text, parse_mode="Markdown")

@dp.message(GameState.playing)
async def process_filter(message: types.Message, state: FSMContext):
    try:
        parts = message.text.strip().split()
        if len(parts) != 3: raise ValueError
        guess, total, place = parts[0], int(parts[1]), int(parts[2])
        guess = guess.zfill(4)
        if len(guess) != 4 or not (0 <= total <= 4) or not (0 <= place <= 4): raise ValueError
    except ValueError:
        await message.answer("⚠️ Вводи так: `число есть место` (Пример: `1234 2 1`)", parse_mode="Markdown")
        return

    data = await state.get_data()
    possible = data.get("possible", ALL_NUMBERS.copy())
    new_possible = [num for num in possible if get_bulls_cows(guess, num) == (total, place)]
    await state.update_data(possible=new_possible)

    if len(new_possible) == 0:
        await message.answer("❌ Ошибка! Осталось 0 вариантов. Напиши /reset.")
        return
    if len(new_possible) == 1:
        await message.answer(f"🎉 **ФИНАЛ! Число:** `{new_possible[0]}`", parse_mode="Markdown")
        return

    msg = await message.answer("🧠 *Считаю ход...*", parse_mode="Markdown")
    best_move = get_best_move(new_possible)
    is_candidate = "из кандидатов" if best_move in new_possible else "РАЗВЕДКА!"
    await msg.edit_text(
        f"📊 **Осталось:** {len(new_possible)}\n💡 **Ход:** `{best_move}` _({is_candidate})_\n\nОтветь: `{best_move} ЕСТЬ МЕСТО`",
        parse_mode="Markdown"
    )

# Микро-сервер для заглушки
async def handle(request):
    return web.Response(text="Bot is running!")

async def main():
    app = web.Application()
    app.router.add_get('/', handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 8080))
    site = web.TCPSite(runner, '0.0.0.0', port)
    await site.start()
    
    # Запуск бота Telegram
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
