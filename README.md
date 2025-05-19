# Wildberries Analysis Bot

Telegram бот для анализа товаров и ниш на Wildberries.

## Возможности

- Анализ товаров по артикулу
- Анализ ниш и категорий
- Отслеживание товаров
- Глобальный поиск товаров
- Система подписок и баланса

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/your-username/wild-bot.git
cd wild-bot
```

2. Создайте виртуальное окружение и установите зависимости:
```bash
python -m venv venv
source venv/bin/activate  # для Linux/Mac
# или
venv\Scripts\activate  # для Windows
pip install -r requirements.txt
```

3. Создайте файл .env и добавьте необходимые переменные окружения:
```
BOT_TOKEN=your_telegram_bot_token
SERPER_API_KEY=your_serper_api_key
```

4. Запустите бота:
```bash
python new_bot.py
```

## Структура проекта

- `new_bot.py` - основной файл бота
- `subscription_manager.py` - менеджер подписок и баланса
- `requirements.txt` - зависимости проекта

## Лицензия

MIT
