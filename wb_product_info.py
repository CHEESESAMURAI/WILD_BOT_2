import logging
import json
import requests

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def get_wb_product_info(article):
    """Получает информацию о товаре через API Wildberries."""
    try:
        logger.info(f"Getting product info for article {article}")
        
        # API для получения цен и основной информации
        price_url = f"https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&spp=27&nm={article}&locale=ru&lang=ru"
        logger.info(f"Making request to price API: {price_url}")
        
        headers = {
            'Accept': '*/*',
            'Accept-Language': 'ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7',
            'Connection': 'keep-alive',
            'Origin': 'https://www.wildberries.ru',
            'Referer': f'https://www.wildberries.ru/catalog/{article}/detail.aspx',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
        
        price_response = requests.get(price_url, headers=headers, timeout=10)
        logger.info(f"Price API response status: {price_response.status_code}")
        
        if price_response.status_code != 200:
            logger.error(f"Price API error: {price_response.text}")
            return None
            
        price_data = price_response.json()
        logger.info(f"Price API response data: {json.dumps(price_data, indent=2)}")
        
        if not price_data.get('data', {}).get('products'):
            logger.error("No products found in price API response")
            return None
            
        product = price_data['data']['products'][0]
        logger.info(f"Found product: {product.get('name')}")
        
        # Подсчитываем общее количество товара на складах
        total_stock = 0
        stocks_by_size = {}
        
        for size in product.get('sizes', []):
            size_name = size.get('name', 'Unknown')
            size_stock = sum(stock.get('qty', 0) for stock in size.get('stocks', []))
            stocks_by_size[size_name] = size_stock
            total_stock += size_stock
        
        # API для получения статистики продаж
        sales_today = 0
        total_sales = 0
        
        # Пробуем получить статистику через API статистики продавца
        stats_url = f"https://catalog.wb.ru/sellers/v1/analytics-data?nm={article}"
        try:
            logger.info(f"Making request to seller stats API: {stats_url}")
            stats_response = requests.get(stats_url, headers=headers, timeout=10)
            logger.info(f"Seller stats API response status: {stats_response.status_code}")
            
            if stats_response.status_code == 200:
                stats_data = stats_response.json()
                logger.info(f"Seller stats API response data: {json.dumps(stats_data, indent=2)}")
                
                if 'data' in stats_data:
                    for stat in stats_data['data']:
                        if str(stat.get('nmId')) == str(article):
                            sales_today = stat.get('sales', {}).get('today', 0)
                            total_sales = stat.get('sales', {}).get('total', 0)
                            break
        except Exception as e:
            logger.error(f"Error getting seller stats: {str(e)}")
        
        # Если не получили данные через статистику продавца, пробуем через API заказов
        if sales_today == 0:
            orders_url = f"https://catalog.wb.ru/sellers/v1/orders-data?nm={article}"
            try:
                logger.info(f"Making request to orders API: {orders_url}")
                orders_response = requests.get(orders_url, headers=headers, timeout=10)
                logger.info(f"Orders API response status: {orders_response.status_code}")
                
                if orders_response.status_code == 200:
                    orders_data = orders_response.json()
                    logger.info(f"Orders API response data: {json.dumps(orders_data, indent=2)}")
                    
                    if 'data' in orders_data:
                        for order in orders_data['data']:
                            if str(order.get('nmId')) == str(article):
                                sales_today = order.get('ordersToday', 0)
                                total_sales = order.get('ordersTotal', 0)
                                break
            except Exception as e:
                logger.error(f"Error getting orders data: {str(e)}")
        
        # Если все еще нет данных, пробуем через старый API
        if sales_today == 0:
            old_sales_url = f"https://product-order-qnt.wildberries.ru/by-nm/?nm={article}"
            try:
                logger.info(f"Making request to old sales API: {old_sales_url}")
                old_sales_response = requests.get(old_sales_url, headers=headers, timeout=10)
                logger.info(f"Old sales API response status: {old_sales_response.status_code}")
                
                if old_sales_response.status_code == 200:
                    old_sales_data = old_sales_response.json()
                    logger.info(f"Old sales API response data: {json.dumps(old_sales_data, indent=2)}")
                    
                    # Обработка как списка
                    if isinstance(old_sales_data, list):
                        for item in old_sales_data:
                            if str(item.get('nmId')) == str(article):
                                sales_today = item.get('qnt', 0)
                                break
                    # Обработка как словаря
                    elif isinstance(old_sales_data, dict):
                        sales_today = old_sales_data.get(str(article), {}).get('qnt', 0)
            except Exception as e:
                logger.error(f"Error getting old sales data: {str(e)}")
        
        # Рассчитываем примерную выручку и прибыль
        current_price = product.get('salePriceU', 0) / 100
        
        # Рассчитываем выручку
        daily_revenue = sales_today * current_price
        weekly_revenue = daily_revenue * 7
        monthly_revenue = daily_revenue * 30
        total_revenue = total_sales * current_price
        
        # Рассчитываем прибыль (приблизительно 85% от выручки)
        profit_margin = 0.85
        daily_profit = daily_revenue * profit_margin
        weekly_profit = weekly_revenue * profit_margin
        monthly_profit = monthly_revenue * profit_margin
        
        # Собираем все данные
        original_price = product.get('priceU', 0) / 100
        
        # Рассчитываем скидку в процентах
        discount_percent = 0
        if original_price > 0 and original_price > current_price:
            discount_percent = round(((original_price - current_price) / original_price) * 100)
        
        result = {
            'name': product.get('name', ''),
            'brand': product.get('brand', ''),
            'price': {
                'current': current_price,
                'original': original_price,
                'discount': discount_percent
            },
            'rating': product.get('rating', 0),
            'feedbacks': product.get('feedbacks', 0),
            'stocks': {
                'total': total_stock,
                'by_size': stocks_by_size
            },
            'sales': {
                'today': sales_today,
                'total': total_sales or product.get('ordersCount', 0) or product.get('salesPerMonth', 0) or 0,
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
            }
        }
        
        logger.info(f"Final product info: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting WB product info: {str(e)}", exc_info=True)
        return None 