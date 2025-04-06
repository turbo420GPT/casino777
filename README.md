# Казино Telegram

Это мини-приложение Telegram, которое позволяет играть в казино через веб-интерфейс Streamlit.

## Установка

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd <repository-name>
```

2. Установите зависимости:
```bash
pip install -r requirements.txt
```

3. Настройте токен бота:
   - Получите токен у @BotFather
   - Замените `your_bot_token_here` в файле `.streamlit/secrets.toml`

## Запуск

1. Запустите Streamlit приложение:
```bash
streamlit run app.py
```

2. Откройте приложение в браузере по адресу: `http://localhost:8501`

## Функциональность

- Авторизация через Telegram
- Игра в слоты
- Отслеживание баланса
- Современный и удобный интерфейс

## Технологии

- Python 3.8+
- Streamlit
- aiogram
- SQLite
- Telegram Bot API 