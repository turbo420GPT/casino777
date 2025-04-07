import streamlit as st
import aiosqlite
import asyncio
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import hashlib
import threading
import sqlite3
import random
import time
from PIL import Image
import requests
from io import BytesIO

# Настройка страницы
st.set_page_config(
    page_title="Казино Telegram",
    page_icon="🎰",
    layout="wide"
)

# Функция инициализации базы данных
async def init_db():
    try:
        async with aiosqlite.connect("casino.db") as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    balance INTEGER DEFAULT 1000,
                    first_name TEXT,
                    last_name TEXT,
                    telegram_username TEXT
                )
            """)
            await db.commit()
            print("База данных успешно инициализирована")
    except Exception as e:
        print(f"Ошибка при инициализации базы данных: {str(e)}")

# Инициализация базы данных при запуске
try:
    asyncio.run(init_db())
except Exception as e:
    print(f"Ошибка при запуске: {str(e)}")

# Инициализация состояния сессии
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False

# Функция для сохранения состояния сессии
def save_session_state():
    if st.session_state.is_logged_in and st.session_state.user_data:
        with open('session.json', 'w') as f:
            json.dump({
                'is_logged_in': st.session_state.is_logged_in,
                'user_data': st.session_state.user_data
            }, f)

# Функция для загрузки состояния сессии
def load_session_state():
    try:
        with open('session.json', 'r') as f:
            data = json.load(f)
            st.session_state.is_logged_in = data['is_logged_in']
            st.session_state.user_data = data['user_data']
    except (FileNotFoundError, json.JSONDecodeError):
        pass

# Загрузка состояния сессии при запуске
load_session_state()

# Функция для хеширования пароля
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Функция для проверки пароля
def verify_password(password, hashed_password):
    return hash_password(password) == hashed_password

# Функция для регистрации пользователя
async def register_user(username, password, first_name=None, last_name=None, telegram_username=None):
    try:
        print(f"Попытка регистрации пользователя: {username}")
        async with aiosqlite.connect("casino.db") as db:
            # Проверяем, существует ли пользователь
            async with db.execute("SELECT username FROM users WHERE username = ?", (username,)) as cursor:
                existing_user = await cursor.fetchone()
                if existing_user:
                    print(f"Пользователь {username} уже существует")
                    return False
            
            # Получаем максимальный user_id
            async with db.execute("SELECT MAX(user_id) FROM users") as cursor:
                max_id = await cursor.fetchone()
                new_user_id = (max_id[0] or 0) + 1
                print(f"Новый user_id: {new_user_id}")
            
            hashed_password = hash_password(password)
            await db.execute("""
                INSERT INTO users (user_id, username, password, first_name, last_name, telegram_username)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (new_user_id, username, hashed_password, first_name, last_name, telegram_username))
            await db.commit()
            print(f"Пользователь {username} успешно зарегистрирован")
            return True
    except Exception as e:
        print(f"Ошибка при регистрации: {str(e)}")
        return False

# Функция для аутентификации пользователя
async def authenticate_user(username, password):
    try:
        print(f"Попытка аутентификации пользователя: {username}")
        async with aiosqlite.connect("casino.db") as db:
            db.row_factory = sqlite3.Row
            cursor = await db.execute("SELECT * FROM users WHERE username = ?", (username,))
            user = await cursor.fetchone()
            await cursor.close()
            
            if user:
                print(f"Пользователь {username} найден в базе данных")
                user_dict = {
                    'user_id': user['user_id'],
                    'username': user['username'],
                    'password': user['password'],
                    'balance': user['balance'],
                    'first_name': user['first_name'],
                    'last_name': user['last_name'],
                    'telegram_username': user['telegram_username']
                }
                if verify_password(password, user_dict['password']):
                    print(f"Пароль для пользователя {username} верный")
                    return user_dict
                else:
                    print(f"Неверный пароль для пользователя {username}")
            else:
                print(f"Пользователь {username} не найден")
            return None
    except Exception as e:
        print(f"Ошибка при аутентификации: {str(e)}")
        return None

# Функция для получения баланса пользователя
async def get_user_balance(user_id):
    async with aiosqlite.connect("casino.db") as db:
        async with db.execute("SELECT balance FROM users WHERE user_id = ?", (user_id,)) as cursor:
            result = await cursor.fetchone()
            return result[0] if result else 1000

# Функция для обновления баланса
async def update_balance(user_id, amount):
    async with aiosqlite.connect("casino.db") as db:
        await db.execute("""
            UPDATE users SET balance = balance + ? WHERE user_id = ?
        """, (amount, user_id))
        await db.commit()

