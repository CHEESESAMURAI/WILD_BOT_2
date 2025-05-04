import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile
from aiogram.enums import ChatAction, ParseMode
from main import ProductCardAnalyzer, TrendAnalyzer
from niche_analyzer import NicheAnalyzer
from subscription_manager import SubscriptionManager
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
import re
import os
import json
import sqlite3
import requests
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.common.exceptions import TimeoutException
import matplotlib.pyplot as plt
import tempfile
import numpy as np
from fpdf import FPDF
import instaloader

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация бота и диспетчера
BOT_TOKEN = "7790448077:AAFiiS0a44A40zJUEivONLRutB-kqradDdE"  # Обновленный токен
ADMIN_ID = 1659228199  # Замените на ваш ID в Telegram
SERPER_API_KEY = "8ba851ed7ae1e6a655102bea15d73fdb39cdac79"  # ключ для serper.dev API

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Инициализация анализаторов и менеджеров
product_analyzer = ProductCardAnalyzer()
trend_analyzer = TrendAnalyzer()
niche_analyzer = NicheAnalyzer()
subscription_manager = SubscriptionManager()

# Стоимость операций
COSTS = {
    'product_analysis': 10,  # рублей
    'trend_analysis': 15,
    'niche_analysis': 20,
    'tracking': 5,
    'global_search': 10  # Добавляем стоимость глобального поиска
}

# Стоимость подписок
SUBSCRIPTION_COSTS = {
    'basic': 1000,
    'pro': 2500,
    'business': 5000
}

# Лимиты действий для разных типов подписок
SUBSCRIPTION_LIMITS = {
    'basic': {
        'product_analysis': 10,
        'niche_analysis': 5,
        'tracking_items': 10,
        'global_search': 20
    },
    'pro': {
        'product_analysis': 50,
        'niche_analysis': 20,
        'tracking_items': 50,
        'global_search': 100
    },
    'business': {
        'product_analysis': float('inf'),
        'niche_analysis': float('inf'),
        'tracking_items': 200,
        'global_search': float('inf')
    }
}

# Состояния FSM
class UserStates(StatesGroup):
    waiting_for_product = State()
    waiting_for_niche = State()
    waiting_for_tracking = State()
    waiting_for_payment_amount = State()
    waiting_for_payment_screenshot = State()
    waiting_for_search = State()
    viewing_search_results = State()

# Приветственное сообщение
WELCOME_MESSAGE = (
    "✨👋 *Добро пожаловать в WHITESAMURAI!* ✨\n\n"
    "Я — ваш цифровой самурай и эксперт по Wildberries!\n"
    "\n"
    "🔎 *Что я умею?*\n"
    "• 📈 Анализирую товары и ниши\n"
    "• 💡 Даю персональные рекомендации\n"
    "• 🏆 Помогаю находить тренды и прибыльные идеи\n"
    "• 📊 Отслеживаю продажи и остатки\n"
    "• 🌐 Ищу упоминания в соцсетях\n"
    "• 📝 Формирую понятные отчёты\n"
    "\n"
    "*Команды для быстрого старта:*\n"
    "▫️ /start — Главное меню\n"
    "▫️ /help — Справка и советы\n"
    "▫️ /balance — Баланс и пополнение\n"
    "▫️ /profile — Личный кабинет\n"
    "\n"
    "⚡️ *Вдохновляйтесь, анализируйте, побеждайте!*\n"
    "Ваш успех — моя миссия.\n\n"
    "👇 *Выберите функцию в меню ниже и начните свой путь к вершинам продаж!* 🚀"
)

# Клавиатура основного меню
def main_menu_kb():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Анализ товара", callback_data="product_analysis"),
            InlineKeyboardButton(text="📈 Анализ ниши", callback_data="niche_analysis")
        ],
        [
            InlineKeyboardButton(text="🌐 Глобальный поиск", callback_data="product_search"),
            InlineKeyboardButton(text="📱 Отслеживание", callback_data="track_item")
        ],
        [
            InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile"),
            InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="add_funds")
        ],
        [
            InlineKeyboardButton(text="📅 Подписка", callback_data="subscription"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats")
        ],
        [
            InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")
        ]
    ])
    return keyboard

# Клавиатура "Назад"
def back_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    return keyboard

# Обработчик кнопки "Назад"
@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback_query: types.CallbackQuery, state: FSMContext):
    await state.clear()
    await callback_query.message.edit_text(
        WELCOME_MESSAGE,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=main_menu_kb()
    )

# Обработчик кнопки "Помощь"
@dp.callback_query(lambda c: c.data == "help")
async def help_callback(callback_query: types.CallbackQuery):
    help_text = (
        "🔍 *Как пользоваться ботом:*\n\n"
        "*1. Анализ товара:*\n"
        "   • Отправьте артикул\n"
        "   • Получите полный анализ\n\n"
        "*2. Анализ ниши:*\n"
        "   • Укажите ключевое слово\n"
        "   • Получите обзор рынка\n\n"
        "*3. Отслеживание:*\n"
        "   • Добавьте товары\n"
        "   • Получайте уведомления\n\n"
        "*4. Поиск товаров:*\n"
        "   • Задайте параметры\n"
        "   • Найдите прибыльные позиции\n\n"
        "*Стоимость операций:*\n"
        f"• Анализ товара: {COSTS['product_analysis']}₽\n"
        f"• Анализ тренда: {COSTS['trend_analysis']}₽\n"
        f"• Анализ ниши: {COSTS['niche_analysis']}₽\n"
        f"• Отслеживание: {COSTS['tracking']}₽"
    )
    await callback_query.message.edit_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_keyboard()
    )

