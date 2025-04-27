# Инструкция по установке и запуску бота

## Предварительные требования

1. Установленный Docker на вашей системе
   - Для Windows/Mac: установите [Docker Desktop](https://www.docker.com/products/docker-desktop)
   - Для Linux: установите [Docker Engine](https://docs.docker.com/engine/install/)

## Настройка проекта

1. Создайте файл `.env` в корневой директории проекта со следующими переменными:
```
BOT_TOKEN=your_telegram_bot_token
SERPER_API_KEY=your_serper_api_key
ADMIN_ID=your_telegram_id
REDIS_HOST=redis
REDIS_PORT=6379
```

2. Замените значения на ваши:
   - `BOT_TOKEN` - токен вашего Telegram бота (получить у @BotFather)
   - `SERPER_API_KEY` - ваш API ключ от serper.dev
   - `ADMIN_ID` - ваш Telegram ID
   - `REDIS_HOST` и `REDIS_PORT` оставьте без изменений

## Запуск бота

1. Создайте необходимые директории:
```bash
mkdir -p logs data
```

2. Запустите все сервисы командой:
```bash
docker compose up -d --build
```

3. Проверьте статус сервисов:
```bash
docker compose ps
```

4. Проверьте логи бота:
```bash
# Все логи
docker compose logs -f

# Только логи бота
docker compose logs -f bot

# Только логи Redis
docker compose logs -f redis
```

5. Для остановки всех сервисов:
```bash
docker compose down
```

6. Для полной очистки (включая данные):
```bash
docker compose down -v
```

## Структура проекта

- `new_bot.py` - основной файл бота
- `requirements.txt` - зависимости проекта
- `.env` - конфигурация (создается пользователем)
- `docker-compose.yml` - конфигурация Docker
- `Dockerfile` - инструкции для сборки контейнера
- `data/` - директория для хранения данных
- `logs/` - директория для логов

## Сервисы

1. **Bot** (`wb_analytics_bot`)
   - Основной сервис бота
   - Хранит логи в ./logs
   - Хранит данные в ./data
   - Автоматически перезапускается при сбоях

2. **Redis** (`wb_redis`)
   - Кэширование данных
   - Персистентное хранение в volume
   - Доступен на порту 6379

## Управление данными

- Все данные сохраняются в директории `./data`
- Redis данные хранятся в Docker volume `redis_data`
- Логи доступны в директории `./logs`

## Возможные проблемы

1. Если бот не запускается, проверьте:
   - Правильность данных в файле `.env`
   - Статус сервисов: `docker compose ps`
   - Логи сервисов: `docker compose logs`
   - Наличие всех необходимых прав у Docker

2. Если нужно перезапустить конкретный сервис:
```bash
docker compose restart bot    # перезапуск бота
docker compose restart redis  # перезапуск redis
```

3. Если нужно обновить образы:
```bash
docker compose pull  # обновить базовые образы
docker compose up -d --build  # пересобрать и запустить
```

## Поддержка

При возникновении проблем:
1. Проверьте логи: `docker compose logs -f`
2. Убедитесь, что все переменные окружения установлены правильно
3. Проверьте подключение к интернету
4. Проверьте статус сервисов: `docker compose ps`

## Проверка работы

1. Откройте вашего бота в Telegram
2. Отправьте команду `/start`
3. Следуйте инструкциям бота

## Возможные проблемы

1. Если бот не запускается, проверьте:
   - Правильность данных в файле `.env`
   - Наличие всех необходимых прав у Docker
   - Логи бота на наличие ошибок

2. Если нужно перезапустить бота:
```bash
docker compose restart
```

## Структура проекта

- `new_bot.py` - основной файл бота
- `requirements.txt` - зависимости проекта
- `.env` - конфигурация (создается пользователем)
- `docker-compose.yml` - конфигурация Docker
- `Dockerfile` - инструкции для сборки контейнера

## Поддержка

При возникновении проблем:
1. Проверьте логи: `docker compose logs -f`
2. Убедитесь, что все переменные окружения установлены правильно
3. Проверьте подключение к интернету 