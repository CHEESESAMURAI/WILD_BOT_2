import re
import os
import json
import sqlite3
import asyncio
import requests
from datetime import date, datetime, timedelta
import time
import aiohttp
import random
from typing import List, Dict, Optional
import logging

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Selenium + webdriver_manager
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException

###############################################################################
# Константы и глобальные переменные

BOT_TOKEN = "7790448077:AAFiiS0a44A40zJUEivONLRutB-kqradDdE"
SERPER_API_KEY = "8ba851ed7ae1e6a655102bea15d73fdb39cdac79"  # ключ для serper.dev
ADMIN_ID = 1659228199  # ID администратора

WELCOME_MESSAGE = (
    "👋 *Добро пожаловать в WHITESAMURAI!*\n\n"
    "Мы — профессиональная компания, которая помогает отслеживать продажи товаров "
    "и анализировать динамику 📊.\n\n"
    "Используйте API для выполнения команд: например, отправьте артикул для анализа или "
    "выполните другие действия через эндпойнты."
)

# Словарь для хранения временных действий пользователей (аналог pending_action)
pending_action = {}

###############################################################################
# Бизнес-логика (функции из Telegram-бота)

def escape_markdown(text: str) -> str:
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

def extract_site(block: str) -> str:
    m = re.search(r'Сайт:\s*([^\n]+)', block, re.IGNORECASE)
    if m:
        site = m.group(1).strip()
        return site.replace('\\', '')
    return "Неизвестно"

def compute_additional_metrics(likes: int,
                               views: int,
                               approx_clients: int,
                               revenue: float,
                               growth_percent: float,
                               price: float = 500.0) -> dict:
    base_score = (likes * 0.1) + (revenue * 0.01) + growth_percent
    if base_score > 100:
        base_score = 100
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

def extract_likes_views(block: str):
    block_lower = block.lower()
    matches = re.findall(r'(\d+)\s*likes,\s*(\d+)\s*comments', block_lower)
    if matches:
        try:
            return int(matches[0][0]), int(matches[0][1])
        except ValueError:
            pass
    m_likes = re.search(r'(\d+)\s*likes', block_lower)
    m_views = re.search(r'(\d+)\s*comments', block_lower)
    likes = int(m_likes.group(1)) if m_likes else 0
    views = int(m_views.group(1)) if m_views else 0
    return likes, views

def estimate_impact(likes, views):
    if likes == 0 and views == 0:
        likes = 10
        views = 100
    approx_clients = int(likes * 0.1 + views * 0.05)
    avg_check = 500
    approx_revenue = approx_clients * avg_check
    baseline = 10000
    growth_percent = (approx_revenue / baseline) * 100 if baseline else 0
    return approx_clients, approx_revenue, growth_percent

def format_site_results_from_items(items: list) -> str:
    lines = []
    for item in items:
        title = item.get("title", "Нет заголовка")
        link = item.get("link", "")
        snippet = item.get("snippet", "")
        likes, views = extract_likes_views(snippet)
        approx_clients, approx_revenue, growth = estimate_impact(likes, views)
        price = 500.0
        metrics = compute_additional_metrics(
            likes=likes,
            views=views,
            approx_clients=approx_clients,
            revenue=approx_revenue,
            growth_percent=growth,
            price=price
        )
        rating = metrics["rating"]
        three_day_orders = metrics["three_day_orders"]
        three_day_growth_rub = metrics["three_day_growth_rub"]
        avg_check = metrics["avg_check"]
        total_orders = metrics["total_orders"]
        clickable_title = f"[{escape_markdown(title)}]({link})" if link else escape_markdown(title)
        domain = "Неизвестно"
        if link:
            domain = re.sub(r'^https?://(www\.)?', '', link).split('/')[0]
        result_text = (
            f"{clickable_title}\n"
            f"🌐 Сайт: {domain}\n"
            f"⭐ Рейтинг блогера: {rating}\n"
            f"📈 Прирост заказов за 3 дня: {three_day_orders} шт ({(three_day_orders*100)//(likes+views+1)}%)\n"
            f"💰 Прирост в рублях: {int(three_day_growth_rub)}₽\n"
            f"📦 Средний чек: {int(avg_check)}₽\n"
            f"📦 Количество заказов: {total_orders} шт\n"
            f"—\n"
            f"👍 Лайки: {likes}, 👀 Просмотры: {views}\n"
            f"👥 Примерно клиентов: {approx_clients}, Выручка ~ {int(approx_revenue)}₽\n"
            f"📈 Рост продаж ~ {growth:.1f}%"
        )
        lines.append(result_text)
    return "\n\n".join(lines)