# Обработчик кнопки "Личный кабинет"
@dp.callback_query(lambda c: c.data == "profile")
async def profile_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info(f"User {user_id} requested profile")
    
    balance = subscription_manager.get_user_balance(user_id)
    tracked_items = subscription_manager.get_tracked_items(user_id)
    subscription = subscription_manager.get_subscription(user_id)
    subscription_stats = subscription_manager.get_subscription_stats(user_id)
    
    subscription_info = "❌ Нет активной подписки"
    if subscription_stats:
        expiry_date = datetime.fromisoformat(subscription_stats['expiry_date'])
        days_left = (expiry_date - datetime.now()).days
        subscription_info = (
            f"📅 *Текущая подписка:* {subscription}\n"
            f"⏳ Осталось дней: {days_left}\n\n"
            "*Лимиты:*\n"
        )
        for action, data in subscription_stats['actions'].items():
            limit = "∞" if data['limit'] == float('inf') else data['limit']
            subscription_info += f"• {action}: {data['used']}/{limit}\n"
    
    profile_text = (
        f"👤 *Личный кабинет*\n\n"
        f"💰 Баланс: {balance}₽\n"
        f"📊 Отслеживаемых товаров: {len(tracked_items)}\n\n"
        f"{subscription_info}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Мои товары", callback_data="tracked"),
            InlineKeyboardButton(text="💳 Пополнить", callback_data="add_funds")
        ],
        [InlineKeyboardButton(text="📅 Подписка", callback_data="subscription")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    await callback_query.message.edit_text(
        profile_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

# Обработчик кнопки "Пополнить баланс"
@dp.callback_query(lambda c: c.data == "add_funds")
async def add_funds_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_payment_amount)
    await callback_query.message.edit_text(
        "💰 *Пополнение баланса*\n\n"
        "Введите сумму пополнения (минимум 100₽):",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_keyboard()
    )

# Обработчик кнопки "Подписка"
@dp.callback_query(lambda c: c.data == "subscription")
async def subscription_callback(callback_query: types.CallbackQuery):
    subscription_text = (
        "📅 *Доступные подписки:*\n\n"
        f"*Basic:* {SUBSCRIPTION_COSTS['basic']}₽/мес\n"
        "• 10 анализов товаров\n"
        "• 5 анализов ниш\n"
        "• Отслеживание 10 товаров\n\n"
        f"*Pro:* {SUBSCRIPTION_COSTS['pro']}₽/мес\n"
        "• 50 анализов товаров\n"
        "• 20 анализов ниш\n"
        "• Отслеживание 50 товаров\n\n"
        f"*Business:* {SUBSCRIPTION_COSTS['business']}₽/мес\n"
        "• Неограниченное количество анализов\n"
        "• Отслеживание 200 товаров\n"
        "• Приоритетная поддержка"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Basic", callback_data="subscribe_basic"),
            InlineKeyboardButton(text="Pro", callback_data="subscribe_pro"),
            InlineKeyboardButton(text="Business", callback_data="subscribe_business")
        ],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    
    await callback_query.message.edit_text(
        subscription_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=keyboard
    )

# Обработчики подписок
@dp.callback_query(lambda c: c.data.startswith("subscribe_"))
async def handle_subscription(callback_query: types.CallbackQuery):
    subscription_type = callback_query.data.split("_")[1]
    cost = SUBSCRIPTION_COSTS[subscription_type]
    
    await callback_query.message.edit_text(
        f"📅 *Оформление подписки {subscription_type.capitalize()}*\n\n"
        f"Стоимость: {cost}₽/мес\n\n"
        "Для оформления подписки:\n"
        "1. Переведите {cost}₽ на наш счет\n"
        "2. Отправьте скриншот подтверждения оплаты\n\n"
        "Реквизиты для оплаты:\n"
        "Сбербанк: 1234 5678 9012 3456\n"
        "QIWI: +7 (999) 123-45-67\n"
        "ЮMoney: 4100 1234 5678 9012",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_keyboard()
    )

# Добавляем обработчик глобального поиска
@dp.callback_query(lambda c: c.data == "product_search")
async def handle_global_search(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback_query.from_user.id
        logger.info(f"User {user_id} clicked global search button")
        
        # Проверяем подписку
        subscription = subscription_manager.get_subscription(user_id)
        if not subscription or not subscription_manager.is_subscription_active(user_id):
            await callback_query.answer(
                "❌ У вас нет активной подписки. Пожалуйста, оформите подписку для доступа к глобальному поиску.",
                show_alert=True
            )
            return
        
        await state.set_state(UserStates.waiting_for_search)
        
        await callback_query.message.edit_text(
            "🌐 *Глобальный поиск в социальных сетях*\n\n"
            "Введите название товара или бренда для анализа.\n"
            "Например: `зимняя куртка nike` или `iphone 15`\n\n"
            "🔍 Анализ будет проведен по следующим площадкам:\n"
            "• VK\n"
            "• Instagram\n"
            "• Telegram\n"
            "• Facebook\n"
            "• Twitter\n\n"
            "📊 Вы получите информацию о:\n"
            "• Популярности товара\n"
            "• Активности в соцсетях\n"
            "• Потенциальной аудитории\n"
            "• Прогнозе продаж",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in global search handler: {str(e)}", exc_info=True)
        await callback_query.answer(
            "Произошла ошибка. Пожалуйста, попробуйте позже.",
            show_alert=True
        )

# Регистрация хендлеров
@dp.message(Command("start"))
async def start_handler(message: types.Message):
    user_id = message.from_user.id
    username = message.from_user.username or "Unknown"
    logger.info(f"New user started: {user_id} (@{username})")
    
    subscription_manager.add_user(user_id)
    await message.answer(WELCOME_MESSAGE, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_kb())

@dp.message(Command("help"))
async def help_handler(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested help")
    help_text = (
        "🔍 *Как пользоваться ботом:*\n\n"
        "*1. Анализ товара:*\n"
        "   • Отправьте артикул\n"
        "   • Получите полный анализ\n\n"
        "*2. Анализ ниши:*\n"
        "   • Укажите ключевое слово\n"
        "   • Получите обзор рынка\n\n"
        "*3. Отслеживание:*\n"
        "   • Добавьте товары\n"
        "   • Получайте уведомления\n\n"
        "*4. Поиск товаров:*\n"
        "   • Задайте параметры\n"
        "   • Найдите прибыльные позиции\n\n"
        "*Стоимость операций:*\n"
        f"• Анализ товара: {COSTS['product_analysis']}₽\n"
        f"• Анализ тренда: {COSTS['trend_analysis']}₽\n"
        f"• Анализ ниши: {COSTS['niche_analysis']}₽\n"
        f"• Отслеживание: {COSTS['tracking']}₽"
    )
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("balance"))
async def balance_handler(message: types.Message):
    user_id = message.from_user.id
    balance = subscription_manager.get_user_balance(user_id)
    logger.info(f"User {user_id} checked balance: {balance}₽")
    
    balance_text = (
        f"💰 *Ваш баланс:* {balance}₽\n\n"
        "Пополнить баланс можно через:\n"
        "• Банковскую карту\n"
        "• Криптовалюту\n"
        "• QIWI\n"
        "• ЮMoney"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="add_funds")]
    ])
    
    await message.answer(balance_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@dp.message(Command("profile"))
async def profile_handler(message: types.Message):
    user_id = message.from_user.id
    logger.info(f"User {user_id} requested profile")
    
    balance = subscription_manager.get_user_balance(user_id)
    tracked_items = subscription_manager.get_tracked_items(user_id)
    subscription = subscription_manager.get_subscription(user_id)
    subscription_stats = subscription_manager.get_subscription_stats(user_id)
    
    # Форматируем информацию о подписке
    subscription_info = "❌ Нет активной подписки"
    if subscription_stats:
        expiry_date = datetime.fromisoformat(subscription_stats['expiry_date'])
        days_left = (expiry_date - datetime.now()).days
        subscription_info = (
            f"📅 *Текущая подписка:* {subscription}\n"
            f"⏳ Осталось дней: {days_left}\n\n"
            "*Лимиты:*\n"
        )
        for action, data in subscription_stats['actions'].items():
            limit = "∞" if data['limit'] == float('inf') else data['limit']
            subscription_info += f"• {action}: {data['used']}/{limit}\n"
    
    profile_text = (
        f"👤 *Личный кабинет*\n\n"
        f"💰 Баланс: {balance}₽\n"
        f"📊 Отслеживаемых товаров: {len(tracked_items)}\n\n"
        f"{subscription_info}"
    )
    
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Мои товары", callback_data="tracked"),
            InlineKeyboardButton(text="💳 Пополнить", callback_data="add_funds")
        ],
        [InlineKeyboardButton(text="📅 Подписка", callback_data="subscription")]
    ])
    
    await message.answer(profile_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)

