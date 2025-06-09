import re
import os
import json
import sqlite3
import asyncio
import requests
from datetime import date, datetime, timedelta

# aiogram v3
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.client.bot import DefaultBotProperties
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatAction

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
# Константы/настройки

BOT_TOKEN = "7774315895:AAFVVUfSBOw3t7WjGTM6KHFK160TveSGheA"
SERPER_API_KEY = "8ba851ed7ae1e6a655102bea15d73fdb39cdac79"  # ключ для serper.dev

ADMIN_ID = 1659228199  # ID администратора

WELCOME_MESSAGE = (
    "👋 *Добро пожаловать в WHITESAMURAI!*\n\n"
    "Мы — профессиональная компания, которая помогает отслеживать продажи товаров "
    "и анализировать динамику 📊.\n\n"
    "Выберите нужное действие из меню ниже:"
)

###############################################################################
# Утилита для экранирования Markdown

def escape_markdown(text: str) -> str:
    if not text:
        return ""
    escape_chars = r'_*[]()~`>#+-=|{}.!'
    return re.sub(f'([{re.escape(escape_chars)}])', r'\\\1', text)

###############################################################################
# База данных (SQLite) – пользователи, баланс, подписка, артикулы

def extract_site(block: str) -> str:
    """
    Извлекает название сайта из строки вида "Сайт: …" в блоке.
    Если не найдено, возвращает "Неизвестно".
    """
    m = re.search(r'Сайт:\s*([^\n]+)', block, re.IGNORECASE)
    if m:
        site = m.group(1).strip()
        # Убираем обратные слеши, если они есть
        return site.replace('\\', '')
    return "Неизвестно"


def compute_additional_metrics(likes: int,
                               views: int,
                               approx_clients: int,
                               revenue: float,
                               growth_percent: float,
                               price: float = 500.0) -> dict:
    """
    Считает дополнительные метрики:
      1) Рейтинг блогера (от 1 до 5) на основе likes, revenue, growth_percent.
      2) Прирост заказов за 3 дня (27% от суммы лайков и просмотров).
      3) Прирост в рублях = (прирост заказов за 3 дня) * (цена товара).
      4) Средний чек = цена товара.
      5) Количество заказов = (approx_clients + 1).

    Параметры:
      likes: число лайков (из snippet).
      views: число просмотров/комментариев (из snippet).
      approx_clients: «примерно клиентов» (из estimate_impact).
      revenue: примерная выручка (из estimate_impact).
      growth_percent: рост продаж в процентах (из estimate_impact).
      price: цена товара (если не из snippet, задаём по умолчанию 500).

    Возвращает словарь с ключами:
      - rating (int) – рейтинг блогера от 1 до 5.
      - three_day_orders (int) – прирост заказов за 3 дня.
      - three_day_growth_rub (float) – прирост в рублях.
      - avg_check (float) – средний чек.
      - total_orders (int) – итоговое количество заказов.
    """

    # (1) Вычисляем рейтинг блогера (от 1 до 5).
    # Пример простого алгоритма: формируем некий «базовый скор» из likes, revenue, growth_percent.
    # Затем переводим скор в рейтинг 1..5.
    base_score = (likes * 0.1) + (revenue * 0.01) + growth_percent
    # Ограничим базовый скор максимум 100
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

    # (2) Прирост заказов за 3 дня: 27% от (likes + views).
    three_day_orders = int(0.27 * (likes + views))

    # (3) Прирост в рублях = (прирост заказов за 3 дня) * (цена товара).
    three_day_growth_rub = three_day_orders * price

    # (4) Средний чек = цена товара.
    avg_check = price

    # (5) Количество заказов = (approx_clients + 1).
    total_orders = approx_clients + 1

    return {
        "rating": rating,
        "three_day_orders": three_day_orders,
        "three_day_growth_rub": three_day_growth_rub,
        "avg_check": avg_check,
        "total_orders": total_orders
    }


def format_site_results_from_items(items: list) -> str:
    lines = []
    for item in items:
        title = item.get("title", "Нет заголовка")
        link = item.get("link", "")
        snippet = item.get("snippet", "")

        # Извлекаем лайки и просмотры
        likes, views = extract_likes_views(snippet)

        # Считаем примерное число клиентов, выручку и рост продаж
        approx_clients, approx_revenue, growth = estimate_impact(likes, views)

        # Цена товара: если у вас нет реальной цены, оставим 500 по умолчанию
        # Или же, если item содержит price, используем его:
        price = 500.0

        # Вызываем нашу новую функцию:
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

        # Формируем кликабельный заголовок
        clickable_title = f"[{escape_markdown(title)}]({link})" if link else escape_markdown(title)

        # Домен сайта (или "Неизвестно")
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


