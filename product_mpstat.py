import asyncio
import aiohttp
import logging
import json
from datetime import datetime, timedelta
from mpstats_item_sales import get_item_sales as fetch_item_sales, parse_item_sales_data
from mpstats_browser_utils import (
    get_mpstats_headers, 
    get_item_sales_browser, 
    get_item_info_browser,
    format_date_for_mpstats,
    get_date_range_30_days
)

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Константы
MPSTAT_API_KEY = "68431d2ac72ea4.96910328a56006b24a55daf65db03835d5fe5b4d"

async def get_product_mpstat_info(article):
    """Получает информацию о товаре через API MPSTAT с браузерным подходом."""
    try:
        logger.info(f"Getting product info for article {article} via MPSTAT API (browser approach)")
        
        # Используем браузерный подход для получения дат
        date_from, date_to = get_date_range_30_days()
        
        logger.info(f"Date range: {date_from} to {date_to}")
        
        results = {}
        
        # 1. Получаем данные о продажах через браузерный метод
        try:
            sales_data = await get_item_sales_browser(article, date_from, date_to)
            if sales_data:
                logger.info(f"✅ Sales data received via browser approach")
                results["sales_data"] = sales_data
            else:
                logger.warning(f"⚠️ No sales data received for article {article}")
        except Exception as e:
            logger.error(f"❌ Error getting sales data: {e}")
        
        # 2. Получаем информацию о товаре через браузерный метод
        try:
            item_info = await get_item_info_browser(article)
            if item_info:
                logger.info(f"✅ Item info received via browser approach")
                results["item_info"] = item_info
            else:
                logger.warning(f"⚠️ No item info received for article {article}")
        except Exception as e:
            logger.error(f"❌ Error getting item info: {e}")
        
        # 3. Если браузерные методы не дали результатов, пробуем legacy подход
        if not results.get("sales_data") and not results.get("item_info"):
            logger.info("Trying legacy approach as fallback...")
            
            headers = get_mpstats_headers()
            
            async with aiohttp.ClientSession() as session:
                # Пробуем старые endpoints как fallback
                legacy_urls = [
                    f"https://mpstats.io/api/wb/get/item/{article}/sales",
                    f"https://mpstats.io/api/wb/get/item/{article}",
                    f"https://mpstats.io/api/wb/get/items/by/id"
                ]
                
                for url in legacy_urls:
                    try:
                        params = {"d1": date_from, "d2": date_to} if "sales" in url else {"id": article} if "by/id" in url else {}
                        
                        async with session.get(url, headers=headers, params=params) as response:
                            if response.status == 200:
                                data = await response.json()
                                if data:
                                    key = "legacy_sales" if "sales" in url else "legacy_item" if "by/id" in url else "legacy_card"
                                    results[key] = data
                                    logger.info(f"✅ Got legacy data from {url}")
                            else:
                                logger.warning(f"⚠️ Legacy endpoint failed: {url} - {response.status}")
                    except Exception as e:
                        logger.warning(f"⚠️ Legacy endpoint error: {url} - {e}")
        
        # Обрабатываем полученные данные
        return process_mpstat_data(results, article)
        
    except Exception as e:
        logger.error(f"❌ Error in get_product_mpstat_info: {str(e)}", exc_info=True)
        return {
            "error": f"Ошибка получения данных: {str(e)}",
            "article": article,
            "name": f"Товар {article}",
            "daily_sales": 0,
            "weekly_sales": 0,
            "monthly_sales": 0,
            "daily_revenue": 0,
            "weekly_revenue": 0,
            "monthly_revenue": 0,
            "daily_profit": 0,
            "weekly_profit": 0,
            "monthly_profit": 0
        }