# Функция для получения топа игроков
async def get_top_players():
    async with aiosqlite.connect("casino.db") as db:
        async with db.execute("SELECT * FROM users ORDER BY balance DESC LIMIT 10") as cursor:
            return await cursor.fetchall()

# Функция для перевода средств
async def transfer_money(from_user_id, to_user_id, amount):
    async with aiosqlite.connect("casino.db") as db:
        try:
            await db.execute("UPDATE users SET balance = balance - ? WHERE user_id = ?", (amount, from_user_id))
            await db.execute("UPDATE users SET balance = balance + ? WHERE user_id = ?", (amount, to_user_id))
            await db.commit()
            return True
        except:
            await db.rollback()
            return False

# Функция для обработки команды /miniapp
async def miniapp_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    miniapp_url = f"https://your-domain.com/miniapp?user_id={user_id}"
    await update.message.reply_text(
        f"🎰 Откройте мини-приложение казино:\n{miniapp_url}",
        reply_markup={
            "inline_keyboard": [[{
                "text": "Открыть мини-приложение",
                "web_app": {"url": miniapp_url}
            }]]
        }
    )

# Функция для запуска бота в отдельном потоке
def run_bot():
    def bot_main():
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        application = Application.builder().token(os.getenv("BOT_TOKEN")).build()
        application.add_handler(CommandHandler("miniapp", miniapp_command))
        loop.run_until_complete(application.initialize())
        loop.run_until_complete(application.start())
        loop.run_until_complete(application.run_polling())
    
    bot_thread = threading.Thread(target=bot_main, daemon=True)
    bot_thread.start()

# Запуск бота в отдельном потоке
if not hasattr(st.session_state, 'bot_thread'):
    run_bot()

