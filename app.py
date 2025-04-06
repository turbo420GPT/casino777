import streamlit as st
import aiosqlite
import asyncio
import json
from streamlit_telegram_login import TelegramLogin

# Настройка страницы
st.set_page_config(
    page_title="Казино Telegram",
    page_icon="🎰",
    layout="wide"
)

# Инициализация состояния сессии
if 'user_data' not in st.session_state:
    st.session_state.user_data = None

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
            INSERT INTO users (user_id, balance) 
            VALUES (?, 1000) 
            ON CONFLICT(user_id) DO UPDATE SET balance = balance + ?
        """, (user_id, amount))
        await db.commit()

# Заголовок приложения
st.title("🎰 Казино Telegram")

# Компонент авторизации через Telegram
try:
    user_data = TelegramLogin(
        bot_token=st.secrets["BOT_TOKEN"],
        button_style="large",
        corner_radius=5,
        request_access=True,
        show_user_photo=True
    ).render()

    if user_data and isinstance(user_data, dict):
        st.session_state.user_data = user_data
        st.success(f"Добро пожаловать, {user_data.get('first_name', 'Пользователь')}!")
except Exception as e:
    st.error(f"Произошла ошибка при авторизации: {str(e)}")
    st.stop()

# Если пользователь авторизован, показываем интерфейс казино
if st.session_state.user_data:
    user_id = st.session_state.user_data['id']
    
    # Получаем баланс пользователя
    balance = asyncio.run(get_user_balance(user_id))
    
    # Отображаем баланс
    st.subheader(f"💰 Ваш баланс: {balance} монет")
    
    # Создаем колонки для игр
    col1, col2 = st.columns(2)
    
    with col1:
        st.header("🎰 Слоты")
        bet = st.number_input("Ваша ставка:", min_value=1, max_value=balance, value=1)
        
        if st.button("Крутить"):
            # Здесь будет логика игры в слоты
            # Пока что просто обновляем баланс для демонстрации
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
        background-color: #1E1E1E;
        color: white;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-size: 16px;
    }
    .stNumberInput>div>div>input {
        background-color: #2E2E2E;
        color: white;
    }
</style>
""", unsafe_allow_html=True) 