def format_sales_info(data):
    def esc(t):
        return escape_markdown(t)
    title = esc(data.get('Название', 'Нет данных'))
    price = esc(data.get('Цена', '0 ₽'))
    reviews = esc(data.get('Отзывы', 'Нет отзывов'))
    s_day = str(data.get('Продажи за сутки', 0))
    s_week_est = str(data.get('Приблизительные продажи за неделю', 0))
    s_month_est = str(data.get('Приблизительные продажи за месяц', 0))
    rev_day = esc(data.get('Выручка за сутки', '0 ₽'))
    rev_week_est = esc(data.get('Выручка за неделю (приблизительно)', '0 ₽'))
    rev_month_est = esc(data.get('Выручка за месяц (приблизительно)', '0 ₽'))
    profit_day = esc(data.get('Прибыль за сутки', '0 ₽'))
    profit_week_est = esc(data.get('Прибыль за неделю (приблизительно)', '0 ₽'))
    profit_month_est = esc(data.get('Прибыль за месяц (приблизительно)', '0 ₽'))
    trend = esc(data.get('Динамика продаж (по предыдущему дню)', 'Нет данных'))
    text = (
        f"*Название:* {title}\n"
        f"*Цена:* {price}\n"
        f"*Отзывы:* {reviews}\n\n"
        f"*Продажи:*\n"
        f"  • За сутки: {s_day}\n"
        f"  • За неделю (приблизительно): {s_week_est}\n"
        f"  • За месяц (приблизительно): {s_month_est}\n\n"
        f"*Выручка:*\n"
        f"  • За сутки: {rev_day}\n"
        f"  • За неделю (приблизительно): {rev_week_est}\n"
        f"  • За месяц (приблизительно): {rev_month_est}\n\n"
        f"*Прибыль:*\n"
        f"  • За сутки: {profit_day}\n"
        f"  • За неделю (приблизительно): {profit_week_est}\n"
        f"  • За месяц (приблизительно): {profit_month_est}\n\n"
        f"*Динамика продаж (по предыдущему дню):* {trend}\n"
    )
    return text

###############################################################################
# Работа с базой данных (SQLite)

def init_db():
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    
    # Таблица отслеживаемых артикулов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS tracked_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            article TEXT
        )
    ''')
    
    # Таблица пользователей
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            subscription_until TEXT DEFAULT NULL
        )
    ''')
    
    # Таблица истории просмотров
    cur.execute('''
        CREATE TABLE IF NOT EXISTS user_view_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            article TEXT,
            view_date TEXT,
            FOREIGN KEY (user_id) REFERENCES users(user_id)
        )
    ''')
    
    # Таблица сезонных паттернов
    cur.execute('''
        CREATE TABLE IF NOT EXISTS seasonal_patterns (
            article TEXT PRIMARY KEY,
            peak_month INTEGER,
            low_month INTEGER,
            seasonal_factor REAL,
            last_updated TEXT
        )
    ''')
    
    conn.commit()
    conn.close()

def get_user_info(user_id):
    if user_id == ADMIN_ID:
        return 777777, None
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute("SELECT balance, subscription_until FROM users WHERE user_id = ?", (user_id,))
    row = cur.fetchone()
    if not row:
        cur.execute("INSERT INTO users (user_id, balance, subscription_until) VALUES (?, ?, ?)",
                    (user_id, 0, None))
        conn.commit()
        balance = 0
        subscription_until = None
    else:
        balance, subscription_until = row
    conn.close()
    return balance, subscription_until

def update_user_balance(user_id, new_balance):
    if user_id == ADMIN_ID:
        return
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET balance = ? WHERE user_id = ?", (new_balance, user_id))
    conn.commit()
    conn.close()

def update_user_subscription(user_id, new_date_str):
    if user_id == ADMIN_ID:
        return
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute("UPDATE users SET subscription_until = ? WHERE user_id = ?", (new_date_str, user_id))
    conn.commit()
    conn.close()

def user_has_subscription(user_id):
    if user_id == ADMIN_ID:
        return True
    balance, sub_until_str = get_user_info(user_id)
    if not sub_until_str:
        return False
    try:
        sub_until = datetime.strptime(sub_until_str, "%Y-%m-%d").date()
        return sub_until >= date.today()
    except:
        return False

def add_article(user_id, article):
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute("SELECT * FROM tracked_articles WHERE user_id = ? AND article = ?", (user_id, article))
    if cur.fetchone() is None:
        cur.execute("INSERT INTO tracked_articles (user_id, article) VALUES (?, ?)", (user_id, article))
        conn.commit()
        conn.close()
        return True
    else:
        conn.close()
        return False

def remove_article(user_id, article):
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute("DELETE FROM tracked_articles WHERE user_id = ? AND article = ?", (user_id, article))
    conn.commit()
    conn.close()

def list_articles(user_id):
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute("SELECT article FROM tracked_articles WHERE user_id = ?", (user_id,))
    rows = cur.fetchall()
    conn.close()
    return [row[0] for row in rows]

###############################################################################
# Функции для работы с Wildberries, Serper.dev и анализа
# (В примере приведены основные функции – их можно дорабатывать и расширять)

def get_api_data(article, price, commission=0.15):
    api_url = f"https://card.wb.ru/cards/v1/detail?appType=1&curr=rub&dest=-1257786&spp=0&nm={article}"
    sales_info = {"sales_today": 0, "revenue_today": 0, "profit_today": 0}
    try:
        resp = requests.get(api_url, headers={"User-Agent": "Mozilla/5.0"})
        if resp.status_code == 200:
            data_api = resp.json()
            products = data_api.get("data", {}).get("products", [])
            if products:
                product_data = products[0]
                sales_today = product_data.get("sale", 0)
                sales_info["sales_today"] = sales_today
                revenue_today = sales_today * price
                profit_today = revenue_today * (1 - commission)
                sales_info["revenue_today"] = revenue_today
                sales_info["profit_today"] = profit_today
    except:
        pass
    return sales_info