def process_mpstat_data(results, article):
    """Обрабатывает данные полученные от MPSTATS API"""
    try:
        # Инициализируем базовые значения
        daily_sales = 0
        total_sales = 0
        daily_revenue = 0
        total_revenue = 0
        daily_profit = 0
        
        name = f"Товар {article}"
        brand = ""
        price_current = 0
        rating = 0
        
        # Обрабатываем данные о продажах (приоритет: браузерные данные)
        sales_data = results.get("sales_data", results.get("legacy_sales", []))
        
        if isinstance(sales_data, list) and len(sales_data) > 0:
            logger.info(f"Processing {len(sales_data)} sales records")
            
            # Анализируем данные за последние 30 дней
            recent_data = sales_data[-30:] if len(sales_data) >= 30 else sales_data
            
            for day_data in recent_data:
                if isinstance(day_data, dict):
                    sales = day_data.get("sales", 0)
                    revenue = day_data.get("revenue", 0)
                    
                    total_sales += sales
                    total_revenue += revenue
            
            # Рассчитываем средние показатели
            days_count = len(recent_data)
            if days_count > 0:
                daily_sales = round(total_sales / days_count)
                daily_revenue = round(total_revenue / days_count)
                daily_profit = round(daily_revenue * 0.85)  # Прибыль = выручка - 15% комиссия
        
        # Обрабатываем информацию о товаре (приоритет: браузерные данные)
        item_data = results.get("item_info", results.get("legacy_item", results.get("legacy_card")))
        
        if isinstance(item_data, list) and len(item_data) > 0:
            # Ищем нужный товар в списке
            for item in item_data:
                if isinstance(item, dict) and str(item.get("id")) == str(article):
                    name = item.get("name", name)
                    brand = item.get("brand", brand)
                    price_current = item.get("price", price_current)
                    rating = item.get("rating", rating)
                    
                    # Если есть данные о продажах в день
                    if item.get("salesPerDay"):
                        daily_sales = max(daily_sales, item.get("salesPerDay", 0))
                        daily_revenue = max(daily_revenue, item.get("revenuePerDay", 0))
                        daily_profit = round(daily_revenue * 0.85)
                    
                    break
        elif isinstance(item_data, dict):
            # Прямые данные о товаре
            if "item" in item_data:
                item_info = item_data["item"]
            else:
                item_info = item_data
            
            name = item_info.get("name", name)
            brand = item_info.get("brand", brand)
            price_current = item_info.get("price", price_current)
            rating = item_info.get("rating", rating)
        
        # Рассчитываем производные показатели
        weekly_sales = daily_sales * 7
        monthly_sales = daily_sales * 30
        weekly_revenue = daily_revenue * 7
        monthly_revenue = daily_revenue * 30
        weekly_profit = daily_profit * 7
        monthly_profit = daily_profit * 30
        
        result = {
            "article": article,
            "name": name,
            "brand": brand,
            "price_current": price_current,
            "rating": rating,
            "daily_sales": daily_sales,
            "weekly_sales": weekly_sales,
            "monthly_sales": monthly_sales,
            "daily_revenue": daily_revenue,
            "weekly_revenue": weekly_revenue,
            "monthly_revenue": monthly_revenue,
            "daily_profit": daily_profit,
            "weekly_profit": weekly_profit,
            "monthly_profit": monthly_profit,
            "data_sources": list(results.keys())  # Для отладки
        }
        
        logger.info(f"✅ Processed data for {article}: daily_sales={daily_sales}, daily_revenue={daily_revenue}")
        return result
        
    except Exception as e:
        logger.error(f"❌ Error processing MPSTAT data: {e}")
        return {
            "error": f"Ошибка обработки данных: {str(e)}",
            "article": article,
            "name": f"Товар {article}",
            "daily_sales": 0,
            "weekly_sales": 0,
            "monthly_sales": 0,
            "daily_revenue": 0,
            "weekly_revenue": 0,
            "monthly_revenue": 0,
            "daily_profit": 0,
            "weekly_profit": 0,
            "monthly_profit": 0
        }

async def get_product_item_sales(article, publish_date, days=3):
    """
    Получает данные о продажах по SKU за период после публикации.
    
    Args:
        article (str): Артикул товара Wildberries
        publish_date (str): Дата публикации в формате YYYY-MM-DD
        days (int, optional): Количество дней после публикации для анализа
    
    Returns:
        dict: Данные о продажах за указанный период
    """
    try:
        logger.info(f"Getting item sales data for article {article} from {publish_date} for {days} days")
        
        # Вызываем функцию из mpstats_item_sales.py
        sales_data = await fetch_item_sales(article, publish_date, days)
        
        # Парсим полученные данные
        parsed_data = parse_item_sales_data(sales_data)
        
        return parsed_data
    except Exception as e:
        logger.error(f"Error getting item sales data: {str(e)}")
        return {
            "success": False,
            "error": f"Error getting item sales data: {str(e)}"
        }

# Тестирование функции
async def main():
    """Тестовая функция для проверки API."""
    article = "360832704"  # Тестовый артикул
    
    # Получаем общую информацию о товаре
    result = await get_product_mpstat_info(article)
    print("Результат API MPSTAT (общая информация):")
    print(json.dumps(result, indent=2))
    
    # Тестируем новую функцию для получения данных о продажах
    publish_date = "2023-05-01"  # Пример даты публикации
    sales_result = await get_product_item_sales(article, publish_date)
    print("\n\nРезультат API MPSTAT (данные о продажах после публикации):")
    print(json.dumps(sales_result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())