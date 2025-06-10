# MPSTATS Item Sales API Integration

## Обзор

Эта интеграция позволяет получать данные о продажах и выручке по SKU товара на Wildberries за указанный период после публикации. Реализация основана на существующих API-эндпоинтах MPSTATS и дополняет существующую функциональность проекта.

## API Endpoints

Реализация использует следующие API-эндпоинты MPSTATS:

1. Основной эндпоинт для получения данных о продажах:
   ```
   GET https://mpstats.io/api/wb/get/item/{sku}/sales?d1={date_from}&d2={date_to}
   ```

2. Альтернативный эндпоинт (используется в случае ошибки основного):
   ```
   GET https://mpstats.io/api/wb/get/items/by/id?id={sku}
   ```

## Файлы реализации

1. `mpstats_item_sales.py` - основной модуль с функциями для работы с API
2. `test_item_sales.py` - тестовый скрипт, демонстрирующий использование модуля
3. Обновленный `product_mpstat.py` - интеграция с существующей функциональностью

## Основные функции

### `get_item_sales(sku, publish_date, days=3)`

Получает данные о продажах и выручке по SKU за указанный период (по умолчанию 3 дня).

**Параметры:**
- `sku` (str): Идентификатор товара (SKU или nmId)
- `publish_date` (str): Дата публикации в формате YYYY-MM-DD
- `days` (int, optional): Количество дней для анализа (по умолчанию 3)

**Возвращаемое значение:**
```json
{
  "success": true,
  "data": {
    "sku": "123456789",
    "title": "Название товара",
    "publishDate": "2023-05-01",
    "units_sold_total": 100,
    "revenue_total": 50000,
    "orders_total": 90,
    "avg_price": 500,
    "orders_growth_pct": 20,
    "revenue_growth_pct": 25,
    "orders_growth_abs": 15,
    "revenue_growth_abs": 10000,
    "account": "seller_account",
    "daily_data": [...]
  }
}
```

### `parse_item_sales_data(response_data)`

Парсит и форматирует данные о продажах, полученные из API.

**Параметры:**
- `response_data` (dict): Ответ от API MPSTATS

**Возвращаемое значение:**
```json
{
  "success": true,
  "result": {
    "sku": "123456789",
    "title": "Название товара",
    "publish_date": "2023-05-01",
    "period_data": {
      "units_sold_total": 100,
      "revenue_total": 50000,
      "orders_total": 90,
      "avg_price": 500,
      "orders_growth_pct": 20,
      "revenue_growth_pct": 25,
      "orders_growth_abs": 15,
      "revenue_growth_abs": 10000
    },
    "account_info": {
      "account": "seller_account"
    },
    "daily_data": [...]
  }
}
```

### `get_product_item_sales(article, publish_date, days=3)` (в product_mpstat.py)

Интегрированная функция для получения данных о продажах по SKU за период после публикации.

**Параметры:**
- `article` (str): Артикул товара Wildberries
- `publish_date` (str): Дата публикации в формате YYYY-MM-DD
- `days` (int, optional): Количество дней после публикации для анализа

## Пример использования

```python
import asyncio
from mpstats_item_sales import get_item_sales, parse_item_sales_data

async def main():
    # Получаем данные о продажах товара с артикулом 123456789 за 3 дня после публикации 01.05.2023
    sales_data = await get_item_sales("123456789", "2023-05-01", 3)
    
    # Парсим полученные данные
    parsed_data = parse_item_sales_data(sales_data)
    
    if parsed_data.get("success", False):
        result = parsed_data.get("result", {})
        period_data = result.get("period_data", {})
        
        # Выводим основные показатели
        print(f"Продано единиц: {period_data.get('units_sold_total', 0)} шт.")
        print(f"Выручка: {period_data.get('revenue_total', 0)} ₽")
        print(f"Прирост заказов: {period_data.get('orders_growth_pct', 0)}%")

if __name__ == "__main__":
    asyncio.run(main())
```

## Альтернативные подходы и ограничения

1. API-эндпоинт `https://mpstats.io/api/wb/get/item_sales` упомянутый в документации MPSTATS, не удалось использовать напрямую из-за требования дополнительных параметров, не указанных в документации.

2. Вместо этого реализация использует существующий API-эндпоинт `/api/wb/get/item/{sku}/sales`, который уже используется в проекте, и адаптирует его данные к требуемому формату.

3. В случае отсутствия данных или ошибки основного API, реализация автоматически пробует альтернативный эндпоинт, чтобы предоставить хотя бы приблизительные данные о продажах товара.

## Обработка ошибок

Реализация включает обработку следующих типов ошибок:
- Ошибки HTTP-запросов к API MPSTATS
- Ошибки парсинга данных
- Отсутствие данных о продажах

В случае ошибки возвращается структура с информацией об ошибке:
```json
{
  "success": false,
  "error": "Описание ошибки",
  "details": "Подробная информация об ошибке (если доступна)"
}
``` 