def get_wb_product_info(article):
    """
    Получает информацию о товаре с Wildberries с использованием Selenium.
    """
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    
    try:
        driver = webdriver.Chrome(service=Service(ChromeDriverManager().install()), options=chrome_options)
        url = f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
        driver.get(url)
        
        # Получаем базовые данные о товаре
        product_data = get_product_page_data(driver)
        
        # Получаем историю продаж
        history = load_sales_history()
        article_history = history.get(article, [])
        
        # Обновляем историю продаж
        update_sales_history(article, product_data['Продажи за сутки'])
        
        # Вычисляем тренд продаж
        trend = compute_sales_trend(article_history)
        
        # Получаем данные через API
        price = int(re.sub(r'[^\d]', '', product_data['Цена']))
        api_data = get_api_data(article, price)
        
        # Объединяем все данные
        result = {
            **product_data,
            'Динамика продаж (по предыдущему дню)': trend,
            **api_data
        }
        
        driver.quit()
        return result
        
    except Exception as e:
        return {
            'Название': f'Ошибка при получении данных: {str(e)}',
            'Цена': '0 ₽',
            'Отзывы': '0',
            'Продажи за сутки': 0,
            'Приблизительные продажи за неделю': 0,
            'Приблизительные продажи за месяц': 0,
            'Динамика продаж (по предыдущему дню)': 'Нет данных'
        }

class SearchCache:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 3600  # 1 час в секундах
    
    def get(self, query):
        if query in self.cache:
            timestamp, data = self.cache[query]
            if time.time() - timestamp < self.cache_timeout:
                return data
        return None
    
    def set(self, query, data):
        self.cache[query] = (time.time(), data)

search_cache = SearchCache()

async def global_search_serper_detailed(query: str, max_results: int = 10, 
                                      include_social: bool = True,
                                      include_news: bool = False,
                                      include_images: bool = False):
    """
    Расширенный поиск через Serper.dev с кэшированием и дополнительными параметрами
    
    Параметры:
    - query: поисковый запрос
    - max_results: максимальное количество результатов
    - include_social: включать ли социальные сети
    - include_news: включать ли новости
    - include_images: включать ли изображения
    """
    # Проверяем кэш
    cached_results = search_cache.get(query)
    if cached_results:
        return cached_results
    
    url = "https://google.serper.dev/search"
    payload = {
        "q": query,
        "gl": "ru",
        "hl": "ru",
        "num": max_results
    }
    
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as resp:
                if resp.status != 200:
                    return {
                        "error": f"Ошибка serper.dev: {resp.status}",
                        "results": []
                    }
                
                data = await resp.json()
                
                # Обрабатываем результаты
                results = {
                    "organic": [],
                    "social": [],
                    "news": [],
                    "images": []
                }
                
                # Обработка органических результатов
                if "organic" in data:
                    for item in data["organic"]:
                        link = item.get("link", "")
                        if "wildberries" in link.lower():
                            continue
                        
                        # Анализ домена
                        domain = re.sub(r'^https?://(www\.)?', '', link).split('/')[0].lower()
                        
                        # Классификация результатов
                        if include_social and any(social in domain for social in ["vk.com", "instagram.com", "t.me"]):
                            results["social"].append(item)
                        elif include_news and any(news in domain for news in ["news", "media", "press"]):
                            results["news"].append(item)
                        else:
                            results["organic"].append(item)
                
                # Обработка изображений
                if include_images and "images" in data:
                    results["images"] = data["images"][:5]  # Берем первые 5 изображений
                
                # Анализ результатов
                analysis = {
                    "total_results": len(results["organic"]) + len(results["social"]) + len(results["news"]),
                    "social_mentions": len(results["social"]),
                    "news_mentions": len(results["news"]),
                    "has_images": len(results["images"]) > 0
                }
                
                final_results = {
                    "results": results,
                    "analysis": analysis,
                    "timestamp": datetime.now().isoformat()
                }
                
                # Сохраняем в кэш
                search_cache.set(query, final_results)
                
                return final_results
                
    except Exception as e:
        return {
            "error": f"Ошибка при выполнении поиска: {str(e)}",
            "results": []
        }

def load_sales_history():
    try:
        with open('sales_history.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

def update_sales_history(article, sales_today):
    history = load_sales_history()
    if article not in history:
        history[article] = []
    history[article].append({
        'date': str(date.today()),
        'sales': sales_today
    })
    with open('sales_history.json', 'w') as f:
        json.dump(history, f)

def compute_sales_trend(article_history):
    if len(article_history) < 2:
        return "Нет данных для сравнения"
    today_sales = article_history[-1]['sales']
    yesterday_sales = article_history[-2]['sales']
    if yesterday_sales == 0:
        return "Нет данных за вчера"
    change = ((today_sales - yesterday_sales) / yesterday_sales) * 100
    if change > 0:
        return f"📈 +{change:.1f}%"
    elif change < 0:
        return f"📉 {change:.1f}%"
    else:
        return "➡️ Без изменений"

def get_extended_sales_data(driver):
    try:
        # Ожидаем загрузку элемента с данными о продажах
        sales_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-widget='webProduct']"))
        )
        
        # Извлекаем данные о продажах
        sales_text = sales_element.text
        sales_today = 0
        sales_week = 0
        sales_month = 0
        
        # Парсим данные о продажах
        if "продано" in sales_text.lower():
            sales_match = re.search(r'продано\s*(\d+)', sales_text.lower())
            if sales_match:
                sales_today = int(sales_match.group(1))
        
        # Оцениваем продажи за неделю и месяц
        sales_week = sales_today * 7
        sales_month = sales_today * 30
        
        return {
            'sales_today': sales_today,
            'sales_week': sales_week,
            'sales_month': sales_month
        }
    except TimeoutException:
        return {
            'sales_today': 0,
            'sales_week': 0,
            'sales_month': 0
        }