@dp.callback_query(lambda c: c.data.startswith('confirm_payment_') or c.data.startswith('reject_payment_'))
async def process_payment_confirmation(callback_query: types.CallbackQuery):
    try:
        action, user_id, amount = callback_query.data.split('_')[1:]
        user_id = int(user_id)
        amount = float(amount)
        
        if action == 'confirm':
            subscription_manager.update_balance(user_id, amount)
            await bot.send_message(
                user_id,
                f"✅ Ваш баланс успешно пополнен на {amount}₽",
                reply_markup=main_menu_kb()
            )
            await callback_query.message.edit_text(
                f"✅ Платеж пользователя {user_id} на сумму {amount}₽ подтвержден",
                reply_markup=None
            )
        else:
            await bot.send_message(
                user_id,
                "❌ Ваш платеж был отклонен администратором. "
                "Пожалуйста, свяжитесь с поддержкой для уточнения деталей.",
                reply_markup=main_menu_kb()
            )
            await callback_query.message.edit_text(
                f"❌ Платеж пользователя {user_id} на сумму {amount}₽ отклонен",
                reply_markup=None
            )
    except Exception as e:
        logger.error(f"Error confirming payment: {str(e)}")
        await callback_query.answer("Произошла ошибка при обработке платежа")

@dp.callback_query(lambda c: c.data == 'product_analysis')
async def handle_product_analysis(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback_query.from_user.id
        
        can_perform = subscription_manager.can_perform_action(user_id, 'product_analysis')
        if not can_perform:
            await callback_query.answer(
                "❌ У вас нет активной подписки или превышен лимит действий",
                show_alert=True
            )
            return
        
        await state.set_state(UserStates.waiting_for_product)
        
        await callback_query.message.edit_text(
            "🔍 *Анализ товара*\n\n"
            "Отправьте артикул товара для анализа.\n"
            "Например: 12345678",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in product analysis handler: {str(e)}")
        await callback_query.answer(
            "Произошла ошибка. Пожалуйста, попробуйте позже.",
            show_alert=True
        )

@dp.callback_query(lambda c: c.data == 'niche_analysis')
async def handle_niche_analysis(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback_query.from_user.id
        
        can_perform = subscription_manager.can_perform_action(user_id, 'niche_analysis')
        if not can_perform:
            await callback_query.answer(
                "❌ У вас нет активной подписки или превышен лимит действий",
                show_alert=True
            )
            return
        
        await state.set_state(UserStates.waiting_for_niche)
        
        await callback_query.message.edit_text(
            "🔍 *Анализ ниши*\n\n"
            "Отправьте ключевое слово для анализа ниши.\n"
            "Например: детские игрушки",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in niche analysis handler: {str(e)}")
        await callback_query.answer(
            "Произошла ошибка. Пожалуйста, попробуйте позже.",
            show_alert=True
        )

def extract_likes_views(snippet: str):
    likes = 0
    views = 0
    # Ищем паттерны типа "123 лайка", "456 просмотров", "123 likes", "456 views", "👍 123", "👀 456"
    m_likes = re.search(r'(\d+)[^\d]{0,5}(лайк|likes?)', snippet, re.IGNORECASE)
    m_views = re.search(r'(\d+)[^\d]{0,5}(просмотр|views?)', snippet, re.IGNORECASE)
    # Эмодзи-форматы
    m_likes_emoji = re.search(r'👍\s*(\d+)', snippet)
    m_views_emoji = re.search(r'👀\s*(\d+)', snippet)
    # YouTube-стиль: "123K views"
    m_views_youtube = re.search(r'(\d+[.,]?\d*[KkМм]?)\s*views?', snippet)
    if m_likes:
        likes = int(m_likes.group(1))
    elif m_likes_emoji:
        likes = int(m_likes_emoji.group(1))
    if m_views:
        views = int(m_views.group(1))
    elif m_views_emoji:
        views = int(m_views_emoji.group(1))
    elif m_views_youtube:
        val = m_views_youtube.group(1).replace(',', '.')
        if 'K' in val or 'К' in val or 'к' in val:
            views = int(float(val.replace('K','').replace('К','').replace('к','')) * 1000)
        elif 'M' in val or 'М' in val or 'м' in val:
            views = int(float(val.replace('M','').replace('М','').replace('м','')) * 1000000)
        else:
            try:
                views = int(val)
            except:
                pass
    return likes, views

# --- YouTube ---
YOUTUBE_API_KEY = 'AIzaSyD-epfqmQhkKJcjy_V3nP93VniUIGEb3Sc'
def get_youtube_likes_views(url):
    """Получить лайки и просмотры с YouTube по ссылке на видео."""
    video_id = None
    m = re.search(r'(?:v=|youtu\.be/)([\w-]{11})', url)
    if m:
        video_id = m.group(1)
    if not video_id:
        return 0, 0
    api_url = f'https://www.googleapis.com/youtube/v3/videos?part=statistics&id={video_id}&key={YOUTUBE_API_KEY}'
    try:
        resp = requests.get(api_url, timeout=5)
        data = resp.json()
        stats = data['items'][0]['statistics']
        views = int(stats.get('viewCount', 0))
        likes = int(stats.get('likeCount', 0)) if 'likeCount' in stats else 0
        return likes, views
    except Exception as e:
        return 0, 0

# --- VK ---
VK_SERVICE_KEY = 'f5a40946f5a40946f5a40946a0f6944232ff5a4f5a409469daa2e76f8ea701e061483db'
def get_vk_likes_views(url):
    """Получить лайки и просмотры с VK по ссылке на пост."""
    # Пример ссылки: https://vk.com/wall-123456_789
    m = re.search(r'vk\.com/wall(-?\d+)_([\d]+)', url)
    if not m:
        return 0, 0
    owner_id, post_id = m.group(1), m.group(2)
    api_url = f'https://api.vk.com/method/wall.getById?posts={owner_id}_{post_id}&access_token={VK_SERVICE_KEY}&v=5.131'
    try:
        resp = requests.get(api_url, timeout=5)
        data = resp.json()
        post = data['response'][0]
        likes = post['likes']['count'] if 'likes' in post else 0
        views = post['views']['count'] if 'views' in post else 0
        return likes, views
    except Exception as e:
        return 0, 0

# --- Instagram парсинг лайков/подписчиков ---
def get_instagram_likes_views(url):
    """Пытается получить лайки/просмотры для поста или подписчиков для профиля Instagram через парсинг."""
    import requests
    import re
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        }
        resp = requests.get(url, headers=headers, timeout=7)
        html = resp.text
        # Для поста (reel/photo/video): ищем "likes" и "views"
        m_likes = re.search(r'"edge_media_preview_like":\{"count":(\d+)\}', html)
        m_views = re.search(r'"video_view_count":(\d+)', html)
        likes = int(m_likes.group(1)) if m_likes else 0
        views = int(m_views.group(1)) if m_views else 0
        # Для профиля: ищем подписчиков
        m_followers = re.search(r'"edge_followed_by":\{"count":(\d+)\}', html)
        if m_followers:
            likes = int(m_followers.group(1))
        return likes, views
    except Exception:
        return 0, 0

# --- Обновляем get_real_likes_views ---
def get_real_likes_views(url, snippet):
    if 'youtube.com' in url or 'youtu.be' in url:
        likes, views = get_youtube_likes_views(url)
        if likes or views:
            return likes, views
    if 'vk.com/wall' in url:
        likes, views = get_vk_likes_views(url)
        if likes or views:
            return likes, views
    if 'instagram.com' in url:
        likes, views = get_instagram_likes_views(url)
        if likes or views:
            return likes, views
    # fallback: из snippet
    return extract_likes_views(snippet)

def estimate_impact(likes, views):
    """Оценивает влияние на основе лайков и просмотров."""
    if likes == 0 and views == 0:
        likes = 10
        views = 100
    approx_clients = int(likes * 0.1 + views * 0.05)
    avg_check = 500  # Средний чек
    approx_revenue = approx_clients * avg_check
    baseline = 10000
    growth_percent = (approx_revenue / baseline) * 100 if baseline else 0
    return approx_clients, approx_revenue, growth_percent

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
                    
                    if isinstance(old_sales_data, list):
                        for item in old_sales_data:
                            if str(item.get('nmId')) == str(article):
                                sales_today = item.get('qnt', 0)
                                break
            except Exception as e:
                logger.error(f"Error getting old sales data: {str(e)}")
        
        # Собираем все данные
        result = {
            'name': product.get('name', ''),
            'brand': product.get('brand', ''),
            'price': {
                'current': product.get('salePriceU', 0) / 100,
                'original': product.get('priceU', 0) / 100,
                'discount': product.get('discount', 0)
            },
            'rating': product.get('rating', 0) / 10,
            'feedbacks': product.get('feedbacks', 0),
            'stocks': {
                'total': total_stock,
                'by_size': stocks_by_size
            },
            'sales': {
                'today': sales_today,
                'total': total_sales or product.get('ordersCount', 0) or product.get('salesPerMonth', 0) or 0
            }
        }
        
        logger.info(f"Final product info: {json.dumps(result, indent=2)}")
        return result
        
    except Exception as e:
        logger.error(f"Error getting WB product info: {str(e)}", exc_info=True)
        return None

async def global_search_serper_detailed(query: str):
    """Выполняет глобальный поиск через API serper.dev с анализом соцсетей."""
    try:
        logger.info(f"Starting global search for query: {query}")
        url = "https://google.serper.dev/search"
        
        payload = json.dumps({
            "q": query,
            "num": 20,
            "gl": "ru",
            "hl": "ru"
        })
        
        headers = {
            'X-API-KEY': SERPER_API_KEY,
            'Content-Type': 'application/json'
        }
        
        logger.info(f"Making request to Serper API")
        response = requests.post(url, headers=headers, data=payload)
        logger.info(f"Serper API response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Serper API error: {response.text}")
            return {"error": "Ошибка при выполнении поиска", "results": []}
            
        search_data = response.json()
        logger.info(f"Serper API response data: {json.dumps(search_data, indent=2)}")
        
        organic = search_data.get("organic", [])
        
        # Разрешённые домены социальных сетей
        allowed_domains = ["vk.com", "instagram.com", "t.me", "facebook.com", "twitter.com", "x.com"]
        filtered_results = []
        
        for item in organic:
            link = item.get("link", "")
            # Исключаем ссылки на Wildberries
            if "wildberries" in link.lower():
                continue
            domain = re.sub(r'^https?://(www\.)?', '', link).split('/')[0].lower()
            if any(allowed_domain in domain for allowed_domain in allowed_domains):
                # Получаем лайки и просмотры
                snippet = item.get("snippet", "")
                likes, views = get_real_likes_views(link, snippet)
                
                # Оцениваем влияние
                clients, revenue, growth = estimate_impact(likes, views)
                
                result = {
                    "title": item.get("title", ""),
                    "link": link,
                    "snippet": snippet,
                    "site": domain,
                    "likes": likes,
                    "views": views,
                    "approx_clients": clients,
                    "approx_revenue": revenue,
                    "growth_percent": growth
                }
                filtered_results.append(result)
        
        if not filtered_results:
            return {
                "error": (
                    "🔍 *Анализ социальных сетей*\n\n"
                    "Мы провели тщательный анализ по следующим площадкам:\n"
                    "• VK\n"
                    "• Instagram\n"
                    "• Telegram\n"
                    "• Facebook\n"
                    "• Twitter\n\n"
                    "📊 *Результаты анализа:*\n"
                    "Не обнаружено активного продвижения товара в социальных сетях. "
                    "Это может означать:\n"
                    "• Товар продвигается органически\n"
                    "• Высокий уровень доверия аудитории\n"
                    "• Стабильный спрос без агрессивной рекламы"
                ),
                "results": []
            }
        
        return {"error": None, "results": filtered_results}
        
    except Exception as e:
        logger.error(f"Error in global search: {str(e)}", exc_info=True)
        return {"error": "Произошла ошибка при выполнении поиска", "results": []}

def format_serper_results_detailed(search_data, chart_path=None):
    """Форматирует результаты поиска в читаемый вид с корректным HTML-форматированием."""
    if search_data["error"]:
        return search_data["error"]

    results = []
    total_likes = 0
    total_views = 0
    platforms_counter = {}
    
    for item in search_data["results"]:
        # Экранируем специальные символы в тексте
        title = item.get("title", "").replace("<", "&lt;").replace(">", "&gt;")
        link = item.get("link", "").replace("<", "&lt;").replace(">", "&gt;")
        site = item.get("site", "").replace("<", "&lt;").replace(">", "&gt;")
        likes = item.get("likes", 0)
        views = item.get("views", 0)
        clients = item.get("approx_clients", 0)
        revenue = item.get("approx_revenue", 0)
        growth = item.get("growth_percent", 0)
        
        total_likes += likes
        total_views += views
        platforms_counter[site] = platforms_counter.get(site, 0) + 1

        # Определяем статус и рекомендацию
        status = ""
        if 'instagram.com' in site and likes == 0 and views == 0:
            status = "⚠️ Данные защищены"
        elif likes + views == 0:
            status = "⚠️ Нет данных"
        elif likes > 1000 or views > 10000:
            status = "🔥 Высокая активность"
        else:
            status = "📊 Средняя активность"

        result = (
            f"\n🔗 <b>{title}</b>\n"
            f"🌐 <b>Площадка:</b> {site}\n"
            f"🔍 <a href='{link}'>Открыть ссылку</a>\n"
            f"👍 <b>Лайки:</b> {likes:,}  👀 <b>Просмотры:</b> {views:,}\n"
            f"👥 <b>Аудитория:</b> {clients:,}\n"
            f"💰 <b>Потенц. выручка:</b> {revenue:,}₽\n"
            f"📈 <b>Прогноз роста:</b> {growth:.1f}%\n"
            f"{status}"
        )
        results.append(result)

    # Формируем заголовок
    most_popular = max(platforms_counter, key=platforms_counter.get) if platforms_counter else "—"
    header = (
        "🌐 <b>Анализ социальных сетей</b>\n\n"
        f"📊 <b>Общая статистика:</b>\n"
        f"• Найдено упоминаний: {len(results)}\n"
        f"• Суммарные лайки: {total_likes:,}\n"
        f"• Суммарные просмотры: {total_views:,}\n"
        f"• Самая активная площадка: {most_popular}\n\n"
        "<b>Результаты поиска:</b>"
    )

    # Добавляем рекомендации
    recommendations = (
        "\n\n📋 <b>Рекомендации:</b>\n"
        "• Фокусируйтесь на площадках с высокой активностью\n"
        "• Используйте таргетированную рекламу\n"
        "• Работайте с блогерами и лидерами мнений\n"
        "• Создавайте качественный контент\n"
    )

    # Добавляем информацию о графике
    chart_info = ""
    if chart_path:
        chart_info = "\n\n📊 <b>Подробный анализ доступен в PDF-отчёте</b>"

    # Добавляем футер
    footer = (
        "\n\n💡 <b>Следующие шаги:</b>\n"
        "1. Проанализируйте площадки с высокой активностью\n"
        "2. Составьте план продвижения\n"
        "3. Начните работу с самых перспективных каналов"
    )

    # Собираем все части сообщения
    return header + "\n".join(results) + recommendations + chart_info + footer

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_search)
async def handle_search_query(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        search_query = message.text.strip()
        logger.info(f"Processing search query from user {user_id}: {search_query}")
        
        # Проверяем подписку
        subscription = subscription_manager.get_subscription(user_id)
        if not subscription or not subscription_manager.is_subscription_active(user_id):
            await message.answer("❌ У вас нет активной подписки для выполнения глобального поиска")
            await state.clear()
            return
        
        await message.answer(
            "🔍 Анализирую социальные сети...\n"
            "⏳ Это может занять некоторое время"
        )
        
        # Выполняем поиск
        search_results = await global_search_serper_detailed(search_query)
        
        # Сохраняем результаты в состоянии для пагинации
        await state.update_data(
            search_results=search_results["results"],
            current_page=0,
            query=search_query
        )
        
        # Форматируем и отправляем первую страницу результатов
        if search_results["error"]:
            await message.answer(
                search_results["error"],
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            # Берем первые 5 результатов
            first_page = search_results["results"][:5]
            formatted_results = format_serper_results_detailed({"error": None, "results": first_page})
            
            # Создаем клавиатуру с кнопками навигации
            keyboard = []
            if len(search_results["results"]) > 5:
                keyboard.append([
                    InlineKeyboardButton(text="➡️ Следующая страница", callback_data="next_page")
                ])
            keyboard.append([
                InlineKeyboardButton(text="🔄 Новый поиск", callback_data="product_search"),
                InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_main")
            ])
            
            await message.answer(
                formatted_results,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
                disable_web_page_preview=True
            )
        
        await state.set_state(UserStates.viewing_search_results)
        
    except Exception as e:
        logger.error(f"Error processing search query: {str(e)}", exc_info=True)
        await message.answer(
            "❌ Произошла ошибка при выполнении поиска\n"
            "Пожалуйста, попробуйте позже"
        )
        await state.clear()

@dp.callback_query(lambda c: c.data in ["next_page", "prev_page"])
async def handle_pagination(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        # Получаем сохраненные данные
        data = await state.get_data()
        results = data.get("search_results", [])
        current_page = data.get("current_page", 0)
        
        # Определяем направление пагинации
        if callback_query.data == "next_page":
            current_page += 1
        else:
            current_page -= 1
        
        # Вычисляем индексы для текущей страницы
        start_idx = current_page * 5
        end_idx = start_idx + 5
        current_results = results[start_idx:end_idx]
        
        # Обновляем номер текущей страницы в состоянии
        await state.update_data(current_page=current_page)
        
        # Создаем клавиатуру с кнопками навигации
        keyboard = []
        nav_buttons = []
        
        if current_page > 0:
            nav_buttons.append(
                InlineKeyboardButton(text="⬅️ Предыдущая", callback_data="prev_page")
            )
        
        if end_idx < len(results):
            nav_buttons.append(
                InlineKeyboardButton(text="➡️ Следующая", callback_data="next_page")
            )
        
        if nav_buttons:
            keyboard.append(nav_buttons)
        
        keyboard.append([
            InlineKeyboardButton(text="🔄 Новый поиск", callback_data="product_search"),
            InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_main")
        ])
        
        # Форматируем и отправляем результаты
        formatted_results = format_serper_results_detailed({"error": None, "results": current_results})
        
        await callback_query.message.edit_text(
            formatted_results,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard),
            disable_web_page_preview=True
        )
        
    except Exception as e:
        logger.error(f"Error handling pagination: {str(e)}", exc_info=True)
        await callback_query.answer(
            "Произошла ошибка при переключении страницы",
            show_alert=True
        )

@dp.message(F.photo)
async def handle_payment_screenshot(message: types.Message, state: FSMContext):
    try:
        data = await state.get_data()
        amount = data.get('amount')
        user_id = message.from_user.id
        
        admin_message = (
            f"🔄 *Новая заявка на пополнение баланса*\n\n"
            f"👤 Пользователь: {message.from_user.full_name} (ID: {user_id})\n"
            f"💰 Сумма: {amount}₽\n\n"
            f"Подтвердите или отклоните заявку:"
        )
        
        admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_payment_{user_id}_{amount}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_payment_{user_id}_{amount}")
            ]
        ])
        
        await bot.send_photo(
            chat_id=ADMIN_ID,
            photo=message.photo[-1].file_id,
            caption=admin_message,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=admin_keyboard
        )
        
        await message.answer(
            "✅ Скриншот оплаты отправлен администратору. "
            "Ожидайте подтверждения.",
            reply_markup=main_menu_kb()
        )
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error handling payment screenshot: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка при обработке скриншота. "
            "Пожалуйста, попробуйте позже.",
            reply_markup=main_menu_kb()
        )
        await state.clear()