def format_site_results(text: str) -> str:
    """
    Разбивает входной текст (результаты поиска) на блоки по пустым строкам.
    Для каждого блока, в котором содержится информация о лайках/комментариях,
    извлекает название сайта, лайки и комментарии (как proxy для просмотров),
    рассчитывает приблизительное число клиентов, выручку и рост продаж,
    и формирует итоговое сообщение.
    """
    blocks = [b.strip() for b in re.split(r'\n\s*\n', text) if b.strip()]
    lines = []
    for block in blocks:
        # Обрабатываем только блоки, где есть информация по лайкам/комментариям
        if re.search(r'likes|comments|лайки|комментар', block, re.IGNORECASE):
            site = extract_site(block)
            likes, views = extract_likes_views(block)
            # Если и лайки, и просмотры равны нулю, подставляем минимальные значения для расчёта
            clients, revenue, growth = estimate_impact(likes, views)
            block_text = (
                f"🌐 Сайт: {site}\n"
                f"👍 Лайки: {likes}, 👀 Просмотры: {views}\n"
                f"👥 Примерно клиентов: {clients}, Выручка ~ {revenue}₽\n"
                f"📈 Рост продаж ~ {growth:.1f}%"
            )
            lines.append(block_text)
    return "\n\n".join(lines)

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
    # Таблица пользователей (balance, subscription_until)
    cur.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            balance REAL DEFAULT 0,
            subscription_until TEXT DEFAULT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_user_info(user_id):
    """
    Возвращает (balance, subscription_until).
    Для ADMIN_ID возвращаем (777777, None).
    """
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
# Накопление данных о продажах (sales_history.json)

def load_sales_history():
    return {}

def update_sales_history(article, sales_today):
    return []

def compute_sales_trend(article_history):
    return "Нет данных"

###############################################################################
# Парсинг Wildberries и дополнительные функции

def get_extended_sales_data(driver):
    extended_sales = {"sale_month": 0, "sale_week": 0}
    try:
        button = driver.find_element(By.XPATH, "//*[contains(text(), 'Подробнее')]")
        driver.execute_script("arguments[0].click();", button)
        WebDriverWait(driver, 5).until(
            lambda d: button not in d.find_elements(By.XPATH, "//*[contains(text(), 'Подробнее')]")
        )
    except:
        pass

    try:
        month_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'за месяц') or contains(text(), '30 дней')]")
        for element in month_elements:
            text = element.text
            match = re.search(r'(\d+)', text)
            if match:
                extended_sales["sale_month"] = int(match.group(1))
                break
    except:
        pass

    try:
        week_elements = driver.find_elements(By.XPATH, "//*[contains(text(), 'за 7 дней') or contains(text(), 'неделя')]")
        for element in week_elements:
            text = element.text
            match = re.search(r'(\d+)', text)
            if match:
                extended_sales["sale_week"] = int(match.group(1))
                break
    except:
        pass
    return extended_sales

def try_find_price_by_selectors(driver, selectors):
    for sel_type, sel_value in selectors:
        try:
            element = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((sel_type, sel_value))
            )
            text = element.text.strip()
            if text:
                print(f"DEBUG: Найдена цена по {sel_type}={sel_value}: {text}")
                return text
        except Exception as e:
            print(f"DEBUG: Не нашли {sel_type}={sel_value}:", e)
    return None