def try_find_price_by_selectors(driver, selectors):
    for selector in selectors:
        try:
            element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, selector))
            )
            price_text = element.text.strip()
            price = int(re.sub(r'[^\d]', '', price_text))
            return price
        except:
            continue
    return 0

def get_product_page_data(driver):
    try:
        # Ожидаем загрузку страницы
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CSS_SELECTOR, "div[data-widget='webProduct']"))
        )
        
        # Получаем название товара
        title = driver.find_element(By.CSS_SELECTOR, "h1[data-widget='webProduct']").text.strip()
        
        # Получаем цену
        price_selectors = [
            "span[data-widget='webPrice']",
            "div[data-widget='webPrice']",
            "span[data-widget='webCurrentPrice']"
        ]
        price = try_find_price_by_selectors(driver, price_selectors)
        
        # Получаем отзывы
        reviews = "0"
        try:
            reviews_element = driver.find_element(By.CSS_SELECTOR, "span[data-widget='webReview']")
            reviews = reviews_element.text.strip()
        except:
            pass
        
        # Получаем данные о продажах
        sales_data = get_extended_sales_data(driver)
        
        return {
            'Название': title,
            'Цена': f"{price} ₽",
            'Отзывы': reviews,
            'Продажи за сутки': sales_data['sales_today'],
            'Приблизительные продажи за неделю': sales_data['sales_week'],
            'Приблизительные продажи за месяц': sales_data['sales_month']
        }
    except Exception as e:
        return {
            'Название': 'Ошибка при получении данных',
            'Цена': '0 ₽',
            'Отзывы': '0',
            'Продажи за сутки': 0,
            'Приблизительные продажи за неделю': 0,
            'Приблизительные продажи за месяц': 0
        }

def analyze_market_trends(article_history):
    """Анализирует рыночные тренды на основе истории продаж"""
    if len(article_history) < 7:
        return "Недостаточно данных для анализа трендов"
    
    # Анализ недельных трендов
    weekly_sales = [day['sales'] for day in article_history[-7:]]
    avg_weekly_sales = sum(weekly_sales) / len(weekly_sales)
    weekly_trend = "📈 Растущий" if weekly_sales[-1] > weekly_sales[0] else "📉 Падающий"
    
    # Анализ волатильности
    volatility = max(weekly_sales) - min(weekly_sales)
    volatility_level = "Высокая" if volatility > avg_weekly_sales else "Низкая"
    
    # Прогноз на следующую неделю
    last_3_days = weekly_sales[-3:]
    forecast = sum(last_3_days) / 3
    
    return {
        "weekly_trend": weekly_trend,
        "avg_weekly_sales": int(avg_weekly_sales),
        "volatility": volatility_level,
        "forecast": int(forecast)
    }

def analyze_competition(article):
    """Анализирует конкурентную среду для товара"""
    # Здесь можно добавить парсинг конкурентов
    # Пока возвращаем заглушку
    return {
        "competitors_count": "Нет данных",
        "avg_price": "Нет данных",
        "market_share": "Нет данных"
    }

def get_extended_analysis(article):
    """Получает расширенный анализ товара"""
    history = load_sales_history()
    article_history = history.get(article, [])
    
    market_trends = analyze_market_trends(article_history)
    competition = analyze_competition(article)
    
    return {
        "market_analysis": market_trends,
        "competition_analysis": competition
    }

###############################################################################
# FastAPI и маршруты API

app = FastAPI(
    title="Whitesamurai Web App",
    description="Веб-интерфейс, реализующий функциональность Telegram-бота",
    version="1.0.0"
)

# Модель запроса для текстовых сообщений
class MessageRequest(BaseModel):
    user_id: int
    text: str

# Модель запроса для установки алерта
class AlertRequest(BaseModel):
    user_id: int
    article: str
    target_price: float

# Модель запроса для расширенного поиска
class SearchRequest(BaseModel):
    query: str
    max_results: int = 10
    include_social: bool = True
    include_news: bool = False
    include_images: bool = False

@app.on_event("startup")
def startup_event():
    init_db()
    print("База данных инициализирована.")

@app.get("/")
def root():
    return {"message": WELCOME_MESSAGE}

