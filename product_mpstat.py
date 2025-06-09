import asyncio
import aiohttp
import logging
import json
from datetime import datetime, timedelta

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Константы
MPSTAT_API_KEY = "68431d2ac72ea4.96910328a56006b24a55daf65db03835d5fe5b4d"

async def get_product_mpstat_info(article):
    """Получает информацию о товаре через API MPSTAT."""
    try:
        logger.info(f"Getting product info for article {article} via MPSTAT API")
        
        today = datetime.now()
        month_ago = today - timedelta(days=30)
        date_from = month_ago.strftime("%d.%m.%Y")
        date_to = today.strftime("%d.%m.%Y")
        date_from_iso = month_ago.strftime("%Y-%m-%d")
        date_to_iso = today.strftime("%Y-%m-%d")
        
        headers = {
            "X-Mpstats-TOKEN": MPSTAT_API_KEY,
            "Content-Type": "application/json"
        }
        
        results = {}
        
        async with aiohttp.ClientSession() as session:
            # 1. Получаем данные о продажах
            sales_url = f"https://mpstats.io/api/wb/get/item/{article}/sales?d1={date_from}&d2={date_to}"
            async with session.get(sales_url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"MPSTAT Sales API response data received")
                    results["sales_data"] = data
                else:
                    logger.error(f"MPSTAT Sales API error: {await response.text()}")
            
            # 2. Получаем данные о карточке товара
            card_url = f"https://mpstats.io/api/wb/get/item/{article}"
            async with session.get(card_url, headers=headers) as card_response:
                if card_response.status == 200:
                    card_data = await card_response.json()
                    logger.info(f"MPSTAT Card API response data received")
                    results["card_data"] = card_data
                else:
                    logger.error(f"MPSTAT Card API error: {await card_response.text()}")

            # 3. Получаем расширенную аналитику товара через другой эндпоинт
            # Пробуем альтернативный подход - используем /api/wb/get/similar для получения подробностей
            try:
                # Используем другой API эндпоинт, который не требует path
                analytics_url = f"https://mpstats.io/api/wb/get/items/by/id?id={article}"
                async with session.get(analytics_url, headers=headers) as analytics_response:
                    if analytics_response.status == 200:
                        analytics_data = await analytics_response.json()
                        logger.info(f"MPSTAT Item API response data received")
                        results["analytics_data"] = analytics_data
                    else:
                        logger.error(f"MPSTAT Item API error: {await analytics_response.text()}")
            except Exception as e:
                logger.error(f"Error getting analytics data: {str(e)}")
        
        # Обрабатываем данные о продажах из первого запроса
        sales_data = []
        if "sales_data" in results:
            data = results["sales_data"]
            
            if isinstance(data, dict):
                sales_data = data.get("sales", [])
            elif isinstance(data, list):
                sales_data = data  # Данные уже в виде списка
        
        # Обрабатываем расширенную аналитику
        extended_analytics = {}
        if "analytics_data" in results:
            analytics_data = results["analytics_data"]
            
            # Проверяем формат данных от /api/wb/get/items/by/id
            if isinstance(analytics_data, list) and len(analytics_data) > 0:
                # Ищем информацию о нашем товаре
                target_item = None
                for item in analytics_data:
                    if str(item.get("id")) == str(article):
                        target_item = item
                        break
                
                if target_item:
                    logger.info(f"Found target item in analytics data")
                    
                    # Извлекаем полезные данные
                    extended_analytics = {
                        "sales": target_item.get("salesPerDay", 0) * 30,  # Примерные продажи за месяц
                        "revenue": target_item.get("revenuePerDay", 0) * 30,  # Примерная выручка за месяц
                        "balance": target_item.get("balance", 0),
                        "comments": target_item.get("commentsCount", 0),
                        "rating": target_item.get("rating", 0),
                        "purchase_rate": target_item.get("buyoutsPercent", 0) / 100 if target_item.get("buyoutsPercent") else 0,
                        "final_price_average": target_item.get("price", 0)
                    }
                    
                    # Рассчитываем дополнительные метрики
                    extended_analytics["sales_per_day_average"] = target_item.get("salesPerDay", 0)
                    extended_analytics["revenue_average"] = target_item.get("revenuePerDay", 0)
                    
                    logger.info(f"Extended analytics data processed: sales={extended_analytics.get('sales')}, revenue={extended_analytics.get('revenue')}")
        
        # Подсчитываем среднедневные продажи за последний месяц
        daily_sales = 0
        total_sales = 0
        daily_revenue = 0
        total_revenue = 0
        daily_profit = 0
        total_profit = 0
        weekly_sales = 0
        weekly_revenue = 0
        weekly_profit = 0
        monthly_sales = 0
        monthly_revenue = 0
        monthly_profit = 0
        
        # Используем данные из расширенной аналитики, если они доступны
        if extended_analytics and extended_analytics.get("sales_per_day_average", 0) > 0:
            daily_sales = extended_analytics.get("sales_per_day_average", 0)
            total_sales = extended_analytics.get("sales", 0)
            
            daily_revenue = extended_analytics.get("revenue_average", 0)
            total_revenue = extended_analytics.get("revenue", 0)
            
            # Прибыль = выручка * 0.85 (примерно)
            daily_profit = round(daily_revenue * 0.85)
            
            # Недельные и месячные показатели
            weekly_sales = daily_sales * 7
            weekly_revenue = daily_revenue * 7
            weekly_profit = daily_profit * 7
            
            monthly_sales = daily_sales * 30
            monthly_revenue = daily_revenue * 30
            monthly_profit = daily_profit * 30
        else:
            # Если расширенная аналитика недоступна, используем данные из sales_data
            if sales_data:
                # Анализируем данные за последний месяц
                last_30_days = sales_data[-30:] if len(sales_data) >= 30 else sales_data
                
                # Собираем данные за день, неделю и месяц
                for day_data in last_30_days:
                    # Проверяем формат элемента списка
                    if isinstance(day_data, dict):
                        sales = day_data.get("sales", 0)
                        revenue = day_data.get("revenue", 0)
                        # Если нет данных о выручке, но есть о продажах и цене
                        if revenue == 0 and sales > 0 and "card_data" in results:
                            card_info = results.get("card_data", {}).get("item", {})
                            if card_info and "price" in card_info:
                                revenue = sales * card_info.get("price", 0)
                        
                        total_sales += sales
                        total_revenue += revenue
                
                # Среднее за день из данных за последний месяц
                days_count = len(last_30_days)
                if days_count > 0:
                    daily_sales = round(total_sales / days_count)
                    daily_revenue = round(total_revenue / days_count)
                    
                    # Прибыль = выручка - комиссия (примерно 15%)
                    daily_profit = round(daily_revenue * 0.85)
                    
                    # Данные за неделю (среднее за день * 7)
                    weekly_sales = daily_sales * 7
                    weekly_revenue = daily_revenue * 7
                    weekly_profit = daily_profit * 7
                    
                    # Данные за месяц (среднее за день * 30)
                    monthly_sales = daily_sales * 30
                    monthly_revenue = daily_revenue * 30
                    monthly_profit = daily_profit * 30
        
        # Данные о карточке товара
        card_info = {}
        if "card_data" in results:
            card_info = results.get("card_data", {}).get("item", {})
        
        name = card_info.get("name", "")
        brand = card_info.get("brand", "")
        price_current = card_info.get("price", 0)
        price_original = card_info.get("originalPrice", price_current)
        discount = 0
        if price_original > price_current and price_original > 0:
            discount = round((1 - price_current / price_original) * 100)
        
        rating = card_info.get("rating", 0)
        feedbacks = card_info.get("feedbacksCount", 0)
        
        # Если данные о рейтинге и отзывах доступны в расширенной аналитике, используем их
        if extended_analytics:
            if "rating" in extended_analytics and extended_analytics["rating"] > 0:
                rating = extended_analytics["rating"]
            if "comments" in extended_analytics and extended_analytics["comments"] > 0:
                feedbacks = extended_analytics["comments"]
        
        # Данные о складах и размерах
        stocks_info = card_info.get("sizes", [])
        total_stock = 0
        stocks_by_size = {}
        
        for size_info in stocks_info:
            size_name = size_info.get("name", "Unknown")
            size_stock = size_info.get("stocks", 0)
            stocks_by_size[size_name] = size_stock
            total_stock += size_stock
        
        # Если данные о остатках доступны в расширенной аналитике, используем их
        if extended_analytics and "balance" in extended_analytics and extended_analytics["balance"] > 0:
            # Если есть только общее количество, но нет разбивки по размерам
            if total_stock == 0:
                total_stock = extended_analytics["balance"]
        
        # Дополнительные данные из расширенной аналитики
        additional_analytics = {}
        if extended_analytics:
            additional_analytics = {
                "purchase_rate": extended_analytics.get("purchase_rate", 0),  # Процент выкупа
                "purchase_after_return": extended_analytics.get("purchase_after_return", 0),  # Процент выкупа с учетом возвратов
                "turnover_days": extended_analytics.get("turnover_days", 0),  # Оборачиваемость в днях
                "days_in_stock": extended_analytics.get("days_in_stock", 0),  # Дни в наличии
                "days_with_sales": extended_analytics.get("days_with_sales", 0)  # Дни с продажами
            }
        
        # Собираем финальный результат
        result = {
            'name': name,
            'brand': brand,
            'price': {
                'current': price_current,
                'original': price_original,
                'discount': discount,
                'average': extended_analytics.get("final_price_average", price_current)  # Средняя цена за период
            },
            'rating': rating,
            'feedbacks': feedbacks,
            'stocks': {
                'total': total_stock,
                'by_size': stocks_by_size
            },
            'sales': {
                'today': daily_sales,  # Среднедневные продажи
                'total': total_sales,  # Общие продажи за период
                'revenue': {
                    'daily': daily_revenue,
                    'weekly': weekly_revenue,
                    'monthly': monthly_revenue,
                    'total': total_revenue
                },
                'profit': {
                    'daily': daily_profit, 
                    'weekly': weekly_profit,
                    'monthly': monthly_profit
                }
            },
            'analytics': additional_analytics  # Дополнительные метрики
        }
        
        logger.info(f"Final MPSTAT product info prepared for article {article}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting MPSTAT product info: {str(e)}", exc_info=True)
        return None

# Тестирование функции
async def main():
    article = "123456" # Тестовый артикул
    result = await get_product_mpstat_info(article)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())