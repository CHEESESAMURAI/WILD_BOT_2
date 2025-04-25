# WHITESAMURAI Wildberries Analytics Bot

## Обзор проекта
Telegram-бот на базе aiogram 3.x для анализа данных маркетплейса Wildberries, предоставляющий аналитику товаров и мониторинг социальных сетей.

## Технологический стек
- **Python 3.9+**
- **Фреймворк:** aiogram 3.x
- **База данных:** SQLite
- **API:**
  - Wildberries API (данные о товарах)
  - Serper.dev API (глобальный поиск)
  - Telegram Bot API

## Структура проекта
```
WILD-BOT-NEW/
├── new_bot.py           # Основной файл бота
├── main.py              # Модуль анализа товаров
├── niche_analyzer.py    # Модуль анализа ниш
├── subscription_manager.py  # Управление подписками
├── requirements.txt     # Зависимости проекта
├── .env                 # Переменные окружения
└── bot.log             # Логи приложения
```

## Основные компоненты

### 1. Модуль анализа товаров (`main.py`)
- `ProductCardAnalyzer`: Обработка данных о товарах
- `TrendAnalyzer`: Обработка трендов продаж и метрик
- Ключевые методы:
  - `get_wb_product_info()`: Получение данных товара через API Wildberries
  - `format_product_analysis()`: Форматирование результатов анализа

### 2. Анализ ниш (`niche_analyzer.py`)
- `NicheAnalyzer`: Обработка данных рыночных ниш
- Анализ конкуренции на рынке
- Анализ ценового диапазона
- Оценка спроса

### 3. Система подписок (`subscription_manager.py`)
- Управление подписками пользователей
- Обработка платежей
- Отслеживание использования
- Схема базы данных:
  ```sql
  subscriptions (
    user_id INTEGER PRIMARY KEY,
    subscription_type TEXT,
    expiry_date TEXT,
    actions JSON
  )
  ```

### 4. Реализация глобального поиска
```python
async def global_search_serper_detailed(query: str):
    # Интеграция с API Serper.dev
    # Агрегация данных из соцсетей
    # Расчет метрик
```

## Интеграции с API

### Эндпоинты Wildberries API
```python
PRICE_URL = "https://card.wb.ru/cards/v1/detail"
SALES_URL = "https://product-order-qnt.wildberries.ru/by-nm/"
SELLER_STATS_URL = "https://catalog.wb.ru/sellers/v1/analytics-data"
```

### Управление состояниями
```python
class UserStates(StatesGroup):
    waiting_for_product = State()
    waiting_for_niche = State()
    waiting_for_tracking = State()
    waiting_for_payment_amount = State()
    waiting_for_payment_screenshot = State()
    waiting_for_search = State()
    viewing_search_results = State()
```

## Установка и настройка

### 1. Настройка окружения
```bash
# Клонирование репозитория
git clone https://github.com/CHEESESAMURAI/WILD-BOT-NEW.git
cd WILD-BOT-NEW

# Создание виртуального окружения
python -m venv venv

# Активация виртуального окружения
# Windows:
venv\Scripts\activate
# Unix/macOS:
source venv/bin/activate

# Установка зависимостей
pip install -r requirements.txt
```

### 2. Конфигурация
Создайте файл `.env`:
```env
BOT_TOKEN=your_telegram_bot_token
SERPER_API_KEY=your_serper_api_key
ADMIN_ID=your_telegram_id
```

### 3. Инициализация базы данных
База данных SQLite инициализируется автоматически при первом запуске.

## Руководство по разработке

### Обработка ошибок
```python
try:
    # API запрос или операция с базой данных
    pass
except Exception as e:
    logger.error(f"Описание ошибки: {str(e)}", exc_info=True)
    # Обработка ошибки
```

### Логирование
```python
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
```

### Добавление новых функций
1. Создайте новый модуль в корне проекта
2. Обновите `new_bot.py` новыми обработчиками
3. Добавьте новые состояния при необходимости
4. Обновите менеджер подписок, если функция требует подписки

## Тестирование
- Модульные тесты (TODO)
- Интеграционные тесты (TODO)
- Процедуры ручного тестирования API интеграций

## Развертывание
```bash
# Запуск бота
python new_bot.py

# Использование PM2 (рекомендуется для продакшена)
pm2 start new_bot.py --name wb-bot
```

## Мониторинг
- Проверка `bot.log` для операционных логов
- Мониторинг истечения подписок
- Отслеживание использования API и лимитов

## Участие в разработке
1. Форкните репозиторий
2. Создайте ветку для функционала
3. Внесите изменения
4. Добавьте тесты при необходимости
5. Отправьте pull request

## Лицензия
MIT License - подробности в файле LICENSE
# WILD-BOT-NEW