# Эндпойнт для обработки входящих текстовых сообщений
@app.post("/message")
async def process_message(msg: MessageRequest):
    user_id = msg.user_id
    text = msg.text.strip()
    # Если для пользователя установлено ожидание действия (pending_action)
    if user_id in pending_action:
        action = pending_action[user_id]["action"]
        # Обработка добавления артикула
        if action == "add":
            if add_article(user_id, text):
                response = f"✅ Артикул {escape_markdown(text)} успешно добавлен."
            else:
                response = f"⚠️ Артикул {escape_markdown(text)} уже отслеживается."
            pending_action.pop(user_id, None)
            return {"response": response}
        # Обработка удаления артикула
        elif action == "remove":
            remove_article(user_id, text)
            response = f"✅ Артикул {escape_markdown(text)} удалён."
            pending_action.pop(user_id, None)
            return {"response": response}
        # Глобальный поиск – пример асинхронного вызова
        elif action == "global":
            query = text
            loop = asyncio.get_event_loop()
            search_data = await loop.run_in_executor(None, global_search_serper_detailed, query)
            if search_data["error"]:
                response_text = search_data["error"]
            else:
                pending_action[user_id] = {
                    "action": "global",
                    "query": query,
                    "results": search_data["results"],
                    "last_displayed": 5
                }
                first_batch = pending_action[user_id]["results"][:5]
                response_text = format_site_results_from_items(first_batch)
            return {"response": response_text}
        # Анализ артикула
        elif action == "analysis_article":
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, get_wb_product_info, text)
            daily_sales = info.get("Продажи за сутки", 0)
            monthly_sales = daily_sales * 30
            yearly_sales = daily_sales * 365
            daily_profit_str = info.get("Прибыль за сутки", "0").replace("₽", "").strip()
            try:
                daily_profit = float(daily_profit_str)
            except:
                daily_profit = 0.0
            yearly_profit = daily_profit * 365
            try:
                price_str = info.get("Цена", "0").replace("₽", "").strip()
                price_value = float(price_str)
            except:
                price_value = 0.0
            if price_value > 0:
                profit_margin = daily_profit / price_value * 100
            else:
                profit_margin = 0
            if profit_margin < 5:
                probability_price_drop_value = 70
            elif profit_margin < 15:
                probability_price_drop_value = 40
            else:
                probability_price_drop_value = 10
            probability_price_drop = f"{probability_price_drop_value}%"
            target_daily = 100
            target_monthly = 2000
            target_half_year = 10000
            target_yearly = 18000
            potential_day_value = min((daily_sales / target_daily) * 100, 100)
            potential_month_value = min((monthly_sales / target_monthly) * 100, 100)
            potential_half_year_value = min(((yearly_sales / 2) / target_half_year) * 100, 100)
            potential_year_value = min((yearly_sales / target_yearly) * 100, 100)
            analysis_text = (
                f"*Анализ Артикула: {escape_markdown(text)}*\n\n"
                f"*Продажи:*\n"
                f"  • За сутки: {daily_sales}\n"
                f"  • За месяц: {monthly_sales}\n"
                f"  • За год: {yearly_sales}\n\n"
                f"*Потенциальная прибыль за следующий год:* {yearly_profit:.0f} ₽\n"
                f"*Вероятность падения цены на следующий год:* {probability_price_drop}\n\n"
                f"*Потенциал продаж:*\n"
                f"  • За сутки: {int(potential_day_value)}%\n"
                f"  • За месяц: {int(potential_month_value)}%\n"
                f"  • За полгода: {int(potential_half_year_value)}%\n"
                f"  • За год: {int(potential_year_value)}%\n"
            )
            pending_action.pop(user_id, None)
            return {"response": analysis_text}
        # Анализ категории
        elif action == "analysis_category":
            category = text
            sum_ascii = sum(ord(ch) for ch in category)
            current_success = (sum_ascii // 10) % 100
            forecast_success = min(current_success + 5, 100)
            analysis_result = (
                f"*Анализ Категорий: {escape_markdown(category)}*\n\n"
                f"Успешность категории сейчас: {current_success}%\n"
                f"Прогноз на следующий год: {forecast_success}% успешность"
            )
            pending_action.pop(user_id, None)
            return {"response": analysis_result}
        else:
            pending_action.pop(user_id, None)
            return {"response": "Непонятный ввод. Используйте API команды."}
    else:
        # Если нет ожидаемого действия, проверяем: если текст состоит только из цифр – считаем это запросом информации по товару
        if text.isdigit():
            if not user_has_subscription(user_id):
                return {"response": "У вас нет активной подписки!"}
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, get_wb_product_info, text)
            response_text = format_sales_info(info)
            return {"response": response_text}
        else:
            return {"response": "Пожалуйста, используйте API для отправки команд или запросов."}

# Эндпойнт для обработки callback-команд (эмулирует логику callback_query)
@app.post("/callback")
async def process_callback(user_id: int, callback_data: str):
    if callback_data == "back":
        pending_action.pop(user_id, None)
        return {"response": WELCOME_MESSAGE}
    elif callback_data == "menu_cabinet":
        balance, sub_until_str = get_user_info(user_id)
        sub_info = f"Активна до {sub_until_str}" if sub_until_str else "Отсутствует"
        text = (
            f"💼 *Личный кабинет*\n\n"
            f"Баланс: {balance:.2f} ₽\n"
            f"Подписка: {sub_info}\n\n"
            "Доступны команды: top_up, subscribe"
        )
        return {"response": text}
    elif callback_data == "top_up":
        pending_action[user_id] = {"action": "top_up_screenshot"}
        return {"response": "Отправьте скриншот оплаты (например, через эндпойнт /photo)."}
    elif callback_data == "subscribe":
        cost = 500
        balance, sub_until_str = get_user_info(user_id)
        if balance >= cost:
            new_balance = balance - cost
            update_user_balance(user_id, new_balance)
            new_sub_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
            update_user_subscription(user_id, new_sub_date)
            return {"response": f"Подписка успешно оформлена до {new_sub_date}! Остаток: {new_balance:.2f} ₽"}
        else:
            return {"response": f"Недостаточно средств. Нужно {cost} ₽. Баланс: {balance:.2f} ₽"}
    else:
        return {"response": "Команда не распознана."}

