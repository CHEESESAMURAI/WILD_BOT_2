# WHITESAMURAI BOT 🤖

Telegram-бот для анализа товаров и ниш на Wildberries с функцией поиска блогеров.

## ✨ Основные функции

- 📊 **Анализ товаров** - детальный анализ по артикулу
- 📈 **Анализ ниш** - исследование рынка по ключевым словам  
- 🏢 **Анализ брендов** - статистика и тренды брендов
- 🔍 **Анализ внешки** - поиск внешней рекламы товаров
- 🗓️ **Анализ сезонности** - данные о сезонных трендах
- 👥 **Поиск блогеров** - поиск инфлюенсеров для коллабораций
- 🤖 **AI помощник** - генерация контента с помощью ИИ
- 📱 **Отслеживание товаров** - мониторинг цен и остатков
- 💳 **Система подписок** - различные тарифные планы

## 🚀 Быстрый старт

### 1. Клонирование репозитория
```bash
git clone https://github.com/CHEESESAMURAI/WILD_BOT_2.git
cd WILD_BOT_2
```

### 2. Установка зависимостей
```bash
pip install -r requirements.txt
```

### 3. Настройка конфигурации
```bash
cp config_example.py config.py
```

Отредактируйте `config.py` и добавьте ваши API ключи:

```python
# Telegram Bot Token (получить у @BotFather)
BOT_TOKEN = "your_telegram_bot_token_here"
ADMIN_ID = 123456789  # Ваш Telegram ID

# API Keys
SERPER_API_KEY = "your_serper_api_key_here"        # https://serper.dev
OPENAI_API_KEY = "your_openai_api_key_here"        # https://openai.com
MPSTATS_API_KEY = "your_mpstats_api_key_here"      # https://mpstats.io
YOUTUBE_API_KEY = "your_youtube_api_key_here"      # Google Cloud Console
VK_SERVICE_KEY = "your_vk_service_key_here"        # VK API
```

### 4. Запуск бота
```bash
python new_bot.py
```

## 🔧 API ключи

Для полной функциональности необходимо получить следующие API ключи:

| Сервис | Назначение | Получить |
|--------|------------|----------|
| **Telegram Bot** | Основной функционал бота | [@BotFather](https://t.me/BotFather) |
| **Serper** | Поиск в Google для блогеров | [serper.dev](https://serper.dev) |
| **OpenAI** | AI генерация контента | [openai.com](https://openai.com) |
| **MPStats** | Аналитика Wildberries | [mpstats.io](https://mpstats.io) |
| **YouTube Data API** | Статистика YouTube | [Google Cloud Console](https://console.cloud.google.com) |
| **VK API** | Статистика ВКонтакте | [vk.com/dev](https://vk.com/dev) |

## 📱 Функция поиска блогеров

### Как работает:
1. 👥 Нажмите кнопку "Поиск блогеров" в боте
2. 💰 Оплатите операцию (30₽)
3. 🔍 Введите запрос: артикул, ключевое слово или категорию
4. ⏳ Ожидайте результаты (30-60 секунд)

### Что ищет:
- **YouTube** - обзоры и распаковки товаров
- **Instagram** - посты с продуктами Wildberries  
- **TikTok** - короткие видео с товарами
- **Telegram** - каналы с обзорами

### Что получаете:
- 📊 Список блогеров с контактами
- 👥 Оценка размера аудитории
- 💰 Примерный бюджет сотрудничества
- 🎯 Тематика контента
- ✅ Наличие контента о Wildberries

## 📁 Структура проекта

```
├── new_bot.py              # Основной файл бота
├── blogger_search.py       # Модуль поиска блогеров
├── ai_helper.py           # AI функции
├── config_example.py      # Пример конфигурации
├── subscription_manager.py # Система подписок
├── product_*.py           # Модули анализа товаров
├── brand_analysis.py      # Анализ брендов
├── niche_analysis_functions.py # Анализ ниш
└── requirements.txt       # Зависимости
```

## 🛠️ Разработка

### Добавление новых функций
1. Создайте новый модуль в корне проекта
2. Добавьте импорт в `new_bot.py`
3. Создайте обработчики команд
4. Добавьте кнопки в меню

### Система состояний
Бот использует FSM (Finite State Machine) для управления диалогами:
```python
class UserStates(StatesGroup):
    waiting_for_product = State()
    waiting_for_blogger_search = State()
    # ... другие состояния
```

## 📊 База данных

Бот использует SQLite базу данных `subscriptions.db` для хранения:
- Пользователей и их балансов
- Подписок и лимитов
- Отслеживаемых товаров
- Статистики использования

## 🔒 Безопасность

- ❌ **НЕ коммитьте** файл `config.py` с реальными ключами
- ✅ Используйте переменные окружения в продакшене
- 🔐 Регулярно обновляйте API ключи
- 👨‍💼 Ограничьте права администратора

## 📞 Поддержка

Если у вас возникли вопросы:
1. Проверьте логи в файле `bot.log`
2. Убедитесь что все API ключи корректны
3. Проверьте подключение к интернету
4. Создайте Issue в GitHub

## 📄 Лицензия

Проект распространяется под лицензией MIT.

---

**Создано с ❤️ для сообщества Wildberries селлеров**