@dp.message(F.text, UserStates.waiting_for_payment_amount)
async def handle_payment_amount(message: types.Message, state: FSMContext):
    try:
        amount = float(message.text)
        if amount < 100:
            await message.answer("❌ Минимальная сумма пополнения: 100₽")
            return
        await state.update_data(amount=amount)
        await state.set_state(UserStates.waiting_for_payment_screenshot)
        await message.answer(
            f"💰 Сумма пополнения: {amount}₽\n\nТеперь отправьте скриншот подтверждения оплаты"
        )
    except ValueError:
        await message.answer("❌ Пожалуйста, введите корректную сумму")

def build_area_chart(labels, sales, revenue, profit, title, filename_prefix):
    plt.figure(figsize=(8, 5))
    x = np.arange(len(labels))
    plt.plot(x, sales, color='#4e79a7', linewidth=2.5, label='Продажи, шт.')
    plt.fill_between(x, sales, color='#4e79a7', alpha=0.18)
    plt.plot(x, revenue, color='#f28e2b', linewidth=2.5, label='Выручка, ₽')
    plt.fill_between(x, revenue, color='#f28e2b', alpha=0.18)
    plt.plot(x, profit, color='#e15759', linewidth=2.5, label='Прибыль, ₽')
    plt.fill_between(x, profit, color='#e15759', alpha=0.18)
    plt.xticks(x, labels, fontsize=13)
    plt.yticks(fontsize=13)
    plt.title(title, fontsize=16)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.legend(fontsize=13)
    # Подписи над точками
    for i, val in enumerate(sales):
        plt.annotate(f'{int(val):,}'.replace(',', ' '), (x[i], sales[i]), textcoords="offset points", xytext=(0,8), ha='center', fontsize=12)
    for i, val in enumerate(revenue):
        plt.annotate(f'{int(val):,}'.replace(',', ' '), (x[i], revenue[i]), textcoords="offset points", xytext=(0,8), ha='center', fontsize=12)
    for i, val in enumerate(profit):
        plt.annotate(f'{int(val):,}'.replace(',', ' '), (x[i], profit[i]), textcoords="offset points", xytext=(0,8), ha='center', fontsize=12)
    plt.tight_layout()
    tmpfile = tempfile.NamedTemporaryFile(suffix='.png', prefix=filename_prefix, delete=False)
    plt.savefig(tmpfile.name)
    plt.close()
    return tmpfile.name

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_product)
async def handle_product_article(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        article = message.text.strip()
        logger.info(f"User {user_id} is waiting for product analysis")

        # Проверяем подписку
        can_perform = subscription_manager.can_perform_action(user_id, 'product_analysis')
        if not can_perform:
            await message.answer("❌ У вас нет активной подписки или превышен лимит действий", reply_markup=main_menu_kb())
            await state.clear()
            return

        await message.answer("⏳ Выполняется анализ артикула, подождите...")
        product_info = await get_wb_product_info(article)
        if not product_info:
            await message.answer("❌ Не удалось получить информацию по артикулу. Проверьте правильность артикула.", reply_markup=main_menu_kb())
            await state.clear()
            return
        result = await format_product_analysis(product_info, article)

        # --- Построение и отправка графиков ---
        daily_sales = product_info['sales']['today']
        used_estimation = False
        if not daily_sales or daily_sales == 0:
            total_sales = product_info['sales'].get('total', 0)
            feedbacks = product_info.get('feedbacks', 0)
            estimated_total_sales = feedbacks * 30
            total_sales = max(total_sales, estimated_total_sales)
            daily_sales = max(1, round(total_sales / 365)) if total_sales > 0 else 0
            used_estimation = True
        week_sales = daily_sales * 7 if not used_estimation else round(total_sales / 52)
        month_sales = daily_sales * 30 if not used_estimation else round(total_sales / 12)
        price = product_info['price']['current']
        commission = 0.15
        daily_revenue = daily_sales * price
        week_revenue = week_sales * price
        month_revenue = month_sales * price
        daily_profit = int(daily_revenue * (1 - commission))
        week_profit = int(week_revenue * (1 - commission))
        month_profit = int(month_revenue * (1 - commission))
        # Графики
        sales_plot = build_area_chart(['Сутки', 'Неделя', 'Месяц'], [daily_sales, week_sales, month_sales], [daily_revenue, week_revenue, month_revenue], [daily_profit, week_profit, month_profit], f'Прогноз продаж {article}', 'sales_')
        revenue_plot = build_area_chart(['Сутки', 'Неделя', 'Месяц'], [daily_sales, week_sales, month_sales], [daily_revenue, week_revenue, month_revenue], [daily_profit, week_profit, month_profit], f'Прогноз выручки {article}', 'revenue_')
        profit_plot = build_area_chart(['Сутки', 'Неделя', 'Месяц'], [daily_sales, week_sales, month_sales], [daily_revenue, week_revenue, month_revenue], [daily_profit, week_profit, month_profit], f'Прогноз прибыли {article}', 'profit_')
        # Отправка графиков
        await bot.send_photo(message.chat.id, FSInputFile(sales_plot), caption="График прогнозных продаж", reply_markup=None)
        await bot.send_photo(message.chat.id, FSInputFile(revenue_plot), caption="График прогнозной выручки", reply_markup=None)
        await bot.send_photo(message.chat.id, FSInputFile(profit_plot), caption="График прогнозной прибыли", reply_markup=None)
        # Текстовый анализ
        await bot.send_message(message.chat.id, result, parse_mode=ParseMode.MARKDOWN, reply_markup=main_menu_kb())

        # --- Визуализация рекламы/глобального поиска ---
        # Автоматически запускаем глобальный поиск по названию товара
        try:
            search_query = product_info.get('name') or product_info.get('brand') or article
            search_results = await global_search_serper_detailed(search_query)
            mentions = search_results.get('results', [])
        except Exception as search_err:
            logger.error(f"Global search error: {search_err}")
            mentions = []
        chart_path = None
        if mentions:
            platforms = [m.get('site', 'Неизвестно') for m in mentions]
            revenues = [m.get('approx_revenue', 0) for m in mentions]
            # График по выручке
            chart_path = build_area_chart(platforms, revenues, revenues, revenues, f'Потенциальная выручка по площадкам', 'adv_')
            await bot.send_photo(message.chat.id, FSInputFile(chart_path), caption="Потенциальная выручка по площадкам (сторонняя реклама)")
        else:
            await bot.send_message(message.chat.id, "Нет данных о сторонней рекламе или продвижении в соцсетях.")

        # --- ДОБАВЛЯЕМ Instagram-поиск по хэштегу, если нет instagram.com ---
        if not any('instagram.com' in m.get('site', '') for m in mentions):
            insta_posts = search_instagram_by_hashtag(article)
            if product_info.get('brand'):
                insta_posts += search_instagram_by_hashtag(product_info['brand'])
            if insta_posts:
                mentions.extend(insta_posts)
                # Перестроить график с учетом новых данных
                platforms = [m.get('site', 'Неизвестно') for m in mentions]
                revenues = [m.get('approx_revenue', 0) for m in mentions]
                chart_path = build_area_chart(platforms, revenues, revenues, revenues, f'Потенциальная выручка по площадкам', 'adv_')
                await bot.send_photo(message.chat.id, FSInputFile(chart_path), caption="Потенциальная выручка по площадкам (Instagram)")

        # --- PDF-отчёт по глобальному поиску ---
        try:
            pdf_path = generate_global_search_pdf(article, mentions, chart_path)
            await bot.send_document(message.chat.id, FSInputFile(pdf_path), caption="PDF-отчёт по глобальному поиску по артикулу")
        except Exception as pdf_err:
            logger.error(f"PDF error: {pdf_err}")
            await bot.send_message(message.chat.id, f"❌ Ошибка при формировании PDF-отчёта: {pdf_err}")
        await state.clear()

        # --- Встраиваем в handle_product_article после основного поиска ---
        # После получения mentions:
        # if not any('instagram.com' in m.get('site', '') for m in mentions):
        #     hashtag = article  # или product_info['brand']
        #     insta_posts = search_instagram_by_hashtag(hashtag)
        #     mentions.extend(insta_posts)
    except Exception as e:
        logger.error(f"Error in handle_product_article: {str(e)}")
        await message.answer("❌ Произошла ошибка при анализе артикула.", reply_markup=main_menu_kb())
        await state.clear()

# Добавляем периодическую проверку истекающих подписок
async def check_expiring_subscriptions():
    logger.info("Starting expiring subscriptions check")
    while True:
        expiring = subscription_manager.get_expiring_subscriptions()
        logger.info(f"Found {len(expiring)} expiring subscriptions")
        
        for sub in expiring:
            days_left = (datetime.fromisoformat(sub['expiry_date']) - datetime.now()).days
            if days_left <= 3:
                logger.info(f"Sending expiry notification to user {sub['user_id']}, {days_left} days left")
                await bot.send_message(
                    sub['user_id'],
                    f"⚠️ *Ваша подписка истекает через {days_left} дней*\n\n"
                    f"Тип подписки: {sub['type']}\n"
                    "Продлите подписку, чтобы сохранить доступ ко всем функциям.",
                    parse_mode="Markdown",
                    reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🔄 Продлить подписку", callback_data="subscription")]
                    ])
                )
        await asyncio.sleep(3600)  # Проверяем каждый час