# Эндпойнт для установки алерта
@app.post("/set_alert")
async def set_price_alert(alert: AlertRequest):
    """Устанавливает алерт на цену для пользователя"""
    if not user_has_subscription(alert.user_id):
        raise HTTPException(status_code=403, detail="У вас нет активной подписки!")
    
    notification_system.set_price_alert(alert.user_id, alert.article, alert.target_price)
    return {"message": f"Алерт установлен на цену {alert.target_price} для артикула {alert.article}"}

# Эндпойнт для удаления алерта
@app.post("/remove_alert")
async def remove_price_alert(alert: AlertRequest):
    """Удаляет алерт на цену для пользователя"""
    notification_system.remove_price_alert(alert.user_id, alert.article)
    return {"message": f"Алерт удален для артикула {alert.article}"}

# Эндпойнт для получения расширенного анализа товара
@app.get("/extended_analysis/{article}")
async def get_article_analysis(article: str):
    """Получает расширенный анализ товара"""
    try:
        analysis = get_extended_analysis(article)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Эндпойнт для получения анализа рыночных трендов для товара
@app.get("/market_trends/{article}")
async def get_market_trends(article: str):
    """Получает анализ рыночных трендов для товара"""
    try:
        history = load_sales_history()
        article_history = history.get(article, [])
        trends = analyze_market_trends(article_history)
        return trends
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/recommendations/{article}")
async def get_product_recommendations(article: str, user_id: int):
    """Получает рекомендации для товара"""
    if not user_has_subscription(user_id):
        raise HTTPException(status_code=403, detail="У вас нет активной подписки!")
    
    try:
        recommendations = recommendation_system.get_recommendations(article, user_id)
        update_user_view_history(user_id, article)
        return recommendations
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/seasonality/{article}")
async def get_seasonality_analysis(article: str):
    """Получает анализ сезонности для товара"""
    try:
        analysis = seasonality_analyzer.predict_seasonal_trend(article)
        return analysis
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/combined_analysis/{article}")
async def get_combined_analysis(article: str, user_id: int):
    """Получает комплексный анализ товара"""
    try:
        # Получаем базовую информацию о товаре
        product_info = get_wb_product_info(article)
        
        # Получаем рекомендации
        recommendations = recommendation_system.get_recommendations(article, user_id)
        
        # Получаем анализ сезонности
        seasonality = seasonality_analyzer.predict_seasonal_trend(article)
        
        # Получаем рыночные тренды
        market_trends = analyze_market_trends(load_sales_history().get(article, []))
        
        return {
            "product_info": product_info,
            "recommendations": recommendations,
            "seasonality": seasonality,
            "market_trends": market_trends
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# Эндпойнт для выполнения расширенного поиска
@app.post("/search")
async def perform_search(search_request: SearchRequest):
    """Выполняет расширенный поиск через Serper.dev"""
    try:
        results = await global_search_serper_detailed(
            query=search_request.query,
            max_results=search_request.max_results,
            include_social=search_request.include_social,
            include_news=search_request.include_news,
            include_images=search_request.include_images
        )
        
        if "error" in results and results["error"]:
            raise HTTPException(status_code=500, detail=results["error"])
            
        return results
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/test_analysis/{article}")
async def test_analysis(article: str):
    """Тестовый эндпоинт для комплексного анализа товара"""
    try:
        # Получаем анализ карточки товара
        product_analysis = await product_card_analyzer.analyze_product(article)
        if "error" in product_analysis:
            return {"error": product_analysis["error"]}
        
        # Получаем анализ трендов
        trend_analysis = await trend_analyzer.analyze_trend(article)
        if "error" in trend_analysis:
            return {"error": trend_analysis["error"]}
        
        # Формируем комплексный отчет
        report = {
            "product_info": product_analysis["product_info"],
            "metrics": product_analysis["metrics"],
            "risk_analysis": product_analysis["risk_analysis"],
            "trend_analysis": trend_analysis["trend_analysis"],
            "seasonality_analysis": trend_analysis["seasonality_analysis"],
            "forecast": {
                "product": product_analysis["forecast"],
                "trend": trend_analysis["forecast"]
            }
        }
        
        return report
        
    except Exception as e:
        return {"error": str(e)}

###############################################################################
# Запуск сервера

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)