# Основной интерфейс
def main():
    st.title("🎰 Казино Telegram")

    # Если пользователь не авторизован, показываем форму входа/регистрации
    if not st.session_state.is_logged_in:
        # Создаем две колонки для входа и регистрации
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("Вход")
            with st.form("login_form"):
                login_username = st.text_input("Имя пользователя")
                login_password = st.text_input("Пароль", type="password")
                login_submitted = st.form_submit_button("Войти")
                
                if login_submitted:
                    try:
                        user = asyncio.run(authenticate_user(login_username, login_password))
                        if user:
                            st.session_state.user_data = {
                                'id': user['user_id'],
                                'username': user['username'],
                                'first_name': user['first_name'],
                                'last_name': user['last_name']
                            }
                            st.session_state.is_logged_in = True
                            save_session_state()  # Сохраняем состояние сессии
                            st.success("Успешный вход!")
                            st.rerun()
                        else:
                            st.error("Неверное имя пользователя или пароль")
                    except Exception as e:
                        st.error(f"Произошла ошибка при входе: {str(e)}")
        
        with col2:
            st.header("Регистрация")
            with st.form("register_form"):
                reg_username = st.text_input("Придумайте имя пользователя")
                reg_password = st.text_input("Придумайте пароль", type="password")
                confirm_password = st.text_input("Подтвердите пароль", type="password")
                reg_first_name = st.text_input("Имя (необязательно)")
                reg_last_name = st.text_input("Фамилия (необязательно)")
                reg_submitted = st.form_submit_button("Зарегистрироваться")
                
                if reg_submitted:
                    try:
                        if reg_password != confirm_password:
                            st.error("Пароли не совпадают")
                        elif len(reg_username) < 3:
                            st.error("Имя пользователя должно содержать минимум 3 символа")
                        elif len(reg_password) < 6:
                            st.error("Пароль должен содержать минимум 6 символов")
                        else:
                            success = asyncio.run(register_user(reg_username, reg_password, reg_first_name, reg_last_name))
                            if success:
                                st.success("Регистрация успешна! Теперь вы можете войти.")
                            else:
                                st.error("Имя пользователя уже занято")
                    except Exception as e:
                        st.error(f"Произошла ошибка при регистрации: {str(e)}")

    # Если пользователь авторизован, показываем интерфейс казино
    else:
        user_id = st.session_state.user_data['id']
        
        # Кнопка выхода
        if st.button("Выйти"):
            st.session_state.is_logged_in = False
            st.session_state.user_data = None
            # Удаляем файл сессии при выходе
            try:
                os.remove('session.json')
            except FileNotFoundError:
                pass
            st.rerun()
        
        # Получаем баланс пользователя
        try:
            balance = asyncio.run(get_user_balance(user_id))
            
            # Отображаем профиль пользователя
            col1, col2 = st.columns([1, 3])
            with col1:
                # Используем эмодзи вместо изображения
                st.markdown("""
                <div style="
                    width: 150px;
                    height: 150px;
                    background-color: #4CAF50;
                    border-radius: 50%;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                    font-size: 60px;
                    color: white;
                    margin: 0 auto;
                ">
                    👤
                </div>
                """, unsafe_allow_html=True)
            with col2:
                st.header(f"👤 {st.session_state.user_data['username']}")
                st.subheader(f"💰 Баланс: {balance} монет")
            
            # Создаем вкладки
            tab1, tab2, tab3 = st.tabs(["🎲 Рулетка", "📊 Топ игроков", "💸 Перевод"])
            
            with tab1:
                st.header("🎲 Игра в рулетку")
                bet = st.number_input("Ваша ставка", min_value=1, max_value=balance)
                numbers = st.multiselect("Выберите 3 числа (1-36)", range(1, 37), max_selections=3)
                
                if st.button("Крутить рулетку"):
                    if len(numbers) != 3:
                        st.error("Пожалуйста, выберите 3 числа!")
                    else:
                        # Анимация рулетки
                        placeholder = st.empty()
                        for i in range(10):
                            random_number = random.randint(1, 36)
                            placeholder.write(f"🎲 Выпало: {random_number}")
                            time.sleep(0.2)
                        
                        final_number = random.randint(1, 36)
                        placeholder.write(f"🎲 Выпало: {final_number}")
                        
                        if final_number in numbers:
                            winnings = bet * 36
                            st.success(f"Поздравляем! Вы выиграли {winnings} монет!")
                            asyncio.run(update_balance(user_id, winnings))
                        else:
                            st.error("К сожалению, вы проиграли!")
                            asyncio.run(update_balance(user_id, -bet))
            
            with tab2:
                st.header("📊 Топ игроков")
                top_players = asyncio.run(get_top_players())
                for i, player in enumerate(top_players, 1):
                    st.write(f"{i}. {player['username']} - {player['balance']} монет")
            
            with tab3:
                st.header("💸 Перевод средств")
                recipient = st.text_input("Ник получателя")
                amount = st.number_input("Сумма перевода", min_value=1, max_value=balance)
                
                if st.button("Перевести"):
                    try:
                        async def process_transfer():
                            async with aiosqlite.connect("casino.db") as db:
                                db.row_factory = sqlite3.Row
                                cursor = await db.execute("SELECT * FROM users WHERE username = ?", (recipient,))
                                recipient_data = await cursor.fetchone()
                                await cursor.close()
                                
                                if recipient_data:
                                    if await transfer_money(user_id, recipient_data['user_id'], amount):
                                        st.success(f"Успешно переведено {amount} монет пользователю {recipient}")
                                    else:
                                        st.error("Ошибка при переводе средств")
                                else:
                                    st.error("Пользователь не найден")
                        
                        asyncio.run(process_transfer())
                    except Exception as e:
                        st.error(f"Произошла ошибка при переводе: {str(e)}")
        except Exception as e:
            st.error(f"Произошла ошибка при загрузке данных: {str(e)}")
            st.session_state.is_logged_in = False
            st.session_state.user_data = None
            st.rerun()

# Стилизация
st.markdown("""
<style>
    .stApp {
        background-color: #2E2E2E;
        color: #FFFFFF;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-size: 16px;
    }
    .stNumberInput>div>div>input {
        background-color: #3E3E3E;
        color: #FFFFFF;
    }
    .stTextInput>div>div>input {
        background-color: #3E3E3E;
        color: #FFFFFF;
    }
    .stForm {
        background-color: #3E3E3E;
        padding: 20px;
        border-radius: 10px;
        color: #FFFFFF;
    }
    h1, h2, h3 {
        color: #4CAF50;
    }
    .stTextInput>div>div>label {
        color: #FFFFFF;
    }
    .stNumberInput>div>div>label {
        color: #FFFFFF;
    }
    .stMarkdown {
        color: #FFFFFF;
    }
    .stAlert {
        background-color: #3E3E3E;
        color: #FFFFFF;
    }
    .stSuccess {
        background-color: #2E7D32;
        color: #FFFFFF;
    }
    .stError {
        background-color: #C62828;
        color: #FFFFFF;
    }
    .stInfo {
        background-color: #1565C0;
        color: #FFFFFF;
    }
</style>
""", unsafe_allow_html=True) 

if __name__ == "__main__":
    main() 