# Обновляем форматирование результатов анализа товара
async def format_product_analysis(product_info, article):
    """Форматирует результаты анализа товара."""
    
    # Получаем продажи за сутки
    daily_sales = product_info['sales']['today']
    used_estimation = False
    # Пробуем альтернативные источники, если нет sales_today
    if not daily_sales or daily_sales == 0:
        total_sales = product_info['sales'].get('total', 0)
        sales_per_month = product_info.get('salesPerMonth', 0)
        feedbacks = product_info.get('feedbacks', 0)
        # Оценка по отзывам: 1 отзыв ≈ 30 продаж за всё время
        estimated_total_sales = feedbacks * 30
        # Если total_sales уже есть и больше — используем его
        total_sales = max(total_sales, estimated_total_sales)
        # Оценка: за месяц — 1/12, за неделю — 1/52, за сутки — 1/365
        estimated_month = round(total_sales / 12)
        estimated_week = round(total_sales / 52)
        daily_sales = max(1, round(total_sales / 365)) if total_sales > 0 else 0
        used_estimation = True
    else:
        estimated_week = daily_sales * 7
        estimated_month = daily_sales * 30
    
    daily_revenue = daily_sales * product_info['price']['current']
    estimated_week_revenue = estimated_week * product_info['price']['current']
    estimated_month_revenue = estimated_month * product_info['price']['current']
    
    # Считаем примерную прибыль (берем 30% от выручки)
    profit_margin = 0.3
    daily_profit = daily_revenue * profit_margin
    estimated_week_profit = estimated_week_revenue * profit_margin
    estimated_month_profit = estimated_month_revenue * profit_margin

    # Корректная обработка рейтинга
    rating = product_info['rating']
    if rating > 5:
        rating = rating / 10
    
    result = (
        f"📊 *Анализ товара {article}*\n\n"
        f"*Основная информация:*\n"
        f"📦 Название: {product_info['name']}\n"
        f"🏷 Бренд: {product_info['brand']}\n"
        f"💰 Цена: {product_info['price']['current']}₽"
    )
    
    # Добавляем информацию о скидке, если она есть
    if product_info['price']['discount'] > 0:
        result += f" (-{product_info['price']['discount']}% от {product_info['price']['original']}₽)"
    
    result += (
        f"\n⭐ Рейтинг: {rating:.1f}/5\n"
        f"📝 Отзывов: {product_info['feedbacks']}\n"
        f"\n*Наличие на складах:*\n"
        f"📦 Всего: {product_info['stocks']['total']} шт.\n"
    )
    
    # Добавляем информацию по размерам
    if product_info['stocks']['by_size']:
        result += "\n*Остатки по размерам:*\n"
        for size, qty in sorted(product_info['stocks']['by_size'].items()):
            if qty > 0:
                result += f"• {size}: {qty} шт.\n"
    
    # Продажи и выручка
    if daily_sales == 0:
        result += (
            f"\n*Продажи и выручка:*\n"
            f"❗ Нет данных о продажах за сутки.\n"
            f"💰 Выручка за сутки: 0₽\n"
            f"💎 Прибыль за сутки: 0₽\n"
        )
        week_note = "❗ Нет данных для прогноза."
        month_note = "❗ Нет данных для прогноза."
    else:
        result += (
            f"\n*Продажи и выручка:*\n"
            f"📈 Продажи за сутки: {daily_sales} шт.\n"
            f"💰 Выручка за сутки: {daily_revenue:,.0f}₽\n"
            f"💎 Прибыль за сутки: {daily_profit:,.0f}₽\n"
        )
        week_note = ""
        month_note = ""
    
    # Прогноз на неделю
    result += (
        f"\n*Прогноз на неделю:*\n"
        f"📈 Продажи: ~{estimated_week} шт.\n"
        f"💰 Выручка: ~{estimated_week_revenue:,.0f}₽\n"
        f"💎 Прибыль: ~{estimated_week_profit:,.0f}₽\n"
    )
    if week_note:
        result += week_note + "\n"
    
    # Прогноз на месяц
    result += (
        f"\n*Прогноз на месяц:*\n"
        f"📈 Продажи: ~{estimated_month} шт.\n"
        f"💰 Выручка: ~{estimated_month_revenue:,.0f}₽\n"
        f"💎 Прибыль: ~{estimated_month_profit:,.0f}₽\n"
    )
    if month_note:
        result += month_note + "\n"
    
    # Пояснение, если использована оценка
    if used_estimation:
        result += ("\n_Данные по продажам оценочные, рассчитаны на основе количества отзывов и средней конверсии Wildberries. Реальные значения могут отличаться._\n")
    
    # Добавляем рекомендации
    recommendations = []
    if rating < 4:
        recommendations.append("\n💡 *Улучшить качество товара и обслуживания*\n- Проанализируйте отзывы покупателей: обратите внимание на повторяющиеся жалобы и пожелания.\n- Внедрите контроль качества на всех этапах производства и упаковки.\n- Улучшите сервис: быстрая доставка, вежливое общение, решение проблем клиентов.")
    if product_info['feedbacks'] < 100:
        recommendations.append("\n💡 *Увеличить количество отзывов*\n- Просите довольных клиентов оставлять отзывы, предлагайте бонусы или скидки за обратную связь.\n- Используйте QR-коды на упаковке для быстрого перехода к форме отзыва.\n- Отвечайте на все отзывы — это повышает доверие новых покупателей.")
    if product_info['stocks']['total'] < 10:
        recommendations.append("\n💡 *Пополнить остатки товара*\n- Следите за остатками на складе, чтобы не терять продажи из-за отсутствия товара.\n- Планируйте закупки заранее, особенно перед сезоном повышенного спроса.\n- Используйте автоматические уведомления о низких остатках.")
    if product_info['price']['discount'] > 30:
        recommendations.append("\n💡 *Проанализировать ценовую политику*\n- Сравните цены с конкурентами: возможно, скидка слишком велика и снижает вашу прибыль.\n- Используйте акции и скидки осознанно — для привлечения новых клиентов или распродажи остатков.\n- Тестируйте разные уровни скидок и отслеживайте их влияние на продажи.")
    if daily_sales == 0 and product_info['stocks']['total'] > 0:
        recommendations.append("\n💡 *Проработать маркетинговую стратегию*\n- Запустите рекламу в социальных сетях и на маркетплейсах.\n- Используйте красивые фото и видео, расскажите историю бренда.\n- Сотрудничайте с блогерами и лидерами мнений.\n- Проведите анализ целевой аудитории и настройте таргетированную рекламу.")
    if not recommendations:
        recommendations.append("\n✅ Ваш товар показывает хорошие результаты! Продолжайте следить за качеством и развивайте маркетинг для дальнейшего роста.")
    result += "\n*Рекомендации:* " + "\n".join(recommendations)
    
    return result