class NotificationSystem:
    def __init__(self):
        self.alerts = {}
    
    async def check_price_alerts(self, article, current_price):
        """Проверяет и отправляет уведомления о изменении цены"""
        if article in self.alerts:
            for user_id, alert_price in self.alerts[article].items():
                if current_price < alert_price:
                    # Здесь можно добавить отправку уведомления через Telegram
                    print(f"Alert: Price for article {article} dropped below {alert_price} for user {user_id}")
    
    def set_price_alert(self, user_id, article, target_price):
        """Устанавливает алерт на цену"""
        if article not in self.alerts:
            self.alerts[article] = {}
        self.alerts[article][user_id] = target_price
    
    def remove_price_alert(self, user_id, article):
        """Удаляет алерт на цену"""
        if article in self.alerts and user_id in self.alerts[article]:
            del self.alerts[article][user_id]

notification_system = NotificationSystem()

class RecommendationSystem:
    def __init__(self):
        self.similar_products = {}
    
    def find_similar_products(self, article, category):
        """Находит похожие товары на основе категории и характеристик"""
        # Здесь можно добавить более сложную логику поиска похожих товаров
        # Пока используем простой пример
        return {
            "similar_articles": [
                {"article": "123456", "similarity": 0.85},
                {"article": "789012", "similarity": 0.78},
                {"article": "345678", "similarity": 0.72}
            ]
        }
    
    def get_recommendations(self, article, user_id):
        """Получает персонализированные рекомендации для пользователя"""
        try:
            # Получаем информацию о товаре
            product_info = get_wb_product_info(article)
            category = product_info.get('category', 'unknown')
            
            # Получаем похожие товары
            similar = self.find_similar_products(article, category)
            
            # Получаем историю просмотров пользователя
            user_history = get_user_view_history(user_id)
            
            # Фильтруем рекомендации на основе истории
            filtered_recommendations = self.filter_by_user_history(similar, user_history)
            
            return {
                "status": "success",
                "recommendations": filtered_recommendations
            }
        except Exception as e:
            return {
                "status": "error",
                "message": str(e)
            }
    
    def filter_by_user_history(self, recommendations, user_history):
        """Фильтрует рекомендации на основе истории просмотров пользователя"""
        # Простая логика фильтрации
        return [rec for rec in recommendations['similar_articles'] 
                if rec['article'] not in user_history]

recommendation_system = RecommendationSystem()

def get_user_view_history(user_id):
    """Получает историю просмотров пользователя"""
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute("SELECT article FROM user_view_history WHERE user_id = ?", (user_id,))
    history = [row[0] for row in cur.fetchall()]
    conn.close()
    return history

