import streamlit as st
import sqlite3
import random
import time
from PIL import Image
import requests
from io import BytesIO
import hashlib

# Настройка страницы
st.set_page_config(
    page_title="Казино Бот",
    page_icon="🎰",
    layout="wide"
)

# Подключение к базе данных
def get_db_connection():
    conn = sqlite3.connect('casino.db')
    conn.row_factory = sqlite3.Row
    return conn

# Функция для хеширования пароля
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Функция для проверки пароля
def verify_password(password, hashed_password):
    return hash_password(password) == hashed_password

# Функция для аутентификации пользователя
def authenticate_user(username, password):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
    conn.close()
    if user and verify_password(password, user['password']):
        return user
    return None

# Функция для получения данных пользователя
def get_user_data(user_id):
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE user_id = ?', (user_id,)).fetchone()
    conn.close()
    return user

# Функция для получения топа игроков
def get_top_players():
    conn = get_db_connection()
    top_players = conn.execute('SELECT * FROM users ORDER BY balance DESC LIMIT 10').fetchall()
    conn.close()
    return top_players

# Функция для перевода средств
def transfer_money(from_user_id, to_user_id, amount):
    conn = get_db_connection()
    try:
        conn.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (amount, from_user_id))
        conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (amount, to_user_id))
        conn.commit()
        return True
    except:
        conn.rollback()
        return False
    finally:
        conn.close()

# Основной интерфейс
def main():
    st.title("🎰 Казино Бот")
    
    # Инициализация состояния сессии
    if 'user_data' not in st.session_state:
        st.session_state.user_data = None
    if 'is_logged_in' not in st.session_state:
        st.session_state.is_logged_in = False
    
    # Если пользователь не авторизован, показываем форму входа
    if not st.session_state.is_logged_in:
        col1, col2 = st.columns(2)
        
        with col1:
            st.header("Вход")
            with st.form("login_form"):
                username = st.text_input("Имя пользователя")
                password = st.text_input("Пароль", type="password")
                submitted = st.form_submit_button("Войти")
                
                if submitted:
                    user = authenticate_user(username, password)
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
                        conn = get_db_connection()
                        try:
                            hashed_password = hash_password(reg_password)
                            conn.execute("""
                                INSERT INTO users (username, password, first_name, last_name)
                                VALUES (?, ?, ?, ?)
                            """, (reg_username, hashed_password, reg_first_name, reg_last_name))
                            conn.commit()
                            st.success("Регистрация успешна! Теперь вы можете войти.")
                        except sqlite3.IntegrityError:
                            st.error("Имя пользователя уже занято")
                        finally:
                            conn.close()
    
    # Если пользователь авторизован, показываем интерфейс казино
    else:
        user_id = st.session_state.user_data['id']
        user_data = get_user_data(user_id)
        
        if user_data:
            # Создаем две колонки для профиля
            col1, col2 = st.columns([1, 3])
            
            with col1:
                # Загрузка аватарки
                try:
                    response = requests.get(f"https://api.telegram.org/file/bot{st.secrets['BOT_TOKEN']}/getUserProfilePhotos?user_id={user_id}")
                    if response.status_code == 200:
                        photo_data = response.json()
                        if photo_data['result']['photos']:
                            photo = photo_data['result']['photos'][0][0]
                            photo_url = f"https://api.telegram.org/file/bot{st.secrets['BOT_TOKEN']}/getFile?file_id={photo['file_id']}"
                            photo_response = requests.get(photo_url)
                            if photo_response.status_code == 200:
                                file_path = photo_response.json()['result']['file_path']
                                image_url = f"https://api.telegram.org/file/bot{st.secrets['BOT_TOKEN']}/{file_path}"
                                image = Image.open(BytesIO(requests.get(image_url).content))
                                st.image(image, width=150)
                except:
                    st.image("default_avatar.png", width=150)
            
            with col2:
                st.header(f"👤 {user_data['username']}")
                st.subheader(f"💰 Баланс: {user_data['balance']} монет")
                
                # Кнопка выхода
                if st.button("Выйти"):
                    st.session_state.is_logged_in = False
                    st.session_state.user_data = None
                    st.rerun()
            
            # Создаем вкладки
            tab1, tab2, tab3 = st.tabs(["🎲 Рулетка", "📊 Топ игроков", "💸 Перевод"])
            
            with tab1:
                st.header("🎲 Игра в рулетку")
                bet = st.number_input("Ваша ставка", min_value=1, max_value=user_data['balance'])
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
                            conn = get_db_connection()
                            conn.execute('UPDATE users SET balance = balance + ? WHERE user_id = ?', (winnings, user_id))
                            conn.commit()
                            conn.close()
                        else:
                            st.error("К сожалению, вы проиграли!")
                            conn = get_db_connection()
                            conn.execute('UPDATE users SET balance = balance - ? WHERE user_id = ?', (bet, user_id))
                            conn.commit()
                            conn.close()
            
            with tab2:
                st.header("📊 Топ игроков")
                top_players = get_top_players()
                for i, player in enumerate(top_players, 1):
                    st.write(f"{i}. {player['username']} - {player['balance']} монет")
            
            with tab3:
                st.header("💸 Перевод средств")
                recipient = st.text_input("Ник получателя")
                amount = st.number_input("Сумма перевода", min_value=1, max_value=user_data['balance'])
                
                if st.button("Перевести"):
                    conn = get_db_connection()
                    recipient_data = conn.execute('SELECT * FROM users WHERE username = ?', (recipient,)).fetchone()
                    if recipient_data:
                        if transfer_money(user_id, recipient_data['user_id'], amount):
                            st.success(f"Успешно переведено {amount} монет пользователю {recipient}")
                        else:
                            st.error("Ошибка при переводе средств")
                    else:
                        st.error("Пользователь не найден")
                    conn.close()
        else:
            st.error("Пользователь не найден")
            st.session_state.is_logged_in = False
            st.session_state.user_data = None
            st.rerun()

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
    .stTextInput>div>div>input {
        background-color: #2E2E2E;
        color: white;
    }
    .stForm {
        background-color: #2E2E2E;
        padding: 20px;
        border-radius: 10px;
    }
    h1, h2, h3 {
        color: #4CAF50;
    }
</style>
""", unsafe_allow_html=True)

if __name__ == "__main__":
    main() 