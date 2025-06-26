import asyncio
import aiohttp
import logging
from datetime import datetime, timedelta
import json
from mpstats_browser_utils import get_mpstats_headers, get_item_sales_browser, get_item_info_browser, format_date_for_mpstats

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Константы - используем тот же ключ API, что и в product_mpstat.py
MPSTAT_API_KEY = "68431d2ac72ea4.96910328a56006b24a55daf65db03835d5fe5b4d"

async def get_item_sales(sku, publish_date, days=3):
    """
    Получает данные о продажах и выручке по SKU за указанный период (браузерный подход).
    
    Args:
        sku (str): Идентификатор товара (SKU или nmId)
        publish_date (str): Дата публикации в формате YYYY-MM-DD
        days (int, optional): Количество дней для анализа (по умолчанию 3)
    
    Returns:
        dict: Данные о продажах за указанный период
    """
    try:
        logger.info(f"Getting item sales data for SKU {sku} from {publish_date} for {days} days")
        
        # Преобразуем дату публикации в объект datetime
        d1 = datetime.strptime(publish_date, "%Y-%m-%d")
        d2 = d1 + timedelta(days=days)
        
        # Форматируем даты для API-запроса
        date_from = format_date_for_mpstats(d1)
        date_to = format_date_for_mpstats(d2)
        
        logger.info(f"Requesting sales data from {date_from} to {date_to}")
        
        # Используем браузерный подход для получения данных о продажах
        sales_data = await get_item_sales_browser(sku, date_from, date_to)
        
        if sales_data:
            logger.info(f"MPSTATS Item Sales API response received successfully")
            
            # Адаптируем данные к ожидаемому формату
            result = {
                "sku": sku,
                "title": f"Product {sku}",
                "publishDate": publish_date,
                "units_sold_total": 0,
                "revenue_total": 0,
                "orders_total": 0,
                "avg_price": 0,
                "orders_growth_pct": 0,
                "revenue_growth_pct": 0,
                "orders_growth_abs": 0,
                "revenue_growth_abs": 0,
                "account": "",
                "daily_data": sales_data if isinstance(sales_data, list) else []
            }
            
            # Обрабатываем данные продаж
            if isinstance(sales_data, list) and len(sales_data) > 0:
                # Фильтруем данные за указанный период
                period_data = []
                for sale in sales_data:
                    if isinstance(sale, dict):
                        sale_date = sale.get("date", "")
                        if sale_date:
                            try:
                                sale_datetime = datetime.strptime(sale_date, "%Y-%m-%d")
                                if d1 <= sale_datetime < d2:
                                    period_data.append(sale)
                            except ValueError:
                                continue
                
                if period_data:
                    # Суммируем показатели за период
                    result["units_sold_total"] = sum(sale.get("sales", 0) for sale in period_data)
                    result["revenue_total"] = sum(sale.get("revenue", 0) for sale in period_data)
                    result["orders_total"] = sum(sale.get("orders", 0) for sale in period_data)
                    
                    # Рассчитываем среднюю цену
                    if result["units_sold_total"] > 0:
                        result["avg_price"] = round(result["revenue_total"] / result["units_sold_total"])
                    
                    # Рассчитываем прирост по сравнению с предыдущим периодом
                    prev_start = d1 - timedelta(days=days)
                    prev_end = d1
                    
                    prev_period_data = []
                    for sale in sales_data:
                        if isinstance(sale, dict):
                            sale_date = sale.get("date", "")
                            if sale_date:
                                try:
                                    sale_datetime = datetime.strptime(sale_date, "%Y-%m-%d")
                                    if prev_start <= sale_datetime < prev_end:
                                        prev_period_data.append(sale)
                                except ValueError:
                                    continue
                    
                    if prev_period_data:
                        prev_orders = sum(sale.get("orders", 0) for sale in prev_period_data)
                        prev_revenue = sum(sale.get("revenue", 0) for sale in prev_period_data)
                        
                        # Абсолютный прирост
                        result["orders_growth_abs"] = result["orders_total"] - prev_orders
                        result["revenue_growth_abs"] = result["revenue_total"] - prev_revenue
                        
                        # Процентный прирост
                        if prev_orders > 0:
                            result["orders_growth_pct"] = round((result["orders_growth_abs"] / prev_orders) * 100)
                        if prev_revenue > 0:
                            result["revenue_growth_pct"] = round((result["revenue_growth_abs"] / prev_revenue) * 100)
            
            # Пробуем получить дополнительную информацию о товаре
            try:
                item_info = await get_item_info_browser(sku)
                if item_info:
                    # Извлекаем название товара если есть
                    if isinstance(item_info, list) and len(item_info) > 0:
                        for item in item_info:
                            if isinstance(item, dict) and str(item.get("id")) == str(sku):
                                result["title"] = item.get("name", result["title"])
                                break
                    elif isinstance(item_info, dict):
                        result["title"] = item_info.get("name", result["title"])
            except Exception as e:
                logger.warning(f"Could not get item info for {sku}: {e}")
            
            return {
                "success": True,
                "data": result
            }
        else:
            logger.error(f"No sales data received for SKU {sku}")
            return {
                "success": False,
                "error": "No sales data available",
                "details": f"SKU: {sku}, Period: {date_from} to {date_to}"
            }
            
    except Exception as e:
        logger.error(f"Error getting item sales for SKU {sku}: {str(e)}", exc_info=True)
        return {
            "success": False,
            "error": f"Ошибка при получении данных: {str(e)}",
            "details": f"SKU: {sku}, Date: {publish_date}, Days: {days}"
        }

def parse_item_sales_data(response_data):
    """
    Парсит и форматирует данные о продажах, полученные из API.
    
    Args:
        response_data (dict): Ответ от API MPSTATS
    
    Returns:
        dict: Структурированные данные о продажах
    """
    if not response_data.get("success", False):
        return response_data
    
    try:
        data = response_data.get("data", {})
        
        # Основные данные по продажам за период
        result = {
            "sku": data.get("sku", ""),
            "title": data.get("title", ""),
            "publish_date": data.get("publishDate", ""),
            "period_data": {
                "units_sold_total": data.get("units_sold_total", 0),
                "revenue_total": data.get("revenue_total", 0),
                "orders_total": data.get("orders_total", 0),
                "avg_price": data.get("avg_price", 0),
                "orders_growth_pct": data.get("orders_growth_pct", 0),
                "revenue_growth_pct": data.get("revenue_growth_pct", 0),
                "orders_growth_abs": data.get("orders_growth_abs", 0),
                "revenue_growth_abs": data.get("revenue_growth_abs", 0)
            },
            "account_info": {
                "account": data.get("account", "")
            },
            "daily_data": data.get("daily_data", [])
        }
        
        return {
            "success": True,
            "result": result
        }
    except Exception as e:
        logger.error(f"Error parsing item sales data: {str(e)}")
        return {
            "success": False,
            "error": f"Parsing error: {str(e)}"
        }

async def main():
    """
    Пример использования функции для получения данных о продажах.
    """
    # Тестовые параметры
    sku = "123456789"  # Замените на реальный SKU товара
    publish_date = "2023-01-01"  # Замените на реальную дату публикации
    
    # Получаем данные о продажах
    sales_data = await get_item_sales(sku, publish_date)
    
    # Парсим полученные данные
    parsed_data = parse_item_sales_data(sales_data)
    
    # Выводим результат
    print(json.dumps(parsed_data, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    asyncio.run(main()) 