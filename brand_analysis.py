import logging
import requests
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import numpy as np
import hashlib
import random

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Константы
MPSTAT_API_KEY = "68431d2ac72ea4.96910328a56006b24a55daf65db03835d5fe5b4d"

async def get_brand_info(brand_name):
    """Получает информацию о бренде из MPSTAT API или Wildberries API."""
    try:
        if not brand_name:
            logger.error("Не указано название бренда")
            return None
            
        logger.info(f"Getting brand info for {brand_name}")
        
        # Сначала пробуем получить данные от MPSTAT API
        mpstat_info = await get_brand_info_mpstat(brand_name)
        if mpstat_info:
            logger.info(f"Получены данные о бренде {brand_name} из MPSTAT API")
            return mpstat_info
            
        # Если MPSTAT недоступен, пробуем получить данные из Wildberries API
        wb_info = await get_brand_info_wb(brand_name)
        if wb_info:
            logger.info(f"Получены данные о бренде {brand_name} из Wildberries API")
            return wb_info
            
        # Если оба API недоступны, возвращаем None
        logger.error(f"Не удалось получить информацию о бренде {brand_name} из обоих API")
        return None
        
    except Exception as e:
        logger.error(f"Ошибка при получении информации о бренде: {str(e)}", exc_info=True)
        return None

async def get_brand_info_mpstat(brand_name):
    """Получает информацию о бренде из MPSTAT API."""
    try:
        # Запрос данных о бренде
        url = f"https://mpstats.io/api/wb/get/brands"
        headers = {
            "X-Mpstats-TOKEN": MPSTAT_API_KEY,
            "Content-Type": "application/json"
        }
        
        # Параметры запроса
        params = {
            "path": "/brands",  # Обязательный параметр path
            "startRow": 0,
            "endRow": 10,
            "query": brand_name
        }
        
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code == 200:
            brands_data = response.json()
            
            # Ищем точное совпадение по имени бренда
            brand_info = None
            for brand in brands_data.get('data', []):
                if brand.get('title', '').lower() == brand_name.lower():
                    brand_info = brand
                    break
            
            # Если не нашли точное совпадение, берем первый результат
            if not brand_info and brands_data.get('data'):
                brand_info = brands_data['data'][0]
            
            if brand_info:
                # Формируем информацию о бренде
                result = {
                    'name': brand_name,
                    'total_items': brand_info.get('itemsCount', 0),
                    'avg_price': brand_info.get('avgPrice', 0),
                    'avg_rating': brand_info.get('rating', 0),
                    'total_sales': brand_info.get('salesCount', 0),
                    'total_revenue': brand_info.get('revenue', 0),
                    'category_position': brand_info.get('position', 0),
                    'categories': brand_info.get('categories', []),
                    'competitors': [],
                    'sales_dynamics': [],
                    'items_stats': []
                }
                
                return result
        
        logger.error(f"MPSTAT API error when getting brand info: {response.status_code} - {response.text}")
        return None
            
    except Exception as e:
        logger.error(f"MPSTAT request error: {str(e)}")
        return None

