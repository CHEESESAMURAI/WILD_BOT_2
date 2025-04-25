import re
import json
import sqlite3
import requests
from datetime import datetime, timedelta
import os
from typing import Dict, List, Optional, Tuple
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

# Константы
SERPER_API_KEY = "8ba851ed7ae1e6a655102bea15d73fdb39cdac79"
ADMIN_ID = 1659228199

def escape_markdown(text: str) -> str:
    """Экранирование Markdown символов"""
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def extract_site(block: str) -> str:
    """Извлекает название сайта из строки"""
    m = re.search(r'Сайт:\s*([^\n]+)', block, re.IGNORECASE)
    if m:
        site = m.group(1).strip()
        return site.replace('\\', '')
    return "Неизвестно"

def compute_additional_metrics(
    likes: int,
    views: int,
    approx_clients: int,
    revenue: float,
    growth_percent: float,
    price: float = 500.0
) -> Dict:
    """Вычисляет дополнительные метрики"""
    # Рейтинг блогера (1-5)
    base_score = (likes * 0.1) + (revenue * 0.01) + growth_percent
    base_score = min(base_score, 100)

    if base_score < 20:
        rating = 1
    elif base_score < 40:
        rating = 2
    elif base_score < 60:
        rating = 3
    elif base_score < 80:
        rating = 4
    else:
        rating = 5

    # Прирост заказов за 3 дня
    three_day_orders = int(0.27 * (likes + views))
    three_day_growth_rub = three_day_orders * price
    avg_check = price
    total_orders = approx_clients + 1

    return {
        "rating": rating,
        "three_day_orders": three_day_orders,
        "three_day_growth_rub": three_day_growth_rub,
        "avg_check": avg_check,
        "total_orders": total_orders
    }

def format_site_results_from_items(items: List[Dict]) -> str:
    """Форматирует результаты поиска из списка товаров"""
    lines = []
    for item in items:
        title = item.get("title", "Нет заголовка")
        link = item.get("link", "")
        snippet = item.get("snippet", "")

        likes, views = extract_likes_views(snippet)
        approx_clients, approx_revenue, growth = estimate_impact(likes, views)
        price = 500.0  # Можно добавить реальную цену из item

        metrics = compute_additional_metrics(
            likes=likes,
            views=views,
            approx_clients=approx_clients,
            revenue=approx_revenue,
            growth_percent=growth,
            price=price
        )

        clickable_title = f"[{escape_markdown(title)}]({link})" if link else escape_markdown(title)
        domain = re.sub(r'^https?://(www\.)?', '', link).split('/')[0] if link else "Неизвестно"

        result_text = (
            f"{clickable_title}\n"
            f"🌐 Сайт: {domain}\n"
            f"⭐ Рейтинг блогера: {metrics['rating']}\n"
            f"📈 Прирост заказов за 3 дня: {metrics['three_day_orders']} шт "
            f"({(metrics['three_day_orders']*100)//(likes+views+1)}%)\n"
            f"💰 Прирост в рублях: {int(metrics['three_day_growth_rub'])}₽\n"
            f"📦 Средний чек: {int(metrics['avg_check'])}₽\n"
            f"📦 Количество заказов: {metrics['total_orders']} шт\n"
            f"—\n"
            f"👍 Лайки: {likes}, 👀 Просмотры: {views}\n"
            f"👥 Примерно клиентов: {approx_clients}, Выручка ~ {int(approx_revenue)}₽\n"
            f"📈 Рост продаж ~ {growth:.1f}%"
        )
        lines.append(result_text)

    return "\n\n".join(lines)

def init_db():
    """Инициализация базы данных"""
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    
    # Таблица отслеживаемых артикулов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tracked_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            article TEXT,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            subscription_until TEXT DEFAULT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Таблица истории продаж
    cur.execute('''
        CREATE TABLE IF NOT EXISTS sales_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            article TEXT,
            sales_count INTEGER,
            date DATE,
            UNIQUE(article, date)
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user_info(user_id: int) -> Tuple[float, Optional[str]]:
    """Получение информации о пользователе"""
    if user_id == ADMIN_ID:
        return 777777, None
        
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute('SELECT balance, subscription_until FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    
    if result:
        return result
    return 0, None

def update_user_balance(user_id: int, new_balance: float):
    """Обновление баланса пользователя"""
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO users (user_id, balance)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET balance = ?
    ''', (user_id, new_balance, new_balance))
    conn.commit()
    conn.close()