def generate_global_search_pdf(article, search_results, chart_path=None):
    import os
    # Логируем все площадки для диагностики
    import logging
    logger = logging.getLogger(__name__)
    logger.info(f"PDF: platforms in mentions: {[item.get('site', '') for item in search_results]}")
    pdf = FPDF()
    # Регистрируем шрифт DejaVuSans для поддержки кириллицы
    font_path = os.path.join(os.path.dirname(__file__), 'DejaVuSans.ttf')
    pdf.add_font('DejaVu', '', font_path, uni=True)
    pdf.add_font('DejaVu', 'B', font_path, uni=True)
    pdf.add_page()
    pdf.set_font('DejaVu', 'B', 18)
    pdf.cell(0, 15, f'Глобальный поиск по артикулу {article}', ln=1, align='C')
    pdf.set_font('DejaVu', '', 12)
    pdf.cell(0, 10, f'Дата анализа: {datetime.now().strftime("%d.%m.%Y %H:%M")}', ln=1, align='C')
    pdf.ln(5)
    if not search_results:
        pdf.set_font('DejaVu', '', 14)
        pdf.set_text_color(200, 0, 0)
        pdf.multi_cell(0, 10, 'Стороннего продвижения не обнаружено. Товар продвигается органически или не найден в соцсетях.', align='C')
        pdf.set_text_color(0, 0, 0)
    else:
        pdf.set_font('DejaVu', 'B', 13)
        pdf.cell(0, 10, 'Таблица упоминаний:', ln=1)
        pdf.set_font('DejaVu', '', 11)
        col_widths = [32, 60, 22, 22, 28, 28, 18]
        headers = ['Площадка', 'Ссылка', 'Лайки', 'Просмотры', 'Аудитория', 'Выручка', 'Рост %']
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, h, border=1, align='C')
        pdf.ln()
        for item in search_results:
            site = item.get('site', '')[:15]
            link = item.get('link', '')
            likes = item.get('likes', 0)
            views = item.get('views', 0)
            # Для Instagram — если нет данных, явно пишем причину
            if 'instagram.com' in site and (likes == 0 and views == 0):
                likes_str = 'нет данных'
                views_str = 'нет данных'
            else:
                likes_str = str(likes)
                views_str = str(views)
            pdf.cell(col_widths[0], 8, site, border=1)
            # Ссылка — обрезаем до 40 символов с ...
            short_link = link if len(link) <= 40 else link[:37] + '...'
            pdf.cell(col_widths[1], 8, short_link, border=1)
            pdf.cell(col_widths[2], 8, likes_str, border=1, align='C')
            pdf.cell(col_widths[3], 8, views_str, border=1, align='C')
            pdf.cell(col_widths[4], 8, str(item.get('approx_clients', 0)), border=1, align='C')
            pdf.cell(col_widths[5], 8, str(item.get('approx_revenue', 0)), border=1, align='C')
            pdf.cell(col_widths[6], 8, f"{item.get('growth_percent', 0):.1f}", border=1, align='C')
            pdf.ln()
        pdf.ln(5)
        if chart_path and os.path.exists(chart_path):
            pdf.set_font('DejaVu', 'B', 12)
            pdf.cell(0, 10, 'График по данным глобального поиска:', ln=1)
            pdf.image(chart_path, x=20, w=170)
        # Сноска для Instagram
        pdf.set_font('DejaVu', '', 9)
        pdf.set_text_color(120, 120, 120)
        pdf.multi_cell(0, 7, 'Для Instagram часто невозможно получить лайки и просмотры из-за ограничений платформы. В таких случаях в таблице указано: нет данных (Instagram защищён).', align='L')
        pdf.set_text_color(0, 0, 0)
    tmpfile = tempfile.NamedTemporaryFile(suffix='.pdf', delete=False)
    pdf.output(tmpfile.name)
    return tmpfile.name

def search_instagram_by_hashtag(hashtag, max_posts=5):
    L = instaloader.Instaloader()
    username = "upir.worldwide"
    password = "GGrenki_1901"
    try:
        L.login(username, password)
        posts = instaloader.Hashtag.from_name(L.context, hashtag).get_posts()
    except Exception as e:
        print(f"Ошибка Instaloader: {e}")
        return []
    results = []
    for i, post in enumerate(posts):
        if i >= max_posts:
            break
        results.append({
            'site': 'instagram.com',
            'link': f'https://www.instagram.com/p/{post.shortcode}/',
            'likes': post.likes,
            'views': post.video_view_count if post.is_video else 0,
            'approx_clients': int(post.likes * 0.1 + (post.video_view_count or 0) * 0.05),
            'approx_revenue': int((post.likes * 0.1 + (post.video_view_count or 0) * 0.05) * 500),
            'growth_percent': 0,
        })
    return results

# Добавляем запуск проверки в main
async def main():
    logger.info("Starting bot...")
    
    # Запускаем проверку истекающих подписок
    asyncio.create_task(check_expiring_subscriptions())
    
    # Запускаем бота
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

if __name__ == '__main__':
    asyncio.run(main()) 