def get_product_page_data(driver):
    data = {}
    try:
        title_element = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.CLASS_NAME, "product-page__header"))
        )
        data["title"] = title_element.text.strip()
    except:
        data["title"] = "Не найдено"

    price_selectors = [
        (By.CLASS_NAME, "price-block__final-price"),
        (By.XPATH, "//span[contains(@class, 'price-block__final-price')]"),
        (By.CLASS_NAME, "price-block__accent-price"),
        (By.XPATH, "//span[contains(@class, 'price-block__accent-price')]"),
    ]
    price_text = try_find_price_by_selectors(driver, price_selectors)
    if price_text:
        clean = price_text.replace(" ", "").replace("\n", "")
        clean = re.sub(r"[₾₽₴₸]", "", clean)
        clean = clean.replace(",", ".")
        try:
            data["price"] = int(float(clean))
        except:
            data["price"] = 0
    else:
        data["price"] = 0

    try:
        reviews_element = WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.CLASS_NAME, "product-review__count-review"))
        )
        data["reviews"] = reviews_element.text.strip()
    except:
        data["reviews"] = "Нет отзывов"

    data.update(get_extended_sales_data(driver))
    return data

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
    url = f"https://www.wildberries.ru/catalog/{article}/detail.aspx"
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                         "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36")

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get(url)
        page_data = get_product_page_data(driver)
    except:
        page_data = {"title": "Ошибка", "price": 0, "reviews": "Нет"}
    finally:
        driver.quit()

    api_data = get_api_data(article, page_data.get("price", 0))
    daily_sales = api_data.get("sales_today", 0)

    factor_week = 0.8
    factor_month = 0.7
    parsed_week = page_data.get("sale_week", 0)
    parsed_month = page_data.get("sale_month", 0)

    if parsed_week == 0:
        estimated_week = int(daily_sales * 7 * factor_week)
    else:
        estimated_week = parsed_week

    if parsed_month == 0:
        estimated_month = int(daily_sales * 30 * factor_month)
    else:
        estimated_month = parsed_month

    price = page_data.get("price", 0)
    estimated_week_revenue = estimated_week * price
    estimated_month_revenue = estimated_month * price
    commission = 0.15
    estimated_week_profit = estimated_week_revenue * (1 - commission)
    estimated_month_profit = estimated_month_revenue * (1 - commission)

    article_history = update_sales_history(article, daily_sales)
    sales_trend = compute_sales_trend(article_history)

    result = {
        "Название": page_data.get("title", "Нет данных"),
        "Цена": f'{price} ₽',
        "Отзывы": page_data.get("reviews", "Нет отзывов"),
        "Продажи за сутки": daily_sales,
        "Приблизительные продажи за неделю": estimated_week,
        "Приблизительные продажи за месяц": estimated_month,
        "Выручка за сутки": f'{api_data.get("revenue_today", 0)} ₽',
        "Прибыль за сутки": f'{api_data.get("profit_today", 0):.0f} ₽',
        "Выручка за неделю (приблизительно)": f'{estimated_week_revenue} ₽',
        "Прибыль за неделю (приблизительно)": f'{estimated_week_profit:.0f} ₽',
        "Выручка за месяц (приблизительно)": f'{estimated_month_revenue} ₽',
        "Прибыль за месяц (приблизительно)": f'{estimated_month_profit:.0f} ₽',
        "Динамика продаж (по предыдущему дню)": sales_trend
    }
    return result

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
# Улучшенный поиск Serper.dev с лайками/просмотрами (оставляем без изменений)

import re

def extract_likes_views(block: str):
    """
    Извлекает из блока (одной записи) количество лайков и комментариев (как proxy для просмотров).
    Сначала ищет шаблон "X likes, Y comments". Если найден – возвращает (X, Y),
    иначе пытается искать по отдельности.
    """
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


def process_text(text: str):
    """
    Разбивает входной текст (результаты поиска) на блоки по пустым строкам
    и для каждого блока, где встречаются слова "likes" или "comments" (или их русские аналоги),
    извлекает кортеж (likes, views) с помощью extract_likes_views.
    Возвращает список кортежей.
    """
    blocks = [b.strip() for b in re.split(r'\n\s*\n', text) if b.strip()]
    results = []
    for block in blocks:
        if re.search(r'likes|comments|лайки|комментар', block, re.IGNORECASE):
            results.append(extract_likes_views(block))
        else:
            results.append((0, 0))
    return results


def format_results_message(results):
    """
    Формирует итоговое сообщение из списка кортежей (likes, views).
    Каждая запись будет выглядеть, например:
    "Блок 2: Лайки: 110, Комментарии (просмотры): 8"
    """
    lines = []
    for idx, (likes, views) in enumerate(results, start=1):
        lines.append(f"Блок {idx}: Лайки: {likes}, Комментарии (просмотры): {views}")
    return "\n".join(lines)







def estimate_impact(likes, views):
    # Если лайков и просмотров нет, задаем минимальные значения для расчета
    if likes == 0 and views == 0:
        likes = 10
        views = 100
    approx_clients = int(likes * 0.1 + views * 0.05)
    avg_check = 500  # Средний чек (можно изменить под реальные данные)
    approx_revenue = approx_clients * avg_check
    baseline = 10000
    growth_percent = (approx_revenue / baseline) * 100 if baseline else 0
    return approx_clients, approx_revenue, growth_percent