async def get_brand_info_wb(brand_name):
    """Получает информацию о бренде из Wildberries API."""
    try:
        # Поиск бренда через API поиска Wildberries
        search_url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?appType=1&couponsGeo=12,3,18,15,21&curr=rub&dest=-1029256,-102269,-2162196,-1257786&emp=0&lang=ru&locale=ru&pricemarginCoeff=1.0&query={brand_name}&reg=0&regions=80,64,83,4,38,33,70,82,69,68,86,75,30,40,48,1,22,66,31,71&resultset=catalog&sort=popular&spp=0&suppressSpellcheck=false"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(search_url, headers=headers, timeout=10)
        
        if response.status_code == 200:
            search_data = response.json()
            products = search_data.get('data', {}).get('products', [])
            
            if not products:
                logger.error(f"No products found for brand {brand_name} in Wildberries API")
                return None
                
            # Проверяем, что это действительно товары искомого бренда
            brand_products = [p for p in products if p.get('brand', '').lower() == brand_name.lower()]
            
            if not brand_products and products:
                # Если нет точного совпадения по имени, используем результаты поиска
                brand_products = products
            
            if brand_products:
                # Расчет средней цены, рейтинга и других показателей
                total_items = len(brand_products)
                total_price = sum(p.get('priceU', 0) / 100 for p in brand_products)
                avg_price = total_price / total_items if total_items > 0 else 0
                
                avg_rating = sum(p.get('rating', 0) for p in brand_products) / total_items if total_items > 0 else 0
                
                # Оцениваем продажи на основе рейтинга и отзывов (это примерная оценка)
                total_feedbacks = sum(p.get('feedbacks', 0) for p in brand_products)
                estimated_sales = total_feedbacks * 10  # Примерная оценка: 1 отзыв ≈ 10 продаж
                
                # Получаем категории
                categories = list(set(p.get('name', '').split('/')[0].strip() for p in brand_products if '/' in p.get('name', '')))
                if not categories:
                    categories = ["Неизвестная категория"]
                
                # Формируем результат
                result = {
                    'name': brand_name,
                    'total_items': total_items,
                    'avg_price': avg_price,
                    'avg_rating': avg_rating,
                    'total_sales': estimated_sales,
                    'total_revenue': estimated_sales * avg_price,
                    'category_position': 0,  # Wildberries API не дает эту информацию
                    'categories': categories[:5],  # Берем до 5 категорий
                    'competitors': [],  # Wildberries API не дает эту информацию
                    'sales_dynamics': [],  # Wildberries API не дает эту информацию
                    'items_stats': []  # Заполним топ товарами
                }
                
                # Добавляем топ товары
                for i, product in enumerate(brand_products[:10]):  # Берем до 10 топ товаров
                    result['items_stats'].append({
                        'name': product.get('name', f"Товар #{i+1}"),
                        'article': product.get('id', 0),
                        'price': product.get('priceU', 0) / 100,
                        'sales': product.get('feedbacks', 0) * 10,  # Примерная оценка
                        'revenue': (product.get('priceU', 0) / 100) * (product.get('feedbacks', 0) * 10),
                        'rating': product.get('rating', 0)
                    })
                
                return result
        
        logger.error(f"Wildberries API error when getting brand info: {response.status_code}")
        return None
            
    except Exception as e:
        logger.error(f"Wildberries request error: {str(e)}")
        return None

# Оставляем функцию generate_placeholder_brand_info для совместимости,
# но её больше не будем использовать в основном коде
def generate_placeholder_brand_info(brand_name):
    """Генерирует заглушку для информации о бренде."""
    # Для реализма генерируем случайные данные на основе имени бренда
    import random
    import hashlib
    
    # Используем хэш имени бренда для генерации псевдослучайных, но стабильных чисел
    hash_obj = hashlib.md5(brand_name.encode())
    hash_int = int(hash_obj.hexdigest(), 16)
    random.seed(hash_int)
    
    # Генерируем показатели
    total_items = random.randint(50, 500)
    avg_price = random.randint(1000, 5000)
    avg_rating = round(3.5 + random.random() * 1.5, 1)  # От 3.5 до 5.0
    category_position = random.randint(1, 50)
    total_sales = random.randint(1000, 10000)
    total_revenue = total_sales * avg_price
    
    # Популярные категории Wildberries
    categories = [
        "Одежда", "Обувь", "Аксессуары", "Красота", 
        "Дом", "Детям", "Электроника", "Спорт"
    ]
    
    # Выбираем случайные категории для бренда
    brand_categories = random.sample(categories, min(3, len(categories)))
    
    # Генерируем динамику продаж (30 дней)
    sales_dynamics = []
    base_sales = random.randint(30, 100)
    for i in range(30):
        date = (datetime.now() - timedelta(days=i)).strftime("%Y-%m-%d")
        sales = int(base_sales * (0.8 + 0.4 * random.random()))  # ±20% колебания
        revenue = sales * avg_price
        sales_dynamics.append({
            "date": date,
            "sales": sales,
            "revenue": revenue
        })
    
    # Генерируем конкурентов
    competitors = []
    competitor_names = [
        "TopStyle", "FashionHub", "TrendMark", "StyleMax", 
        "CoolBrand", "NewWave", "PrimeBrand", "EliteStyle"
    ]
    for i in range(min(5, len(competitor_names))):
        competitors.append({
            "name": competitor_names[i],
            "total_items": random.randint(30, total_items * 2),
            "avg_price": random.randint(int(avg_price * 0.8), int(avg_price * 1.2)),
            "total_sales": random.randint(int(total_sales * 0.5), int(total_sales * 1.5))
        })
    
    # Топ товары бренда
    items_stats = []
    for i in range(10):
        item_name = f"Товар {brand_name} #{i+1}"
        items_stats.append({
            "name": item_name,
            "article": random.randint(1000000, 9999999),
            "price": random.randint(int(avg_price * 0.7), int(avg_price * 1.3)),
            "sales": random.randint(10, 100),
            "revenue": random.randint(10000, 100000),
            "rating": round(3.0 + random.random() * 2.0, 1)
        })
    
    return {
        'name': brand_name,
        'total_items': total_items,
        'avg_price': avg_price,
        'avg_rating': avg_rating,
        'total_sales': total_sales,
        'total_revenue': total_revenue,
        'category_position': category_position,
        'categories': brand_categories,
        'sales_dynamics': sales_dynamics,
        'competitors': competitors,
        'items_stats': items_stats
    }

