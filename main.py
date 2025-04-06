import asyncio
import logging
import random
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import aiosqlite
import os
from dotenv import load_dotenv

# Загрузка переменных окружения
load_dotenv()

# Настройка логирования
logging.basicConfig(level=logging.INFO)

# Инициализация бота и диспетчера
bot = Bot(token=os.getenv("BOT_TOKEN"))
dp = Dispatcher()

# Состояния для FSM
class UserState:
    WAITING_FOR_BET = "waiting_for_bet"

# Словарь для хранения состояний пользователей
user_states = {}

# Символы для слотов
SLOT_SYMBOLS = ["🍒", "🍊", "🍋", "🍇", "7️⃣", "💰"]

# Инициализация базы данных
async def init_db():
    async with aiosqlite.connect("casino.db") as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                balance INTEGER DEFAULT 1000
            )
        """)
        await db.commit()

# Обработчик команды /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    async with aiosqlite.connect("casino.db") as db:
        await db.execute("INSERT OR IGNORE INTO users (user_id, balance) VALUES (?, 1000)", (user_id,))
        await db.commit()
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Слоты", callback_data="slots")],
        [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")]
    ])
    
    await message.answer(
        "Добро пожаловать в казино! 🎲\n"
        "Ваш начальный баланс: 1000 монет\n"
        "Выберите игру:",
        reply_markup=keyboard
    )

# Обработчик кнопки баланса
@dp.callback_query(lambda c: c.data == "balance")
async def show_balance(callback: types.CallbackQuery):
    async with aiosqlite.connect("casino.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (callback.from_user.id,)) as cursor:
            balance = await cursor.fetchone()
    
    await callback.message.edit_text(f"Ваш баланс: {balance[0]} монет")

# Обработчик кнопки слотов
@dp.callback_query(lambda c: c.data == "slots")
async def play_slots(callback: types.CallbackQuery):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🎰 Крутить", callback_data="spin_slots")]
    ])
    await callback.message.edit_text(
        "🎰 Добро пожаловать в игру Слоты!\n"
        "Нажмите кнопку 'Крутить', чтобы начать игру.",
        reply_markup=keyboard
    )

# Обработчик кнопки крутить
@dp.callback_query(lambda c: c.data == "spin_slots")
async def ask_bet(callback: types.CallbackQuery):
    user_states[callback.from_user.id] = UserState.WAITING_FOR_BET
    await callback.message.edit_text(
        "Введите вашу ставку (целое число):"
    )

# Обработчик ввода ставки
@dp.message()
async def process_bet(message: types.Message):
    if message.from_user.id not in user_states or user_states[message.from_user.id] != UserState.WAITING_FOR_BET:
        return

    try:
        bet = int(message.text)
        if bet <= 0:
            await message.answer("Ставка должна быть положительным числом!")
            return

        async with aiosqlite.connect("casino.db") as db:
            async with db.execute("SELECT balance FROM users WHERE user_id = ?", (message.from_user.id,)) as cursor:
                balance = await cursor.fetchone()
                if balance[0] < bet:
                    await message.answer("У вас недостаточно средств!")
                    return

        # Генерация результатов слотов
        results = [random.choice(SLOT_SYMBOLS) for _ in range(3)]
        result_text = f"🎰 Результат: {' '.join(results)}"

        # Проверка выигрыша
        if results[0] == results[1] == results[2]:
            win = bet * 3
            result_text += f"\n🎉 Поздравляем! Вы выиграли {win} монет!"
        elif results[0] == results[1] or results[1] == results[2] or results[0] == results[2]:
            win = bet
            result_text += f"\n🎉 Поздравляем! Вы выиграли {win} монет!"
        else:
            win = -bet
            result_text += f"\n😢 К сожалению, вы проиграли {bet} монет."

        # Обновление баланса
        async with aiosqlite.connect("casino.db") as db:
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (win, message.from_user.id))
            await db.commit()

        # Показ результатов
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🎰 Крутить снова", callback_data="spin_slots")],
            [InlineKeyboardButton(text="💰 Баланс", callback_data="balance")]
        ])
        
        await message.answer(result_text, reply_markup=keyboard)
        del user_states[message.from_user.id]

    except ValueError:
        await message.answer("Пожалуйста, введите корректное число!")

# Запуск бота
async def main():
    await init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 