def global_search_serper_detailed(query: str):
    url = "https://google.serper.dev/search"
    payload = {"q": query, "gl": "ru", "hl": "ru"}
    headers = {
        "X-API-KEY": SERPER_API_KEY,
        "Content-Type": "application/json"
    }
    resp = requests.post(url, headers=headers, json=payload)
    if resp.status_code != 200:
        return {"error": f"Ошибка serper.dev: {resp.status_code}", "results": []}
    data = resp.json()
    organic = data.get("organic", [])

    # Разрешённые домены социальных сетей
    allowed_domains = ["vk.com", "instagram.com", "t.me", "facebook.com", "twitter.com", "x.com"]
    filtered_results = []
    for item in organic:
        link = item.get("link", "")
        # Исключаем ссылки, связанные с wildberries
        if "wildberries" in link.lower():
            continue
        domain = re.sub(r'^https?://(www\.)?', '', link).split('/')[0].lower()
        if any(allowed_domain in domain for allowed_domain in allowed_domains):
            filtered_results.append(item)
    if not filtered_results:
        return {
            "error": (
                "Мы провели тщательный анализ по следующим социальным сетям: VK, Instagram, Telegram, Facebook, X и Twitter. "
                "На основе полученных данных не обнаружено ни одного случая использования данного товара в рекламных целях. "
                "Это может свидетельствовать о том, что товар продвигается органически, без агрессивных маркетинговых кампаний, "
                "что зачастую является признаком высокого уровня доверия со стороны аудитории и стабильного спроса."
            ),
            "results": []
        }
    # Возвращаем все найденные результаты для последующей пагинации
    return {"error": None, "results": filtered_results}

    out = {"error": None, "results": []}

    for item in filtered_results:
        title = item.get("title", "Нет заголовка")
        link = item.get("link", "")
        snippet = item.get("snippet", "")

        # Пример: получаем лайки/просмотры
        likes, views = parse_likes_and_views(snippet)

        # Допустим, мы хотим рейтинг блогера (пока как заглушку):
        blogger_rating = 10  # или рассчитываем на основе каких-то данных

        # Допустим, средний прирост заказов за 3 дня:
        # можно взять growth_percent, который у нас уже есть, и переименовать
        # или завести свою логику (заглушка 150%):
        three_day_growth_percent = 150

        # Средний прирост в рублях (заглушка):
        three_day_growth_rub = 1000

        # Средний чек (можно взять avg_check, который используем в estimate_impact)
        avg_check = 500

        # Количество заказов, шт (пока заглушка)
        orders_qty = 50

        # Или берем наши клиенты/выручку из estimate_impact:
        approx_clients, approx_revenue, growth = estimate_impact(likes, views)

        out["results"].append({
            "title": title,
            "link": link,
            "snippet": snippet,
            "rating": blogger_rating,  # Новое поле
            "three_day_growth_percent": three_day_growth_percent,
            "three_day_growth_rub": three_day_growth_rub,
            "avg_check": avg_check,
            "orders_qty": orders_qty,
            # Старые поля
            "likes": likes,
            "views": views,
            "approx_clients": approx_clients,
            "approx_revenue": approx_revenue,
            "growth_percent": growth
        })
    return out

def format_serper_results_detailed(search_data):
    """Форматирует список результатов в текст для отправки пользователю."""
    if search_data["error"]:
        return search_data["error"]
    out_text = ""
    for r in search_data["results"]:
        title_md = escape_markdown(r.get("title", "Нет заголовка"))
        link_md = escape_markdown(r.get("link", ""))
        snippet_md = escape_markdown(r.get("snippet", ""))
        # Если ключ 'site' отсутствует, извлекаем домен из ссылки
        site_val = r.get("site")
        if not site_val:
            site_val = re.sub(r'^https?://(www\.)?', '', r.get("link", "Неизвестно")).split('/')[0]
        site_md = escape_markdown(site_val)
        likes = r.get("likes", 0)
        views = r.get("views", 0)
        clients = r.get("approx_clients", 0)
        revenue = r.get("approx_revenue", 0)
        growth = r.get("growth_percent", 0)
        out_text += (
            f"🔗 [{title_md}]({link_md})\n"
            f"🌐 Сайт: {site_md}\n"
            f"💬 {snippet_md}\n"
            f"👍 Лайки: {likes}, 👀 Просмотры: {views}\n"
            f"👥 Примерно клиентов: {clients}, Выручка ~ {revenue}₽\n"
            f"📈 Рост продаж ~ {growth:.1f}%\n\n"
        )
    return out_text.strip()
###############################################################################
# Telegram-бот

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode="Markdown"))
dp = Dispatcher()

def back_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    return kb

