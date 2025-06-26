#!/usr/bin/env python3
"""
Тестирование всех функций MPSTATS с браузерным подходом
"""
import asyncio
from mpstats_browser_utils import (
    get_category_data_browser,
    get_item_sales_browser,
    get_item_info_browser,
    get_seasonality_annual_browser,
    get_seasonality_weekly_browser,
    search_products_browser,
    get_date_range_30_days,
    get_date_range_month
)

async def test_all_mpstats_functions():
    """Тестируем все функции MPSTATS с браузерным подходом"""
    
    print("🌐 Тестирование всех функций MPSTATS с браузерным подходом...")
    print("=" * 70)
    
    # Получаем диапазон дат
    start_date, end_date = get_date_range_30_days()
    print(f"📅 Диапазон дат: {start_date} - {end_date}")
    print()
    
    # Тест 1: Данные по категории
    print("🧪 Тест 1: Получение данных по категории")
    try:
        category_data = await get_category_data_browser("Электроника", start_date, end_date)
        if category_data and category_data.get('data'):
            print(f"✅ Успех! Товаров в категории: {len(category_data['data'])}")
            print(f"Пример товара: {category_data['data'][0].get('name', 'N/A')[:50]}...")
        else:
            print("❌ Данные по категории не получены")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("-" * 70)
    
    # Тест 2: Данные продаж товара
    print("\n🧪 Тест 2: Данные продаж товара")
    test_article = "13738266"  # Пример артикула из предыдущих тестов
    try:
        sales_data = await get_item_sales_browser(test_article, start_date, end_date)
        if sales_data:
            print(f"✅ Успех! Получены данные продаж для артикула {test_article}")
            print(f"Структура данных: {list(sales_data.keys()) if isinstance(sales_data, dict) else type(sales_data)}")
        else:
            print(f"❌ Данные продаж для артикула {test_article} не получены")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("-" * 70)
    
    # Тест 3: Информация о товаре
    print("\n🧪 Тест 3: Информация о товаре")
    try:
        item_info = await get_item_info_browser(test_article)
        if item_info:
            print(f"✅ Успех! Получена информация о товаре {test_article}")
            print(f"Структура данных: {list(item_info.keys()) if isinstance(item_info, dict) else type(item_info)}")
        else:
            print(f"❌ Информация о товаре {test_article} не получена")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("-" * 70)
    
    # Тест 4: Сезонность (годовая)
    print("\n🧪 Тест 4: Годовая сезонность")
    try:
        annual_data = await get_seasonality_annual_browser("Электроника")
        if annual_data:
            print("✅ Успех! Получены данные годовой сезонности")
            print(f"Тип данных: {type(annual_data)}")
            if isinstance(annual_data, list):
                print(f"Элементов: {len(annual_data)}")
            elif isinstance(annual_data, dict):
                print(f"Ключи: {list(annual_data.keys())}")
        else:
            print("❌ Данные годовой сезонности не получены")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("-" * 70)
    
    # Тест 5: Сезонность (недельная)
    print("\n🧪 Тест 5: Недельная сезонность")
    try:
        weekly_data = await get_seasonality_weekly_browser("Электроника")
        if weekly_data:
            print("✅ Успех! Получены данные недельной сезонности")
            print(f"Тип данных: {type(weekly_data)}")
            if isinstance(weekly_data, list):
                print(f"Элементов: {len(weekly_data)}")
            elif isinstance(weekly_data, dict):
                print(f"Ключи: {list(weekly_data.keys())}")
        else:
            print("❌ Данные недельной сезонности не получены")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("-" * 70)
    
    # Тест 6: Поиск товаров (экспериментальный)
    print("\n🧪 Тест 6: Поиск товаров по ключевому слову")
    try:
        search_data = await search_products_browser("телефон", start_date, end_date)
        if search_data:
            print("✅ Успех! Найдены товары по поиску")
            print(f"Структура данных: {list(search_data.keys()) if isinstance(search_data, dict) else type(search_data)}")
        else:
            print("❌ Поиск товаров не дал результатов")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    
    print("\n" + "=" * 70)
    
    # Тест даты
    print("\n📅 Тест функций дат:")
    print(f"Последние 30 дней: {get_date_range_30_days()}")
    print(f"Январь 2024: {get_date_range_month(2024, 1)}")
    
    print("\n✅ Все тесты завершены!")

if __name__ == "__main__":
    asyncio.run(test_all_mpstats_functions()) 