def update_user_subscription(user_id: int, new_date_str: str):
    """Обновление подписки пользователя"""
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO users (user_id, subscription_until)
        VALUES (?, ?)
        ON CONFLICT(user_id) DO UPDATE SET subscription_until = ?
    ''', (user_id, new_date_str, new_date_str))
    conn.commit()
    conn.close()

def user_has_subscription(user_id: int) -> bool:
    """Проверка наличия активной подписки"""
    if user_id == ADMIN_ID:
        return True
        
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute('SELECT subscription_until FROM users WHERE user_id = ?', (user_id,))
    result = cur.fetchone()
    conn.close()
    
    if not result or not result[0]:
        return False
        
    subscription_until = datetime.strptime(result[0], '%Y-%m-%d')
    return subscription_until > datetime.now()

def add_article(user_id: int, article: str) -> bool:
    """Добавление артикула в отслеживание"""
    try:
        conn = sqlite3.connect('tracked_articles.db')
        cur = conn.cursor()
        cur.execute('''
            INSERT INTO tracked_articles (user_id, article)
            VALUES (?, ?)
        ''', (user_id, article))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def remove_article(user_id: int, article: str):
    """Удаление артикула из отслеживания"""
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute('''
        DELETE FROM tracked_articles
        WHERE user_id = ? AND article = ?
    ''', (user_id, article))
    conn.commit()
    conn.close()

def list_articles(user_id: int) -> List[str]:
    """Получение списка отслеживаемых артикулов"""
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute('SELECT article FROM tracked_articles WHERE user_id = ?', (user_id,))
    articles = [row[0] for row in cur.fetchall()]
    conn.close()
    return articles

def load_sales_history(article: str) -> List[Dict]:
    """Загрузка истории продаж для артикула"""
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute('''
        SELECT date, sales_count
        FROM sales_history
        WHERE article = ?
        ORDER BY date DESC
        LIMIT 30
    ''', (article,))
    history = [{'date': row[0], 'sales': row[1]} for row in cur.fetchall()]
    conn.close()
    return history

def update_sales_history(article: str, sales_count: int):
    """Обновление истории продаж"""
    today = datetime.now().date().strftime('%Y-%m-%d')
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO sales_history (article, sales_count, date)
        VALUES (?, ?, ?)
        ON CONFLICT(article, date) DO UPDATE SET sales_count = ?
    ''', (article, sales_count, today, sales_count))
    conn.commit()
    conn.close()

def compute_sales_trend(history: List[Dict]) -> float:
    """Вычисление тренда продаж"""
    if len(history) < 2:
        return 0.0
        
    current = history[0]['sales']
    previous = history[1]['sales']
    
    if previous == 0:
        return 100.0 if current > 0 else 0.0
        
    return ((current - previous) / previous) * 100

def get_wb_product_info(article: str) -> Dict:
    """Получение информации о товаре через API Wildberries"""
    try:
        api_url = f"https://card.wb.ru/cards/detail?curr=rub&dest=-1257786&regions=80,64,83,4,38,33,70,82,69,30,86,75,40,1,66,48,110,31,22,71,114&nm={article}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(api_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            if data.get('data', {}).get('products'):
                product = data['data']['products'][0]
                
                return {
                    'title': product.get('name', 'Unknown Product'),
                    'price': product.get('priceU', 0) / 100 if 'priceU' in product else product.get('price', 0),
                    'rating': product.get('rating', 0.0),
                    'reviews': product.get('reviewRating', 0),
                    'sales_count': product.get('soldQuantity', 0),
                    'views': product.get('views', 0),
                    'likes': product.get('likes', 0)
                }
    except Exception as e:
        print(f"Error getting product info: {str(e)}")
    return None