def main_menu_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить артикул", callback_data="menu_add")],
        [InlineKeyboardButton(text="➖ Удалить артикул", callback_data="menu_remove")],
        [InlineKeyboardButton(text="📋 Список артикулов", callback_data="menu_list")],
        [InlineKeyboardButton(text="📈 Ежедневный отчёт", callback_data="menu_daily")],
        [InlineKeyboardButton(text="🌐 Глобальный поиск", callback_data="menu_global")],
        [InlineKeyboardButton(text="💼 Личный кабинет", callback_data="menu_cabinet")],
        [InlineKeyboardButton(text="🔍 Анализ", callback_data="analysis")]
    ])
    return kb

def analysis_menu_kb():
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Анализ Артикула", callback_data="analysis_article")],
        [InlineKeyboardButton(text="Анализ Бренда", callback_data="analysis_brand")],
        [InlineKeyboardButton(text="Анализ Поставщика", callback_data="analysis_supplier")],
        [InlineKeyboardButton(text="Анализ Категорий", callback_data="analysis_category")],
        [InlineKeyboardButton(text="Анализ Характеристик", callback_data="analysis_characteristics")],
        [InlineKeyboardButton(text="Анализ Топа поиска", callback_data="analysis_top_search")],
        [InlineKeyboardButton(text="Частотность Артикула", callback_data="analysis_frequency")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])
    return kb

pending_action = {}

@dp.message(Command("start"))
async def start_handler(message: types.Message):
    await message.answer(WELCOME_MESSAGE, reply_markup=main_menu_kb())

@dp.callback_query()
async def callback_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    data = callback.data

    if data == "back":
        await callback.message.edit_text(WELCOME_MESSAGE, reply_markup=main_menu_kb())

    elif data == "menu_cabinet":
        balance, sub_until_str = get_user_info(user_id)
        sub_info = f"Активна до {sub_until_str}" if sub_until_str else "Отсутствует"
        text = (
            f"💼 *Личный кабинет*\n\n"
            f"Баланс: {balance:.2f} ₽\n"
            f"Подписка: {sub_info}\n\n"
            "Выберите действие:"
        )
        await callback.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Пополнить баланс", callback_data="top_up")],
            [InlineKeyboardButton(text="Оформить подписку", callback_data="subscribe")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
        ]))

    elif data == "top_up":
        pending_action[user_id] = {"action": "top_up_screenshot"}
        await callback.message.edit_text(
            "Отправьте скриншот оплаты (СБП и т.д.). После проверки администратором баланс будет пополнен.",
            reply_markup=back_kb()
        )

    elif data == "subscribe":
        cost = 500
        balance, sub_until_str = get_user_info(user_id)
        if balance >= cost:
            new_balance = balance - cost
            update_user_balance(user_id, new_balance)
            new_sub_date = (date.today() + timedelta(days=30)).strftime("%Y-%m-%d")
            update_user_subscription(user_id, new_sub_date)
            await callback.message.edit_text(
                f"Подписка успешно оформлена до {new_sub_date}!\nОстаток на счёте: {new_balance:.2f} ₽",
                reply_markup=back_kb()
            )
        else:
            await callback.message.edit_text(
                f"Недостаточно средств. Нужно {cost} ₽. Баланс: {balance:.2f} ₽",
                reply_markup=back_kb()
            )

    # Основные пункты меню (добавление, удаление, список, отчёт, глобальный поиск)
    elif data in ["menu_add", "menu_remove", "menu_list", "menu_daily", "menu_global"]:
        if not user_has_subscription(user_id):
            await callback.answer("У вас нет активной подписки! Оформите подписку в личном кабинете.")
            return

        if data == "menu_add":
            pending_action[user_id] = {"action": "add"}
            await callback.message.edit_text("Введите артикул для добавления:", reply_markup=back_kb())

        elif data == "menu_remove":
            pending_action[user_id] = {"action": "remove"}
            await callback.message.edit_text("Введите артикул для удаления:", reply_markup=back_kb())

        elif data == "menu_list":
            articles = list_articles(user_id)
            if articles:
                text = "📋 *Отслеживаемые артикулы:*\n" + "\n".join(escape_markdown(a) for a in articles)
            else:
                text = "У вас нет отслеживаемых артикулов."
            await callback.message.edit_text(text, reply_markup=back_kb())

        elif data == "menu_daily":
            await callback.message.edit_text("⏳ Получаем данные, пожалуйста, подождите...")
            await bot.send_chat_action(callback.message.chat.id, action=ChatAction.TYPING)
            articles = list_articles(user_id)
            if not articles:
                text = "У вас нет отслеживаемых артикулов. Добавьте их кнопкой \"Добавить артикул\"."
            else:
                text = ""
                for art in articles:
                    loop = asyncio.get_event_loop()
                    info = await loop.run_in_executor(None, get_wb_product_info, art)
                    text += f"🔢 *Артикул:* {escape_markdown(art)}\n{format_sales_info(info)}\n"
            await callback.message.edit_text(text, reply_markup=back_kb())

        elif data == "menu_global":
            pending_action[user_id] = {"action": "global"}
            await callback.message.edit_text("Введите запрос для глобального поиска:", reply_markup=back_kb())

    # Новое подменю "Анализ"
    elif data == "analysis":
        await callback.message.edit_text("Выберите тип анализа:", reply_markup=analysis_menu_kb())

    elif data == "analysis_article":
        if not user_has_subscription(user_id):
            await callback.answer("У вас нет активной подписки! Оформите подписку в личном кабинете.")
            return
        pending_action[user_id] = {"action": "analysis_article"}
        await callback.message.edit_text("Введите артикул для анализа:", reply_markup=back_kb())

    elif data == "analysis_brand":
        # Изменяем заглушку на перенаправление к новому боту для анализа бренда
        pending_action[user_id] = {"action": "analysis_brand"}
        await callback.message.edit_text(
            "Введите название бренда для анализа:", 
            reply_markup=back_kb()
        )

    elif data == "analysis_supplier":
        await callback.message.edit_text("Функция 'Анализ Поставщика' пока в разработке (заглушка).", reply_markup=back_kb())

    elif data == "analysis_category":
        pending_action[user_id] = {"action": "analysis_category"}
        await callback.message.edit_text("Введите название категории для анализа:", reply_markup=back_kb())

    elif data == "analysis_characteristics":
        await callback.message.edit_text("Функция 'Анализ Характеристик' пока в разработке (заглушка).", reply_markup=back_kb())

    elif data == "analysis_top_search":
        await callback.message.edit_text("Функция 'Анализ Топа поиска' пока в разработке (заглушка).", reply_markup=back_kb())

    elif data == "analysis_frequency":
        await callback.message.edit_text("Функция 'Частотность Артикула' пока в разработке (заглушка).", reply_markup=back_kb())

