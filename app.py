import streamlit as st
import aiosqlite
import asyncio
import json
import os
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import hashlib
import threading

# Настройка страницы
st.set_page_config(
    page_title="Казино Telegram",
    page_icon="🎰",
    layout="wide"
)

# Функция инициализации базы данных
async def init_db():
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

# Инициализация базы данных при запуске
asyncio.run(init_db())

# Инициализация состояния сессии
if 'user_data' not in st.session_state:
    st.session_state.user_data = None
if 'is_logged_in' not in st.session_state:
    st.session_state.is_logged_in = False

# Функция для хеширования пароля
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Функция для проверки пароля
def verify_password(password, hashed_password):
    return hash_password(password) == hashed_password

# Функция для регистрации пользователя
async def register_user(username, password, first_name=None, last_name=None, telegram_username=None):
    async with aiosqlite.connect("casino.db") as db:
        try:
            # Получаем максимальный user_id
            async with db.execute("SELECT MAX(user_id) FROM users") as cursor:
                max_id = await cursor.fetchone()
                new_user_id = (max_id[0] or 0) + 1
            
            hashed_password = hash_password(password)
            await db.execute("""
                INSERT INTO users (user_id, username, password, first_name, last_name, telegram_username)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (new_user_id, username, hashed_password, first_name, last_name, telegram_username))
            await db.commit()
            return True
        except aiosqlite.IntegrityError:
            return False
        except Exception as e:
            print(f"Ошибка при регистрации: {str(e)}")
            return False

# Функция для аутентификации пользователя
async def authenticate_user(username, password):
    async with aiosqlite.connect("casino.db") as db:
        async with db.execute("SELECT * FROM users WHERE username = ?", (username,)) as cursor:
            user = await cursor.fetchone()
            if user and verify_password(password, user['password']):
                return user
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
    async def bot_main():
        application = Application.builder().token(os.getenv("BOT_TOKEN")).build()
        application.add_handler(CommandHandler("miniapp", miniapp_command))
        await application.initialize()
        await application.start()
        await application.run_polling()
    
    asyncio.run(bot_main())

# Запуск бота в отдельном потоке
if not hasattr(st.session_state, 'bot_thread'):
    st.session_state.bot_thread = threading.Thread(target=run_bot, daemon=True)
    st.session_state.bot_thread.start()

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
                    user = asyncio.run(authenticate_user(login_username, login_password))
                    if user:
                        st.session_state.user_data = {
                            'id': user['user_id'],
                            'username': user['username'],
                            'first_name': user['first_name'],
                            'last_name': user['last_name']
                        }
                        st.session_state.is_logged_in = True
                        st.success("Успешный вход!")
                        st.rerun()
                    else:
                        st.error("Неверное имя пользователя или пароль")
        
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
                    if reg_password != confirm_password:
                        st.error("Пароли не совпадают")
                    elif len(reg_username) < 3:
                        st.error("Имя пользователя должно содержать минимум 3 символа")
                    elif len(reg_password) < 6:
                        st.error("Пароль должен содержать минимум 6 символов")
                    else:
                        if asyncio.run(register_user(reg_username, reg_password, reg_first_name, reg_last_name)):
                            st.success("Регистрация успешна! Теперь вы можете войти.")
                        else:
                            st.error("Имя пользователя уже занято")

    # Если пользователь авторизован, показываем интерфейс казино
    else:
        user_id = st.session_state.user_data['id']
        
        # Кнопка выхода
        if st.button("Выйти"):
            st.session_state.is_logged_in = False
            st.session_state.user_data = None
            st.rerun()
        
        # Получаем баланс пользователя
        balance = asyncio.run(get_user_balance(user_id))
        
        # Отображаем профиль пользователя
        col1, col2 = st.columns([1, 3])
        with col1:
            st.image("default_avatar.png", width=150)
        with col2:
            st.header(f"👤 {st.session_state.user_data['username']}")
            st.subheader(f"💰 Баланс: {balance} монет")
        
        # Создаем колонки для игр
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("🎰 Слоты")
            bet = st.number_input("Ваша ставка:", min_value=1, max_value=balance, value=1)
            
            if st.button("Крутить"):
                win = bet * 2  # Пример выигрыша
                asyncio.run(update_balance(user_id, win))
                st.success(f"Вы выиграли {win} монет!")
                st.balloons()
        
        with col2:
            st.header("🎲 Другие игры")
            st.info("Скоро появятся новые игры!")

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