def format_brand_analysis(brand_info):
    """Форматирует информацию о бренде для отображения."""
    try:
        if not brand_info:
            return "❌ Не удалось получить информацию о бренде. Пожалуйста, проверьте название бренда и попробуйте снова."
            
        brand_name = brand_info.get('name', 'Неизвестный бренд')
        total_items = brand_info.get('total_items', 0)
        avg_price = brand_info.get('avg_price', 0)
        avg_rating = brand_info.get('avg_rating', 0)
        category_position = brand_info.get('category_position', 0)
        total_sales = brand_info.get('total_sales', 0)
        total_revenue = brand_info.get('total_revenue', 0)
        
        result = f"🏢 АНАЛИЗ БРЕНДА: {brand_name}\n"
        result += "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━\n\n"
        
        # Основные показатели
        result += "📌 Основные показатели:\n"
        result += f"• Количество товаров: {total_items:,}".replace(',', ' ') + " шт.\n"
        result += f"• Средняя цена: {avg_price:,}₽".replace(',', ' ') + "\n"
        result += f"• Средний рейтинг: {avg_rating:.1f}/5\n"
        
        if category_position > 0:
            result += f"• Позиция в категории: {category_position}-е место\n"
        
        if total_sales > 0:
            result += f"• Общие продажи: {total_sales:,}".replace(',', ' ') + " шт.\n"
        
        if total_revenue > 0:
            formatted_revenue = "{:,}".format(int(total_revenue)).replace(',', ' ')
            result += f"• Общая выручка: {formatted_revenue}₽\n"
        
        # Категории
        categories = brand_info.get('categories', [])
        if categories:
            result += "\n📁 Представлен в категориях:\n"
            for category in categories[:5]:  # Ограничиваем 5 категориями
                result += f"• {category}\n"
            
            if len(categories) > 5:
                result += f"• ... и еще {len(categories) - 5} категорий\n"
        
        # Топ товары бренда
        items = brand_info.get('items_stats', [])
        if items:
            result += "\n🔝 Топ-5 товаров бренда:\n"
            for i, item in enumerate(items[:5]):
                name = item.get('name', f"Товар #{i+1}")
                price = item.get('price', 0)
                sales = item.get('sales', 0)
                rating = item.get('rating', 0)
                result += f"• {name} — {price:,}₽".replace(',', ' ')
                if sales:
                    result += f", {sales} продаж"
                if rating:
                    result += f", рейтинг {rating:.1f}/5"
                result += "\n"
        
        # Конкуренты
        competitors = brand_info.get('competitors', [])
        if competitors:
            result += "\n🥊 Основные конкуренты:\n"
            for comp in competitors[:5]:
                comp_name = comp.get('name', '')
                comp_items = comp.get('total_items', 0)
                comp_sales = comp.get('total_sales', 0)
                
                result += f"• {comp_name}"
                if comp_items:
                    result += f" — {comp_items:,}".replace(',', ' ') + " товаров"
                if comp_sales:
                    result += f", {comp_sales:,}".replace(',', ' ') + " продаж"
                result += "\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error formatting brand analysis: {str(e)}", exc_info=True)
        return f"❌ Ошибка при форматировании результатов анализа бренда: {str(e)}" 