###############################################################################
# Обработка фото (скриншотов для пополнения)

@dp.message(F.photo)
async def photo_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id in pending_action and pending_action[user_id].get("action") == "top_up_screenshot":
        await message.forward(ADMIN_ID)
        await message.answer("Скриншот отправлен администратору на проверку. Ожидайте!")
        pending_action[user_id]["action"] = "top_up_wait_admin"
    else:
        await message.answer("Фото получено, но сейчас оно не требуется. Если хотите пополнить баланс, нажмите 'Пополнить баланс'.")

###############################################################################
# Обработка текстовых сообщений

@dp.message()
async def text_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id in pending_action:
        action = pending_action[user_id]["action"]

        if user_id in pending_action and pending_action[user_id].get("action") == "global":
            query = message.text.strip()
            await message.answer("⏳ Выполняется расширенный поиск, подождите...")
            await bot.send_chat_action(message.chat.id, action=ChatAction.TYPING)
            loop = asyncio.get_event_loop()
            search_data = await loop.run_in_executor(None, global_search_serper_detailed, query)
            if search_data["error"]:
                text = search_data["error"]
                inline_kb = None
            else:
                pending_action[user_id] = {
                    "action": "global",
                    "query": query,
                    "results": search_data["results"],
                    "last_displayed": 0
                }
                first_batch = pending_action[user_id]["results"][:5]
                text = format_site_results_from_items(first_batch)
                pending_action[user_id]["last_displayed"] = len(first_batch)
                inline_kb = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Еще поиск", callback_data="more_search")],
                    [InlineKeyboardButton(text="Поставить слежение", callback_data="set_tracking")]
                ])
            await message.answer(text, reply_markup=inline_kb)
            # Удаляем вызов pending_action.pop(user_id, None)
            return

        elif action == "add":
            article = message.text.strip()
            if add_article(user_id, article):
                response = f"✅ Артикул *{escape_markdown(article)}* успешно добавлен."
            else:
                response = f"⚠️ Артикул *{escape_markdown(article)}* уже отслеживается."
            pending_action.pop(user_id, None)
            await message.answer(response, reply_markup=main_menu_kb())

        elif action == "remove":
            article = message.text.strip()
            remove_article(user_id, article)
            response = f"✅ Артикул *{escape_markdown(article)}* удалён."
            pending_action.pop(user_id, None)
            await message.answer(response, reply_markup=main_menu_kb())

        elif action == "top_up_wait_admin":
            await message.answer("Ожидайте проверки администратором.")

        elif action == "analysis_brand":
            brand_name = message.text.strip()
            await message.answer(f"⏳ Анализирую бренд {brand_name}, это может занять некоторое время...")
            
            # Здесь мы переадресуем запрос на анализ бренда в новую функцию
            try:
                # Импортируем необходимые функции из brand_analysis.py
                from brand_analysis import get_brand_info, format_brand_analysis
                from product_data_formatter import generate_brand_charts
                
                # Получаем информацию о бренде
                brand_info = await get_brand_info(brand_name)
                
                if not brand_info:
                    await message.answer("❌ Не удалось получить информацию о бренде. Проверьте название и попробуйте ещё раз.", reply_markup=back_kb())
                    pending_action.pop(user_id, None)
                    return
                
                # Форматируем результаты
                result = format_brand_analysis(brand_info)
                
                # Создаем объект для отправки в функцию генерации графиков
                product_info = {"brand_info": brand_info}
                
                # Генерируем графики бренда
                brand_chart_paths = generate_brand_charts(product_info)
                
                # Отправляем результаты
                await message.answer(result, reply_markup=back_kb())
                
                # Словарь с описаниями графиков бренда
                brand_chart_descriptions = {
                    'brand_sales_chart': "📈 Динамика продаж бренда — изменение объема продаж и выручки по дням",
                    'brand_competitors_chart': "🥊 Сравнение с конкурентами — сопоставление по количеству товаров и продажам",
                    'brand_categories_chart': "📁 Распределение по категориям — показывает долю товаров бренда в разных категориях"
                }
                
                # Отправляем графики бренда, если они есть
                if brand_chart_paths:
                    await message.answer("📊 ГРАФИКИ ПО БРЕНДУ:", reply_markup=back_kb())
                    
                    for chart_path in brand_chart_paths:
                        chart_name = chart_path.replace('.png', '')
                        caption = brand_chart_descriptions.get(chart_name, f"График: {chart_name}")
                        
                        with open(chart_path, 'rb') as photo:
                            await message.answer_photo(photo, caption=caption)
                
            except Exception as e:
                logger.error(f"Ошибка при анализе бренда: {str(e)}", exc_info=True)
                await message.answer(f"❌ Произошла ошибка при анализе бренда: {str(e)}", reply_markup=back_kb())
            
            pending_action.pop(user_id, None)
            return

        elif action == "analysis_article":
            article = message.text.strip()
            await message.answer("⏳ Выполняется анализ артикула, подождите...")
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, get_wb_product_info, article)
            daily_sales = info.get("Продажи за сутки", 0)
            monthly_sales = daily_sales * 30
            yearly_sales = daily_sales * 365
            daily_profit_str = info.get("Прибыль за сутки", "0").replace("₽", "").strip()
            try:
                daily_profit = float(daily_profit_str)
            except:
                daily_profit = 0.0
            yearly_profit = daily_profit * 365
            # Расчёт вероятности падения цены на основе маржи (прибыли относительно цены)
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
            # Расчёт потенциала продаж с использованием различных целевых значений
            target_daily = 100  # Целевые продажи в день
            target_monthly = 2000  # Целевые продажи в месяц
            target_half_year = 10000  # Целевые продажи за полгода
            target_yearly = 18000  # Целевые продажи за год
            potential_day_value = min((daily_sales / target_daily) * 100, 100)
            potential_month_value = min((monthly_sales / target_monthly) * 100, 100)
            potential_half_year_value = min(((yearly_sales / 2) / target_half_year) * 100, 100)
            potential_year_value = min((yearly_sales / target_yearly) * 100, 100)
            potential_day = f"{int(potential_day_value)}%"
            potential_month = f"{int(potential_month_value)}%"
            potential_half_year = f"{int(potential_half_year_value)}%"
            potential_year = f"{int(potential_year_value)}%"
            analysis_text = (
                f"*Анализ Артикула: {escape_markdown(article)}*\n\n"
                f"*Продажи:*\n"
                f"  • За сутки: {daily_sales}\n"
                f"  • За месяц: {monthly_sales}\n"
                f"  • За год: {yearly_sales}\n\n"
                f"*Потенциальная прибыль за следующий год:* {yearly_profit:.0f} ₽\n"
                f"*Вероятность падения цены на следующий год:* {probability_price_drop}\n\n"
                f"*Потенциал продаж:*\n"
                f"  • За сутки: {potential_day}\n"
                f"  • За месяц: {potential_month}\n"
                f"  • За полгода: {potential_half_year}\n"
                f"  • За год: {potential_year}\n"

            )

            pending_action.pop(user_id, None)

            await message.answer(analysis_text, reply_markup=main_menu_kb())


        elif action == "analysis_category":

            category = message.text.strip()

            # Вычисляем сумму ASCII-кодов символов названия категории

            sum_ascii = sum(ord(ch) for ch in category)

            # Формула для текущей успешности: делим сумму на 10 и берём остаток от деления на 100

            current_success = (sum_ascii // 10) % 100

            # Прогнозируем успешность на следующий год как текущую успешность + 5%, но не более 100%

            forecast_success = min(current_success + 5, 100)

            analysis_result = (

                f"*Анализ Категорий: {escape_markdown(category)}*\n\n"

                f"Успешность категории сейчас: {current_success}%\n"

                f"Прогноз на следующий год: {forecast_success}% успешность"

            )

            pending_action.pop(user_id, None)

            await message.answer(analysis_result, reply_markup=main_menu_kb())


        else:
            await message.answer("Непонятный ввод. Используйте меню.", reply_markup=main_menu_kb())
    else:
        # Если нет pending_action и введён артикул (число)
        if message.text.strip().isdigit():
            if not user_has_subscription(user_id):
                await message.answer("У вас нет активной подписки!")
                return
            await bot.send_chat_action(message.chat.id, action=ChatAction.TYPING)
            await message.answer("⏳ Обработка запроса, пожалуйста, подождите...")
            loop = asyncio.get_event_loop()
            info = await loop.run_in_executor(None, get_wb_product_info, message.text.strip())
            text = format_sales_info(info)
            await message.answer(text, reply_markup=main_menu_kb())
        else:
            await message.answer(
                "Пожалуйста, используйте меню ниже для управления вашим личным кабинетом.",
                reply_markup=main_menu_kb()
            )

@dp.callback_query(lambda c: c.data == "more_search")
async def more_search_handler(callback: types.CallbackQuery):
    await callback.answer()  # подтверждаем нажатие
    user_id = callback.from_user.id
    if user_id not in pending_action or pending_action[user_id].get("action") != "global":
        await callback.answer("Нет дополнительных результатов.", show_alert=True)
        return

    data = pending_action[user_id]
    results = data.get("results", [])
    offset = data.get("last_displayed", 0)
    next_batch = results[offset:offset+5]
    if not next_batch:
        await callback.answer("Больше результатов нет.", show_alert=True)
        return

    new_text = format_site_results_from_items(next_batch)
    pending_action[user_id]["last_displayed"] = offset + len(next_batch)
    inline_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Еще поиск", callback_data="more_search")],
        [InlineKeyboardButton(text="Поставить слежение", callback_data="set_tracking")]
    ])
    await callback.message.edit_text(new_text, reply_markup=inline_kb)