def update_user_view_history(user_id, article):
    """Обновляет историю просмотров пользователя"""
    conn = sqlite3.connect('tracked_articles.db')
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO user_view_history (user_id, article, view_date) 
        VALUES (?, ?, ?)
    """, (user_id, article, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
    conn.commit()
    conn.close()

class SeasonalityAnalyzer:
    def __init__(self):
        self.seasonal_patterns = {}
    
    def analyze_seasonality(self, article_history):
        """Анализирует сезонность продаж на основе истории"""
        if len(article_history) < 30:
            return "Недостаточно данных для анализа сезонности"
        
        # Группируем продажи по месяцам
        monthly_sales = {}
        for record in article_history:
            date_obj = datetime.strptime(record['date'], "%Y-%m-%d")
            month = date_obj.month
            if month not in monthly_sales:
                monthly_sales[month] = []
            monthly_sales[month].append(record['sales'])
        
        # Вычисляем средние продажи по месяцам
        avg_monthly_sales = {
            month: sum(sales) / len(sales) 
            for month, sales in monthly_sales.items()
        }
        
        # Определяем сезонность
        max_month = max(avg_monthly_sales.items(), key=lambda x: x[1])[0]
        min_month = min(avg_monthly_sales.items(), key=lambda x: x[1])[0]
        
        # Вычисляем коэффициент сезонности
        seasonal_factor = avg_monthly_sales[max_month] / avg_monthly_sales[min_month]
        
        return {
            "peak_month": max_month,
            "low_month": min_month,
            "seasonal_factor": round(seasonal_factor, 2),
            "monthly_averages": avg_monthly_sales
        }
    
    def predict_seasonal_trend(self, article):
        """Прогнозирует сезонный тренд для товара"""
        history = load_sales_history()
        article_history = history.get(article, [])
        
        if len(article_history) < 30:
            return "Недостаточно данных для прогноза"
        
        seasonality = self.analyze_seasonality(article_history)
        current_month = datetime.now().month
        
        # Простой прогноз на основе сезонности
        if current_month == seasonality["peak_month"]:
            trend = "📈 Пик сезона"
        elif current_month == seasonality["low_month"]:
            trend = "📉 Низкий сезон"
        else:
            trend = "➡️ Средний сезон"
        
        return {
            "current_trend": trend,
            "seasonality_analysis": seasonality,
            "recommendation": self.get_seasonal_recommendation(seasonality)
        }
    
    def get_seasonal_recommendation(self, seasonality):
        """Генерирует рекомендации на основе сезонности"""
        current_month = datetime.now().month
        months_to_peak = (seasonality["peak_month"] - current_month) % 12
        
        if months_to_peak == 0:
            return "Сейчас пик сезона - оптимальное время для продаж"
        elif months_to_peak <= 3:
            return f"До пика сезона осталось {months_to_peak} месяцев - готовьтесь к росту спроса"
        else:
            return "Сейчас низкий сезон - рассмотрите возможность снижения цен"

seasonality_analyzer = SeasonalityAnalyzer()

class NicheAnalyzer:
    def __init__(self):
        self.cache = {}
        self.cache_timeout = 3600  # 1 час
        self._session = None
    
    @property
    def session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def analyze_niche(self, keyword: str):
        """Анализирует нишу по ключевому слову"""
        try:
            # Проверяем кэш
            cache_key = f"{keyword}"
            if cache_key in self.cache:
                timestamp, data = self.cache[cache_key]
                if time.time() - timestamp < self.cache_timeout:
                    return data
            
            # Получаем товары по ключевому слову
            products = await self.get_products_by_keyword(keyword)
            if not products:
                return {"error": "Не удалось найти товары по данному ключевому слову"}
            
            # Анализируем данные
            total_products = len(products)
            total_sales = sum(p['sales'] for p in products)
            avg_price = sum(p['price'] for p in products) / total_products if total_products > 0 else 0
            avg_rating = sum(p['rating'] for p in products) / total_products if total_products > 0 else 0
            
            # Рассчитываем конкуренцию
            competition_level = "Высокая" if total_products > 100 else "Средняя" if total_products > 50 else "Низкая"
            
            # Оцениваем потенциал ниши
            market_volume = total_sales * avg_price
            potential = "Высокий" if market_volume > 1000000 else "Средний" if market_volume > 500000 else "Низкий"
            
            # Формируем рекомендации
            recommendations = []
            if competition_level == "Высокая":
                recommendations.append("Рекомендуется искать менее конкурентную нишу")
            if avg_rating < 4:
                recommendations.append("Есть возможность выйти на рынок с более качественным товаром")
            if market_volume > 1000000:
                recommendations.append("Высокий потенциал для входа в нишу при наличии качественного товара")
            
            analysis = {
                "metrics": {
                    "market_volume": market_volume,
                    "competition": competition_level,
                    "products_count": total_products,
                    "avg_price": avg_price,
                    "avg_rating": avg_rating
                },
                "trends": {
                    "sales_trend": "Растущий" if total_sales > 1000 else "Стабильный",
                    "potential": potential
                },
                "risks": [
                    "Высокая конкуренция" if competition_level == "Высокая" else "Низкий спрос" if total_sales < 100 else "Умеренные риски"
                ],
                "recommendations": recommendations
            }
            
            # Сохраняем в кэш
            self.cache[cache_key] = (time.time(), analysis)
            return analysis
            
        except Exception as e:
            return {"error": str(e)}
    
    async def get_products_by_keyword(self, keyword: str, min_sales: int = 0, max_competition: float = 1.0, min_margin: int = 0) -> List[Dict]:
        """Поиск товаров по ключевому слову с фильтрацией"""
        try:
            # Формируем URL для поиска
            url = f"https://search.wb.ru/exactmatch/ru/common/v4/search?TestGroup=no_test&TestID=no_test&appType=1&curr=rub&dest=-1257786&query={keyword}&resultset=catalog&sort=popular&spp=0"
            
            async with self.session.get(url) as response:
                if response.status != 200:
                    return []
                
                data = await response.json()
                products = data.get('data', {}).get('products', [])
                
                # Фильтруем товары по заданным критериям
                filtered_products = []
                for product in products:
                    sales = product.get('salePriceU', 0) / 100
                    price = product.get('priceU', 0) / 100
                    rating = product.get('rating', 0)
                    
                    # Рассчитываем конкуренцию (упрощенно)
                    competition = len(products) / 1000  # Нормализуем к диапазону 0-1
                    
                    # Рассчитываем маржинальность (упрощенно)
                    margin = (price - sales) / price * 100 if price > 0 else 0
                    
                    if (sales >= min_sales and 
                        competition <= max_competition and 
                        margin >= min_margin):
                        filtered_products.append({
                            'id': product.get('id'),
                            'name': product.get('name'),
                            'sales': sales,
                            'price': price,
                            'rating': rating,
                            'competition': competition,
                            'margin': margin
                        })
                
                return filtered_products
        except Exception as e:
            logger.error(f"Error searching products: {e}")
            return []

class ProductCardAnalyzer:
    """Класс для анализа карточки товара."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def analyze_product(self, article):
        """Анализирует товар по артикулу."""
        self.logger.info(f"Analyzing product with article {article}")
        try:
            # Заглушка для демонстрации
            return {
                "article": article,
                "name": f"Товар {article}",
                "price": random.randint(500, 5000),
                "rating": random.uniform(3.5, 5.0),
                "feedbacks": random.randint(10, 1000),
                "sales": {
                    "today": random.randint(1, 100),
                    "total": random.randint(100, 10000)
                }
            }
        except Exception as e:
            self.logger.error(f"Error analyzing product: {str(e)}")
            return None

class TrendAnalyzer:
    """Класс для анализа трендов."""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    async def analyze_trend(self, keyword):
        """Анализирует тренд по ключевому слову."""
        self.logger.info(f"Analyzing trend for keyword {keyword}")
        try:
            # Заглушка для демонстрации
            return {
                "keyword": keyword,
                "popularity": random.randint(1, 100),
                "growth": random.uniform(-10.0, 30.0),
                "competition": random.randint(1, 100),
                "sales_potential": random.randint(1, 5)
            }
        except Exception as e:
            self.logger.error(f"Error analyzing trend: {str(e)}")
            return None