def format_sales_info(data: Dict) -> str:
    """Форматирование информации о продажах"""
    def esc(t):
        return str(t).replace('_', '\\_').replace('*', '\\*').replace('[', '\\[').replace(']', '\\]').replace('(', '\\(').replace(')', '\\)').replace('~', '\\~').replace('`', '\\`').replace('>', '\\>').replace('#', '\\#').replace('+', '\\+').replace('-', '\\-').replace('=', '\\=').replace('|', '\\|').replace('{', '\\{').replace('}', '\\}').replace('.', '\\.').replace('!', '\\!')
    
    if not data:
        return "❌ Не удалось получить информацию о товаре"
        
    return f"""
📊 *Информация о товаре*

📦 Название: {esc(data['title'])}
💰 Цена: {data['price']}₽
⭐ Рейтинг: {data['rating']}
📝 Отзывов: {data['reviews']}
📈 Продаж: {data['sales_count']}
👀 Просмотров: {data['views']}
👍 Лайков: {data['likes']}
"""

def extract_likes_views(block: str) -> Tuple[int, int]:
    """Извлечение количества лайков и просмотров"""
    likes = 0
    views = 0
    
    # Поиск лайков
    likes_match = re.search(r'(\d+)\s*(?:лайк|like)', block, re.IGNORECASE)
    if likes_match:
        likes = int(likes_match.group(1))
    
    # Поиск просмотров/комментариев
    views_match = re.search(r'(\d+)\s*(?:просмотр|view|комментар|comment)', block, re.IGNORECASE)
    if views_match:
        views = int(views_match.group(1))
    
    return likes, views

def process_text(text: str) -> str:
    """Обработка текста"""
    # Удаляем лишние пробелы
    text = re.sub(r'\s+', ' ', text)
    # Удаляем специальные символы
    text = re.sub(r'[^\w\s.,!?-]', '', text)
    return text.strip()

def format_results_message(results: List[Dict]) -> str:
    """Форматирование сообщения с результатами"""
    if not results:
        return "❌ Результаты не найдены"
    
    message = "🔍 *Результаты поиска:*\n\n"
    for i, result in enumerate(results, 1):
        message += f"{i}. {result['title']}\n"
        if result.get('price'):
            message += f"💰 Цена: {result['price']}₽\n"
        if result.get('rating'):
            message += f"⭐ Рейтинг: {result['rating']}\n"
        message += "\n"
    
    return message

def estimate_impact(likes: int, views: int) -> Tuple[int, float, float]:
    """Оценка влияния на продажи"""
    # Если лайков и просмотров нет, задаем минимальные значения
    if likes == 0 and views == 0:
        likes, views = 1, 1
    
    # Примерная оценка клиентов (можно улучшить)
    approx_clients = int((likes + views) * 0.1)
    
    # Примерная выручка (средний чек 500₽)
    revenue = approx_clients * 500
    
    # Рост продаж (процент от базового уровня)
    growth = (likes + views) * 0.1
    
    return approx_clients, revenue, growth

def global_search_serper_detailed(query: str) -> Dict:
    """Поиск товаров через Serper API"""
    try:
        url = "https://google.serper.dev/search"
        headers = {
            'X-API-KEY': SERPER_API_KEY,
            'Content-Type': 'application/json'
        }
        payload = {
            'q': f"{query} site:wildberries.ru",
            'gl': 'ru',
            'hl': 'ru'
        }
        
        response = requests.post(url, headers=headers, json=payload)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error in global search: {str(e)}")
    return {}

def format_serper_results_detailed(search_data: Dict) -> str:
    """Форматирование результатов поиска"""
    if not search_data or 'organic' not in search_data:
        return "❌ Ничего не найдено"
        
    results = []
    for item in search_data['organic'][:5]:  # Показываем только первые 5 результатов
        title = item.get('title', 'Нет заголовка')
        link = item.get('link', '')
        snippet = item.get('snippet', '')
        
        # Извлекаем артикул из ссылки
        article = link.split('/')[-1] if link else ''
        
        # Формируем кликабельный заголовок
        clickable_title = f"[{title}]({link})" if link else title
        
        result = f"""
📦 {clickable_title}
🔗 Артикул: {article}
📝 {snippet}
"""
        results.append(result)
    
    return "\n\n".join(results) 