# Обработка callback-запроса "Поставить слежение"
@dp.callback_query(lambda c: c.data == "set_tracking")
async def set_tracking_handler(callback: types.CallbackQuery):
    await callback.answer()  # подтверждаем нажатие
    user_id = callback.from_user.id
    query = pending_action.get(user_id, {}).get("query", "")
    await callback.message.edit_text(
        f"Мы поставили слежение за запросом: *{escape_markdown(query)}*.\n"
        "Как только появятся новые посты по этому товару в социальных сетях, вы получите уведомление.",
        reply_markup=main_menu_kb()
    )
    pending_action.pop(user_id, None)

###############################################################################
# Команды админа (подтверждение платежей)

@dp.message(Command("approve"), F.chat.id == ADMIN_ID)
async def admin_approve_handler(message: types.Message):
    parts = message.text.split()
    if len(parts) < 3:
        await message.answer("Использование: /approve <user_id> <сумма>")
        return
    try:
        uid = int(parts[1])
        amount = float(parts[2])
    except:
        await message.answer("Неверный формат /approve <user_id> <сумма>")
        return

    balance, _ = get_user_info(uid)
    new_balance = balance + amount
    update_user_balance(uid, new_balance)
    await message.answer(f"Баланс пользователя {uid} увеличен на {amount:.2f}. Новый баланс: {new_balance:.2f}")
    await bot.send_message(uid, f"Ваш баланс пополнен на {amount:.2f} ₽. Текущий баланс: {new_balance:.2f} ₽")

@dp.message(Command("reject"), F.chat.id == ADMIN_ID)
async def admin_reject_handler(message: types.Message):
    parts = message.text.split()
    if len(parts) < 2:
        await message.answer("Использование: /reject <user_id>")
        return
    try:
        uid = int(parts[1])
    except:
        await message.answer("Неверный формат /reject <user_id>")
        return

    await message.answer(f"Отклонили пополнение для пользователя {uid}")
    await bot.send_message(uid, "Администратор отклонил пополнение баланса.")

###############################################################################
# Запуск бота

async def main():
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
