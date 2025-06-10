import asyncio
import json
from mpstats_item_sales import get_item_sales, parse_item_sales_data

async def test_item_sales():
    # Тестовый SKU (замените на реальный артикул Wildberries)
    sku = "360832704"  # Используем тот же артикул, что и в test_mpstat.py
    
    # Дата публикации (YYYY-MM-DD)
    publish_date = "2023-05-01"  # Замените на реальную дату
    
    # Период анализа (дней)
    days = 3
    
    print(f"Получение данных о продажах для SKU {sku} с {publish_date} за {days} дней...")
    
    # Вызываем API для получения данных о продажах
    sales_data = await get_item_sales(sku, publish_date, days)
    
    if not sales_data.get("success", False):
        print("Ошибка при получении данных:")
        print(json.dumps(sales_data, indent=2, ensure_ascii=False))
        return
    
    # Выводим сырой ответ API
    print("\n--- Сырой ответ API ---")
    print(json.dumps(sales_data.get("data", {}), indent=2, ensure_ascii=False))
    
    # Парсим и форматируем данные
    parsed_data = parse_item_sales_data(sales_data)
    
    if not parsed_data.get("success", False):
        print("Ошибка при парсинге данных:")
        print(json.dumps(parsed_data, indent=2, ensure_ascii=False))
        return
    
    # Выводим обработанные данные
    print("\n--- Обработанные данные ---")
    print(json.dumps(parsed_data.get("result", {}), indent=2, ensure_ascii=False))
    
    # Формируем человекочитаемый отчет
    result = parsed_data.get("result", {})
    period_data = result.get("period_data", {})
    
    print("\n=== Отчет о продажах ===")
    print(f"SKU/Артикул: {result.get('sku', 'Н/Д')}")
    print(f"Название: {result.get('title', 'Н/Д')}")
    print(f"Дата публикации: {result.get('publish_date', 'Н/Д')}")
    print(f"Аккаунт: {result.get('account_info', {}).get('account', 'Н/Д')}")
    print("\nПродажи за период:")
    print(f"• Продано единиц: {period_data.get('units_sold_total', 0)} шт.")
    print(f"• Заказов: {period_data.get('orders_total', 0)} шт.")
    print(f"• Выручка: {period_data.get('revenue_total', 0):,} ₽".replace(',', ' '))
    print(f"• Средняя цена: {period_data.get('avg_price', 0):,} ₽".replace(',', ' '))
    
    # Информация о росте
    print("\nПрирост по сравнению с предыдущим периодом:")
    print(f"• Прирост заказов: {period_data.get('orders_growth_pct', 0)}% (+{period_data.get('orders_growth_abs', 0)} шт.)")
    print(f"• Прирост выручки: {period_data.get('revenue_growth_pct', 0)}% (+{period_data.get('revenue_growth_abs', 0):,} ₽)".replace(',', ' '))

if __name__ == "__main__":
    asyncio.run(test_item_sales()) 