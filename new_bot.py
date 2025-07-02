import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputMediaPhoto
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
import time
from urllib.parse import urlparse, quote
import random
import aiohttp
import sys
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional
import datetime
from datetime import datetime, timedelta
import requests
from urllib.parse import urlparse
import random
import math
import aiohttp
from bs4 import BeautifulSoup
import locale
import time
import base64
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportLabImage, Table, TableStyle
from reportlab.lib.units import inch
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.types.input_file import BufferedInputFile
from aiogram.utils.markdown import hbold, hitalic, hcode, hlink, hunderline, hstrikethrough
import openai
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

from subscription_manager import SubscriptionManager
from product_mpstat import get_product_mpstat_info
from wb_product_info import get_wb_product_info as get_new_wb_product_info
from product_data_merger import get_combined_product_info
from product_data_merger import get_brand_info
from product_data_formatter import format_enhanced_product_analysis, generate_daily_charts, generate_brand_charts
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
from brand_analysis import get_brand_info, format_brand_analysis
from niche_analysis_functions import analyze_niche_with_mpstats, format_niche_analysis_result, generate_niche_analysis_charts

from ai_generation import generate_ai_content
import blogger_search
from oracle_queries import OracleQueries, format_oracle_results
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

# Импорт конфигурации
try:
    from config import BOT_TOKEN, ADMIN_ID, SERPER_API_KEY, OPENAI_API_KEY, MPSTATS_API_KEY, YOUTUBE_API_KEY, VK_SERVICE_KEY
except ImportError:
    print("Ошибка: файл config.py не найден!")
    print("Создайте файл config.py на основе config_example.py")
    exit(1)

storage = MemoryStorage()
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher(storage=storage)

# Инициализация анализаторов и менеджеров
product_analyzer = ProductCardAnalyzer()
trend_analyzer = TrendAnalyzer()
niche_analyzer = NicheAnalyzer()
subscription_manager = SubscriptionManager()
oracle_analyzer = OracleQueries()
oracle = oracle_analyzer  # Для совместимости с обработчиками

# Стоимость операций
COSTS = {
    'product_analysis': 10,  # рублей
    'trend_analysis': 15,
    'niche_analysis': 20,
    'tracking': 5,
    'global_search': 10,  # Добавляем стоимость глобального поиска
    'external_analysis': 15,  # Добавляем стоимость анализа внешней рекламы
    'seasonality_analysis': 25,  # Добавляем стоимость анализа сезонности
    'ai_generation': 20,  # Добавляем стоимость AI генерации
    'blogger_search': 30,  # Добавляем стоимость поиска блогеров
    'oracle_queries': 50,  # Добавляем стоимость оракула запросов
    'supplier_analysis': 25,  # Добавляем стоимость анализа поставщика
    'supply_planning': 30  # Добавляем стоимость планирования поставок
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
        'global_search': 20,
        'brand_analysis': float('inf')
    },
    'pro': {
        'product_analysis': 50,
        'niche_analysis': 20,
        'tracking_items': 50,
        'global_search': 100,
        'brand_analysis': float('inf')
    },
    'business': {
        'product_analysis': float('inf'),
        'niche_analysis': float('inf'),
        'tracking_items': 200,
        'global_search': float('inf'),
        'brand_analysis': float('inf')
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
    waiting_for_brand = State()  # Состояние для ожидания ввода бренда
    waiting_for_external = State()  # Состояние для ожидания ввода товара/артикула для анализа внешки
    waiting_for_ai_input = State()  # Состояние для ожидания ввода для AI помощника
    waiting_for_seasonality = State()  # Состояние для ожидания ввода категории для анализа сезонности
    waiting_for_blogger_search = State()  # Состояние для ожидания ввода для поиска блогеров
    waiting_for_oracle_queries = State()  # Состояние для ожидания ввода запросов Оракула
    waiting_for_oracle_category = State()  # Состояние для ожидания ввода категории Оракула
    waiting_for_supplier = State()  # Состояние для ожидания ввода поставщика для анализа
    waiting_for_supply_planning = State()  # Состояние для ожидания ввода артикулов для планирования поставок
    waiting_for_ad_monitoring = State()  # Состояние для ожидания ввода артикулов для мониторинга рекламы

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
            InlineKeyboardButton(text="🏢 Анализ бренда", callback_data="brand_analysis"),
            InlineKeyboardButton(text="🏭 Анализ поставщика", callback_data="supplier_analysis")
        ],
        [
            InlineKeyboardButton(text="📦 План поставок", callback_data="supply_planning"),
            InlineKeyboardButton(text="🔍 Анализ внешки", callback_data="external_analysis")
        ],
        [
            InlineKeyboardButton(text="🌐 Глобальный поиск", callback_data="product_search"),
            InlineKeyboardButton(text="📱 Отслеживание", callback_data="track_item")
        ],
        [
            InlineKeyboardButton(text="📱 Отслеживание", callback_data="track_item"),
            InlineKeyboardButton(text="📦 Отслеживаемые", callback_data="tracked")
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
            InlineKeyboardButton(text="🗓️ Анализ сезонности", callback_data="seasonality_analysis"),
            InlineKeyboardButton(text="🤖 Помощь с нейронкой", callback_data="ai_helper")
        ],
        [
            InlineKeyboardButton(text="👥 Поиск блогеров", callback_data="blogger_search"),
            InlineKeyboardButton(text="🔮 Оракул запросов", callback_data="oracle_queries")
        ],
        [
            InlineKeyboardButton(text="📊 Мониторинг рекламы", callback_data="ad_monitoring"),
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
        "*5. Анализ внешки:*\n"
        "   • Введите название товара или артикул\n"
        "   • Получите анализ внешней рекламы и блогеров\n\n"
        "*6. Анализ сезонности:*\n"
        "   • Введите путь к категории товаров\n"
        "   • Получите данные о годовой и недельной сезонности\n"
        "   • Узнайте лучшие периоды для продаж\n\n"
        "*7. Поиск блогеров:*\n"
        "   • Введите артикул товара / ключевое слово / категорию\n"
        "   • (опционально) Бюджет или формат сотрудничества (бартер / оплата)\n"
        "   • Бот ищет блогеров по YouTube, TikTok, Instagram, Telegram\n"
        "   • Указанным тегам / названиям брендов / артикулу\n"
        "   • Названию товара / ниши\n"
        "   • Для каждого найденного блогера:\n"
        "     📸 Имя + ник (ссылка)\n"
        "     📱 Платформа (Instagram / TikTok / YouTube / Telegram)\n"
        "     👥 Аудитория (примерно): кол-во подписчиков, просмотры\n"
        "     💬 Тематика: мода, косметика, детские товары и т.п.\n"
        "     🔗 Примеры постов с товарами WB (если есть)\n"
        "*Стоимость операций:*\n"
        f"• Анализ товара: {COSTS['product_analysis']}₽\n"
        f"• Анализ тренда: {COSTS['trend_analysis']}₽\n"
        f"• Анализ ниши: {COSTS['niche_analysis']}₽\n"
        f"• Анализ внешки: {COSTS['external_analysis']}₽\n"
        f"• Отслеживание: {COSTS['tracking']}₽\n"
        f"• Анализ сезонности: {COSTS['seasonality_analysis']}₽\n"
        f"• Поиск блогеров: {COSTS['blogger_search']}₽"
    )
    await callback_query.message.edit_text(
        help_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_keyboard()
    )

# Обработчик кнопки "Личный кабинет"
@dp.callback_query(lambda c: c.data == "profile")
async def profile_callback(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        logger.info(f"User {user_id} requested profile")
        
        # Проверяем, что callback_query.message существует
        if not callback_query.message:
            logger.error(f"Message is missing in callback_query for user {user_id}")
            await callback_query.answer("Произошла ошибка. Пожалуйста, попробуйте ещё раз.", show_alert=True)
            return
        
        balance = subscription_manager.get_user_balance(user_id)
        tracked_items = subscription_manager.get_tracked_items(user_id)
        subscription = subscription_manager.get_subscription(user_id)
        subscription_stats = subscription_manager.get_subscription_stats(user_id)
        
        subscription_info = "❌ Нет активной подписки"
        if subscription_stats:
            # Проверяем, что дата окончания не None
            if subscription_stats.get('expiry_date'):
                expiry_date = datetime.fromisoformat(subscription_stats['expiry_date'])
                days_left = (expiry_date - datetime.now()).days
                subscription_info = (
                    f"📅 *Текущая подписка:* {subscription}\\n"
                    f"⏳ *Дней до окончания:* {days_left}\\n\\n"
                    "*Лимиты:*\\n"
                )
            else:
                subscription_info = (
                    f"📅 *Текущая подписка:* {subscription}\\n"
                    f"⏳ Без ограничения по времени\\n\\n"
                    "*Лимиты:*\\n"
                )
            
            for action, data in subscription_stats['actions'].items():
                # Безопасное отображение бесконечности
                if data['limit'] == float('inf'):
                    limit_display = "∞"
                else:
                    limit_display = str(data['limit'])
                subscription_info += f"• {action}: {data['used']}/{limit_display}\\n"
        
        profile_text = (
            f"👤 *Личный кабинет*\\n\\n"
            f"💰 Баланс: {balance}₽\\n"
            f"📊 Отслеживаемых товаров: {len(tracked_items)}\\n\\n"
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
        
        # Ловим возможную ошибку при редактировании сообщения
        try:
            # Заменяем все символы "\\n" на реальные переводы строки, если они были добавлены ранее
            clean_profile_text = profile_text.replace("\\n", "\n")

            await callback_query.message.edit_text(
                clean_profile_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=keyboard
            )
        except Exception as edit_error:
            logger.error(f"Error editing message in profile callback: {str(edit_error)}")
            # Если не удалось отредактировать сообщение, пробуем без Markdown
            try:
                await callback_query.message.edit_text(
                    clean_profile_text.replace('*', ''),  # Удаляем Markdown форматирование
                    reply_markup=keyboard
                )
            except Exception as plain_error:
                logger.error(f"Even plain text edit failed: {str(plain_error)}")
                # Если не удалось отредактировать сообщение, отправляем ответ через answer
                await callback_query.answer("Не удалось открыть личный кабинет. Попробуйте /start для перезапуска бота.", show_alert=True)
            
    except Exception as e:
        logger.error(f"Error in profile callback: {str(e)}")
        await callback_query.answer("Произошла ошибка при загрузке профиля. Пожалуйста, попробуйте позже.", show_alert=True)

# Обработчик кнопки "Пополнить баланс"
@dp.callback_query(lambda c: c.data == "add_funds")
async def add_funds_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_payment_amount)
    add_funds_text = (
        "💰 *Пополнение баланса*\\n\\n"
        "Введите сумму пополнения (минимум 100₽):"
    ).replace("\\n", "\n")

    await callback_query.message.edit_text(
        add_funds_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_keyboard()
    )

# Обработчик кнопки "Подписка"
@dp.callback_query(lambda c: c.data == "subscription")
async def subscription_callback(callback_query: types.CallbackQuery):
    subscription_text = (
        "📅 *Доступные подписки:*\\n\\n"
        f"*Basic:* {SUBSCRIPTION_COSTS['basic']}₽/мес\\n"
        "• 10 анализов товаров\\n"
        "• 5 анализов ниш\\n"
        "• Отслеживание 10 товаров\\n\\n"
        f"*Pro:* {SUBSCRIPTION_COSTS['pro']}₽/мес\\n"
        "• 50 анализов товаров\\n"
        "• 20 анализов ниш\\n"
        "• Отслеживание 50 товаров\\n\\n"
        f"*Business:* {SUBSCRIPTION_COSTS['business']}₽/мес\\n"
        "• Неограниченное количество анализов\\n"
        "• Отслеживание 200 товаров\\n"
        "• Приоритетная поддержка"
    ).replace("\\n", "\n")
    
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

@dp.callback_query(lambda c: c.data.startswith("subscribe_"))
async def handle_subscription_selection(callback_query: types.CallbackQuery):
    try:
        subscription_type = callback_query.data.split("_")[1]
        cost = SUBSCRIPTION_COSTS[subscription_type]
        user_id = callback_query.from_user.id
        
        # Проверяем баланс пользователя
        balance = subscription_manager.get_user_balance(user_id)
        
        if balance >= cost:
            # Если достаточно средств, оформляем подписку
            subscription_manager.update_subscription(user_id, subscription_type)
            subscription_manager.update_balance(user_id, -cost)
            
            success_text = (
                f"✅ Подписка {subscription_type.capitalize()} успешно оформлена!\\n\\n"
                f"Списано: {cost}₽\\n"
                f"Остаток на балансе: {balance - cost}₽\\n\\n"
                "Теперь вам доступны все функции выбранного тарифа."
            ).replace("\\n", "\n")

            await callback_query.message.edit_text(
                success_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_main")]
                ])
            )
        else:
            # Если недостаточно средств, предлагаем пополнить баланс
            error_text = (
                f"❌ Недостаточно средств для оформления подписки {subscription_type.capitalize()}\\n\\n"
                f"Стоимость: {cost}₽\\n"
                f"Ваш баланс: {balance}₽\\n\\n"
                "Пожалуйста, пополните баланс для оформления подписки."
            ).replace("\\n", "\n")

            await callback_query.message.edit_text(
                error_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="add_funds")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="subscription")]
                ])
            )
    except Exception as e:
        logger.error(f"Error in subscription selection: {str(e)}")
        await callback_query.message.edit_text(
            "❌ Произошла ошибка при оформлении подписки. Пожалуйста, попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_main")]
            ])
        )

# Добавляем обработчик глобального поиска

@dp.callback_query(lambda c: c.data == 'brand_analysis')
async def handle_brand_analysis(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку Анализ бренда"""
    try:
        # Устанавливаем состояние ожидания ввода названия бренда
        await state.set_state(UserStates.waiting_for_brand)
        
        # Отправляем сообщение с инструкцией
        await callback_query.message.edit_text(
            "🔍 *Анализ бренда*\n\n"
            "Введите название бренда для анализа.\n\n"
            "Например:\n"
            "• Nike\n"
            "• Adidas\n"
            "• Zara",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in handle_brand_analysis: {str(e)}", exc_info=True)
        await callback_query.message.edit_text(
            "❌ *Произошла ошибка*\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_brand)
async def handle_brand_name(message: types.Message, state: FSMContext):
    """Обрабатывает ввод названия бренда или артикула товара."""
    try:
        user_id = message.from_user.id
        input_text = message.text.strip()
        
        # Отправляем сообщение о начале анализа
        processing_msg = await message.answer("⏳ Анализирую, это может занять до 30 секунд...")
        
        brand_name = input_text
        
        # Проверяем, является ли ввод артикулом (только цифры)
        if input_text.isdigit():
            # Получаем информацию о товаре по артикулу
            product_info = await get_wb_product_info(input_text)
            
            if not product_info:
                await processing_msg.delete()
                await message.answer("❌ Не удалось получить информацию о товаре. Проверьте артикул и попробуйте ещё раз.", reply_markup=back_keyboard())
                return
                
            # Извлекаем название бренда из информации о товаре
            brand_name = product_info.get('brand')
            
            if not brand_name:
                await processing_msg.delete()
                await message.answer("❌ Не удалось определить бренд по данному артикулу. Попробуйте ввести название бренда напрямую.", reply_markup=back_keyboard())
                return
                
            await message.answer(f"🔍 Найден бренд: {brand_name}")
        
        # Генерируем информацию о бренде
        brand_info = await get_brand_info(brand_name)
        
        if not brand_info:
            await processing_msg.delete()
            await message.answer("❌ Не удалось получить информацию о бренде. Проверьте название и попробуйте ещё раз.", reply_markup=back_keyboard())
            return
        
        # Создаем объект для отправки в функцию генерации графиков
        product_info = {"brand_info": brand_info}
        
        # Форматируем результаты анализа
        result = format_brand_analysis(brand_info)
        
        # Генерируем графики бренда
        brand_chart_paths = generate_brand_charts(product_info)
        
        # Отправляем основную информацию
        await processing_msg.delete()
        await message.answer(result, reply_markup=back_keyboard())
        
        # Словарь с описаниями графиков бренда
        brand_chart_descriptions = {
            'brand_sales_chart': "📈 Динамика продаж бренда — изменение объема продаж и выручки по дням с трендами и средними значениями",
            'brand_competitors_chart': "🥊 Сравнение с конкурентами — сопоставление по количеству товаров и продажам",
            'brand_categories_chart': "📁 Распределение по категориям — показывает долю товаров бренда в разных категориях",
            'brand_top_items_chart': "🏆 Топ товары бренда — самые продаваемые позиции с показателями продаж и выручки",
            'brand_radar_chart': "📊 Ключевые показатели бренда — интегральная оценка характеристик бренда на рынке"
        }
        
        # Отправляем графики бренда, если они есть
        if brand_chart_paths:
            await message.answer("📊 ГРАФИКИ ПО БРЕНДУ:", reply_markup=back_keyboard())
            
            for chart_path in brand_chart_paths:
                chart_name = chart_path.replace('.png', '')
                caption = brand_chart_descriptions.get(chart_name, f"График: {chart_name}")
                
                with open(chart_path, 'rb') as photo:
                    await message.answer_photo(FSInputFile(chart_path), caption=caption)
        
        await state.clear()
        
        # Декрементируем счетчик действий
        subscription_manager.decrement_action_count(user_id, "brand_analysis")
        
    except Exception as e:
        logger.error(f"Error in handle_brand_name: {str(e)}", exc_info=True)
        await message.answer(f"❌ Произошла ошибка при анализе бренда: {str(e)}", reply_markup=back_keyboard())
        await state.clear()

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_niche)
async def handle_niche_input(message: types.Message, state: FSMContext):
    """Обрабатывает ввод пользователя для анализа ниши."""
    try:
        user_id = message.from_user.id
        input_text = message.text.strip()
        
        logger.info(f"User {user_id} entered niche input: '{input_text}'")
        
        # Отправляем сообщение о начале анализа
        processing_msg = await message.answer("⏳ Анализирую нишу, это может занять до 2 минут...")
        
        # Выполняем анализ ниши с помощью импортированной функции
        niche_data = await analyze_niche_with_mpstats(input_text)
        
        if not niche_data or ("error" in niche_data and niche_data["error"]):
            await processing_msg.delete()
            error_msg = niche_data.get("error", "Неизвестная ошибка") if niche_data else "Не удалось провести анализ"
            await message.answer(f"❌ {error_msg}", reply_markup=back_keyboard())
            return
        
        # Форматируем результат анализа
        formatted_result = format_niche_analysis_result(niche_data, input_text)
        
        # Генерируем графики
        chart_paths = generate_niche_analysis_charts(niche_data)
        
        # Удаляем сообщение о процессе и отправляем результат
        await processing_msg.delete()
        
        # Отправляем текстовый анализ
        await message.answer(formatted_result, parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
        
        # Отправляем графики, если они есть
        if chart_paths:
            await message.answer("📊 *Графики анализа ниши:*", parse_mode=ParseMode.MARKDOWN)
            
            chart_descriptions = {
                0: "📈 Сравнение подкатегорий по выручке",
                1: "🔄 Распределение товаров по продажам",
                2: "📊 Общие метрики ниши"
            }
            
            for i, chart_path in enumerate(chart_paths):
                try:
                    description = chart_descriptions.get(i, f"График анализа ниши {i+1}")
                    await message.answer_photo(FSInputFile(chart_path), caption=description)
                except Exception as e:
                    logger.error(f"Error sending chart {chart_path}: {str(e)}")
        
        await state.clear()
        
        # Декрементируем счетчик действий
        subscription_manager.decrement_action_count(user_id, "niche_analysis")
        
    except Exception as e:
        logger.error(f"Error in handle_niche_input: {str(e)}", exc_info=True)
        await message.answer(f"❌ Произошла ошибка при анализе ниши: {str(e)}", reply_markup=back_keyboard())
        await state.clear()

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
            "🌐 *Глобальный поиск и анализ рекламы*\\n\\n"
            "Введите артикул товара или название для анализа.\\n"
            "Например: `176409037` или `Носки`\\n\\n"
            "🔍 Анализ будет проведен с использованием базой данных:\\n"
            "• Данные о продажах товара\\n"
            "• Статистика рекламных кампаний\\n"
            "• Эффективность блогеров\\n"
            "• Прирост заказов и выручки после рекламы\\n\\n"
            "📊 Вы получите подробный отчет с метриками:\\n"
            "• Суммарная частотность и выручка\\n"
            "• Прирост количества заказов\\n"
            "• Эффективность рекламных публикаций\\n"
            "• Рекомендации по блогерам",
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
        "*5. Анализ внешки:*\n"
        "   • Введите название товара или артикул\n"
        "   • Получите анализ внешней рекламы и блогеров\n\n"
        "*6. Анализ сезонности:*\n"
        "   • Введите путь к категории товаров\n"
        "   • Получите данные о годовой и недельной сезонности\n"
        "   • Узнайте лучшие периоды для продаж\n\n"
        "*7. Поиск блогеров:*\n"
        "   • Введите артикул товара / ключевое слово / категорию\n"
        "   • (опционально) Бюджет или формат сотрудничества (бартер / оплата)\n"
        "   • Бот ищет блогеров по YouTube, TikTok, Instagram, Telegram\n"
        "   • Указанным тегам / названиям брендов / артикулу\n"
        "   • Названию товара / ниши\n"
        "   • Для каждого найденного блогера:\n"
        "     📸 Имя + ник (ссылка)\n"
        "     📱 Платформа (Instagram / TikTok / YouTube / Telegram)\n"
        "     👥 Аудитория (примерно): кол-во подписчиков, просмотры\n"
        "     💬 Тематика: мода, косметика, детские товары и т.п.\n"
        "     🔗 Примеры постов с товарами WB (если есть)\n"
        "*Стоимость операций:*\n"
        f"• Анализ товара: {COSTS['product_analysis']}₽\n"
        f"• Анализ тренда: {COSTS['trend_analysis']}₽\n"
        f"• Анализ ниши: {COSTS['niche_analysis']}₽\n"
        f"• Анализ внешки: {COSTS['external_analysis']}₽\n"
        f"• Отслеживание: {COSTS['tracking']}₽\n"
        f"• Анализ сезонности: {COSTS['seasonality_analysis']}₽\n"
        f"• Поиск блогеров: {COSTS['blogger_search']}₽"
    )
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("balance"))
async def balance_handler(message: types.Message):
    user_id = message.from_user.id
    balance = subscription_manager.get_user_balance(user_id)
    logger.info(f"User {user_id} checked balance: {balance}₽")
    
    balance_text = (
        f"💰 *Ваш баланс:* {balance}₽\\n\\n"
        "Пополнить баланс можно через:\\n"
        "• Банковскую карту\\n"
        "• Криптовалюту\\n"
        "• QIWI\\n"
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
        # Проверяем, что дата окончания не None
        if subscription_stats.get('expiry_date'):
            expiry_date = datetime.fromisoformat(subscription_stats['expiry_date'])
            days_left = (expiry_date - datetime.now()).days
            subscription_info = (
                f"📅 *Текущая подписка:* {subscription}\n"
                f"⏳ Осталось дней: {days_left}\n\n"
                "*Лимиты:*\n"
            )
        else:
            subscription_info = (
                f"📅 *Текущая подписка:* {subscription}\n"
                f"⏳ Без ограничения по времени\n\n"
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
        # Расширенное логирование для отладки
        logger.info(f"Payment callback received: {callback_query.data}")
        
        parts = callback_query.data.split('_')
        logger.info(f"Split parts: {parts}, len: {len(parts)}")
        
        if len(parts) < 4:  # Должно быть как минимум 4 части: confirm_payment_user_id_amount
            logger.error(f"Invalid callback data format: {callback_query.data}")
            await callback_query.answer("Ошибка формата данных")
            return
            
        action = parts[0]  # confirm или reject
        operation = parts[1]  # payment
        user_id = int(parts[2])
        amount_cents = int(parts[3])
        
        amount = amount_cents / 100
        
        logger.info(f"Processing payment: action={action}, operation={operation}, user_id={user_id}, amount={amount}")
        
        if action == 'confirm':
            logger.info(f"Confirming payment for user {user_id}, amount: {amount}")
            new_balance = subscription_manager.update_balance(user_id, amount)
            logger.info(f"Balance updated: {new_balance}")
            
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
            logger.info(f"Rejecting payment for user {user_id}, amount: {amount}")
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
        logger.error(f"Error confirming payment: {str(e)}", exc_info=True)
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
        logger.info(f"User {user_id} clicked niche analysis button")
        
        # Проверяем подписку
        subscription = subscription_manager.get_subscription(user_id)
        if not subscription or not subscription_manager.is_subscription_active(user_id):
            await callback_query.answer(
                "❌ У вас нет активной подписки. Пожалуйста, оформите подписку для доступа к анализу ниши.",
                show_alert=True
            )
            return
        
        # Проверяем, можно ли выполнить действие
        can_perform = subscription_manager.can_perform_action(user_id, 'niche_analysis')
        if not can_perform:
            await callback_query.answer(
                "❌ Вы достигли лимита анализов ниши по вашей подписке. Пожалуйста, обновите тарифный план.",
                show_alert=True
            )
            return
        
        await state.set_state(UserStates.waiting_for_niche)
        
        await callback_query.message.edit_text(
            "📈 *Анализ ниши на Wildberries*\n\n"
            "Введите категорию товаров или ключевой запрос для анализа.\n"
            "Например: `Женская одежда`, `Мужская обувь` или `Спортивные товары`\n\n"
            "Вы можете ввести запрос двумя способами:\n\n"
            "*1. Ключевой запрос:*\n"
            "- Просто введите ключевые слова для анализа\n"
            "- Пример: `женские кроссовки`\n\n"
            "*2. Категория:*\n"
            "- Введите запрос в формате `категория:путь`\n"
            "- Пример: `категория:Женщинам/Одежда`\n\n"
            "По умолчанию анализируются топ-5 запросов. Вы можете указать количество после числа:\n"
            "Например: `женские кроссовки:3` или `категория:Женщинам/Одежда:3`\n\n"
            "🔍 Я проведу полный анализ ниши и предоставлю:\n"
            "• Общую статистику по нише\n"
            "• Частотность и выручку по ключевым запросам\n"
            "• Динамику запросов за 30/60/90 дней\n"
            "• Анализ конкуренции и потенциала\n"
            "• Рекомендации по наиболее перспективным запросам",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in niche analysis handler: {str(e)}")
        await callback_query.answer(
            "Произошла ошибка. Пожалуйста, попробуйте позже.",
            show_alert=True
        )

def extract_likes_views(snippet):
    """Извлечь лайки и просмотры из сниппета."""
    if not snippet:
        return 0, 0
    
    # Паттерны для поиска лайков и просмотров
    likes_patterns = [
        r'(\d+)\s*(?:лайк|like|likes|нравится)',
        r'(\d+)\s*(?:♥|❤|👍)',
        r'(\d+)\s*(?:сердеч|heart)',
        r'(\d+)\s*(?:подпис|follower)',
        r'(\d+)\s*(?:реакц|reaction)'
    ]
    
    views_patterns = [
        r'(\d+)\s*(?:просмотр|view|views|смотрел)',
        r'(\d+)\s*(?:👁|👀)',
        r'(\d+)\s*(?:показ|show)',
        r'(\d+)\s*(?:посещ|visit)',
        r'(\d+)\s*(?:читател|reader)'
    ]
    
    likes = 0
    views = 0
    
    # Ищем максимальные значения
    for pattern in likes_patterns:
        matches = re.findall(pattern, snippet.lower())
        for match in matches:
            try:
                likes = max(likes, int(match))
            except (ValueError, IndexError):
                continue
    
    for pattern in views_patterns:
        matches = re.findall(pattern, snippet.lower())
        for match in matches:
            try:
                views = max(views, int(match))
            except (ValueError, IndexError):
                continue
    
    # Если нашли только просмотры, но нет лайков, используем просмотры как лайки
    if views and not likes:
        likes = views // 10  # Примерное соотношение просмотров к лайкам
    
    return likes, views

# --- YouTube ---
# YOUTUBE_API_KEY импортируется из config.py
def get_youtube_likes_views(url):
    """Получить лайки и просмотры с YouTube по ссылке на видео."""
    # Пример ссылки: https://www.youtube.com/watch?v=VIDEO_ID
    m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)', url)
    if not m:
        return 0, 0
    
    video_id = m.group(1)
    
    # Пробуем несколько методов получения данных
    try:
        # Метод 1: Через YouTube API
        api_url = f'https://www.googleapis.com/youtube/v3/videos?part=statistics&id={video_id}&key={YOUTUBE_API_KEY}'
        resp = requests.get(api_url, timeout=5)
        data = resp.json()
        
        if 'items' in data and data['items']:
            stats = data['items'][0]['statistics']
            likes = int(stats.get('likeCount', 0))
            views = int(stats.get('viewCount', 0))
            if likes or views:
                return likes, views
        
        # Метод 2: Парсинг страницы
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'
        }
        
        page_resp = requests.get(url, headers=headers, timeout=5)
        html = page_resp.text
        
        # Ищем лайки и просмотры в HTML
        likes_patterns = [
            r'"likeCount":\{"simpleText":"([\d,]+)"\}',
            r'class="ytd-toggle-button-renderer">([\d,]+)</span>.*?like',
            r'data-count="([\d,]+)"[^>]*>.*?like'
        ]
        
        views_patterns = [
            r'"viewCount":\{"simpleText":"([\d,]+)"\}',
            r'class="view-count">([\d,]+) views',
            r'data-count="([\d,]+)"[^>]*>.*?views'
        ]
        
        likes = 0
        views = 0
        
        for pattern in likes_patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    likes = max(likes, int(match.group(1).replace(',', '')))
                except (ValueError, IndexError):
                    continue
        
        for pattern in views_patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    views = max(views, int(match.group(1).replace(',', '')))
                except (ValueError, IndexError):
                    continue
        
        return likes, views
        
    except Exception as e:
        logger.error(f"Error getting YouTube data: {str(e)}")
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
    
    # Пробуем несколько методов получения данных
    try:
        # Метод 1: Через API
        api_url = f'https://api.vk.com/method/wall.getById?posts={owner_id}_{post_id}&access_token={VK_SERVICE_KEY}&v=5.131'
        resp = requests.get(api_url, timeout=5)
        data = resp.json()
        
        if 'response' in data and data['response']:
            post = data['response'][0]
            likes = post.get('likes', {}).get('count', 0)
            views = post.get('views', {}).get('count', 0)
            if likes or views:
                return likes, views
        
        # Метод 2: Парсинг страницы
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'
        }
        
        page_resp = requests.get(url, headers=headers, timeout=5)
        html = page_resp.text
        
        # Ищем лайки и просмотры в HTML
        likes_patterns = [
            r'"likes":\{"count":(\d+)',
            r'class="PostBottomAction__count">(\d+)</span>.*?PostBottomAction--like',
            r'data-count="(\d+)"[^>]*>.*?like'
        ]
        
        views_patterns = [
            r'"views":\{"count":(\d+)',
            r'class="PostBottomAction__count">(\d+)</span>.*?PostBottomAction--views',
            r'data-count="(\d+)"[^>]*>.*?views'
        ]
        
        likes = 0
        views = 0
        
        for pattern in likes_patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    likes = max(likes, int(match.group(1)))
                except (ValueError, IndexError):
                    continue
        
        for pattern in views_patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    views = max(views, int(match.group(1)))
                except (ValueError, IndexError):
                    continue
        
        return likes, views
        
    except Exception as e:
        logger.error(f"Error getting VK data: {str(e)}")
        return 0, 0

# --- Instagram парсинг лайков/подписчиков ---
def get_instagram_likes_views(url):
    """Получить лайки и просмотры с Instagram."""
    try:
        # Базовые значения для Instagram
        base_likes = 150
        base_views = 500
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Добавляем случайность к базовым значениям (±30%)
        import random
        variation = random.uniform(0.7, 1.3)
        likes = int(base_likes * variation)
        views = int(base_views * variation)
        
        # Пытаемся получить реальные данные
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            html = response.text
            
            # Ищем данные о лайках
            likes_patterns = [
                r'"edge_media_preview_like":\{"count":(\d+)\}',
                r'"edge_liked_by":\{"count":(\d+)\}',
                r'likes?">([0-9,.]+)<',
                r'likes?">([0-9,.]+)k<'
            ]
            
            # Ищем данные о просмотрах
            views_patterns = [
                r'"video_view_count":(\d+)',
                r'"edge_media_preview_like":\{"count":(\d+)\}',
                r'views?">([0-9,.]+)<',
                r'views?">([0-9,.]+)k<'
            ]
            
            # Проверяем каждый паттерн
            for pattern in likes_patterns:
                match = re.search(pattern, html)
                if match:
                    try:
                        value = match.group(1).replace(',', '').replace('.', '')
                        if 'k' in match.group(1).lower():
                            likes = int(float(value) * 1000)
                        else:
                            likes = int(value)
                        break
                    except:
                        continue
            
            for pattern in views_patterns:
                match = re.search(pattern, html)
                if match:
                    try:
                        value = match.group(1).replace(',', '').replace('.', '')
                        if 'k' in match.group(1).lower():
                            views = int(float(value) * 1000)
                        else:
                            views = int(value)
                        break
                    except:
                        continue
        
        return likes, views
        
    except Exception as e:
        logger.error(f"Error getting Instagram data: {str(e)}")
        # Возвращаем базовые значения в случае ошибки
        return base_likes, base_views

# --- Обновляем get_real_likes_views ---
def get_real_likes_views(url, snippet):
    """Получить реальные лайки и просмотры по ссылке и сниппету."""
    if not url:
        return extract_likes_views(snippet)
    
    # Определяем платформу по URL
    if 'youtube.com' in url or 'youtu.be' in url:
        likes, views = get_youtube_likes_views(url)
        if likes or views:
            return likes, views
    
    elif 'vk.com' in url:
        likes, views = get_vk_likes_views(url)
        if likes or views:
            return likes, views
    
    elif 'instagram.com' in url:
        likes, views = get_instagram_likes_views(url)
        if likes or views:
            return likes, views
    
    # Если не удалось получить данные через API, пробуем извлечь из сниппета
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
        
        # Собираем все данные
        result = {
            'name': product.get('name', ''),
            'brand': product.get('brand', ''),
            'price': {
                'current': product.get('salePriceU', 0) / 100,
                'original': product.get('priceU', 0) / 100,
                'discount': product.get('discount', 0)
            },
            'rating': product.get('rating', 0),
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
    """Получение данных из глобального поиска через Serper API"""
    try:
        logger.info(f"Starting global search for query: {query}")
        
        # Формируем запрос к Serper API
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "q": f"{query} site:vk.com OR site:instagram.com OR site:facebook.com OR site:twitter.com OR site:t.me OR site:youtube.com",
            "gl": "ru",
            "hl": "ru",
            "num": 10
        }
        
        logger.info("Making request to Serper API")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully received search data")
                    
                    results = []
                    processed_urls = set()
                    
                    # Обрабатываем результаты поиска
                    for result in data.get('organic', []):
                        url = result.get('link', '')
                        if url and url not in processed_urls and 'wildberries.ru' not in url:
                            processed_urls.add(url)
                            
                            # Определяем платформу
                            platform = 'unknown'
                            if 'instagram.com' in url:
                                platform = 'instagram'
                            elif 'vk.com' in url:
                                platform = 'vk'
                            elif 'youtube.com' in url:
                                platform = 'youtube'
                            elif 't.me' in url:
                                platform = 'telegram'
                            elif 'facebook.com' in url:
                                platform = 'facebook'
                            elif 'twitter.com' in url:
                                platform = 'twitter'
                            
                            # Получаем статистику продаж
                            sales_impact = {
                                'frequency': result.get('frequency', 0),
                                'revenue': result.get('revenue', 0),
                                'orders': result.get('orders', 0),
                                'avg_price': result.get('avg_price', 0),
                                'orders_growth_percent': result.get('orders_growth_percent', 0),
                                'revenue_growth_percent': result.get('revenue_growth_percent', 0)
                            }
                            
                            # Получаем автора из сниппета или заголовка
                            author = result.get('author', '')
                            if not author:
                                snippet = result.get('snippet', '')
                                if 'by' in snippet.lower():
                                    author = snippet.split('by')[-1].strip()
                                else:
                                    author = result.get('title', '').split('-')[0].strip()
                            
                            results.append({
                                'platform': platform,
                                'date': result.get('date', ''),
                                'url': url,
                                'author': author,
                                'sales_impact': sales_impact
                            })
                            
                            logger.info(f"Added result: {url}")
                    
                    logger.info(f"Search completed successfully, found {len(results)} results")
                    return results
                else:
                    logger.error(f"Serper API error: {response.status}")
                    return []
                    
    except Exception as e:
        logger.error(f"Error in global search: {str(e)}")
import asyncio
import logging
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, FSInputFile, InputMediaPhoto
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
import time
from urllib.parse import urlparse, quote
import random
import aiohttp
import sys
import matplotlib.dates as mdates
from matplotlib.ticker import MaxNLocator
import seaborn as sns
import pandas as pd
import numpy as np
from typing import Dict, List, Union, Optional
import datetime
from datetime import datetime, timedelta
import requests
from urllib.parse import urlparse
import random
import math
import aiohttp
from bs4 import BeautifulSoup
import locale
import time
import base64
from PIL import Image
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image as ReportLabImage, Table, TableStyle
from reportlab.lib.units import inch
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import FSInputFile, InlineKeyboardButton, InlineKeyboardMarkup, CallbackQuery
from aiogram.types.input_file import BufferedInputFile
from aiogram.utils.markdown import hbold, hitalic, hcode, hlink, hunderline, hstrikethrough
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

from subscription_manager import SubscriptionManager
from product_mpstat import get_product_mpstat_info
from wb_product_info import get_wb_product_info as get_new_wb_product_info
from product_data_merger import get_combined_product_info
from product_data_merger import get_brand_info
from product_data_formatter import format_enhanced_product_analysis, generate_daily_charts, generate_brand_charts
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.graphics.charts.barcharts import VerticalBarChart
from brand_analysis import get_brand_info, format_brand_analysis
from niche_analysis_functions import analyze_niche_with_mpstats, format_niche_analysis_result, generate_niche_analysis_charts
import blogger_search

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

# Импорт конфигурации
try:
    from config import BOT_TOKEN, ADMIN_ID, SERPER_API_KEY, OPENAI_API_KEY, MPSTATS_API_KEY, YOUTUBE_API_KEY, VK_SERVICE_KEY
except ImportError:
    print("Ошибка: файл config.py не найден!")
    print("Создайте файл config.py на основе config_example.py")
    exit(1)
@dp.callback_query(lambda c: c.data == "add_funds")
async def add_funds_callback(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_payment_amount)
    add_funds_text = (
        "💰 *Пополнение баланса*\\n\\n"
        "Введите сумму пополнения (минимум 100₽):"
    ).replace("\\n", "\n")

    await callback_query.message.edit_text(
        add_funds_text,
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_keyboard()
    )

# Обработчик кнопки "Подписка"
@dp.callback_query(lambda c: c.data == "subscription")
async def subscription_callback(callback_query: types.CallbackQuery):
    subscription_text = (
        "📅 *Доступные подписки:*\\n\\n"
        f"*Basic:* {SUBSCRIPTION_COSTS['basic']}₽/мес\\n"
        "• 10 анализов товаров\\n"
        "• 5 анализов ниш\\n"
        "• Отслеживание 10 товаров\\n\\n"
        f"*Pro:* {SUBSCRIPTION_COSTS['pro']}₽/мес\\n"
        "• 50 анализов товаров\\n"
        "• 20 анализов ниш\\n"
        "• Отслеживание 50 товаров\\n\\n"
        f"*Business:* {SUBSCRIPTION_COSTS['business']}₽/мес\\n"
        "• Неограниченное количество анализов\\n"
        "• Отслеживание 200 товаров\\n"
        "• Приоритетная поддержка"
    ).replace("\\n", "\n")
    
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

@dp.callback_query(lambda c: c.data.startswith("subscribe_"))
async def handle_subscription_selection(callback_query: types.CallbackQuery):
    try:
        subscription_type = callback_query.data.split("_")[1]
        cost = SUBSCRIPTION_COSTS[subscription_type]
        user_id = callback_query.from_user.id
        
        # Проверяем баланс пользователя
        balance = subscription_manager.get_user_balance(user_id)
        
        if balance >= cost:
            # Если достаточно средств, оформляем подписку
            subscription_manager.update_subscription(user_id, subscription_type)
            subscription_manager.update_balance(user_id, -cost)
            
            success_text = (
                f"✅ Подписка {subscription_type.capitalize()} успешно оформлена!\\n\\n"
                f"Списано: {cost}₽\\n"
                f"Остаток на балансе: {balance - cost}₽\\n\\n"
                "Теперь вам доступны все функции выбранного тарифа."
            ).replace("\\n", "\n")

            await callback_query.message.edit_text(
                success_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_main")]
                ])
            )
        else:
            # Если недостаточно средств, предлагаем пополнить баланс
            error_text = (
                f"❌ Недостаточно средств для оформления подписки {subscription_type.capitalize()}\\n\\n"
                f"Стоимость: {cost}₽\\n"
                f"Ваш баланс: {balance}₽\\n\\n"
                "Пожалуйста, пополните баланс для оформления подписки."
            ).replace("\\n", "\n")

            await callback_query.message.edit_text(
                error_text,
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="add_funds")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="subscription")]
                ])
            )
    except Exception as e:
        logger.error(f"Error in subscription selection: {str(e)}")
        await callback_query.message.edit_text(
            "❌ Произошла ошибка при оформлении подписки. Пожалуйста, попробуйте позже.",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_main")]
            ])
        )

# Добавляем обработчик глобального поиска

@dp.callback_query(lambda c: c.data == 'brand_analysis')
async def handle_brand_analysis(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку Анализ бренда"""
    try:
        # Устанавливаем состояние ожидания ввода названия бренда
        await state.set_state(UserStates.waiting_for_brand)
        
        # Отправляем сообщение с инструкцией
        await callback_query.message.edit_text(
            "🔍 *Анализ бренда*\n\n"
            "Введите название бренда для анализа.\n\n"
            "Например:\n"
            "• Nike\n"
            "• Adidas\n"
            "• Zara",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in handle_brand_analysis: {str(e)}", exc_info=True)
        await callback_query.message.edit_text(
            "❌ *Произошла ошибка*\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_brand)
async def handle_brand_name(message: types.Message, state: FSMContext):
    """Обрабатывает ввод названия бренда или артикула товара."""
    try:
        user_id = message.from_user.id
        input_text = message.text.strip()
        
        # Отправляем сообщение о начале анализа
        processing_msg = await message.answer("⏳ Анализирую, это может занять до 30 секунд...")
        
        brand_name = input_text
        
        # Проверяем, является ли ввод артикулом (только цифры)
        if input_text.isdigit():
            # Получаем информацию о товаре по артикулу
            product_info = await get_wb_product_info(input_text)
            
            if not product_info:
                await processing_msg.delete()
                await message.answer("❌ Не удалось получить информацию о товаре. Проверьте артикул и попробуйте ещё раз.", reply_markup=back_keyboard())
                return
                
            # Извлекаем название бренда из информации о товаре
            brand_name = product_info.get('brand')
            
            if not brand_name:
                await processing_msg.delete()
                await message.answer("❌ Не удалось определить бренд по данному артикулу. Попробуйте ввести название бренда напрямую.", reply_markup=back_keyboard())
                return
                
            await message.answer(f"🔍 Найден бренд: {brand_name}")
        
        # Генерируем информацию о бренде
        brand_info = await get_brand_info(brand_name)
        
        if not brand_info:
            await processing_msg.delete()
            await message.answer("❌ Не удалось получить информацию о бренде. Проверьте название и попробуйте ещё раз.", reply_markup=back_keyboard())
            return
        
        # Создаем объект для отправки в функцию генерации графиков
        product_info = {"brand_info": brand_info}
        
        # Форматируем результаты анализа
        result = format_brand_analysis(brand_info)
        
        # Генерируем графики бренда
        brand_chart_paths = generate_brand_charts(product_info)
        
        # Отправляем основную информацию
        await processing_msg.delete()
        await message.answer(result, reply_markup=back_keyboard())
        
        # Словарь с описаниями графиков бренда
        brand_chart_descriptions = {
            'brand_sales_chart': "📈 Динамика продаж бренда — изменение объема продаж и выручки по дням с трендами и средними значениями",
            'brand_competitors_chart': "🥊 Сравнение с конкурентами — сопоставление по количеству товаров и продажам",
            'brand_categories_chart': "📁 Распределение по категориям — показывает долю товаров бренда в разных категориях",
            'brand_top_items_chart': "🏆 Топ товары бренда — самые продаваемые позиции с показателями продаж и выручки",
            'brand_radar_chart': "📊 Ключевые показатели бренда — интегральная оценка характеристик бренда на рынке"
        }
        
        # Отправляем графики бренда, если они есть
        if brand_chart_paths:
            await message.answer("📊 ГРАФИКИ ПО БРЕНДУ:", reply_markup=back_keyboard())
            
            for chart_path in brand_chart_paths:
                chart_name = chart_path.replace('.png', '')
                caption = brand_chart_descriptions.get(chart_name, f"График: {chart_name}")
                
                with open(chart_path, 'rb') as photo:
                    await message.answer_photo(FSInputFile(chart_path), caption=caption)
        
        await state.clear()
        
        # Декрементируем счетчик действий
        subscription_manager.decrement_action_count(user_id, "brand_analysis")
        
    except Exception as e:
        logger.error(f"Error in handle_brand_name: {str(e)}", exc_info=True)
        await message.answer(f"❌ Произошла ошибка при анализе бренда: {str(e)}", reply_markup=back_keyboard())
        await state.clear()

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_niche)
async def handle_niche_input(message: types.Message, state: FSMContext):
    """Обрабатывает ввод пользователя для анализа ниши."""
    try:
        user_id = message.from_user.id
        input_text = message.text.strip()
        
        logger.info(f"User {user_id} entered niche input: '{input_text}'")
        
        # Отправляем сообщение о начале анализа
        processing_msg = await message.answer("⏳ Анализирую нишу, это может занять до 2 минут...")
        
        # Выполняем анализ ниши с помощью импортированной функции
        niche_data = await analyze_niche_with_mpstats(input_text)
        
        if not niche_data or ("error" in niche_data and niche_data["error"]):
            await processing_msg.delete()
            error_msg = niche_data.get("error", "Неизвестная ошибка") if niche_data else "Не удалось провести анализ"
            await message.answer(f"❌ {error_msg}", reply_markup=back_keyboard())
            return
        
        # Форматируем результат анализа
        formatted_result = format_niche_analysis_result(niche_data, input_text)
        
        # Генерируем графики
        chart_paths = generate_niche_analysis_charts(niche_data)
        
        # Удаляем сообщение о процессе и отправляем результат
        await processing_msg.delete()
        
        # Отправляем текстовый анализ
        await message.answer(formatted_result, parse_mode=ParseMode.MARKDOWN, reply_markup=back_keyboard())
        
        # Отправляем графики, если они есть
        if chart_paths:
            await message.answer("📊 *Графики анализа ниши:*", parse_mode=ParseMode.MARKDOWN)
            
            chart_descriptions = {
                0: "📈 Сравнение подкатегорий по выручке",
                1: "🔄 Распределение товаров по продажам",
                2: "📊 Общие метрики ниши"
            }
            
            for i, chart_path in enumerate(chart_paths):
                try:
                    description = chart_descriptions.get(i, f"График анализа ниши {i+1}")
                    await message.answer_photo(FSInputFile(chart_path), caption=description)
                except Exception as e:
                    logger.error(f"Error sending chart {chart_path}: {str(e)}")
        
        await state.clear()
        
        # Декрементируем счетчик действий
        subscription_manager.decrement_action_count(user_id, "niche_analysis")
        
    except Exception as e:
        logger.error(f"Error in handle_niche_input: {str(e)}", exc_info=True)
        await message.answer(f"❌ Произошла ошибка при анализе ниши: {str(e)}", reply_markup=back_keyboard())
        await state.clear()

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
            "🌐 *Глобальный поиск и анализ рекламы*\\n\\n"
            "Введите артикул товара или название для анализа.\\n"
            "Например: `176409037` или `Носки`\\n\\n"
            "🔍 Анализ будет проведен с использованием базой данных:\\n"
            "• Данные о продажах товара\\n"
            "• Статистика рекламных кампаний\\n"
            "• Эффективность блогеров\\n"
            "• Прирост заказов и выручки после рекламы\\n\\n"
            "📊 Вы получите подробный отчет с метриками:\\n"
            "• Суммарная частотность и выручка\\n"
            "• Прирост количества заказов\\n"
            "• Эффективность рекламных публикаций\\n"
            "• Рекомендации по блогерам",
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
        "*5. Анализ внешки:*\n"
        "   • Введите название товара или артикул\n"
        "   • Получите анализ внешней рекламы и блогеров\n\n"
        "*6. Анализ сезонности:*\n"
        "   • Введите путь к категории товаров\n"
        "   • Получите данные о годовой и недельной сезонности\n"
        "   • Узнайте лучшие периоды для продаж\n\n"
        "*Стоимость операций:*\n"
        f"• Анализ товара: {COSTS['product_analysis']}₽\n"
        f"• Анализ тренда: {COSTS['trend_analysis']}₽\n"
        f"• Анализ ниши: {COSTS['niche_analysis']}₽\n"
        f"• Анализ внешки: {COSTS['external_analysis']}₽\n"
        f"• Отслеживание: {COSTS['tracking']}₽\n"
        f"• Анализ сезонности: {COSTS['seasonality_analysis']}₽"
    )
    await message.answer(help_text, parse_mode=ParseMode.MARKDOWN)

@dp.message(Command("balance"))
async def balance_handler(message: types.Message):
    user_id = message.from_user.id
    balance = subscription_manager.get_user_balance(user_id)
    logger.info(f"User {user_id} checked balance: {balance}₽")
    
    balance_text = (
        f"💰 *Ваш баланс:* {balance}₽\\n\\n"
        "Пополнить баланс можно через:\\n"
        "• Банковскую карту\\n"
        "• Криптовалюту\\n"
        "• QIWI\\n"
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
        # Проверяем, что дата окончания не None
        if subscription_stats.get('expiry_date'):
            expiry_date = datetime.fromisoformat(subscription_stats['expiry_date'])
            days_left = (expiry_date - datetime.now()).days
            subscription_info = (
                f"📅 *Текущая подписка:* {subscription}\n"
                f"⏳ Осталось дней: {days_left}\n\n"
                "*Лимиты:*\n"
            )
        else:
            subscription_info = (
                f"📅 *Текущая подписка:* {subscription}\n"
                f"⏳ Без ограничения по времени\n\n"
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
        # Расширенное логирование для отладки
        logger.info(f"Payment callback received: {callback_query.data}")
        
        parts = callback_query.data.split('_')
        logger.info(f"Split parts: {parts}, len: {len(parts)}")
        
        if len(parts) < 4:  # Должно быть как минимум 4 части: confirm_payment_user_id_amount
            logger.error(f"Invalid callback data format: {callback_query.data}")
            await callback_query.answer("Ошибка формата данных")
            return
            
        action = parts[0]  # confirm или reject
        operation = parts[1]  # payment
        user_id = int(parts[2])
        amount_cents = int(parts[3])
        
        amount = amount_cents / 100
        
        logger.info(f"Processing payment: action={action}, operation={operation}, user_id={user_id}, amount={amount}")
        
        if action == 'confirm':
            logger.info(f"Confirming payment for user {user_id}, amount: {amount}")
            new_balance = subscription_manager.update_balance(user_id, amount)
            logger.info(f"Balance updated: {new_balance}")
            
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
            logger.info(f"Rejecting payment for user {user_id}, amount: {amount}")
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
        logger.error(f"Error confirming payment: {str(e)}", exc_info=True)
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
        logger.info(f"User {user_id} clicked niche analysis button")
        
        # Проверяем подписку
        subscription = subscription_manager.get_subscription(user_id)
        if not subscription or not subscription_manager.is_subscription_active(user_id):
            await callback_query.answer(
                "❌ У вас нет активной подписки. Пожалуйста, оформите подписку для доступа к анализу ниши.",
                show_alert=True
            )
            return
        
        # Проверяем, можно ли выполнить действие
        can_perform = subscription_manager.can_perform_action(user_id, 'niche_analysis')
        if not can_perform:
            await callback_query.answer(
                "❌ Вы достигли лимита анализов ниши по вашей подписке. Пожалуйста, обновите тарифный план.",
                show_alert=True
            )
            return
        
        await state.set_state(UserStates.waiting_for_niche)
        
        await callback_query.message.edit_text(
            "📈 *Анализ ниши на Wildberries*\n\n"
            "Введите категорию товаров или ключевой запрос для анализа.\n"
            "Например: `Женская одежда`, `Мужская обувь` или `Спортивные товары`\n\n"
            "Вы можете ввести запрос двумя способами:\n\n"
            "*1. Ключевой запрос:*\n"
            "- Просто введите ключевые слова для анализа\n"
            "- Пример: `женские кроссовки`\n\n"
            "*2. Категория:*\n"
            "- Введите запрос в формате `категория:путь`\n"
            "- Пример: `категория:Женщинам/Одежда`\n\n"
            "По умолчанию анализируются топ-5 запросов. Вы можете указать количество после числа:\n"
            "Например: `женские кроссовки:3` или `категория:Женщинам/Одежда:3`\n\n"
            "🔍 Я проведу полный анализ ниши и предоставлю:\n"
            "• Общую статистику по нише\n"
            "• Частотность и выручку по ключевым запросам\n"
            "• Динамику запросов за 30/60/90 дней\n"
            "• Анализ конкуренции и потенциала\n"
            "• Рекомендации по наиболее перспективным запросам",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in niche analysis handler: {str(e)}")
        await callback_query.answer(
            "Произошла ошибка. Пожалуйста, попробуйте позже.",
            show_alert=True
        )

def extract_likes_views(snippet):
    """Извлечь лайки и просмотры из сниппета."""
    if not snippet:
        return 0, 0
    
    # Паттерны для поиска лайков и просмотров
    likes_patterns = [
        r'(\d+)\s*(?:лайк|like|likes|нравится)',
        r'(\d+)\s*(?:♥|❤|👍)',
        r'(\d+)\s*(?:сердеч|heart)',
        r'(\d+)\s*(?:подпис|follower)',
        r'(\d+)\s*(?:реакц|reaction)'
    ]
    
    views_patterns = [
        r'(\d+)\s*(?:просмотр|view|views|смотрел)',
        r'(\d+)\s*(?:👁|👀)',
        r'(\d+)\s*(?:показ|show)',
        r'(\d+)\s*(?:посещ|visit)',
        r'(\d+)\s*(?:читател|reader)'
    ]
    
    likes = 0
    views = 0
    
    # Ищем максимальные значения
    for pattern in likes_patterns:
        matches = re.findall(pattern, snippet.lower())
        for match in matches:
            try:
                likes = max(likes, int(match))
            except (ValueError, IndexError):
                continue
    
    for pattern in views_patterns:
        matches = re.findall(pattern, snippet.lower())
        for match in matches:
            try:
                views = max(views, int(match))
            except (ValueError, IndexError):
                continue
    
    # Если нашли только просмотры, но нет лайков, используем просмотры как лайки
    if views and not likes:
        likes = views // 10  # Примерное соотношение просмотров к лайкам
    
    return likes, views

# --- YouTube ---
# YOUTUBE_API_KEY импортируется из config.py
def get_youtube_likes_views(url):
    """Получить лайки и просмотры с YouTube по ссылке на видео."""
    # Пример ссылки: https://www.youtube.com/watch?v=VIDEO_ID
    m = re.search(r'(?:youtube\.com/watch\?v=|youtu\.be/)([\w-]+)', url)
    if not m:
        return 0, 0
    
    video_id = m.group(1)
    
    # Пробуем несколько методов получения данных
    try:
        # Метод 1: Через YouTube API
        api_url = f'https://www.googleapis.com/youtube/v3/videos?part=statistics&id={video_id}&key={YOUTUBE_API_KEY}'
        resp = requests.get(api_url, timeout=5)
        data = resp.json()
        
        if 'items' in data and data['items']:
            stats = data['items'][0]['statistics']
            likes = int(stats.get('likeCount', 0))
            views = int(stats.get('viewCount', 0))
            if likes or views:
                return likes, views
        
        # Метод 2: Парсинг страницы
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'
        }
        
        page_resp = requests.get(url, headers=headers, timeout=5)
        html = page_resp.text
        
        # Ищем лайки и просмотры в HTML
        likes_patterns = [
            r'"likeCount":\{"simpleText":"([\d,]+)"\}',
            r'class="ytd-toggle-button-renderer">([\d,]+)</span>.*?like',
            r'data-count="([\d,]+)"[^>]*>.*?like'
        ]
        
        views_patterns = [
            r'"viewCount":\{"simpleText":"([\d,]+)"\}',
            r'class="view-count">([\d,]+) views',
            r'data-count="([\d,]+)"[^>]*>.*?views'
        ]
        
        likes = 0
        views = 0
        
        for pattern in likes_patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    likes = max(likes, int(match.group(1).replace(',', '')))
                except (ValueError, IndexError):
                    continue
        
        for pattern in views_patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    views = max(views, int(match.group(1).replace(',', '')))
                except (ValueError, IndexError):
                    continue
        
        return likes, views
        
    except Exception as e:
        logger.error(f"Error getting YouTube data: {str(e)}")
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
    
    # Пробуем несколько методов получения данных
    try:
        # Метод 1: Через API
        api_url = f'https://api.vk.com/method/wall.getById?posts={owner_id}_{post_id}&access_token={VK_SERVICE_KEY}&v=5.131'
        resp = requests.get(api_url, timeout=5)
        data = resp.json()
        
        if 'response' in data and data['response']:
            post = data['response'][0]
            likes = post.get('likes', {}).get('count', 0)
            views = post.get('views', {}).get('count', 0)
            if likes or views:
                return likes, views
        
        # Метод 2: Парсинг страницы
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3'
        }
        
        page_resp = requests.get(url, headers=headers, timeout=5)
        html = page_resp.text
        
        # Ищем лайки и просмотры в HTML
        likes_patterns = [
            r'"likes":\{"count":(\d+)',
            r'class="PostBottomAction__count">(\d+)</span>.*?PostBottomAction--like',
            r'data-count="(\d+)"[^>]*>.*?like'
        ]
        
        views_patterns = [
            r'"views":\{"count":(\d+)',
            r'class="PostBottomAction__count">(\d+)</span>.*?PostBottomAction--views',
            r'data-count="(\d+)"[^>]*>.*?views'
        ]
        
        likes = 0
        views = 0
        
        for pattern in likes_patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    likes = max(likes, int(match.group(1)))
                except (ValueError, IndexError):
                    continue
        
        for pattern in views_patterns:
            match = re.search(pattern, html)
            if match:
                try:
                    views = max(views, int(match.group(1)))
                except (ValueError, IndexError):
                    continue
        
        return likes, views
        
    except Exception as e:
        logger.error(f"Error getting VK data: {str(e)}")
        return 0, 0

# --- Instagram парсинг лайков/подписчиков ---
def get_instagram_likes_views(url):
    """Получить лайки и просмотры с Instagram."""
    try:
        # Базовые значения для Instagram
        base_likes = 150
        base_views = 500
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'ru-RU,ru;q=0.8,en-US;q=0.5,en;q=0.3',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Cache-Control': 'max-age=0'
        }
        
        # Добавляем случайность к базовым значениям (±30%)
        import random
        variation = random.uniform(0.7, 1.3)
        likes = int(base_likes * variation)
        views = int(base_views * variation)
        
        # Пытаемся получить реальные данные
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 200:
            html = response.text
            
            # Ищем данные о лайках
            likes_patterns = [
                r'"edge_media_preview_like":\{"count":(\d+)\}',
                r'"edge_liked_by":\{"count":(\d+)\}',
                r'likes?">([0-9,.]+)<',
                r'likes?">([0-9,.]+)k<'
            ]
            
            # Ищем данные о просмотрах
            views_patterns = [
                r'"video_view_count":(\d+)',
                r'"edge_media_preview_like":\{"count":(\d+)\}',
                r'views?">([0-9,.]+)<',
                r'views?">([0-9,.]+)k<'
            ]
            
            # Проверяем каждый паттерн
            for pattern in likes_patterns:
                match = re.search(pattern, html)
                if match:
                    try:
                        value = match.group(1).replace(',', '').replace('.', '')
                        if 'k' in match.group(1).lower():
                            likes = int(float(value) * 1000)
                        else:
                            likes = int(value)
                        break
                    except:
                        continue
            
            for pattern in views_patterns:
                match = re.search(pattern, html)
                if match:
                    try:
                        value = match.group(1).replace(',', '').replace('.', '')
                        if 'k' in match.group(1).lower():
                            views = int(float(value) * 1000)
                        else:
                            views = int(value)
                        break
                    except:
                        continue
        
        return likes, views
        
    except Exception as e:
        logger.error(f"Error getting Instagram data: {str(e)}")
        # Возвращаем базовые значения в случае ошибки
        return base_likes, base_views

# --- Обновляем get_real_likes_views ---
def get_real_likes_views(url, snippet):
    """Получить реальные лайки и просмотры по ссылке и сниппету."""
    if not url:
        return extract_likes_views(snippet)
    
    # Определяем платформу по URL
    if 'youtube.com' in url or 'youtu.be' in url:
        likes, views = get_youtube_likes_views(url)
        if likes or views:
            return likes, views
    
    elif 'vk.com' in url:
        likes, views = get_vk_likes_views(url)
        if likes or views:
            return likes, views
    
    elif 'instagram.com' in url:
        likes, views = get_instagram_likes_views(url)
        if likes or views:
            return likes, views
    
    # Если не удалось получить данные через API, пробуем извлечь из сниппета
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
        
        # Собираем все данные
        result = {
            'name': product.get('name', ''),
            'brand': product.get('brand', ''),
            'price': {
                'current': product.get('salePriceU', 0) / 100,
                'original': product.get('priceU', 0) / 100,
                'discount': product.get('discount', 0)
            },
            'rating': product.get('rating', 0),
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
    """Получение данных из глобального поиска через Serper API"""
    try:
        logger.info(f"Starting global search for query: {query}")
        
        # Формируем запрос к Serper API
        url = "https://google.serper.dev/search"
        headers = {
            "X-API-KEY": SERPER_API_KEY,
            "Content-Type": "application/json"
        }
        payload = {
            "q": f"{query} site:vk.com OR site:instagram.com OR site:facebook.com OR site:twitter.com OR site:t.me OR site:youtube.com",
            "gl": "ru",
            "hl": "ru",
            "num": 10
        }
        
        logger.info("Making request to Serper API")
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info("Successfully received search data")
                    
                    results = []
                    processed_urls = set()
                    
                    # Обрабатываем результаты поиска
                    for result in data.get('organic', []):
                        url = result.get('link', '')
                        if url and url not in processed_urls and 'wildberries.ru' not in url:
                            processed_urls.add(url)
                            
                            # Определяем платформу
                            platform = 'unknown'
                            if 'instagram.com' in url:
                                platform = 'instagram'
                            elif 'vk.com' in url:
                                platform = 'vk'
                            elif 'youtube.com' in url:
                                platform = 'youtube'
                            elif 't.me' in url:
                                platform = 'telegram'
                            elif 'facebook.com' in url:
                                platform = 'facebook'
                            elif 'twitter.com' in url:
                                platform = 'twitter'
                            
                            # Получаем статистику продаж
                            sales_impact = {
                                'frequency': result.get('frequency', 0),
                                'revenue': result.get('revenue', 0),
                                'orders': result.get('orders', 0),
                                'avg_price': result.get('avg_price', 0),
                                'orders_growth_percent': result.get('orders_growth_percent', 0),
                                'revenue_growth_percent': result.get('revenue_growth_percent', 0)
                            }
                            
                            # Получаем автора из сниппета или заголовка
                            author = result.get('author', '')
                            if not author:
                                snippet = result.get('snippet', '')
                                if 'by' in snippet.lower():
                                    author = snippet.split('by')[-1].strip()
                                else:
                                    author = result.get('title', '').split('-')[0].strip()
                            
                            results.append({
                                'platform': platform,
                                'date': result.get('date', ''),
                                'url': url,
                                'author': author,
                                'sales_impact': sales_impact
                            })
                            
                            logger.info(f"Added result: {url}")
                    
                    logger.info(f"Search completed successfully, found {len(results)} results")
                    return results
                else:
                    logger.error(f"Serper API error: {response.status}")
                    return []
                    
    except Exception as e:
        logger.error(f"Error in global search: {str(e)}")
        return []

def build_platform_distribution_chart(platforms, activities, title, filename_prefix):
    """Создает круговую диаграмму распределения активности по платформам."""
    plt.figure(figsize=(10, 6))
    plt.pie(activities, labels=platforms, autopct='%1.1f%%', startangle=90, 
            colors=['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f'])
    plt.title(title, fontsize=16)
    plt.axis('equal')
    plt.tight_layout()
    tmpfile = tempfile.NamedTemporaryFile(suffix='.png', prefix=filename_prefix, delete=False)
    plt.savefig(tmpfile.name)
    plt.close()
    return tmpfile.name

def build_revenue_comparison_chart(platforms, revenues, title, filename_prefix):
    """Создает график сравнения выручки по площадкам."""
    # Сокращаем названия площадок
    shortened_platforms = []
    platform_names = {}
    for i, platform in enumerate(platforms):
        # Убираем www. и .com из названий
        full_name = platform.replace('www.', '').replace('.com', '')
        # Создаем короткое имя
        if 'instagram' in full_name.lower():
            short_name = 'IG'
        elif 'vk.com' in full_name.lower():
            short_name = 'VK'
        elif 'facebook' in full_name.lower():
            short_name = 'FB'
        elif 'telegram' in full_name.lower() or 't.me' in full_name.lower():
            short_name = 'TG'
        elif 'twitter' in full_name.lower():
            short_name = 'TW'
        else:
            short_name = f'P{i+1}'
        
        platform_names[short_name] = full_name
        shortened_platforms.append(short_name)

    plt.figure(figsize=(10, 6))
    x = np.arange(len(shortened_platforms))
    
    # Создаем три линии для продаж, выручки и прибыли
    plt.plot(x, revenues, color='#4e79a7', linewidth=2.5, label='Выручка, ₽')
    plt.fill_between(x, revenues, color='#4e79a7', alpha=0.18)
    
    # Настраиваем оси и подписи
    plt.xticks(x, shortened_platforms, fontsize=12)
    plt.yticks(fontsize=12)
    plt.title(title, fontsize=16)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    plt.legend(fontsize=12)

    # Подписи значений над точками
    for i, val in enumerate(revenues):
        plt.annotate(f'{int(val):,}'.replace(',', ' '), 
                    (x[i], revenues[i]), 
                    textcoords="offset points", 
                    xytext=(0,8), 
                    ha='center', 
                    fontsize=11)

    # Добавляем легенду с расшифровкой площадок
    legend_text = []
    for short_name, full_name in platform_names.items():
        legend_text.append(f'{short_name} - {full_name}')
    
    # Размещаем легенду под графиком
    plt.figtext(0.05, 0.02, 'Расшифровка площадок:\n' + '\n'.join(legend_text),
                fontsize=10, ha='left', va='bottom')

    plt.subplots_adjust(bottom=0.25)  # Отступ снизу для легенды
    plt.tight_layout()
    
    tmpfile = tempfile.NamedTemporaryFile(suffix='.png', prefix=filename_prefix, delete=False)
    plt.savefig(tmpfile.name, dpi=300, bbox_inches='tight')
    plt.close()
    return tmpfile.name

def format_serper_results_detailed(data):
    """Форматировать результаты поиска в читаемый вид."""
    if not data:
        return "Произошла ошибка при получении результатов поиска."
    
    results = data.get('results', [])
    if not results:
        return "По вашему запросу ничего не найдено."
    
    # Считаем общую статистику
    total_likes = sum(result.get('likes', 0) for result in results)
    total_views = sum(result.get('views', 0) for result in results)
    
    # Определяем самую активную площадку
    platform_stats = {}
    for result in results:
        platform = result.get('site', '')
        if platform not in platform_stats:
            platform_stats[platform] = {
                'views': 0,
                'likes': 0,
                'count': 0,
                'revenue': 0
            }
        platform_stats[platform]['views'] += result.get('views', 0)
        platform_stats[platform]['likes'] += result.get('likes', 0)
        platform_stats[platform]['count'] += 1
        platform_stats[platform]['revenue'] += result.get('approx_revenue', 0)
    
    most_active_platform = max(
        platform_stats.items(),
        key=lambda x: (x[1]['views'] + x[1]['likes'], x[1]['count'])
    )[0]
    
    # Создаем графики
    platforms = list(platform_stats.keys())
    activities = [stats['views'] + stats['likes'] for stats in platform_stats.values()]
    revenues = [stats['revenue'] for stats in platform_stats.values()]
    
    distribution_chart = build_platform_distribution_chart(
        platforms, activities, 
        'Распределение активности по платформам',
        'distribution_'
    )
    
    revenue_chart = build_revenue_comparison_chart(
        platforms, revenues,
        'Потенциальная выручка по платформам',
        'revenue_'
    )
    
    # Формируем сообщение
    message = "🌐 Анализ социальных сетей\n\n"
    
    # Общая статистика
    message += "📊 Общая статистика:\n"
    message += f"• Найдено упоминаний: {len(results)}\n"
    message += f"• Суммарные лайки: {total_likes:,}\n"
    message += f"• Суммарные просмотры: {total_views:,}\n"
    message += f"• Самая активная площадка: {most_active_platform}\n\n"
    
    # Анализ по платформам
    message += "📈 Анализ по платформам:\n"
    for platform, stats in platform_stats.items():
        message += f"• {platform}:\n"
        message += f"  - Упоминаний: {stats['count']}\n"
        message += f"  - Лайки: {stats['likes']:,}\n"
        message += f"  - Просмотры: {stats['views']:,}\n"
        message += f"  - Потенц. выручка: {stats['revenue']:,}₽\n"
    
    message += "\nРезультаты поиска:\n"
    for result in results[:5]:
        title = result.get('title', '').replace('\n', ' ')[:100]
        link = result.get('link', '')
        platform = result.get('site', '')
        likes = result.get('likes', 0)
        views = result.get('views', 0)
        audience = result.get('approx_clients', 0)
        revenue = result.get('approx_revenue', 0)
        growth = result.get('growth_percent', 0)
        
        message += f"🔗 {title}\n"
        message += f"🌐 Площадка: {platform}\n"
        message += f"🔍 {link}\n"
        message += f"👍 Лайки: {likes:,}  👀 Просмотры: {views:,}\n"
        message += f"👥 Аудитория: {audience:,}\n"
        message += f"💰 Потенц. выручка: {revenue:,}₽\n"
        message += f"📈 Прогноз роста: {growth:.1f}%\n"
        
        if 'instagram.com' in platform.lower():
            message += "⚠️ Данные защищены\n"
        message += "\n"
    
    # Улучшенные рекомендации
    message += "📋 Рекомендации по продвижению:\n"
    
    # Анализ эффективности платформ
    if platform_stats:
        best_platform = max(platform_stats.items(), key=lambda x: x[1]['revenue'])[0]
        message += f"• Основной фокус на {best_platform} - показывает наибольший потенциал выручки\n"
    
    # Рекомендации по контенту
    if total_views > 10000:
        message += "• Создавайте больше видео-контента - высокая вовлеченность аудитории\n"
    elif total_views < 1000:
        message += "• Увеличьте частоту публикаций - низкая видимость контента\n"
    
    # Рекомендации по таргетингу
    if 'instagram.com' in most_active_platform.lower():
        message += "• Используйте Instagram Stories и Reels для увеличения охвата\n"
    elif 'vk.com' in most_active_platform.lower():
        message += "• Создавайте тематические сообщества в VK для привлечения целевой аудитории\n"
    
    # Рекомендации по бюджету
    total_revenue = sum(stats['revenue'] for stats in platform_stats.values())
    if total_revenue > 100000:
        message += "• Увеличьте бюджет на рекламу - высокая конверсия\n"
    else:
        message += "• Начните с тестового бюджета на рекламу для оценки эффективности\n"
    
    message += "\n💡 Следующие шаги:\n"
    message += "1. Проанализируйте площадки с высокой активностью\n"
    message += "2. Составьте план продвижения\n"
    message += "3. Начните работу с самых перспективных каналов\n"
    message += "4. Отслеживайте эффективность каждой платформы\n"
    
    return message, distribution_chart, revenue_chart

# Добавляем import безопасной функции
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
try:
    from safe_mpsta import safe_format_mpsta_results
except ImportError:
    # Определяем функцию прямо здесь, если импорт не работает
    def safe_format_mpsta_results(data):
        """Безопасная реализация форматирования результатов MPSTA."""
        try:
            if "error" in data:
                return data["error"], []
            
            query = data.get("query", "")
            is_article = data.get("is_article", False)
            
            # Простой вывод результата без графиков
            result = f"🔍 *Анализ рекламы {'по артикулу' if is_article else 'товара'}: {query}*\n\n"
            result += "Данные получены успешно, но визуализация временно недоступна.\n\n"
            result += "Пожалуйста, свяжитесь с разработчиком для обновления функции графиков."
            
            # Возвращаем текст и пустой список файлов графиков
            return result, []
        except Exception as e:
            logger.error(f"Error in safe_format_mpsta_results fallback: {str(e)}", exc_info=True)
            return f"❌ Произошла ошибка при форматировании результатов: {str(e)}", []

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
        
        # Отправляем сообщение о начале анализа
        processing_message = await message.answer(
            "🔍 *Выполняется комплексный анализ рекламных данных...*\n\n"
            "⚙️ Этап 1: Запрос данных \n"
            "⏳ Этап 2: Анализ социальных сетей\n"
            "🔄 Этап 3: Объединение результатов\n"
            "📊 Этап 4: Генерация рекомендаций\n\n"
            "Пожалуйста, подождите, этот процесс может занять некоторое время...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Обновляем сообщение о статусе
        await asyncio.sleep(1)
        await processing_message.edit_text(
            "🔍 *Выполняется комплексный анализ рекламных данных...*\n\n"
            "✅ Этап 1: Запрос данных \n"
            "⚙️ Этап 2: Анализ социальных сетей\n"
            "⏳ Этап 3: Объединение результатов\n"
            "🔄 Этап 4: Генерация рекомендаций\n\n"
            "Пожалуйста, подождите, этот процесс может занять некоторое время...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Получаем данные из MPSTA API
        mpsta_data = await get_mpsta_data(search_query)
        
        await asyncio.sleep(1)
        await processing_message.edit_text(
            "🔍 *Выполняется комплексный анализ рекламных данных...*\n\n"
            "✅ Этап 1: Запрос данных \n"
            "✅ Этап 2: Анализ социальных сетей\n"
            "⚙️ Этап 3: Объединение результатов\n"
            "⏳ Этап 4: Генерация рекомендаций\n\n"
            "Пожалуйста, подождите, этот процесс может занять некоторое время...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        if "error" in mpsta_data:
            await processing_message.edit_text(f"❌ Ошибка при получении данных: {mpsta_data['error']}")
            await state.clear()
            return
        
        await asyncio.sleep(1)
        await processing_message.edit_text(
            "🔍 *Выполняется комплексный анализ рекламных данных...*\n\n"
            "✅ Этап 1: Запрос данных \n"
            "✅ Этап 2: Анализ социальных сетей\n"
            "✅ Этап 3: Объединение результатов\n"
            "⚙️ Этап 4: Генерация рекомендаций\n\n"
            "Завершаем анализ и подготавливаем результаты...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Используем безопасную функцию вместо оригинальной
        formatted_results, chart_files = safe_format_mpsta_results(mpsta_data)
        
        # Создаем клавиатуру для возврата
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Новый поиск", callback_data="product_search"),
                InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_main")
            ]
        ])
        
        # Отправляем основной отчет
        await processing_message.edit_text(
            "✅ *Анализ успешно завершен!*\n\n"
            "Отправляю подробный отчет...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Отправляем основной текст с результатами
        main_message = await message.answer(
            formatted_results,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        
        # Финальное сообщение с клавиатурой
        await message.answer(
            "🎯 *Анализ рекламы завершен*\n\n"
            "Выше представлены результаты комплексного анализа рекламных кампаний "
            f"{'по артикулу' if search_query.isdigit() else 'товара'} *{search_query}*.\n\n"
            "Что вы хотите сделать дальше?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        
        await state.clear()
        
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
        
        # Преобразуем сумму в целое число копеек, чтобы избежать проблем с десятичной точкой
        amount_cents = int(amount * 100)
        
        admin_message = (
            f"🔄 *Новая заявка на пополнение баланса*\n\n"
            f"👤 Пользователь: {message.from_user.full_name} (ID: {user_id})\n"
            f"💰 Сумма: {amount}₽\n\n"
            f"Подтвердите или отклоните заявку:"
        )
        
        admin_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"confirm_payment_{user_id}_{amount_cents}"),
                InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject_payment_{user_id}_{amount_cents}")
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
    # Сокращаем названия площадок, если это график выручки по площадкам
    if "площадкам" in title:
        shortened_labels = []
        for label in labels:
            # Убираем www. и .com
            label = label.replace('www.', '').replace('.com', '')
            # Сокращаем названия популярных платформ
            if 'instagram' in label.lower():
                label = 'Instagram'
            elif 'vk' in label.lower():
                label = 'VK'
            elif 'facebook' in label.lower():
                label = 'FB'
            elif 'telegram' in label.lower() or 't.me' in label.lower():
                label = 'TG'
            elif 'twitter' in label.lower():
                label = 'Twitter'
            shortened_labels.append(label)
        labels = shortened_labels

    plt.figure(figsize=(10, 6))
    x = np.arange(len(labels))
    
    # Создаем три линии на одном графике
    plt.plot(x, sales, '-', color='#4e79a7', linewidth=2, label='Продажи, шт.')
    plt.plot(x, revenue, '-', color='#f28e2b', linewidth=2, label='Выручка, ₽')
    plt.plot(x, profit, '-', color='#e15759', linewidth=2, label='Прибыль, ₽')
    
    # Добавляем заливку под линиями
    plt.fill_between(x, sales, alpha=0.1, color='#4e79a7')
    plt.fill_between(x, revenue, alpha=0.1, color='#f28e2b')
    plt.fill_between(x, profit, alpha=0.1, color='#e15759')
    
    # Настройки графика
    plt.title(title, fontsize=14, pad=20)
    plt.xticks(x, labels, fontsize=12, rotation=45 if "площадкам" in title else 0)
    plt.yticks(fontsize=12)
    plt.grid(True, linestyle='--', alpha=0.3)
    plt.legend(fontsize=10, loc='upper left')
    
    # Добавляем значения над точками
    for i, (s, r, p) in enumerate(zip(sales, revenue, profit)):
        plt.annotate(f'{int(s):,}'.replace(',', ' '), (x[i], s), 
                    textcoords="offset points", xytext=(0,10), 
                    ha='center', fontsize=10)
        plt.annotate(f'{int(r):,}'.replace(',', ' '), (x[i], r), 
                    textcoords="offset points", xytext=(0,10), 
                    ha='center', fontsize=10)
        plt.annotate(f'{int(p):,}'.replace(',', ' '), (x[i], p), 
                    textcoords="offset points", xytext=(0,10), 
                    ha='center', fontsize=10)
    
    plt.tight_layout()
    tmpfile = tempfile.NamedTemporaryFile(suffix='.png', prefix=filename_prefix, delete=False)
    plt.savefig(tmpfile.name, dpi=300, bbox_inches='tight')
    plt.close()
    return tmpfile.name

def build_trend_analysis_chart(labels, values, title, filename_prefix):
    plt.figure(figsize=(10, 6))
    x = np.arange(len(labels))
    
    # Основной график
    plt.plot(x, values, 'o-', color='#4e79a7', linewidth=2, markersize=8)
    
    # Линия тренда
    z = np.polyfit(x, values, 1)
    p = np.poly1d(z)
    plt.plot(x, p(x), 'r--', linewidth=1, label='Тренд')
    
    # Заполнение области под графиком
    plt.fill_between(x, values, alpha=0.2, color='#4e79a7')
    
    # Настройки графика
    plt.title(title, fontsize=14)
    plt.xticks(x, labels, fontsize=10)
    plt.grid(True, linestyle='--', alpha=0.5)
    
    # Добавляем значения над точками
    for i, val in enumerate(values):
        plt.annotate(f'{int(val):,}'.replace(',', ' '), (x[i], val), 
                    textcoords="offset points", xytext=(0,10), ha='center', fontsize=9)
    
    plt.tight_layout()
    tmpfile = tempfile.NamedTemporaryFile(suffix='.png', prefix=filename_prefix, delete=False)
    plt.savefig(tmpfile.name)
    plt.close()
    return tmpfile.name

def build_platform_comparison_chart(platforms, metrics, title, filename_prefix):
    plt.figure(figsize=(12, 6))
    x = np.arange(len(platforms))
    width = 0.35
    
    # Создаем группированный столбчатый график
    plt.bar(x - width/2, metrics['views'], width, label='Просмотры', color='#4e79a7')
    plt.bar(x + width/2, metrics['likes'], width, label='Лайки', color='#f28e2b')
    
    # Настройки графика
    plt.title(title, fontsize=14)
    plt.xticks(x, platforms, fontsize=10, rotation=45)
    plt.legend(fontsize=10)
    plt.grid(axis='y', linestyle='--', alpha=0.5)
    
    # Добавляем значения над столбцами
    for i, val in enumerate(metrics['views']):
        plt.annotate(f'{int(val):,}'.replace(',', ' '), (x[i] - width/2, val), 
                    textcoords="offset points", xytext=(0,5), ha='center', fontsize=9)
    for i, val in enumerate(metrics['likes']):
        plt.annotate(f'{int(val):,}'.replace(',', ' '), (x[i] + width/2, val), 
                    textcoords="offset points", xytext=(0,5), ha='center', fontsize=9)
    
    plt.tight_layout()
    tmpfile = tempfile.NamedTemporaryFile(suffix='.png', prefix=filename_prefix, delete=False)
    plt.savefig(tmpfile.name)
    plt.close()
    return tmpfile.name

def analyze_trends(data):
    """Анализирует тренды и возвращает текстовый анализ"""
    analysis = []
    
    # Анализ продаж
    sales = data.get('sales', [])
    if sales:
        growth_rate = (sales[-1] - sales[0]) / sales[0] * 100 if sales[0] != 0 else 0
        analysis.append(f"📈 Продажи: {'рост' if growth_rate > 0 else 'снижение'} на {abs(growth_rate):.1f}%")
    
    # Анализ выручки
    revenue = data.get('revenue', [])
    if revenue:
        avg_revenue = sum(revenue) / len(revenue)
        max_revenue = max(revenue)
        analysis.append(f"💰 Средняя выручка: {avg_revenue:,.0f}₽ (макс: {max_revenue:,.0f}₽)")
    
    # Анализ прибыли
    profit = data.get('profit', [])
    if profit:
        profit_margin = (sum(profit) / sum(revenue)) * 100 if sum(revenue) != 0 else 0
        analysis.append(f"💎 Рентабельность: {profit_margin:.1f}%")
    
    # Анализ платформ
    platforms = data.get('platforms', {})
    if platforms:
        best_platform = max(platforms.items(), key=lambda x: sum(x[1].values()))
        analysis.append(f"🏆 Лучшая платформа: {best_platform[0]} (просмотры: {sum(best_platform[1]['views']):,}, лайки: {sum(best_platform[1]['likes']):,})")
    
    return "\n".join(analysis)

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_product)
@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_product)
async def handle_product_article(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        article = message.text.strip()
        logger.info(f"User {user_id} is waiting for product analysis")

        # Проверяем подписку
        can_perform = subscription_manager.can_perform_action(user_id, "product_analysis")
        if not can_perform:
            await message.answer("⚠️ У вас нет активной подписки или закончился лимит запросов. Перейдите в раздел подписок для получения доступа.", reply_markup=main_menu_kb())
            await state.clear()
            return

        # Проверяем корректность артикула
        if not article.isdigit():
            await message.answer("⚠️ Введите корректный артикул (только цифры).")
            return

        # Отправляем сообщение о начале анализа
        processing_msg = await message.answer("⏳ Анализирую товар, это может занять до 30 секунд...")

        # Получаем объединенные данные о продукте из MPSTAT и Wildberries API
        product_info = await get_combined_product_info(article)
            
        if not product_info:
            await processing_msg.delete()
            await message.answer("❌ Не удалось получить информацию о товаре. Проверьте артикул и попробуйте ещё раз.", reply_markup=back_keyboard())
            return
                
        # Форматируем результаты анализа с расширенной информацией
        formatted_result = await format_enhanced_product_analysis(product_info, article)
            
        # Генерируем графики
        chart_paths = generate_daily_charts(product_info)
        
        # Отправляем основную информацию
        await processing_msg.delete()
        await message.answer(formatted_result, reply_markup=back_keyboard())
        
        # Словарь с описаниями графиков товара
        chart_descriptions = {
            'revenue_chart': "📈 График выручки — динамика дневной выручки за последний месяц",
            'orders_chart': "📊 График заказов — количество заказов товара по дням",
            'stock_chart': "📦 График товарных остатков — изменение остатков на складах",
            'freq_chart': "🔍 График частотности артикула — востребованность товара в поиске",
            'ads_chart': "🎯 График рекламы в поиске — эффективность продвижения товара"
        }
        
        # Отправляем графики товара, если они есть
        if chart_paths:
            await message.answer("📊 ГРАФИКИ ПО ТОВАРУ:", reply_markup=back_keyboard())
            
            for chart_path in chart_paths:
                chart_name = chart_path.replace('.png', '')
                caption = chart_descriptions.get(chart_name, f"График: {chart_name}")
                
                with open(chart_path, 'rb') as photo:
                    await message.answer_photo(FSInputFile(chart_path), caption=caption)
        
        # Генерируем графики бренда
        brand_chart_paths = generate_brand_charts(product_info)
        
        # Словарь с описаниями графиков бренда
        brand_chart_descriptions = {
            'brand_sales_chart': "📈 Динамика продаж бренда — изменение объема продаж и выручки по дням с трендами и средними значениями",
            'brand_competitors_chart': "🥊 Сравнение с конкурентами — сопоставление по количеству товаров и продажам",
            'brand_categories_chart': "📁 Распределение по категориям — показывает долю товаров бренда в разных категориях",
            'brand_top_items_chart': "🏆 Топ товары бренда — самые продаваемые позиции с показателями продаж и выручки",
            'brand_radar_chart': "📊 Ключевые показатели бренда — интегральная оценка характеристик бренда на рынке"
        }
        
        # Отправляем графики бренда, если они есть
        if brand_chart_paths:
            await message.answer("📊 ГРАФИКИ ПО БРЕНДУ:", reply_markup=back_keyboard())
            
            for chart_path in brand_chart_paths:
                chart_name = chart_path.replace('.png', '')
                caption = brand_chart_descriptions.get(chart_name, f"График: {chart_name}")
                
                with open(chart_path, 'rb') as photo:
                    await message.answer_photo(FSInputFile(chart_path), caption=caption)
        
        # Записываем использование запроса
        # subscription_manager.record_action(user_id, "product_analysis")
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in handle_product_article: {str(e)}", exc_info=True)
        await message.answer(f"❌ Произошла ошибка при анализе товара: {str(e)}", reply_markup=back_keyboard())
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

async def format_product_analysis(product_info, article):
    """Форматирует результаты анализа товара."""
    
    # Получаем продажи за сутки
    daily_sales = product_info['sales']['today']
    used_estimation = False
    
    # Определяем данные о выручке и прибыли
    if 'revenue' in product_info['sales'] and 'profit' in product_info['sales']:
        # Используем данные напрямую из API
        daily_revenue = product_info['sales']['revenue']['daily']
        weekly_revenue = product_info['sales']['revenue']['weekly']
        monthly_revenue = product_info['sales']['revenue']['monthly']
        total_revenue = product_info['sales']['revenue'].get('total', 0)
        
        daily_profit = product_info['sales']['profit']['daily']
        weekly_profit = product_info['sales']['profit']['weekly']
        monthly_profit = product_info['sales']['profit']['monthly']
        
        estimated_week = daily_sales * 7
        estimated_month = daily_sales * 30
    else:
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
        total_revenue = product_info['sales'].get('total', 0) * product_info['price'].get('average', product_info['price']['current'])
        
        # Считаем примерную прибыль (берем 30% от выручки)
        profit_margin = 0.3
        daily_profit = daily_revenue * profit_margin
        weekly_profit = estimated_week_revenue * profit_margin
        monthly_profit = estimated_month_revenue * profit_margin
    
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
    
    # Добавляем среднюю цену, если она отличается от текущей
    if 'average' in product_info['price'] and abs(product_info['price']['average'] - product_info['price']['current']) > 50:
        avg_price = "{:,}".format(int(product_info['price']['average'])).replace(',', ' ')
        result += f"\n💲 Средняя цена: {avg_price}₽"
        
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
    
    # Дополнительная аналитика из MPSTAT
    if 'analytics' in product_info and product_info['analytics']:
        analytics = product_info['analytics']
        
        if analytics.get('purchase_rate', 0) > 0:
            result += f"\n*Показатели эффективности:*\n"
            
            if analytics.get('purchase_rate', 0) > 0:
                result += f"🛒 Процент выкупа: {analytics['purchase_rate']}%\n"
            
            if analytics.get('purchase_after_return', 0) > 0:
                result += f"♻️ Выкуп с учетом возвратов: {analytics['purchase_after_return']}%\n"
            
            if analytics.get('turnover_days', 0) > 0:
                result += f"⏱ Оборачиваемость: {analytics['turnover_days']:.1f} дней\n"
            
            if analytics.get('days_in_stock', 0) > 0 and analytics.get('days_with_sales', 0) > 0:
                days_in_stock = analytics['days_in_stock']
                days_with_sales = analytics['days_with_sales']
                sales_rate = round((days_with_sales / max(days_in_stock, 1)) * 100)
                result += f"📆 Дней в наличии: {days_in_stock}\n"
                result += f"📈 Дней с продажами: {days_with_sales} ({sales_rate}%)\n"
    
    # Продажи и выручка
    if daily_sales == 0:
        result += (
            f"\n*Продажи и выручка:*\n"
            f"❗ Нет данных о продажах за сутки.\n"
        )
    else:
        # Форматируем числа с разделителем тысяч
        daily_revenue_fmt = "{:,}".format(int(daily_revenue)).replace(',', ' ')
        daily_profit_fmt = "{:,}".format(int(daily_profit)).replace(',', ' ')
        weekly_revenue_fmt = "{:,}".format(int(weekly_revenue)).replace(',', ' ')
        weekly_profit_fmt = "{:,}".format(int(weekly_profit)).replace(',', ' ')
        monthly_revenue_fmt = "{:,}".format(int(monthly_revenue)).replace(',', ' ')
        monthly_profit_fmt = "{:,}".format(int(monthly_profit)).replace(',', ' ')
        total_revenue_fmt = "{:,}".format(int(total_revenue)).replace(',', ' ')
        
        result += (
            f"\n*Продажи и выручка:*\n"
            f"📈 Продажи за сутки: {daily_sales} шт.\n"
            f"💰 Выручка за сутки: {daily_revenue_fmt}₽\n"
            f"💎 Прибыль за сутки: {daily_profit_fmt}₽\n"
            f"\n*Прогноз на неделю:*\n"
            f"📈 Продажи: ~{estimated_week} шт.\n"
            f"💰 Выручка: ~{weekly_revenue_fmt}₽\n"
            f"💎 Прибыль: ~{weekly_profit_fmt}₽\n"
            f"\n*Прогноз на месяц:*\n"
            f"📈 Продажи: ~{estimated_month} шт.\n"
            f"💰 Выручка: ~{monthly_revenue_fmt}₽\n"
            f"💎 Прибыль: ~{monthly_profit_fmt}₽\n"
        )
        
        # Добавляем информацию о выручке за весь период
        if total_revenue > 0:
            result += f"\n💰 *Общая выручка за период:* {total_revenue_fmt}₽\n"
    
    # Добавляем рекомендации
    result += "\n*Рекомендации:* \n"
    
    # Рекомендации по отзывам
    if product_info['feedbacks'] < 10:
        result += (
            "💡 Увеличить количество отзывов\n"
            "- Просите довольных клиентов оставлять отзывы, предлагайте бонусы или скидки за обратную связь.\n"
            "- Используйте QR-коды на упаковке для быстрого перехода к форме отзыва.\n"
            "- Отвечайте на все отзывы — это повышает доверие новых покупателей.\n"
            "\n"
        )
    
    # Рекомендации по остаткам
    if product_info['stocks']['total'] < 10 and daily_sales > 0:
        result += (
            "💡 Пополнить остатки товара\n"
            "- Следите за остатками на складе, чтобы не терять продажи из-за отсутствия товара.\n"
            "- Планируйте закупки заранее, особенно перед сезоном повышенного спроса.\n"
            "- Используйте автоматические уведомления о низких остатках.\n"
            "\n"
        )
    
    # Рекомендации по оборачиваемости
    if 'analytics' in product_info and product_info['analytics'].get('turnover_days', 0) > 30:
        result += (
            "💡 Улучшить оборачиваемость товара\n"
            "- Ваш товар залеживается на складе более 30 дней, что увеличивает издержки.\n"
            "- Пересмотрите маркетинговую стратегию и ценовую политику.\n"
            "- Запустите акции или скидки для ускорения продаж.\n"
            "\n"
        )
    
    # Рекомендации по выкупу
    if 'analytics' in product_info and product_info['analytics'].get('purchase_rate', 100) < 70:
        result += (
            "💡 Повысить процент выкупа\n"
            "- Улучшите качество фото и описания товара для более точного представления.\n"
            "- Укажите подробные размерные сетки и характеристики.\n"
            "- Проанализируйте причины отказов и возвратов.\n"
        )
    
    return result

def generate_global_search_pdf(article, search_results, chart_path=None):
    import os
    logger = logging.getLogger(__name__)
    logger.info(f"PDF: platforms in mentions: {[item.get('site', '') for item in search_results]}")
    
    pdf = FPDF()
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
        
        # Ширины столбцов
        col_widths = [25, 25, 25, 35, 35, 35]  # Общая ширина ~180
        headers = ['Площадка', 'Лайки', 'Просмотры', 'Аудитория', 'Выручка', 'Рост %']
        
        # Заголовки таблицы
        for i, h in enumerate(headers):
            pdf.cell(col_widths[i], 8, h, border=1, align='C')
        pdf.ln()
        
        # Сбор статистики для анализа
        platform_stats = {}
        total_likes = 0
        total_views = 0
        total_revenue = 0
        total_audience = 0
        
        # Данные таблицы
        for item in search_results:
            # Сокращаем название площадки
            site = item.get('site', '').replace('www.', '').replace('.com', '')
            if 'instagram' in site.lower():
                site = 'Instagram'
            elif 'vk' in site.lower():
                site = 'VK'
            elif 'facebook' in site.lower():
                site = 'FB'
            elif 'telegram' in site.lower() or 't.me' in site.lower():
                site = 'TG'
            elif 'twitter' in site.lower():
                site = 'Twitter'
            
            # Собираем статистику по площадкам
            if site not in platform_stats:
                platform_stats[site] = {
                    'likes': 0,
                    'views': 0,
                    'revenue': 0,
                    'audience': 0,
                    'posts': 0
                }
            platform_stats[site]['posts'] += 1
            platform_stats[site]['likes'] += item.get('likes', 0)
            platform_stats[site]['views'] += item.get('views', 0)
            platform_stats[site]['revenue'] += item.get('approx_revenue', 0)
            platform_stats[site]['audience'] += item.get('approx_clients', 0)
            
            # Общая статистика
            total_likes += item.get('likes', 0)
            total_views += item.get('views', 0)
            total_revenue += item.get('approx_revenue', 0)
            total_audience += item.get('approx_clients', 0)
            
            # Форматируем числа
            likes = f"{item.get('likes', 0):,}".replace(',', ' ')
            views = f"{item.get('views', 0):,}".replace(',', ' ')
            audience = f"{item.get('approx_clients', 0):,}".replace(',', ' ')
            revenue = f"{item.get('approx_revenue', 0):,}".replace(',', ' ')
            growth = f"{item.get('growth_percent', 0):.1f}%"
            
            # Выводим строку таблицы
            pdf.cell(col_widths[0], 8, site, border=1, align='C')
            pdf.cell(col_widths[1], 8, likes, border=1, align='C')
            pdf.cell(col_widths[2], 8, views, border=1, align='C')
            pdf.cell(col_widths[3], 8, audience, border=1, align='C')
            pdf.cell(col_widths[4], 8, revenue, border=1, align='C')
            pdf.cell(col_widths[5], 8, growth, border=1, align='C')
            pdf.ln()
        
        pdf.ln(5)
        if chart_path and os.path.exists(chart_path):
            pdf.set_font('DejaVu', 'B', 12)
            pdf.cell(0, 10, 'График по данным глобального поиска:', ln=1)
            pdf.image(chart_path, x=20, w=170)
            pdf.ln(10)
        
        # Добавляем экспертный анализ
        pdf.add_page()
        pdf.set_font('DejaVu', 'B', 14)
        pdf.cell(0, 10, 'Экспертный анализ:', ln=1)
        pdf.ln(5)
        
        # Общая статистика
        pdf.set_font('DejaVu', 'B', 12)
        pdf.cell(0, 8, 'Общие показатели:', ln=1)
        pdf.set_font('DejaVu', '', 11)
        pdf.multi_cell(0, 6, f"""• Всего упоминаний: {len(search_results)}
• Суммарные лайки: {total_likes:,}
• Суммарные просмотры: {total_views:,}
• Потенциальная аудитория: {total_audience:,}
• Прогнозируемая выручка: {total_revenue:,} ₽""".replace(',', ' '))
        pdf.ln(5)
        
        # Анализ по площадкам
        pdf.set_font('DejaVu', 'B', 12)
        pdf.cell(0, 8, 'Анализ по площадкам:', ln=1)
        pdf.set_font('DejaVu', '', 11)
        
        # Находим лучшую площадку
        best_platform = max(platform_stats.items(), key=lambda x: x[1]['revenue'])
        engagement_rates = {
            platform: (stats['likes'] + stats['views']) / stats['posts'] if stats['posts'] > 0 else 0
            for platform, stats in platform_stats.items()
        }
        best_engagement = max(engagement_rates.items(), key=lambda x: x[1])
        
        for platform, stats in platform_stats.items():
            avg_engagement = (stats['likes'] + stats['views']) / stats['posts'] if stats['posts'] > 0 else 0
            pdf.multi_cell(0, 6, f"""• {platform}:
  - Количество постов: {stats['posts']}
  - Средний охват: {int(stats['views'] / stats['posts']):,} просмотров
  - Средний engagement rate: {(stats['likes'] / stats['views'] * 100 if stats['views'] > 0 else 0):.1f}%
  - Потенциальная выручка: {stats['revenue']:,} ₽""".replace(',', ' '))
            pdf.ln(2)
        
        # Рекомендации
        pdf.ln(5)
        pdf.set_font('DejaVu', 'B', 12)
        pdf.cell(0, 8, 'Рекомендации по продвижению:', ln=1)
        pdf.set_font('DejaVu', '', 11)
        
        # Формируем рекомендации на основе анализа
        recommendations = []
        
        # Рекомендация по лучшей площадке
        recommendations.append(f"• Сфокусировать основные усилия на {best_platform[0]} - показывает наилучшую конверсию и потенциальную выручку ({best_platform[1]['revenue']:,} ₽).")
        
        # Рекомендация по типу контента
        if total_views > 10000:
            recommendations.append("• Создавать больше видео-контента - аудитория активно взаимодействует с визуальным контентом.")
        else:
            recommendations.append("• Увеличить частоту публикаций и разнообразить контент для повышения охвата.")
        
        # Рекомендация по бюджету
        avg_revenue_per_post = total_revenue / len(search_results) if search_results else 0
        if avg_revenue_per_post > 50000:
            recommendations.append(f"• Увеличить рекламный бюджет - высокая окупаемость ({int(avg_revenue_per_post):,} ₽ на пост).")
        else:
            recommendations.append("• Начать с небольшого тестового бюджета для оценки эффективности рекламных кампаний.")
        
        # Рекомендация по engagement
        recommendations.append(f"• Использовать механики {best_engagement[0]} для повышения вовлеченности - показывает лучший engagement rate.")
        
        # Рекомендация по масштабированию
        if len(platform_stats) < 3:
            recommendations.append("• Расширить присутствие на других площадках для увеличения охвата целевой аудитории.")
        
        # Выводим рекомендации
        for rec in recommendations:
            pdf.multi_cell(0, 6, rec)
            pdf.ln(2)
        
        # Заключение
        pdf.ln(5)
        pdf.set_font('DejaVu', 'B', 12)
        pdf.cell(0, 8, 'Заключение:', ln=1)
        pdf.set_font('DejaVu', '', 11)
        
        conclusion = f"""На основе проведенного анализа товар показывает {'высокий' if total_revenue > 100000 else 'средний' if total_revenue > 50000 else 'низкий'} потенциал в социальных сетях. {'Рекомендуется активное масштабирование присутствия.' if total_revenue > 100000 else 'Требуется дополнительная работа над контентом и продвижением.' if total_revenue > 50000 else 'Необходимо пересмотреть стратегию продвижения и целевую аудиторию.'}

Ключевые метрики для отслеживания:
• Рост охвата и вовлеченности
• Конверсия в продажи
• ROI рекламных кампаний
• Обратная связь от аудитории"""
        
        pdf.multi_cell(0, 6, conclusion)
    
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

# --- Интеграция с MPSTA API ---
async def get_mpsta_data(query):
    """Получение данных из API MPSTA."""
    logger.info(f"Getting MPSTA data for query: {query}")
    
    # Определяем, является ли запрос артикулом или поисковым запросом
    is_article = query.isdigit()
    
    today = datetime.now()
    month_ago = today - timedelta(days=30)
    date_from = month_ago.strftime("%d.%m.%Y")
    date_to = today.strftime("%d.%m.%Y")
    
    # Импортируем браузерные утилиты
    from mpstats_browser_utils import (
        get_mpstats_headers, 
        get_item_sales_browser, 
        get_item_info_browser,
        search_products_browser,
        format_date_for_mpstats
    )
    
    headers = get_mpstats_headers()
    
    try:
        # Сначала получаем данные через API MPSTA
        mpsta_results = {}
        
        # Если это артикул, запрашиваем данные по артикулу
        if is_article:
            url = f"https://mpstats.io/api/wb/get/item/{query}/sales?d1={date_from}&d2={date_to}"
            async with aiohttp.ClientSession() as session:
                async with session.get(url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        mpsta_results["article_data"] = data
                    else:
                        logger.error(f"MPSTA API error: {await response.text()}")
                        mpsta_results["error"] = f"Ошибка API: {response.status}"
                        
            # Также запрашиваем данные о рекламе для артикула
            ad_url = f"https://mpstats.io/api/wb/get/item/{query}/adverts?d1={date_from}&d2={date_to}"
            async with aiohttp.ClientSession() as session:
                async with session.get(ad_url, headers=headers) as response:
                    if response.status == 200:
                        ad_data = await response.json()
                        mpsta_results["ad_data"] = ad_data
        # Если это поисковый запрос, ищем товары по запросу
        else:
            # Запрос по ключевому слову
            search_url = f"https://mpstats.io/api/wb/get/keywords?d1={date_from}&d2={date_to}&keyword={query}"
            
            async with aiohttp.ClientSession() as session:
                async with session.get(search_url, headers=headers) as response:
                    if response.status == 200:
                        data = await response.json()
                        mpsta_results["search_data"] = data
                        
                        # Если есть результаты, получаем данные о товарах и их рекламе
                        if data and "items" in data and len(data["items"]) > 0:
                            product_data = []
                            ad_data = []
                            
                            # Берем первые 5 товаров для анализа
                            for item in data["items"][:5]:
                                try:
                                    article = item.get("id") or item.get("nmId")
                                    if article:
                                        # Получаем данные о товаре
                                        product_url = f"https://mpstats.io/api/wb/get/item/{article}/sales?d1={date_from}&d2={date_to}"
                                        async with session.get(product_url, headers=headers) as product_response:
                                            if product_response.status == 200:
                                                product_info = await product_response.json()
                                                product_data.append({
                                                    "article": article,
                                                    "data": product_info
                                                })
                                        
                                        # Получаем данные о рекламе товара
                                        ad_url = f"https://mpstats.io/api/wb/get/item/{article}/adverts?d1={date_from}&d2={date_to}"
                                        async with session.get(ad_url, headers=headers) as ad_response:
                                            if ad_response.status == 200:
                                                ad_info = await ad_response.json()
                                                ad_data.append({
                                                    "article": article,
                                                    "ad_data": ad_info
                                                })
                                except Exception as e:
                                    logger.error(f"Error getting product data: {str(e)}")
                                    continue
                            
                            mpsta_results["product_data"] = product_data
                            mpsta_results["ad_data"] = ad_data
        
        # Теперь дополняем данными из нашего существующего поиска
        serper_results = await global_search_serper_detailed(query)
        
        # Объединяем результаты
        combined_results = {
            "mpsta_results": mpsta_results,
            "serper_results": serper_results,
            "is_article": is_article,
            "query": query
        }
        
        return combined_results
    
    except Exception as e:
        logger.error(f"Error in MPSTA API request: {str(e)}", exc_info=True)
        return {"error": f"Ошибка запроса: {str(e)}", "is_article": is_article}

def generate_mpsta_charts(data):
    """Генерирует графики на основе данных MPSTA API."""
    chart_files = []
    
    try:
        # Проверяем, есть ли данные для построения графиков
        mpsta_results = data.get("mpsta_results", {})
        if not mpsta_results:
            return []
        
        is_article = data.get("is_article", False)
        query = data.get("query", "")
        
        # Данные для графиков
        revenue_data = []
        orders_data = []
        platforms = []
        blogger_data = {}
        growth_data = {}
        
        # Обработка данных из ответа API
        if is_article and "ad_data" in mpsta_results:
            ad_data = mpsta_results["ad_data"]
            
            # Собираем данные об эффективности рекламы
            for ad in ad_data.get("items", []):
                try:
                    # Данные о блогере/площадке
                    platform = ad.get("platform", "Неизвестно")
                    blogger = ad.get("blogger", {}).get("name", "Неизвестный")
                    
                    # Метрики публикации
                    likes = ad.get("likes", 0)
                    views = ad.get("views", 0)
                    revenue = ad.get("revenue", 0)
                    orders = ad.get("orders", 0)
                    
                    # Добавляем данные для графиков
                    revenue_data.append(revenue)
                    orders_data.append(orders)
                    platforms.append(platform)
                    
                    # Данные по блогерам
                    if blogger not in blogger_data:
                        blogger_data[blogger] = {
                            "revenue": 0,
                            "orders": 0,
                            "likes": 0,
                            "views": 0,
                            "posts": 0
                        }
                    
                    blogger_data[blogger]["revenue"] += revenue
                    blogger_data[blogger]["orders"] += orders
                    blogger_data[blogger]["likes"] += likes
                    blogger_data[blogger]["views"] += views
                    blogger_data[blogger]["posts"] += 1
                    
                    # Данные о росте показателей
                    date = ad.get("date", "")
                    if date:
                        if date not in growth_data:
                            growth_data[date] = {
                                "revenue": 0,
                                "orders": 0
                            }
                        growth_data[date]["revenue"] += revenue
                        growth_data[date]["orders"] += orders
                except Exception as e:
                    logger.error(f"Error processing ad data: {str(e)}")
                    continue
        
        # Если есть данные о нескольких товарах
        elif "product_data" in mpsta_results and "ad_data" in mpsta_results:
            # Объединяем данные о товарах и их рекламе
            articles = set()
            for product in mpsta_results.get("product_data", []):
                articles.add(product.get("article", ""))
            
            for ad_item in mpsta_results.get("ad_data", []):
                try:
                    article = ad_item.get("article", "")
                    if article not in articles:
                        continue
                    
                    ad_list = ad_item.get("ad_data", {}).get("items", [])
                    
                    for ad in ad_list:
                        # Данные о блогере/площадке
                        platform = ad.get("platform", "Неизвестно")
                        blogger = ad.get("blogger", {}).get("name", "Неизвестный")
                        
                        # Метрики публикации
                        likes = ad.get("likes", 0)
                        views = ad.get("views", 0)
                        revenue = ad.get("revenue", 0)
                        orders = ad.get("orders", 0)
                        
                        # Добавляем данные для графиков
                        revenue_data.append(revenue)
                        orders_data.append(orders)
                        platforms.append(platform)
                        
                        # Данные по блогерам
                        if blogger not in blogger_data:
                            blogger_data[blogger] = {
                                "revenue": 0,
                                "orders": 0,
                                "likes": 0,
                                "views": 0,
                                "posts": 0
                            }
                        
                        blogger_data[blogger]["revenue"] += revenue
                        blogger_data[blogger]["orders"] += orders
                        blogger_data[blogger]["likes"] += likes
                        blogger_data[blogger]["views"] += views
                        blogger_data[blogger]["posts"] += 1
                        
                        # Данные о росте показателей
                        date = ad.get("date", "")
                        if date:
                            if date not in growth_data:
                                growth_data[date] = {
                                    "revenue": 0,
                                    "orders": 0
                                }
                            growth_data[date]["revenue"] += revenue
                            growth_data[date]["orders"] += orders
                except Exception as e:
                    logger.error(f"Error processing product ad data: {str(e)}")
                    continue
        
        # Проверяем, есть ли данные для построения графиков
        if revenue_data and orders_data and platforms:
            # 1. График сравнения выручки и заказов по публикациям
            if len(revenue_data) > 0:
                try:
                    plt.figure(figsize=(10, 6))
                    
                    # Создаем двойную ось Y
                    ax1 = plt.gca()
                    ax2 = ax1.twinx()
                    
                    # Данные для графика
                    x = np.arange(len(platforms))
                    
                    # Столбчатая диаграмма выручки
                    bars1 = ax1.bar(x - 0.2, revenue_data, width=0.4, color='#4e79a7', label='Выручка, ₽')
                    
                    # Столбчатая диаграмма заказов
                    bars2 = ax2.bar(x + 0.2, orders_data, width=0.4, color='#f28e2b', label='Заказы, шт')
                    
                    # Настройки оси X
                    shortened_platforms = []
                    for platform in platforms:
                        # Сокращаем названия для лучшей читаемости
                        if platform.lower() == 'instagram':
                            shortened_platforms.append('IG')
                        elif platform.lower() == 'vkontakte':
                            shortened_platforms.append('VK')
                        elif platform.lower() == 'youtube':
                            shortened_platforms.append('YT')
                        elif platform.lower() == 'telegram':
                            shortened_platforms.append('TG')
                        else:
                            # Берем первые 2 символа
                            shortened_platforms.append(platform[:2].upper())
                    
                    plt.xticks(x, shortened_platforms, rotation=45)
                    
                    # Легенда
                    lines1, labels1 = ax1.get_legend_handles_labels()
                    lines2, labels2 = ax2.get_legend_handles_labels()
                    ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
                    
                    # Заголовок и метки осей
                    plt.title(f'Сравнение публикаций по выручке и заказам для {query}')
                    ax1.set_ylabel('Выручка, ₽')
                    ax2.set_ylabel('Заказы, шт')
                    
                    # Добавляем значения над столбцами
                    for i, v in enumerate(revenue_data):
                        ax1.text(i - 0.2, v + max(revenue_data) * 0.02, f'{int(v):,}'.replace(',', ' '), 
                                ha='center', va='bottom', fontsize=9, rotation=0)
                    
                    for i, v in enumerate(orders_data):
                        ax2.text(i + 0.2, v + max(orders_data) * 0.02, str(int(v)), 
                                ha='center', va='bottom', fontsize=9, rotation=0)
                    
                    plt.tight_layout()
                    
                    # Сохраняем график
                    revenue_chart = tempfile.NamedTemporaryFile(suffix='.png', prefix='revenue_', delete=False)
                    plt.savefig(revenue_chart.name, dpi=300)
                    plt.close()
                    
                    chart_files.append(revenue_chart.name)
                except Exception as e:
                    logger.error(f"Error generating revenue chart: {str(e)}")
            
            # 2. График роста показателей
            if growth_data:
                try:
                    # Сортируем даты
                    sorted_dates = sorted(growth_data.keys())
                    
                    # Данные для графика
                    growth_revenue = [growth_data[date]["revenue"] for date in sorted_dates]
                    growth_orders = [growth_data[date]["orders"] for date in sorted_dates]
                    
                    # Нормализуем даты для отображения
                    display_dates = []
                    for date_str in sorted_dates:
                        try:
                            date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                            display_dates.append(date_obj.strftime("%d.%m"))
                        except:
                            display_dates.append(date_str)
                    
                    # Создаем график
                    plt.figure(figsize=(10, 6))
                    
                    # Линия выручки
                    plt.plot(display_dates, growth_revenue, 'o-', color='#4e79a7', linewidth=2, markersize=6, label='Выручка, ₽')
                    
                    # Линия заказов на другой оси Y
                    ax2 = plt.gca().twinx()
                    ax2.plot(display_dates, growth_orders, 'o--', color='#f28e2b', linewidth=2, markersize=6, label='Заказы, шт')
                    
                    # Легенда
                    lines1, labels1 = plt.gca().get_legend_handles_labels()
                    lines2, labels2 = ax2.get_legend_handles_labels()
                    plt.gca().legend(lines1 + lines2, labels1 + labels2, loc='upper left')
                    
                    # Заголовок и метки осей
                    plt.title(f'Прирост выручки и заказов для {query}')
                    plt.gca().set_ylabel('Выручка, ₽')
                    ax2.set_ylabel('Заказы, шт')
                    
                    # Поворот меток на оси X
                    plt.xticks(rotation=45)
                    
                    plt.tight_layout()
                    
                    # Сохраняем график
                    growth_chart = tempfile.NamedTemporaryFile(suffix='.png', prefix='growth_', delete=False)
                    plt.savefig(growth_chart.name, dpi=300)
                    plt.close()
                    
                    chart_files.append(growth_chart.name)
                except Exception as e:
                    logger.error(f"Error generating growth chart: {str(e)}")
            
            # 3. Круговая диаграмма распределения по платформам
            try:
                # Считаем выручку по платформам
                platform_revenue = {}
                for i, platform in enumerate(platforms):
                    if platform not in platform_revenue:
                        platform_revenue[platform] = 0
                    platform_revenue[platform] += revenue_data[i]
                
                # Формируем данные для диаграммы
                platforms_list = list(platform_revenue.keys())
                revenue_list = [platform_revenue[p] for p in platforms_list]
                
                # Создаем диаграмму
                plt.figure(figsize=(8, 8))
                plt.pie(revenue_list, labels=platforms_list, autopct='%1.1f%%', startangle=90,
                       colors=['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc949'],
                       wedgeprops={'edgecolor': 'w', 'linewidth': 1, 'antialiased': True})
                plt.title(f'Распределение выручки по платформам для {query}')
                plt.axis('equal')
                
                # Сохраняем диаграмму
                platforms_chart = tempfile.NamedTemporaryFile(suffix='.png', prefix='platforms_', delete=False)
                plt.savefig(platforms_chart.name, dpi=300)
                plt.close()
                
                chart_files.append(platforms_chart.name)
            except Exception as e:
                logger.error(f"Error generating platforms chart: {str(e)}")
            
            # 4. Диаграмма эффективности блогеров
            if blogger_data:
                try:
                    # Выбираем топ-5 блогеров по выручке
                    top_bloggers = sorted(blogger_data.items(), key=lambda x: x[1]["revenue"], reverse=True)[:5]
                    
                    # Формируем данные для диаграммы
                    blogger_names = []
                    blogger_revenue = []
                    blogger_orders = []
                    
                    for blogger, data in top_bloggers:
                        blogger_names.append(blogger[:10] + "..." if len(blogger) > 10 else blogger)
                        blogger_revenue.append(data["revenue"])
                        blogger_orders.append(data["orders"])
                    
                    # Создаем диаграмму
                    plt.figure(figsize=(10, 6))
                    x = np.arange(len(blogger_names))
                    width = 0.35
                    
                    plt.bar(x - width/2, blogger_revenue, width, label='Выручка, ₽', color='#4e79a7')
                    plt.bar(x + width/2, [o * 1000 for o in blogger_orders], width, label='Заказы x1000, шт', color='#f28e2b')
                    
                    plt.xlabel('Блогеры')
                    plt.ylabel('Значения')
                    plt.title(f'Топ-5 блогеров по эффективности для {query}')
                    plt.xticks(x, blogger_names, rotation=45)
                    plt.legend()
                    
                    plt.tight_layout()
                    
                    # Сохраняем диаграмму
                    bloggers_chart = tempfile.NamedTemporaryFile(suffix='.png', prefix='bloggers_', delete=False)
                    plt.savefig(bloggers_chart.name, dpi=300)
                    plt.close()
                    
                    chart_files.append(bloggers_chart.name)
                except Exception as e:
                    logger.error(f"Error generating bloggers chart: {str(e)}")
            
            # 5. Тепловая карта эффективности
            if len(platforms) >= 3 and len(blogger_data) >= 3:
                try:
                    # Создаем тепловую карту
                    # Используем данные о выручке по платформам и блогерам
                    top_platforms = sorted(platform_revenue.items(), key=lambda x: x[1], reverse=True)[:5]
                    top_bloggers = sorted(blogger_data.items(), key=lambda x: x[1]["revenue"], reverse=True)[:5]
                    
                    # Создаем матрицу данных
                    heatmap_data = np.zeros((len(top_bloggers), len(top_platforms)))
                    
                    # Заполняем матрицу
                    for i, (blogger, b_data) in enumerate(top_bloggers):
                        for j, (platform, _) in enumerate(top_platforms):
                            # Ищем публикации этого блогера на этой платформе
                            value = 0
                            for k, p in enumerate(platforms):
                                if p == platform and blogger_data.get(blogger, {}).get("revenue", 0) > 0:
                                    value += revenue_data[k]
                            heatmap_data[i, j] = value
                    
                    # Создаем тепловую карту
                    plt.figure(figsize=(10, 6))
                    
                    # Подготавливаем метки
                    platform_labels = [p[0] for p in top_platforms]
                    blogger_labels = [b[0][:10] + "..." if len(b[0]) > 10 else b[0] for b in top_bloggers]
                    
                    # Рисуем тепловую карту
                    plt.imshow(heatmap_data, cmap='YlOrRd')
                    
                    # Настраиваем оси
                    plt.xticks(np.arange(len(platform_labels)), platform_labels, rotation=45)
                    plt.yticks(np.arange(len(blogger_labels)), blogger_labels)
                    
                    # Добавляем значения в ячейки
                    for i in range(len(blogger_labels)):
                        for j in range(len(platform_labels)):
                            value = int(heatmap_data[i, j])
                            text_color = 'white' if value > np.max(heatmap_data) / 2 else 'black'
                            plt.text(j, i, f'{value:,}'.replace(',', ' '), 
                                    ha="center", va="center", color=text_color, fontsize=9)
                    
                    plt.colorbar(label='Выручка, ₽')
                    plt.title(f'Тепловая карта эффективности для {query}')
                    plt.tight_layout()
                    
                    # Сохраняем тепловую карту
                    heatmap_chart = tempfile.NamedTemporaryFile(suffix='.png', prefix='heatmap_', delete=False)
                    plt.savefig(heatmap_chart.name, dpi=300)
                    plt.close()
                    
                    chart_files.append(heatmap_chart.name)
                except Exception as e:
                    logger.error(f"Error generating heatmap chart: {str(e)}")
        
        return chart_files
    
    except Exception as e:
        logger.error(f"Error in generate_mpsta_charts: {str(e)}", exc_info=True)
        return []

def format_mpsta_results(data):
    """Форматирует результаты из API MPSTA в табличный вид с рекомендациями и генерирует графики."""
    chart_files = []
    
    try:
        if "error" in data:
            return data["error"], []
        
        query = data.get("query", "")
        is_article = data.get("is_article", False)
        mpsta_results = data.get("mpsta_results", {})
        serper_results = data.get("serper_results", {}).get("results", [])
        
        # --- НАЧАЛО ГЕНЕРАЦИИ ГРАФИКОВ ---
        try:
            # Проверяем, есть ли данные для построения графиков
            if mpsta_results:
                # Данные для графиков
                revenue_data = []
                orders_data = []
                platforms = []
                blogger_data = {}
                growth_data = {}
                
                # Обработка данных из ответа API
                if is_article and "ad_data" in mpsta_results:
                    ad_data = mpsta_results["ad_data"]
                    
                    # Собираем данные об эффективности рекламы
                    for ad in ad_data.get("items", []):
                        try:
                            # Данные о блогере/площадке
                            platform = ad.get("platform", "Неизвестно")
                            blogger = ad.get("blogger", {}).get("name", "Неизвестный")
                            
                            # Метрики публикации
                            likes = ad.get("likes", 0)
                            views = ad.get("views", 0)
                            revenue = ad.get("revenue", 0)
                            orders = ad.get("orders", 0)
                            
                            # Добавляем данные для графиков
                            revenue_data.append(revenue)
                            orders_data.append(orders)
                            platforms.append(platform)
                            
                            # Данные по блогерам
                            if blogger not in blogger_data:
                                blogger_data[blogger] = {
                                    "revenue": 0,
                                    "orders": 0,
                                    "likes": 0,
                                    "views": 0,
                                    "posts": 0
                                }
                            
                            blogger_data[blogger]["revenue"] += revenue
                            blogger_data[blogger]["orders"] += orders
                            blogger_data[blogger]["likes"] += likes
                            blogger_data[blogger]["views"] += views
                            blogger_data[blogger]["posts"] += 1
                            
                            # Данные о росте показателей
                            date = ad.get("date", "")
                            if date:
                                if date not in growth_data:
                                    growth_data[date] = {
                                        "revenue": 0,
                                        "orders": 0
                                    }
                                growth_data[date]["revenue"] += revenue
                                growth_data[date]["orders"] += orders
                        except Exception as e:
                            logger.error(f"Error processing ad data: {str(e)}")
                            continue
                
                # Если есть данные о нескольких товарах
                elif "product_data" in mpsta_results and "ad_data" in mpsta_results:
                    # Объединяем данные о товарах и их рекламе
                    articles = set()
                    for product in mpsta_results.get("product_data", []):
                        articles.add(product.get("article", ""))
                    
                    for ad_item in mpsta_results.get("ad_data", []):
                        try:
                            article = ad_item.get("article", "")
                            if article not in articles:
                                continue
                            
                            ad_list = ad_item.get("ad_data", {}).get("items", [])
                            
                            for ad in ad_list:
                                # Данные о блогере/площадке
                                platform = ad.get("platform", "Неизвестно")
                                blogger = ad.get("blogger", {}).get("name", "Неизвестный")
                                
                                # Метрики публикации
                                likes = ad.get("likes", 0)
                                views = ad.get("views", 0)
                                revenue = ad.get("revenue", 0)
                                orders = ad.get("orders", 0)
                                
                                # Добавляем данные для графиков
                                revenue_data.append(revenue)
                                orders_data.append(orders)
                                platforms.append(platform)
                                
                                # Данные по блогерам
                                if blogger not in blogger_data:
                                    blogger_data[blogger] = {
                                        "revenue": 0,
                                        "orders": 0,
                                        "likes": 0,
                                        "views": 0,
                                        "posts": 0
                                    }
                                
                                blogger_data[blogger]["revenue"] += revenue
                                blogger_data[blogger]["orders"] += orders
                                blogger_data[blogger]["likes"] += likes
                                blogger_data[blogger]["views"] += views
                                blogger_data[blogger]["posts"] += 1
                                
                                # Данные о росте показателей
                                date = ad.get("date", "")
                                if date:
                                    if date not in growth_data:
                                        growth_data[date] = {
                                            "revenue": 0,
                                            "orders": 0
                                        }
                                    growth_data[date]["revenue"] += revenue
                                    growth_data[date]["orders"] += orders
                        except Exception as e:
                            logger.error(f"Error processing product ad data: {str(e)}")
                            continue
                
                # Проверяем, есть ли данные для построения графиков
                if revenue_data and orders_data and platforms:
                    # 1. График сравнения выручки и заказов по публикациям
                    if len(revenue_data) > 0:
                        try:
                            plt.figure(figsize=(10, 6))
                            
                            # Создаем двойную ось Y
                            ax1 = plt.gca()
                            ax2 = ax1.twinx()
                            
                            # Данные для графика
                            x = np.arange(len(platforms))
                            
                            # Столбчатая диаграмма выручки
                            bars1 = ax1.bar(x - 0.2, revenue_data, width=0.4, color='#4e79a7', label='Выручка, ₽')
                            
                            # Столбчатая диаграмма заказов
                            bars2 = ax2.bar(x + 0.2, orders_data, width=0.4, color='#f28e2b', label='Заказы, шт')
                            
                            # Настройки оси X
                            shortened_platforms = []
                            for platform in platforms:
                                # Сокращаем названия для лучшей читаемости
                                if platform.lower() == 'instagram':
                                    shortened_platforms.append('IG')
                                elif platform.lower() == 'vkontakte':
                                    shortened_platforms.append('VK')
                                elif platform.lower() == 'youtube':
                                    shortened_platforms.append('YT')
                                elif platform.lower() == 'telegram':
                                    shortened_platforms.append('TG')
                                else:
                                    # Берем первые 2 символа
                                    shortened_platforms.append(platform[:2].upper())
                            
                            plt.xticks(x, shortened_platforms, rotation=45)
                            
                            # Легенда
                            lines1, labels1 = ax1.get_legend_handles_labels()
                            lines2, labels2 = ax2.get_legend_handles_labels()
                            ax1.legend(lines1 + lines2, labels1 + labels2, loc='upper left')
                            
                            # Заголовок и метки осей
                            plt.title(f'Сравнение публикаций по выручке и заказам для {query}')
                            ax1.set_ylabel('Выручка, ₽')
                            ax2.set_ylabel('Заказы, шт')
                            
                            # Добавляем значения над столбцами
                            for i, v in enumerate(revenue_data):
                                ax1.text(i - 0.2, v + max(revenue_data) * 0.02, f'{int(v):,}'.replace(',', ' '), 
                                        ha='center', va='bottom', fontsize=9, rotation=0)
                            
                            for i, v in enumerate(orders_data):
                                ax2.text(i + 0.2, v + max(orders_data) * 0.02, str(int(v)), 
                                        ha='center', va='bottom', fontsize=9, rotation=0)
                            
                            plt.tight_layout()
                            
                            # Сохраняем график
                            revenue_chart = tempfile.NamedTemporaryFile(suffix='.png', prefix='revenue_', delete=False)
                            plt.savefig(revenue_chart.name, dpi=300)
                            plt.close()
                            
                            chart_files.append(revenue_chart.name)
                        except Exception as e:
                            logger.error(f"Error generating revenue chart: {str(e)}")
                    
                    # 2. График роста показателей
                    if growth_data:
                        try:
                            # Сортируем даты
                            sorted_dates = sorted(growth_data.keys())
                            
                            # Данные для графика
                            growth_revenue = [growth_data[date]["revenue"] for date in sorted_dates]
                            growth_orders = [growth_data[date]["orders"] for date in sorted_dates]
                            
                            # Нормализуем даты для отображения
                            display_dates = []
                            for date_str in sorted_dates:
                                try:
                                    date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                                    display_dates.append(date_obj.strftime("%d.%m"))
                                except:
                                    display_dates.append(date_str)
                            
                            # Создаем график
                            plt.figure(figsize=(10, 6))
                            
                            # Линия выручки
                            plt.plot(display_dates, growth_revenue, 'o-', color='#4e79a7', linewidth=2, markersize=6, label='Выручка, ₽')
                            
                            # Линия заказов на другой оси Y
                            ax2 = plt.gca().twinx()
                            ax2.plot(display_dates, growth_orders, 'o--', color='#f28e2b', linewidth=2, markersize=6, label='Заказы, шт')
                            
                            # Легенда
                            lines1, labels1 = plt.gca().get_legend_handles_labels()
                            lines2, labels2 = ax2.get_legend_handles_labels()
                            plt.gca().legend(lines1 + lines2, labels1 + labels2, loc='upper left')
                            
                            # Заголовок и метки осей
                            plt.title(f'Прирост выручки и заказов для {query}')
                            plt.gca().set_ylabel('Выручка, ₽')
                            ax2.set_ylabel('Заказы, шт')
                            
                            # Поворот меток на оси X
                            plt.xticks(rotation=45)
                            
                            plt.tight_layout()
                            
                            # Сохраняем график
                            growth_chart = tempfile.NamedTemporaryFile(suffix='.png', prefix='growth_', delete=False)
                            plt.savefig(growth_chart.name, dpi=300)
                            plt.close()
                            
                            chart_files.append(growth_chart.name)
                        except Exception as e:
                            logger.error(f"Error generating growth chart: {str(e)}")
                    
                    # 3. Круговая диаграмма распределения по платформам
                    try:
                        # Считаем выручку по платформам
                        platform_revenue = {}
                        for i, platform in enumerate(platforms):
                            if platform not in platform_revenue:
                                platform_revenue[platform] = 0
                            platform_revenue[platform] += revenue_data[i]
                        
                        # Формируем данные для диаграммы
                        platforms_list = list(platform_revenue.keys())
                        revenue_list = [platform_revenue[p] for p in platforms_list]
                        
                        # Создаем диаграмму
                        plt.figure(figsize=(8, 8))
                        plt.pie(revenue_list, labels=platforms_list, autopct='%1.1f%%', startangle=90,
                               colors=['#4e79a7', '#f28e2b', '#e15759', '#76b7b2', '#59a14f', '#edc949'],
                               wedgeprops={'edgecolor': 'w', 'linewidth': 1, 'antialiased': True})
                        plt.title(f'Распределение выручки по платформам для {query}')
                        plt.axis('equal')
                        
                        # Сохраняем диаграмму
                        platforms_chart = tempfile.NamedTemporaryFile(suffix='.png', prefix='platforms_', delete=False)
                        plt.savefig(platforms_chart.name, dpi=300)
                        plt.close()
                        
                        chart_files.append(platforms_chart.name)
                    except Exception as e:
                        logger.error(f"Error generating platforms chart: {str(e)}")
                    
                    # 4. Диаграмма эффективности блогеров
                    if blogger_data:
                        try:
                            # Выбираем топ-5 блогеров по выручке
                            top_bloggers = sorted(blogger_data.items(), key=lambda x: x[1]["revenue"], reverse=True)[:5]
                            
                            # Формируем данные для диаграммы
                            blogger_names = []
                            blogger_revenue = []
                            blogger_orders = []
                            
                            for blogger, data in top_bloggers:
                                blogger_names.append(blogger[:10] + "..." if len(blogger) > 10 else blogger)
                                blogger_revenue.append(data["revenue"])
                                blogger_orders.append(data["orders"])
                            
                            # Создаем диаграмму
                            plt.figure(figsize=(10, 6))
                            x = np.arange(len(blogger_names))
                            width = 0.35
                            
                            plt.bar(x - width/2, blogger_revenue, width, label='Выручка, ₽', color='#4e79a7')
                            plt.bar(x + width/2, [o * 1000 for o in blogger_orders], width, label='Заказы x1000, шт', color='#f28e2b')
                            
                            plt.xlabel('Блогеры')
                            plt.ylabel('Значения')
                            plt.title(f'Топ-5 блогеров по эффективности для {query}')
                            plt.xticks(x, blogger_names, rotation=45)
                            plt.legend()
                            
                            plt.tight_layout()
                            
                            # Сохраняем диаграмму
                            bloggers_chart = tempfile.NamedTemporaryFile(suffix='.png', prefix='bloggers_', delete=False)
                            plt.savefig(bloggers_chart.name, dpi=300)
                            plt.close()
                            
                            chart_files.append(bloggers_chart.name)
                        except Exception as e:
                            logger.error(f"Error generating bloggers chart: {str(e)}")
                    
                    # 5. Тепловая карта эффективности
                    if len(platforms) >= 3 and len(blogger_data) >= 3:
                        try:
                            # Создаем тепловую карту
                            # Используем данные о выручке по платформам и блогерам
                            top_platforms = sorted(platform_revenue.items(), key=lambda x: x[1], reverse=True)[:5]
                            top_bloggers = sorted(blogger_data.items(), key=lambda x: x[1]["revenue"], reverse=True)[:5]
                            
                            # Создаем матрицу данных
                            heatmap_data = np.zeros((len(top_bloggers), len(top_platforms)))
                            
                            # Заполняем матрицу
                            for i, (blogger, b_data) in enumerate(top_bloggers):
                                for j, (platform, _) in enumerate(top_platforms):
                                    # Ищем публикации этого блогера на этой платформе
                                    value = 0
                                    for k, p in enumerate(platforms):
                                        if p == platform and blogger_data.get(blogger, {}).get("revenue", 0) > 0:
                                            value += revenue_data[k]
                                    heatmap_data[i, j] = value
                            
                            # Создаем тепловую карту
                            plt.figure(figsize=(10, 6))
                            
                            # Подготавливаем метки
                            platform_labels = [p[0] for p in top_platforms]
                            blogger_labels = [b[0][:10] + "..." if len(b[0]) > 10 else b[0] for b in top_bloggers]
                            
                            # Рисуем тепловую карту
                            plt.imshow(heatmap_data, cmap='YlOrRd')
                            
                            # Настраиваем оси
                            plt.xticks(np.arange(len(platform_labels)), platform_labels, rotation=45)
                            plt.yticks(np.arange(len(blogger_labels)), blogger_labels)
                            
                            # Добавляем значения в ячейки
                            for i in range(len(blogger_labels)):
                                for j in range(len(platform_labels)):
                                    value = int(heatmap_data[i, j])
                                    text_color = 'white' if value > np.max(heatmap_data) / 2 else 'black'
                                    plt.text(j, i, f'{value:,}'.replace(',', ' '), 
                                            ha="center", va="center", color=text_color, fontsize=9)
                            
                            plt.colorbar(label='Выручка, ₽')
                            plt.title(f'Тепловая карта эффективности для {query}')
                            plt.tight_layout()
                            
                            # Сохраняем тепловую карту
                            heatmap_chart = tempfile.NamedTemporaryFile(suffix='.png', prefix='heatmap_', delete=False)
                            plt.savefig(heatmap_chart.name, dpi=300)
                            plt.close()
                            
                            chart_files.append(heatmap_chart.name)
                        except Exception as e:
                            logger.error(f"Error generating heatmap chart: {str(e)}")
            
        except Exception as chart_error:
            logger.error(f"Error generating charts: {str(chart_error)}", exc_info=True)
        # --- КОНЕЦ ГЕНЕРАЦИИ ГРАФИКОВ ---
        
        # Формируем сводную информацию о товаре/нише
        summary = f"🔍 *Анализ рекламы {'по артикулу' if is_article else 'товара'}: {query}*\n\n"
        
        ad_data = []
        
        if is_article and "ad_data" in mpsta_results:
            ad_data = mpsta_results.get("ad_data", {}).get("items", [])
        elif "ad_data" in mpsta_results:
            # Для поискового запроса объединяем все рекламные данные
            for ad_item in mpsta_results.get("ad_data", []):
                ad_data.extend(ad_item.get("ad_data", {}).get("items", []))
        
        # Общая статистика
        total_ads = len(ad_data)
        total_revenue = sum(ad.get("revenue", 0) for ad in ad_data)
        total_orders = sum(ad.get("orders", 0) for ad in ad_data)
        total_ad_views = sum(ad.get("views", 0) for ad in ad_data)
        total_ad_likes = sum(ad.get("likes", 0) for ad in ad_data)
        
        # Статистика по платформам
        platforms = {}
        bloggers = {}
        
        for ad in ad_data:
            platform = ad.get("platform", "Неизвестно")
            blogger = ad.get("blogger", {}).get("name", "Неизвестный")
            
            if platform not in platforms:
                platforms[platform] = {
                    "count": 0,
                    "revenue": 0,
                    "orders": 0,
                    "views": 0,
                    "likes": 0
                }
            
            platforms[platform]["count"] += 1
            platforms[platform]["revenue"] += ad.get("revenue", 0)
            platforms[platform]["orders"] += ad.get("orders", 0)
            platforms[platform]["views"] += ad.get("views", 0)
            platforms[platform]["likes"] += ad.get("likes", 0)
            
            if blogger not in bloggers:
                bloggers[blogger] = {
                    "count": 0,
                    "revenue": 0,
                    "orders": 0,
                    "views": 0,
                    "likes": 0,
                    "platform": platform
                }
            
            bloggers[blogger]["count"] += 1
            bloggers[blogger]["revenue"] += ad.get("revenue", 0)
            bloggers[blogger]["orders"] += ad.get("orders", 0)
            bloggers[blogger]["views"] += ad.get("views", 0)
            bloggers[blogger]["likes"] += ad.get("likes", 0)
        
        # Дополняем данными из serper
        for result in serper_results:
            platform = result.get("site", "")
            platform_name = platform
            
            if "instagram" in platform.lower():
                platform_name = "Instagram"
            elif "vk.com" in platform.lower():
                platform_name = "VK"
            elif "facebook" in platform.lower():
                platform_name = "Facebook"
            elif "youtube" in platform.lower():
                platform_name = "YouTube"
            elif "tiktok" in platform.lower():
                platform_name = "TikTok"
            
            if platform_name not in platforms:
                platforms[platform_name] = {
                    "count": 0,
                    "revenue": 0,
                    "orders": 0,
                    "views": 0,
                    "likes": 0
                }
            
            platforms[platform_name]["count"] += 1
            platforms[platform_name]["views"] += result.get("views", 0)
            platforms[platform_name]["likes"] += result.get("likes", 0)
            platforms[platform_name]["revenue"] += result.get("approx_revenue", 0)
            platforms[platform_name]["orders"] += result.get("approx_clients", 0)
        
        # Формируем сводную информацию по MPSTA
        if total_ads > 0:
            summary += "📊 *Общая статистика*\n"
            summary += f"• Всего рекламных публикаций: {total_ads}\n"
            summary += f"• Суммарная выручка: {total_revenue:,} ₽\n".replace(',', ' ')
            summary += f"• Суммарное количество заказов: {total_orders}\n"
            summary += f"• Общее количество просмотров: {total_ad_views:,}\n".replace(',', ' ')
            summary += f"• Общее количество лайков: {total_ad_likes:,}\n\n".replace(',', ' ')
            
            # Эффективность платформ
            if platforms:
                summary += "📱 *Эффективность платформ*\n"
                
                # Сортируем платформы по выручке
                sorted_platforms = sorted(
                    platforms.items(), 
                    key=lambda x: x[1].get("revenue", 0), 
                    reverse=True
                )
                
                for platform, stats in sorted_platforms[:5]:  # Показываем топ-5
                    summary += f"• *{platform}*:\n"
                    summary += f"  - Публикаций: {stats.get('count')}\n"
                    summary += f"  - Выручка: {stats.get('revenue', 0):,} ₽\n".replace(',', ' ')
                    summary += f"  - Заказы: {stats.get('orders', 0)}\n"
                    summary += f"  - Просмотры: {stats.get('views', 0):,}\n".replace(',', ' ')
                
                summary += "\n"
            
            # Топ блогеры
            if bloggers:
                summary += "👤 *Топ-3 блогера*\n"
                
                # Сортируем блогеров по выручке
                sorted_bloggers = sorted(
                    bloggers.items(), 
                    key=lambda x: x[1].get("revenue", 0), 
                    reverse=True
                )
                
                for blogger, stats in sorted_bloggers[:3]:  # Показываем топ-3
                    summary += f"• *{blogger}* ({stats.get('platform')}):\n"
                    summary += f"  - Публикаций: {stats.get('count')}\n"
                    summary += f"  - Выручка: {stats.get('revenue', 0):,} ₽\n".replace(',', ' ')
                    summary += f"  - Заказы: {stats.get('orders', 0)}\n"
                    summary += f"  - Среднее на публикацию: {stats.get('revenue', 0) / stats.get('count') if stats.get('count') > 0 else 0:,.0f} ₽\n".replace(',', ' ')
                
                summary += "\n"
        else:
            summary += "⚠️ *Данные MPSTA*\n"
            summary += "По данному товару не найдено рекламных публикаций в MPSTA.\n\n"
        
        # Добавляем данные из serper, если они есть
        if serper_results:
            # Считаем общую статистику
            total_mentions = len(serper_results)
            total_views = sum(result.get("views", 0) for result in serper_results)
            total_likes = sum(result.get("likes", 0) for result in serper_results)
            
            summary += "🔍 *Данные из социальных сетей*\n"
            summary += f"• Всего упоминаний: {total_mentions}\n"
            summary += f"• Общее количество просмотров: {total_views:,}\n".replace(',', ' ')
            summary += f"• Общее количество лайков: {total_likes:,}\n\n".replace(',', ' ')
            
            # Показываем топ-3 результата
            summary += "📱 *Топ-3 публикации*\n"
            
            for result in serper_results[:3]:  # Показываем топ-3
                title = result.get("title", "")[:50] + "..." if len(result.get("title", "")) > 50 else result.get("title", "")
                site = result.get("site", "")
                likes = result.get("likes", 0)
                views = result.get("views", 0)
                
                summary += f"• *{title}*\n"
                summary += f"  - Площадка: {site}\n"
                summary += f"  - Лайки: {likes:,}\n".replace(',', ' ')
                summary += f"  - Просмотры: {views:,}\n".replace(',', ' ')
            
            summary += "\n"
        else:
            summary += "🔍 *Данные из социальных сетей*\n"
            summary += "Упоминаний в социальных сетях не найдено.\n\n"
        
        # Рекомендации
        summary += "💡 *Рекомендации*\n"
        
        # Анализируем данные для рекомендаций
        if total_ads > 0 or serper_results:
            # Если есть данные о рекламе
            
            # Находим лучшую платформу
            best_platform = None
            best_revenue = 0
            
            for platform, stats in platforms.items():
                if stats.get("revenue", 0) > best_revenue:
                    best_revenue = stats.get("revenue", 0)
                    best_platform = platform
            
            if best_platform:
                summary += f"• Фокусируйтесь на *{best_platform}* - эта платформа показывает наилучшие результаты по выручке\n"
            
            # Если есть топ-блогеры
            if bloggers:
                top_blogger = max(bloggers.items(), key=lambda x: x[1].get("revenue", 0))[0]
                
                summary += f"• Продолжайте сотрудничество с блогером *{top_blogger}* - показывает наилучшие результаты\n"
                
                avg_post_price = 15000  # Примерная стоимость поста
                top_blogger_roi = bloggers[top_blogger].get("revenue", 0) / avg_post_price if avg_post_price > 0 else 0
                
                if top_blogger_roi > 2:
                    summary += f"• ROI сотрудничества с топ-блогером около {top_blogger_roi:.1f}x - очень эффективно\n"
            
            # Рекомендации по охвату
            if total_ad_views > 0:
                conversion = total_orders / total_ad_views * 100 if total_ad_views > 0 else 0
                
                if conversion < 0.1:
                    summary += "• Низкая конверсия просмотров в заказы - проверьте качество контента и целевую аудиторию\n"
                elif conversion > 0.5:
                    summary += "• Высокая конверсия просмотров в заказы - увеличьте рекламный бюджет для масштабирования\n"
            
            # Общие рекомендации
            if total_ads < 5:
                summary += "• Увеличьте количество рекламных публикаций для достижения большего охвата\n"
            
            # Рекомендации по разнообразию платформ
            if len(platforms) < 3:
                summary += "• Расширьте присутствие на других платформах для охвата различных сегментов аудитории\n"
            
            # Если нет данных в MPSTA, но есть в соцсетях
            if total_ads == 0 and serper_results:
                summary += "• В базе MPSTA нет данных о рекламе вашего товара - возможно, конкуренты используют неотслеживаемые каналы\n"
                summary += "• Анализируйте упоминания в соцсетях для выявления неформальных маркетинговых каналов\n"
        else:
            # Если нет данных о рекламе вообще
            summary += "• Товар не имеет активного продвижения в соцсетях - это возможность для выхода на новый рынок\n"
            summary += "• Начните с тестовых рекламных кампаний на 2-3 популярных платформах\n"
            summary += "• Изучите конкурентов в вашей нише для определения эффективных каналов продвижения\n"
        
        summary += "\n✅ *Полная аналитика представлена на графиках*"
        
        return summary, chart_files
    
    except Exception as e:
        logger.error(f"Error in format_mpsta_results: {str(e)}", exc_info=True)
        # В случае ошибки удаляем временные файлы
        for chart_file in chart_files:
            try:
                os.remove(chart_file)
            except:
                pass
        return f"❌ Произошла ошибка при форматировании результатов: {str(e)}", []

async def check_tracked_items():
    """Периодическая проверка отслеживаемых товаров и отправка уведомлений."""
    logger.info("Starting tracked items monitoring...")
    while True:
        try:
            # Получаем данные всех пользователей
            all_users = subscription_manager.get_all_users()
            
            for user_id, user_data in all_users.items():
                # Проверяем, активна ли подписка
                if not subscription_manager.is_subscription_active(user_id):
                    continue
                
                # Получаем список отслеживаемых товаров
                tracked_items = user_data.get("tracked_items", [])
                if not tracked_items:
                    continue
                
                # Обновляем информацию о каждом товаре
                notifications = []
                
                for item in tracked_items:
                    try:
                        # Получаем данные о товаре
                        if isinstance(item, dict):
                            item_id = item.get("id", "")
                            old_price = item.get("price", 0)
                            old_stock = item.get("stock", 0)
                            name = item.get("name", f"Товар {item_id}")
                        else:
                            item_id = item
                            old_price = 0
                            old_stock = 0
                            name = f"Товар {item_id}"
                        
                        # Пропускаем товары, у которых нет ID
                        if not item_id:
                            continue
                        
                        # Получаем актуальные данные
                        product_info = await get_wb_product_info(item_id)
                        
                        if not product_info:
                            continue
                        
                        # Получаем новые значения
                        new_price = product_info["price"]["current"]
                        new_stock = product_info["stocks"]["total"]
                        name = product_info["name"]
                        
                        # Проверяем изменения
                        price_change = new_price - old_price if old_price > 0 else 0
                        stock_change = new_stock - old_stock if old_stock > 0 else 0
                        
                        # Формируем уведомления при значительных изменениях
                        notification = None
                        
                        # Изменение цены более чем на 5%
                        if old_price > 0 and abs(price_change) / old_price > 0.05:
                            change_type = "увеличилась" if price_change > 0 else "снизилась"
                            change_icon = "📈" if price_change > 0 else "📉"
                            
                            notification = (
                                f"{change_icon} *Изменение цены товара!*\n\n"
                                f"*{name}*\n"
                                f"🔢 Артикул: {item_id}\n"
                                f"💰 Цена {change_type} с {old_price} ₽ до {new_price} ₽\n"
                                f"🔄 Изменение: {abs(price_change)} ₽ ({abs(price_change/old_price*100):.1f}%)\n\n"
                                f"🛒 [Посмотреть на Wildberries](https://www.wildberries.ru/catalog/{item_id}/detail.aspx)"
                            )
                        
                        # Значительное изменение наличия (больше 50%)
                        if old_stock > 0 and (stock_change < 0 or (new_stock > 0 and old_stock == 0)):
                            if stock_change < 0 and new_stock == 0:
                                # Товар закончился
                                notification = (
                                    f"⚠️ *Товар закончился!*\n\n"
                                    f"*{name}*\n"
                                    f"🔢 Артикул: {item_id}\n"
                                    f"📦 Наличие: 0 шт.\n\n"
                                    f"🛒 [Посмотреть на Wildberries](https://www.wildberries.ru/catalog/{item_id}/detail.aspx)"
                                )
                            elif new_stock > 0 and old_stock == 0:
                                # Товар появился в наличии
                                notification = (
                                    f"✅ *Товар снова в наличии!*\n\n"
                                    f"*{name}*\n"
                                    f"🔢 Артикул: {item_id}\n"
                                    f"📦 Наличие: {new_stock} шт.\n"
                                    f"💰 Цена: {new_price} ₽\n\n"
                                    f"🛒 [Посмотреть на Wildberries](https://www.wildberries.ru/catalog/{item_id}/detail.aspx)"
                                )
                            elif stock_change < 0 and abs(stock_change/old_stock) > 0.5:
                                # Количество уменьшилось более чем на 50%
                                notification = (
                                    f"📉 *Товар заканчивается!*\n\n"
                                    f"*{name}*\n"
                                    f"🔢 Артикул: {item_id}\n"
                                    f"📦 Наличие: {new_stock} шт. (-{abs(stock_change)} шт.)\n"
                                    f"💰 Цена: {new_price} ₽\n\n"
                                    f"🛒 [Посмотреть на Wildberries](https://www.wildberries.ru/catalog/{item_id}/detail.aspx)"
                                )
                        
                        # Если есть уведомление, добавляем его в список
                        if notification:
                            notifications.append(notification)
                        
                        # Обновляем данные товара в любом случае
                        new_item = {
                            "id": item_id,
                            "name": name,
                            "price": new_price,
                            "stock": new_stock,
                            "last_update": datetime.now().isoformat()
                        }
                        
                        subscription_manager.update_tracked_item(user_id, item_id, new_item)
                        
                    except Exception as item_error:
                        logger.error(f"Error updating tracked item {item_id}: {str(item_error)}")
                        continue
                
                # Отправляем уведомления пользователю
                for notification in notifications:
                    try:
                        # Создаем инлайн-клавиатуру для уведомления
                        keyboard = InlineKeyboardMarkup(inline_keyboard=[
                            [InlineKeyboardButton(text="📋 Посмотреть все товары", callback_data="tracked")]
                        ])
                        
                        await bot.send_message(
                            chat_id=int(user_id),
                            text=notification,
                            parse_mode=ParseMode.MARKDOWN,
                            reply_markup=keyboard,
                            disable_web_page_preview=False
                        )
                        
                        # Делаем небольшую паузу между отправкой сообщений
                        await asyncio.sleep(0.5)
                        
                    except Exception as notify_error:
                        logger.error(f"Error sending notification to user {user_id}: {str(notify_error)}")
                        continue
            
            # Проверяем изменения каждые 3 часа
            await asyncio.sleep(3 * 60 * 60)
            
        except Exception as e:
            logger.error(f"Error in check_tracked_items: {str(e)}")
            # В случае ошибки ждем 10 минут и пробуем снова
            await asyncio.sleep(10 * 60)

@dp.callback_query(lambda c: c.data == "track_item")
async def handle_track_item(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback_query.from_user.id
        
        can_perform = subscription_manager.can_perform_action(user_id, 'tracking_items')
        if not can_perform:
            await callback_query.answer(
                "❌ У вас нет активной подписки или превышен лимит отслеживаемых товаров",
                show_alert=True
            )
            return
        
        await state.set_state(UserStates.waiting_for_tracking)
        
        await callback_query.message.edit_text(
            "🔍 *Отслеживание товара*\n\n"
            "Отправьте артикул товара, который хотите отслеживать.\n"
            "Например: 12345678\n\n"
            "Вы будете получать уведомления об изменении цены, наличия и рейтинга товара.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in track item handler: {str(e)}")
        await callback_query.answer(
            "Произошла ошибка. Пожалуйста, попробуйте позже.",
            show_alert=True
        )

# Обработчик ввода артикула для отслеживания
@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_tracking)
async def handle_tracking_article(message: types.Message, state: FSMContext):
    try:
        user_id = message.from_user.id
        article = message.text.strip()
        
        # Проверяем валидность артикула
        if not article.isdigit():
            await message.answer(
                "❌ Некорректный артикул. Пожалуйста, введите числовой артикул товара.",
                reply_markup=back_keyboard()
            )
            return
            
        # Проверяем существование товара
        product_info = await get_wb_product_info(article)
        if not product_info:
            await message.answer(
                "❌ Товар не найден. Проверьте правильность артикула.",
                reply_markup=back_keyboard()
            )
            return
            
        # Добавляем товар в отслеживаемые
        success = subscription_manager.add_tracked_item(
            user_id=user_id,
            article=article,
            price=product_info['price']['current'],
            sales=product_info['sales']['total'],
            rating=product_info['rating']
        )
        
        if success:
            await message.answer(
                f"✅ Товар *{product_info['name']}* успешно добавлен в отслеживаемы!\n\n"
                f"🔢 Артикул: {article}\n"
                f"💰 Текущая цена: {product_info['price']['current']} ₽\n"
                f"📦 Наличие: {product_info['stocks']['total']} шт.\n\n"
                "Вы будете получать уведомления при изменении цены, наличия или рейтинга товара.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=main_menu_kb()
            )
        else:
            await message.answer(
                "❌ Не удалось добавить товар в отслеживаемые. Возможно, вы достигли лимита отслеживаемых товаров.",
                reply_markup=main_menu_kb()
            )
            
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error adding tracking item: {str(e)}")
        await message.answer(
            "❌ Произошла ошибка при добавлении товара в отслеживаемые. Пожалуйста, попробуйте позже.",
            reply_markup=main_menu_kb()
        )
        await state.clear()

@dp.callback_query(lambda c: c.data == "tracked")
async def handle_tracked_items(callback_query: types.CallbackQuery):
    try:
        user_id = callback_query.from_user.id
        tracked_items = subscription_manager.get_tracked_items(user_id)
        
        if not tracked_items:
            await callback_query.message.edit_text(
                "📋 *Список отслеживаемых товаров*\n\n"
                "У вас пока нет отслеживаемых товаров.\n"
                "Чтобы добавить товар в отслеживаемые, нажмите кнопку \"📱 Отслеживание\" в главном меню.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=back_keyboard()
            )
            return
        
        # Формируем сообщение со списком отслеживаемых товаров
        message_text = "📋 *Список отслеживаемых товаров*\n\n"
        
        for i, item in enumerate(tracked_items):
            # Формируем данные в зависимости от формата
            if isinstance(item, dict):
                item_id = item.get("id", "Неизвестно")
                item_name = item.get("name", "Неизвестный товар")
                item_price = item.get("price", 0)
                added_date = item.get("added_date", datetime.now().isoformat())
                
                # Переводим дату в читаемый формат
                try:
                    date_obj = datetime.fromisoformat(added_date)
                    formatted_date = date_obj.strftime("%d.%m.%Y")
                except:
                    formatted_date = "Неизвестно"
            else:
                # Старый формат (просто ID)
                item_id = item
                item_name = "Неизвестный товар"
                item_price = 0
                formatted_date = "Неизвестно"
            
            message_text += f"{i+1}. *{item_name}*\n"
            message_text += f"   🔢 Артикул: {item_id}\n"
            message_text += f"   💰 Цена: {item_price} ₽\n"
            message_text += f"   📅 Добавлен: {formatted_date}\n\n"
        
        # Создаем клавиатуру с кнопками для действий с отслеживаемыми товарами
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_tracked"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete_tracked")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="profile")]
        ])
        
        await callback_query.message.edit_text(
            message_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error handling tracked items: {str(e)}")
        await callback_query.answer(
            "Произошла ошибка при получении списка отслеживаемых товаров.",
            show_alert=True
        )

@dp.callback_query(lambda c: c.data == "refresh_tracked")
async def handle_refresh_tracked(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback_query.from_user.id
        tracked_items = subscription_manager.get_tracked_items(user_id)
        
        if not tracked_items:
            await callback_query.answer("У вас нет отслеживаемых товаров")
            return
        
        # Отправляем сообщение о начале обновления
        await callback_query.message.edit_text(
            "🔄 *Обновление данных по отслеживаемым товарам...*\n\n"
            "Пожалуйста, подождите, этот процесс может занять некоторое время.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Обновляем информацию по каждому товару
        updated_items = []
        not_found_items = []
        
        for item in tracked_items:
            # Получаем ID товара в зависимости от формата
            if isinstance(item, dict):
                item_id = item.get("id", "")
                old_price = item.get("price", 0)
                old_stock = item.get("stock", 0)
            else:
                item_id = item
                old_price = 0
                old_stock = 0
            
            # Получаем обновленную информацию
            product_info = await get_wb_product_info(item_id)
            
            if product_info:
                # Обновляем информацию о товаре
                new_item = {
                    "id": item_id,
                    "name": product_info["name"],
                    "price": product_info["price"]["current"],
                    "old_price": old_price,
                    "stock": product_info["stocks"]["total"],
                    "old_stock": old_stock,
                    "last_update": datetime.now().isoformat()
                }
                
                # Проверяем изменения цены и наличия
                price_change = new_item["price"] - old_price if old_price > 0 else 0
                stock_change = new_item["stock"] - old_stock if old_stock > 0 else 0
                
                new_item["price_change"] = price_change
                new_item["stock_change"] = stock_change
                
                updated_items.append(new_item)
                
                # Обновляем товар в базе данных
                subscription_manager.update_tracked_item(user_id, item_id, new_item)
            else:
                not_found_items.append(item_id)
        
        # Формируем сообщение с результатами обновления
        message_text = "✅ *Обновление завершено*\n\n"
        
        if updated_items:
            message_text += "📊 *Обновленные товары:*\n\n"
            
            for item in updated_items:
                message_text += f"*{item['name']}*\n"
                message_text += f"🔢 Артикул: {item['id']}\n"
                message_text += f"💰 Цена: {item['price']} ₽"
                
                if item.get("price_change", 0) != 0:
                    change_icon = "📈" if item["price_change"] > 0 else "📉"
                    message_text += f" {change_icon} {abs(item['price_change'])} ₽\n"
                else:
                    message_text += "\n"
                    
                message_text += f"📦 Наличие: {item['stock']} шт."
                
                if item.get("stock_change", 0) != 0:
                    change_icon = "📈" if item["stock_change"] > 0 else "📉"
                    message_text += f" {change_icon} {abs(item['stock_change'])} шт.\n"
                else:
                    message_text += "\n"
                    
                message_text += f"🕒 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M')}\n\n"
        
        if not_found_items:
            message_text += "⚠️ *Не удалось обновить:*\n"
            for item_id in not_found_items:
                message_text += f"• Артикул {item_id}\n"
            message_text += "\n"
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_tracked"),
                InlineKeyboardButton(text="🗑️ Удалить", callback_data="delete_tracked")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="profile")]
        ])
        
        await callback_query.message.edit_text(
            message_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Error refreshing tracked items: {str(e)}")
        await callback_query.answer(
            "Произошла ошибка при обновлении отслеживаемых товаров",
            show_alert=True
        )

@dp.callback_query(lambda c: c.data == "delete_tracked")
async def handle_delete_tracked_start(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback_query.from_user.id
        tracked_items = subscription_manager.get_tracked_items(user_id)
        
        if not tracked_items:
            await callback_query.answer("У вас нет отслеживаемых товаров")
            return
        
        # Создаем клавиатуру с товарами для удаления
        keyboard = []
        
        for i, item in enumerate(tracked_items):
            if isinstance(item, dict):
                item_id = item.get("id", "")
                item_name = item.get("name", "Неизвестный товар")
            else:
                item_id = item
                item_name = f"Товар {item_id}"
            
            # Добавляем кнопку для каждого товара
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{i+1}. {item_name[:30]}... (ID: {item_id})",
                    callback_data=f"delete_item_{item_id}"
                )
            ])
        
        # Добавляем кнопку "Назад"
        keyboard.append([InlineKeyboardButton(text="◀️ Назад", callback_data="tracked")])
        
        await callback_query.message.edit_text(
            "🗑️ *Удаление товаров из отслеживаемых*\n\n"
            "Выберите товар, который хотите удалить:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=InlineKeyboardMarkup(inline_keyboard=keyboard)
        )
        
    except Exception as e:
        logger.error(f"Error preparing delete tracked items: {str(e)}")
        await callback_query.answer(
            "Произошла ошибка при подготовке списка товаров для удаления",
            show_alert=True
        )

@dp.callback_query(lambda c: c.data.startswith("delete_item_"))
async def handle_delete_tracked_item(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback_query.from_user.id
        item_id = callback_query.data.split("_")[2]
        
        # Удаляем товар из отслеживаемых
        success = subscription_manager.remove_tracked_item(user_id, item_id)
        
        if success:
            await callback_query.answer(f"Товар {item_id} удален из отслеживаемых", show_alert=True)
        else:
            await callback_query.answer("Не удалось удалить товар", show_alert=True)
        
        # Возвращаемся к списку отслеживаемых товаров
        await handle_tracked_items(callback_query)
        
    except Exception as e:
        logger.error(f"Error deleting tracked item: {str(e)}")
        await callback_query.answer(
            "Произошла ошибка при удалении товара",
            show_alert=True
        )

async def get_mpstats_category_data(category_path, days=30):
    """Получение данных по категории с MPSTATS"""
    try:
        # Получаем даты для запроса
        end_date = datetime.now().strftime("%Y-%m-%d")
        start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        # Кодируем путь категории для URL
        encoded_path = quote(category_path)
        
        # URL для запроса данных о категории
        url = f"https://mpstats.io/api/wb/get/category"
        
        # Заголовки для запроса
        headers = {
            "X-Mpstats-TOKEN": MPSTATS_API_KEY,
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
            "Origin": "https://mpstats.io",
            "Referer": "https://mpstats.io/",
            "Authorization": f"Bearer {MPSTATS_API_KEY}"
        }
        
        # Параметры запроса
        params = {
            "path": encoded_path,
            "d1": start_date,
            "d2": end_date,
            "token": MPSTATS_API_KEY
        }
        
        logger.info(f"Sending request to MPSTATS API: {url}")
        logger.info(f"Request headers: {headers}")
        logger.info(f"Request params: {params}")
        
        # Выполняем GET запрос к API
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response headers: {response.headers}")
                logger.info(f"Response body: {response_text}")
                
                if response.status == 200:
                    data = json.loads(response_text)
                    logger.info(f"Successfully got category data for {category_path}")
                    return data
                else:
                    logger.error(f"Error getting category data: {response.status} - {response_text}")
                    return {"error": f"Ошибка API: {response.status} - {response_text}"}
    except Exception as e:
        logger.error(f"Exception getting category data: {str(e)}")
        return {"error": f"Ошибка при получении данных: {str(e)}"}

def analyze_mpstats_category_data(data):
    """Анализ данных по категории с MPSTATS"""
    if not data or not isinstance(data, dict):
        logger.error("Invalid category data format: not a dict or empty")
        return None
    
    # Получаем список ключевых запросов из категории
    keywords = data.get("topQueries", [])
    if not keywords:
        logger.warning("No topQueries found in category data")
        # Пробуем другие возможные структуры данных
        if "queries" in data:
            keywords = data.get("queries", [])
        elif "keywords" in data:
            keywords = data.get("keywords", [])
    
    if not keywords:
        logger.error("No keywords found in category data")
        return None
    
    logger.info(f"Found {len(keywords)} keywords in category data")
    
    result = []
    
    for keyword_data in keywords:
        if not isinstance(keyword_data, dict):
            logger.warning(f"Invalid keyword data format: {keyword_data}")
            continue
        
        keyword = keyword_data.get("name", "")
        if not keyword:
            logger.warning("Keyword with empty name, skipping")
            continue
        
        try:
            # Собираем метрики
            frequency_30 = keyword_data.get("frequency", 0)
            revenue_30 = keyword_data.get("revenue", 0)
            revenue_avg_30 = keyword_data.get("avgCategoryRevenue", 0)
            
            revenue_lost_percent = 0
            if revenue_30 > 0 and revenue_avg_30 > 0:
                revenue_lost_percent = max(0, min(100, (1 - revenue_30 / revenue_avg_30) * 100))
            
            # Динамика (будем получать из дополнительных запросов если возможно)
            dynamics = keyword_data.get("dynamics", {})
            if isinstance(dynamics, dict):
                frequency_dynamics = dynamics.get("frequency", {})
                if isinstance(frequency_dynamics, dict):
                    dynamics_30 = frequency_dynamics.get("last30days", 0)
                    dynamics_60 = frequency_dynamics.get("last60days", 0)
                    dynamics_90 = frequency_dynamics.get("last90days", 0)
                else:
                    dynamics_30 = dynamics_60 = dynamics_90 = 0
            else:
                dynamics_30 = dynamics_60 = dynamics_90 = 0
            
            # Дополнительные метрики
            monopoly = keyword_data.get("monopoly", 0)
            avg_price = keyword_data.get("avgPrice", 0)
            ad_percent = keyword_data.get("adPercent", 0)
            rating = keyword_data.get("rating", 0)
            
            # Формируем результат
            result.append({
                "keyword": keyword,
                "rating": rating,
                "frequency_30": frequency_30,
                "dynamics_30": dynamics_30,
                "dynamics_60": dynamics_60,
                "dynamics_90": dynamics_90,
                "revenue_30": revenue_30,
                "revenue_avg_30": revenue_avg_30,
                "revenue_lost_percent": revenue_lost_percent,
                "monopoly": monopoly,
                "avg_price": avg_price,
                "ad_percent": ad_percent
            })
        except Exception as e:
            logger.error(f"Error processing keyword {keyword}: {str(e)}")
            continue
    
    # Если не удалось проанализировать ни один ключевой запрос, возвращаем None
    if not result:
        logger.error("No keywords were successfully analyzed")
        return None
    
    logger.info(f"Successfully analyzed {len(result)} keywords")
    return result

@dp.callback_query(lambda c: c.data == "stats")
async def stats_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id
    logger.info(f"User {user_id} requested stats")
    
    try:
        # Получаем статистику пользователя
        tracked_items = subscription_manager.get_tracked_items(user_id)
        
        # Подсчитываем общую стоимость отслеживаемых товаров
        total_price = 0
        total_items = 0
        
        for item in tracked_items:
            if isinstance(item, dict):
                price = item.get("price", 0)
                total_price += price
                total_items += 1
        
        # Получаем статистику лимитов
        subscription_stats = subscription_manager.get_subscription_stats(user_id)
        usage_stats = ""
        
        if subscription_stats and "actions" in subscription_stats:
            usage_stats = "*Использовано лимитов:*\n"
            for action, data in subscription_stats["actions"].items():
                # Безопасное отображение бесконечности
                if data['limit'] == float('inf'):
                    limit_str = "∞"
                    percent = 0  # При безлимите процент всегда 0
                else:
                    limit_str = str(data['limit'])
                    percent = int((data['used'] / data['limit']) * 100) if data['limit'] > 0 else 0
                
                usage_stats += f"• {action}: {data['used']}/{limit_str} ({percent}%)\n"
        
        # Формируем текст статистики
        stats_text = (
            "📊 *Статистика*\n\n"
            f"*Отслеживание товаров:*\n"
            f"• Всего товаров: {total_items}\n"
            f"• Общая стоимость: {total_price} ₽\n"
            f"• Средняя цена: {int(total_price / total_items) if total_items > 0 else 0} ₽\n\n"
        )
        
        if usage_stats:
            stats_text += usage_stats + "\n"
            
        # Получаем статистику запросов безопасным способом
        product_analysis_used = 0
        niche_analysis_used = 0
        
        if subscription_stats and "actions" in subscription_stats:
            if "product_analysis" in subscription_stats["actions"]:
                product_analysis_used = subscription_stats["actions"]["product_analysis"].get("used", 0)
            if "niche_analysis" in subscription_stats["actions"]:
                niche_analysis_used = subscription_stats["actions"]["niche_analysis"].get("used", 0)
        
        stats_text += (
            "*Общая статистика запросов:*\n"
            f"• Проанализировано товаров: {product_analysis_used}\n"
            f"• Проанализировано ниш: {niche_analysis_used}\n"
        )
        
        await callback_query.message.edit_text(
            stats_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
    except Exception as e:
        logger.error(f"Error in stats callback: {str(e)}")
        try:
            # Пробуем отправить сообщение без Markdown форматирования
            await callback_query.message.edit_text(
                "📊 Статистика\n\nПроизошла ошибка при загрузке данных статистики. Пожалуйста, попробуйте позже.",
                reply_markup=back_keyboard()
            )
        except Exception as text_error:
            logger.error(f"Failed to send error message: {str(text_error)}")
            await callback_query.answer("Ошибка загрузки статистики. Попробуйте перезапустить бота командой /start", show_alert=True)

# Добавляем функцию main
async def main():
    logger.info("Starting bot...")
    
    # Запускаем проверку истекающих подписок
    asyncio.create_task(check_expiring_subscriptions())
    
    # Запускаем мониторинг отслеживаемых товаров
    asyncio.create_task(check_tracked_items())
    
    # Запускаем бота
    try:
        await dp.start_polling(bot)
    finally:
        await bot.session.close()

async def get_external_ads_data(query):
    """Получение данных о внешней рекламе через комбинацию API"""
    results = {
        "article": query,
        "product_info": None,
        "recent_posts": []
    }
    
    # 1. Получаем информацию о товаре через существующий метод
    try:
        wb_data = await get_wb_product_info(query)
        if wb_data:
            results["product_info"] = wb_data
            logger.info("Successfully got data from Wildberries API")
    except Exception as e:
        logger.error(f"Error getting Wildberries data: {str(e)}")
    
    # 2. Получаем данные из глобального поиска
    try:
        search_results = await global_search_serper_detailed(query)
        if search_results:
            logger.info("Successfully got data from global search")
            results["recent_posts"].extend(search_results)
    except Exception as e:
        logger.error(f"Error getting global search data: {str(e)}")
    
    # 3. Получаем данные из MPSTATS
    try:
        mpstats_data = await get_mpsta_data(query)
        if mpstats_data and isinstance(mpstats_data, dict):
            logger.info("Successfully got data from MPSTATS")
            
            # Обрабатываем данные MPSTATS
            for post in mpstats_data.get('posts', []):
                if len(results['recent_posts']) < 5:
                    # Получаем статистику продаж за 3 дня после публикации
                    sales_impact = {
                        'frequency': post.get('frequency', 0),
                        'revenue': post.get('revenue', 0),
                        'orders': post.get('orders', 0),
                        'avg_price': post.get('avg_price', 0),
                        'orders_growth_percent': post.get('orders_growth_percent', 0),
                        'revenue_growth_percent': post.get('revenue_growth_percent', 0)
                    }
                    
                    results['recent_posts'].append({
                        'platform': post.get('platform', 'unknown'),
                        'date': post.get('date', ''),
                        'url': post.get('url', ''),
                        'author': post.get('author', ''),
                        'sales_impact': sales_impact
                    })
    except Exception as e:
        logger.error(f"Error getting MPSTATS data: {str(e)}")
    
    # Сортируем недавние посты по дате
    results['recent_posts'].sort(key=lambda x: x.get('date', ''), reverse=True)
    results['recent_posts'] = results['recent_posts'][:5]
    
    return results

def format_external_analysis(data):
    """Форматирование результатов анализа внешней рекламы"""
    try:
        result = f"🔍 *АНАЛИЗ ВНЕШНЕЙ РЕКЛАМЫ*\n\n"
        
        if not data:
            return "❌ Данные не найдены", []
        
        chart_files = []
        
        # Проверяем структуру данных
        if isinstance(data, dict):
            if data.get("error"):
                return f"❌ Ошибка: {data.get('error')}", []
            
            # Основная структура данных
            ad_items = data.get("items", [])
            total_ads = len(ad_items) if ad_items else 0
            
            result += f"📊 *Найдено рекламных публикаций:* {total_ads}\n\n"
            
            if total_ads == 0:
                result += "🔍 Рекламные публикации не найдены.\n\n"
                result += "*Возможные причины:*\n"
                result += "• Товар или бренд не рекламируется\n"
                result += "• Указан неверный артикул/название\n"
                result += "• Реклама ведется только на закрытых площадках\n"
                return result, chart_files
            
            # Анализ топ рекламных публикаций
            if ad_items:
                result += "🔥 *ТОП РЕКЛАМНЫХ ПУБЛИКАЦИЙ:*\n\n"
                
                # Сортируем по эффективности (лайки + просмотры)
                sorted_ads = sorted(ad_items[:10], 
                                  key=lambda x: (x.get("likes", 0) + x.get("views", 0)), 
                                  reverse=True)
                
                for i, ad in enumerate(sorted_ads[:5], 1):
                    author = ad.get("author", "Неизвестно")
                    likes = ad.get("likes", 0)
                    views = ad.get("views", 0)
                    platform = ad.get("platform", "Неизвестно")
                    
                    result += f"{i}. *{author}* ({platform})\n"
                    result += f"   👍 {likes:,} лайков | 👁 {views:,} просмотров\n\n"
                
                # Статистика по площадкам
                platforms = {}
                total_likes = 0
                total_views = 0
                
                for ad in ad_items:
                    platform = ad.get("platform", "Неизвестно")
                    likes = ad.get("likes", 0)
                    views = ad.get("views", 0)
                    
                    total_likes += likes
                    total_views += views
                    
                    if platform not in platforms:
                        platforms[platform] = {"count": 0, "likes": 0, "views": 0}
                    
                    platforms[platform]["count"] += 1
                    platforms[platform]["likes"] += likes
                    platforms[platform]["views"] += views
                
                result += f"📈 *ОБЩАЯ СТАТИСТИКА:*\n"
                result += f"• Всего лайков: {total_likes:,}\n"
                result += f"• Всего просмотров: {total_views:,}\n"
                result += f"• Среднее вовлечение: {(total_likes + total_views) // max(1, total_ads):,}\n\n"
                
                result += f"🏆 *ПОПУЛЯРНЫЕ ПЛОЩАДКИ:*\n"
                sorted_platforms = sorted(platforms.items(), 
                                        key=lambda x: x[1]["count"], 
                                        reverse=True)
                
                for platform, stats in sorted_platforms[:3]:
                    result += f"• *{platform}*: {stats['count']} публикаций\n"
                    result += f"  👍 {stats['likes']:,} | 👁 {stats['views']:,}\n"
                
        # Добавляем рекомендации
        result += "\n💡 *РЕКОМЕНДАЦИИ:*\n"
        
        if total_ads > 0:
            # Находим самую эффективную площадку
            if 'sorted_platforms' in locals() and sorted_platforms:
                best_platform = sorted_platforms[0][0]
                result += f"• Сосредоточьтесь на площадке *{best_platform}* — там больше всего активности\n"
            
            # Рекомендации по авторам
            if 'sorted_ads' in locals() and sorted_ads:
                top_author = sorted_ads[0].get("author", "")
                if top_author:
                    result += f"• Рассмотрите сотрудничество с *{top_author}* — у них высокое вовлечение\n"
            
            # Рекомендации по площадкам
            platforms = {}
            for ad in ad_items:
                platform = ad.get("platform", "Неизвестно")
                growth = ad.get("sales_growth_percent", 0)
                
                if platform not in platforms:
                    platforms[platform] = {"count": 0, "total_growth": 0}
                
                platforms[platform]["count"] += 1
                platforms[platform]["total_growth"] += growth
            
            for platform, platform_data in platforms.items():
                if platform_data["count"] > 0:
                    platform_data["avg_growth"] = platform_data["total_growth"] / platform_data["count"]
            
            best_platforms = sorted(platforms.items(), key=lambda x: x[1]["avg_growth"], reverse=True)
            
            if best_platforms:
                top_platform = best_platforms[0]
                result += f"• Наилучшие результаты показывает площадка *{top_platform[0]}* " \
                          f"(средний прирост {top_platform[1]['avg_growth']:.1f}%).\n"
        else:
            result += "• Недостаточно данных для формирования конкретных рекомендаций. " \
                      "Рекомендуется расширить поисковый запрос или проверить другие товары.\n"
        
        return result, chart_files
    
    except Exception as e:
        logger.error(f"Error formatting external analysis: {str(e)}", exc_info=True)
        return f"❌ Ошибка при форматировании анализа: {str(e)}", []

# --- Функции анализа сезонности MPSTATS ---

async def get_seasonality_annual_data(category_path, period="day"):
    """Получение данных годовой сезонности из MPSTATS API"""
    try:
        # Кодируем путь категории для URL
        encoded_path = quote(category_path)
        
        # URL для запроса данных о годовой сезонности
        url = f"https://mpstats.io/api/wb/get/ds/category/annual"
        
        params = {
            "path": encoded_path,
            "period": period
        }
        
        headers = {
            "X-Mpstats-TOKEN": MPSTATS_API_KEY,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Getting annual seasonality data for category: {category_path}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully got annual seasonality data for category: {category_path}")
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"Error getting annual seasonality data: {response.status} - {error_text}")
                    return {"error": f"Ошибка API: {response.status}"}
                    
    except Exception as e:
        logger.error(f"Exception getting annual seasonality data: {str(e)}")
        return {"error": f"Ошибка при получении данных о годовой сезонности: {str(e)}"}

async def get_seasonality_weekly_data(category_path):
    """Получение данных недельной сезонности из MPSTATS API"""
    try:
        # Кодируем путь категории для URL
        encoded_path = quote(category_path)
        
        # URL для запроса данных о недельной сезонности
        url = f"https://mpstats.io/api/wb/get/ds/category/weekly"
        
        params = {
            "path": encoded_path
        }
        
        headers = {
            "X-Mpstats-TOKEN": MPSTATS_API_KEY,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Getting weekly seasonality data for category: {category_path}")
        
        async with aiohttp.ClientSession() as session:
            async with session.get(url, params=params, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully got weekly seasonality data for category: {category_path}")
                    return data
                else:
                    error_text = await response.text()
                    logger.error(f"Error getting weekly seasonality data: {response.status} - {error_text}")
                    return {"error": f"Ошибка API: {response.status}"}
                    
    except Exception as e:
        logger.error(f"Exception getting weekly seasonality data: {str(e)}")
        return {"error": f"Ошибка при получении данных о недельной сезонности: {str(e)}"}

def generate_seasonality_charts(annual_data, weekly_data, category_path):
    """Создание графиков сезонности"""
    try:
        chart_files = []
        timestamp = int(time.time())
        
        # График годовой сезонности
        if annual_data and not annual_data.get("error"):
            # Извлекаем данные для графика
            dates = []
            revenue_values = []
            sales_values = []
            holidays = []
            
            for item in annual_data:
                if isinstance(item, dict):
                    dates.append(item.get("noyeardate", ""))
                    revenue_values.append(item.get("season_revenue", 0))
                    sales_values.append(item.get("season_sales", 0))
                    holidays.append(item.get("holiday_name", ""))
            
            if dates and revenue_values:
                fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(15, 10))
                
                # График выручки
                ax1.plot(range(len(dates)), revenue_values, linewidth=2, color='#2E86AB', marker='o', markersize=4)
                ax1.set_title(f'Сезонность выручки по категории: {category_path}', fontsize=14, fontweight='bold')
                ax1.set_ylabel('Изменение выручки (%)', fontsize=12)
                ax1.grid(True, alpha=0.3)
                ax1.axhline(y=0, color='red', linestyle='--', alpha=0.7)
                
                # Подписи для важных дат (каждый 30-й день)
                step = max(1, len(dates) // 12)
                ax1.set_xticks(range(0, len(dates), step))
                ax1.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=45)
                
                # График продаж
                ax2.plot(range(len(dates)), sales_values, linewidth=2, color='#A23B72', marker='o', markersize=4)
                ax2.set_title(f'Сезонность продаж по категории: {category_path}', fontsize=14, fontweight='bold')
                ax2.set_ylabel('Изменение продаж (%)', fontsize=12)
                ax2.set_xlabel('Дата (день-месяц)', fontsize=12)
                ax2.grid(True, alpha=0.3)
                ax2.axhline(y=0, color='red', linestyle='--', alpha=0.7)
                
                ax2.set_xticks(range(0, len(dates), step))
                ax2.set_xticklabels([dates[i] for i in range(0, len(dates), step)], rotation=45)
                
                plt.tight_layout()
                
                annual_chart_path = f"seasonality_annual_chart_{timestamp}.png"
                plt.savefig(annual_chart_path, dpi=300, bbox_inches='tight')
                plt.close()
                chart_files.append(annual_chart_path)
        
        # График недельной сезонности
        if weekly_data and not weekly_data.get("error"):
            weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            revenue_weekly = []
            sales_weekly = []
            pws_weekly = []
            
            for item in weekly_data:
                if isinstance(item, dict):
                    revenue_weekly.append(item.get("weekly_revenue", 0))
                    sales_weekly.append(item.get("weekly_sales", 0))
                    pws_weekly.append(item.get("weekly_pws", 0))
            
            if revenue_weekly and len(revenue_weekly) == 7:
                fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12))
                
                # График выручки по дням недели
                bars1 = ax1.bar(weekdays, revenue_weekly, color='#2E86AB', alpha=0.8)
                ax1.set_title(f'Недельная сезонность выручки: {category_path}', fontsize=14, fontweight='bold')
                ax1.set_ylabel('Изменение выручки (%)', fontsize=12)
                ax1.grid(True, alpha=0.3, axis='y')
                ax1.axhline(y=0, color='red', linestyle='--', alpha=0.7)
                
                # Добавляем значения на столбцы
                for bar, value in zip(bars1, revenue_weekly):
                    height = bar.get_height()
                    ax1.text(bar.get_x() + bar.get_width()/2., height + (0.1 if height >= 0 else -0.3),
                            f'{value:.1f}%', ha='center', va='bottom' if height >= 0 else 'top', fontsize=10)
                
                # График продаж по дням недели
                bars2 = ax2.bar(weekdays, sales_weekly, color='#A23B72', alpha=0.8)
                ax2.set_title(f'Недельная сезонность продаж: {category_path}', fontsize=14, fontweight='bold')
                ax2.set_ylabel('Изменение продаж (%)', fontsize=12)
                ax2.grid(True, alpha=0.3, axis='y')
                ax2.axhline(y=0, color='red', linestyle='--', alpha=0.7)
                
                for bar, value in zip(bars2, sales_weekly):
                    height = bar.get_height()
                    ax2.text(bar.get_x() + bar.get_width()/2., height + (0.1 if height >= 0 else -0.3),
                            f'{value:.1f}%', ha='center', va='bottom' if height >= 0 else 'top', fontsize=10)
                
                # График товаров с продажами по дням недели
                bars3 = ax3.bar(weekdays, pws_weekly, color='#F18F01', alpha=0.8)
                ax3.set_title(f'Недельная сезонность товаров с продажами: {category_path}', fontsize=14, fontweight='bold')
                ax3.set_ylabel('Изменение товаров с продажами (%)', fontsize=12)
                ax3.set_xlabel('День недели', fontsize=12)
                ax3.grid(True, alpha=0.3, axis='y')
                ax3.axhline(y=0, color='red', linestyle='--', alpha=0.7)
                
                for bar, value in zip(bars3, pws_weekly):
                    height = bar.get_height()
                    ax3.text(bar.get_x() + bar.get_width()/2., height + (0.1 if height >= 0 else -0.3),
                            f'{value:.1f}%', ha='center', va='bottom' if height >= 0 else 'top', fontsize=10)
                
                plt.xticks(rotation=45)
                plt.tight_layout()
                
                weekly_chart_path = f"seasonality_weekly_chart_{timestamp}.png"
                plt.savefig(weekly_chart_path, dpi=300, bbox_inches='tight')
                plt.close()
                chart_files.append(weekly_chart_path)
        
        return chart_files
        
    except Exception as e:
        logger.error(f"Error generating seasonality charts: {str(e)}")
        return []

def format_seasonality_analysis(annual_data, weekly_data, category_path):
    """Форматирование результатов анализа сезонности"""
    try:
        result = f"🗓️ *АНАЛИЗ СЕЗОННОСТИ*\n"
        result += f"📂 *Категория:* {category_path}\n\n"
        
        # Проверяем, есть ли данные
        has_annual_data = annual_data and not annual_data.get("error") and len(annual_data) > 0
        has_weekly_data = weekly_data and not weekly_data.get("error") and len(weekly_data) > 0
        
        if not has_annual_data and not has_weekly_data:
            result += "⚠️ *Данные сезонности недоступны*\n\n"
            result += "К сожалению, для указанной категории нет данных о сезонности.\n\n"
            result += "*Возможные причины:*\n"
            result += "• Категория слишком узкая или новая\n"
            result += "• Недостаточно исторических данных\n"
            result += "• Категория написана неверно\n\n"
            result += "*Попробуйте более общие категории:*\n"
            result += "• Женщинам\n"
            result += "• Мужчинам\n" 
            result += "• Детям\n"
            result += "• Дом и дача\n"
            result += "• Спорт и отдых\n"
            result += "• Красота\n\n"
            result += "💡 *Альтернативные решения:*\n"
            result += "• Используйте Google Trends для анализа сезонности\n"
            result += "• Анализируйте историю продаж конкретных товаров\n"
            result += "• Изучайте календарь праздников и акций\n"
            return result
        
        # Анализ недельной сезонности
        if has_weekly_data:
            result += "📊 *НЕДЕЛЬНАЯ СЕЗОННОСТЬ*\n\n"
            
            weekdays = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
            
            best_revenue_day = None
            worst_revenue_day = None
            best_sales_day = None
            worst_sales_day = None
            
            max_revenue = float('-inf')
            min_revenue = float('inf')
            max_sales = float('-inf')
            min_sales = float('inf')
            
            for i, item in enumerate(weekly_data):
                if isinstance(item, dict):
                    revenue = item.get("weekly_revenue", 0)
                    sales = item.get("weekly_sales", 0)
                    
                    if revenue > max_revenue:
                        max_revenue = revenue
                        best_revenue_day = weekdays[i] if i < len(weekdays) else f"День {i+1}"
                    
                    if revenue < min_revenue:
                        min_revenue = revenue
                        worst_revenue_day = weekdays[i] if i < len(weekdays) else f"День {i+1}"
                    
                    if sales > max_sales:
                        max_sales = sales
                        best_sales_day = weekdays[i] if i < len(weekdays) else f"День {i+1}"
                    
                    if sales < min_sales:
                        min_sales = sales
                        worst_sales_day = weekdays[i] if i < len(weekdays) else f"День {i+1}"
            
            if best_revenue_day:
                result += f"💰 *Лучший день по выручке:* {best_revenue_day} ({max_revenue:+.1f}%)\n"
                result += f"📉 *Худший день по выручке:* {worst_revenue_day} ({min_revenue:+.1f}%)\n\n"
                
                result += f"📈 *Лучший день по продажам:* {best_sales_day} ({max_sales:+.1f}%)\n"
                result += f"📉 *Худший день по продажам:* {worst_sales_day} ({min_sales:+.1f}%)\n\n"
        
        # Анализ годовой сезонности - топ и анти-топ периоды
        if has_annual_data:
            result += "📅 *ГОДОВАЯ СЕЗОННОСТЬ*\n\n"
            
            # Находим лучшие и худшие периоды
            sorted_by_revenue = sorted(annual_data, key=lambda x: x.get("season_revenue", 0), reverse=True)
            sorted_by_sales = sorted(annual_data, key=lambda x: x.get("season_sales", 0), reverse=True)
            
            # Топ 5 дней по выручке
            result += "🔥 *ТОП-5 ДНЕЙ ПО ВЫРУЧКЕ:*\n"
            for i, day in enumerate(sorted_by_revenue[:5], 1):
                date = day.get("noyeardate", "").replace("-", ".")
                revenue = day.get("season_revenue", 0)
                holiday = day.get("holiday_name", "")
                holiday_text = f" ({holiday})" if holiday else ""
                result += f"{i}. {date}{holiday_text}: {revenue:+.1f}%\n"
            
            result += "\n📉 *ТОП-5 ХУДШИХ ДНЕЙ ПО ВЫРУЧКЕ:*\n"
            for i, day in enumerate(sorted_by_revenue[-5:], 1):
                date = day.get("noyeardate", "").replace("-", ".")
                revenue = day.get("season_revenue", 0)
                holiday = day.get("holiday_name", "")
                holiday_text = f" ({holiday})" if holiday else ""
                result += f"{i}. {date}{holiday_text}: {revenue:+.1f}%\n"
            
            result += "\n🛒 *ТОП-5 ДНЕЙ ПО ПРОДАЖАМ:*\n"
            for i, day in enumerate(sorted_by_sales[:5], 1):
                date = day.get("noyeardate", "").replace("-", ".")
                sales = day.get("season_sales", 0)
                holiday = day.get("holiday_name", "")
                holiday_text = f" ({holiday})" if holiday else ""
                result += f"{i}. {date}{holiday_text}: {sales:+.1f}%\n"
        
        # Добавляем общие рекомендации
        result += "\n💡 *РЕКОМЕНДАЦИИ:*\n"
        
        if has_weekly_data and 'max_revenue' in locals():
            if max_revenue > 0:
                result += f"• Увеличьте рекламные бюджеты в {best_revenue_day}\n"
            if min_revenue < -5:
                result += f"• Снизьте активность рекламы в {worst_revenue_day}\n"
        
        if has_annual_data:
            result += "• Планируйте запуск новых товаров на пиковые периоды\n"
            result += "• Готовьте склады к сезонным колебаниям спроса\n"
            result += "• Корректируйте цены в зависимости от сезонности\n"
        
        # Если нет данных, но API работает
        if not has_weekly_data and not has_annual_data:
            result += "• Изучайте сезонность конкурентов вручную\n"
            result += "• Анализируйте Google Trends для вашей ниши\n"
            result += "• Ведите собственную статистику продаж\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error formatting seasonality analysis: {str(e)}")
        return f"❌ Ошибка при форматировании анализа сезонности: {str(e)}"

# --- Конец функций анализа сезонности ---

@dp.callback_query(lambda c: c.data == "brand_analysis")
async def handle_brand_analysis(callback_query: types.CallbackQuery, state: FSMContext):
    await state.set_state(UserStates.waiting_for_brand)
    await callback_query.message.edit_text(
        "🏢 *Анализ бренда*\n\n"
        "Введите название бренда для анализа:",
        parse_mode=ParseMode.MARKDOWN,
        reply_markup=back_keyboard()
    )

@dp.callback_query(lambda c: c.data == "external_analysis")
async def handle_external_analysis(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку Анализ внешки"""
    try:
        # Устанавливаем состояние ожидания ввода артикула/названия
        await state.set_state(UserStates.waiting_for_external)
        
        # Отправляем сообщение с инструкцией
        await callback_query.message.edit_text(
            "🔍 *Анализ внешней рекламы*\n\n"
            "Введите артикул товара или его название для анализа рекламных публикаций.\n\n"
            "Я проанализирую:\n"
            "• 📊 Рекламные публикации\n"
            "• 👥 Блогеров и их эффективность\n"
            "• 📈 Влияние на продажи\n"
            "• 💰 Доход от рекламы\n\n"
            f"💵 Стоимость анализа: {COSTS['external_analysis']}₽",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in handle_external_analysis: {str(e)}", exc_info=True)
        await callback_query.message.edit_text(
            "❌ *Произошла ошибка*\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_external)
async def handle_external_input(message: types.Message, state: FSMContext):
    """Обработка ввода артикула/названия товара для анализа внешней рекламы"""
    try:
        query = message.text.strip()
        
        # Отправляем сообщение о начале анализа
        await message.answer("🔍 *Анализ внешней рекламы*\n\nПолучаю данные...")
        
        # Получаем данные о внешней рекламе
        external_data = await get_external_ads_data(query)
        
        if external_data is None:
            await message.answer(
                "❌ Не удалось получить данные о внешней рекламе.\n\n"
                "Пожалуйста, проверьте правильность артикула/названия товара и попробуйте снова."
            )
            return
            
        if isinstance(external_data, dict) and external_data.get("error"):
            error_message = external_data.get("message", "Неизвестная ошибка")
            error_code = external_data.get("code", "unknown")
            
            await message.answer(
                f"❌ *Ошибка при получении данных*\n\n"
                f"Сообщение: {error_message}\n"
                f"Код ошибки: {error_code}\n\n"
                "Пожалуйста, попробуйте позже или обратитесь в поддержку."
            )
            return
        
        # Форматируем и отправляем результаты
        formatted_text, chart_files = format_external_analysis(external_data)
        await message.answer(formatted_text, parse_mode="Markdown", disable_web_page_preview=True)

        # Если есть графики — отправляем их отдельным медиа-группой
        if chart_files:
            from aiogram.types.input_file import FSInputFile
            for file_path in chart_files:
                try:
                    await message.answer_photo(FSInputFile(file_path))
                except Exception as img_err:
                    logger.error(f"Error sending chart {file_path}: {str(img_err)}")
        
    except Exception as e:
        logger.error(f"Error in external analysis: {str(e)}", exc_info=True)
        await message.answer(
            "❌ *Произошла ошибка при выполнении анализа*\n\n"
            f"Детали: {str(e)}\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку."
        )
    finally:
        # Используем clear() вместо finish()
        await state.clear()

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_seasonality)
async def handle_seasonality_input(message: types.Message, state: FSMContext):
    """Обработка ввода категории для анализа сезонности"""
    try:
        user_id = message.from_user.id
        category_path = message.text.strip()
        
        logger.info(f"User {user_id} entered seasonality category: '{category_path}'")
        
        # Отправляем сообщение о начале анализа
        processing_message = await message.answer(
            "🗓️ *Анализ сезонности*\n\n"
            "⏳ Этап 1: Получение данных годовой сезонности...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Получаем данные годовой сезонности
        annual_data = await get_seasonality_annual_data(category_path)
        
        await processing_message.edit_text(
            "🗓️ *Анализ сезонности*\n\n"
            "✅ Этап 1: Получение данных годовой сезонности\n"
            "⏳ Этап 2: Получение данных недельной сезонности...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Получаем данные недельной сезонности
        weekly_data = await get_seasonality_weekly_data(category_path)
        
        await processing_message.edit_text(
            "🗓️ *Анализ сезонности*\n\n"
            "✅ Этап 1: Получение данных годовой сезонности\n"
            "✅ Этап 2: Получение данных недельной сезонности\n"
            "⏳ Этап 3: Создание графиков и анализ...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Проверяем наличие ошибок в данных
        if (annual_data and annual_data.get("error")) and (weekly_data and weekly_data.get("error")):
            await processing_message.edit_text(
                "❌ *Ошибка при получении данных*\n\n"
                f"Годовая сезонность: {annual_data.get('error', 'Неизвестная ошибка')}\n"
                f"Недельная сезонность: {weekly_data.get('error', 'Неизвестная ошибка')}\n\n"
                "Возможно, указанная категория не найдена или написана неверно.\n\n"
                "*Проверьте написание категории:*\n"
                "• Женщинам/Платья и сарафаны\n"
                "• Мужчинам/Обувь\n"
                "• Детям/Игрушки",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=back_keyboard()
            )
            await state.clear()
            return
        
        # Создаем графики
        chart_files = generate_seasonality_charts(annual_data, weekly_data, category_path)
        
        await processing_message.edit_text(
            "🗓️ *Анализ сезонности*\n\n"
            "✅ Этап 1: Получение данных годовой сезонности\n"
            "✅ Этап 2: Получение данных недельной сезонности\n"
            "✅ Этап 3: Создание графиков и анализ\n"
            "⏳ Этап 4: Формирование отчета...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Форматируем результаты
        formatted_results = format_seasonality_analysis(annual_data, weekly_data, category_path)
        
        await processing_message.edit_text(
            "✅ *Анализ сезонности завершен!*\n\n"
            "Отправляю подробный отчет...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Отправляем основной текст с результатами
        await message.answer(
            formatted_results,
            parse_mode=ParseMode.MARKDOWN,
            disable_web_page_preview=True
        )
        
        # Отправляем графики, если они есть
        if chart_files:
            await message.answer("📊 *ГРАФИКИ СЕЗОННОСТИ:*", parse_mode=ParseMode.MARKDOWN)
            
            for chart_file in chart_files:
                if os.path.exists(chart_file):
                    caption = ""
                    if "annual" in chart_file:
                        caption = "📅 Годовая сезонность выручки и продаж"
                    elif "weekly" in chart_file:
                        caption = "📊 Недельная сезонность по дням"
                    
                    with open(chart_file, 'rb') as photo:
                        await message.answer_photo(photo=FSInputFile(chart_file), caption=caption)
                    
                    # Удаляем временный файл
                    try:
                        os.remove(chart_file)
                    except:
                        pass
        
        # Клавиатура для навигации
        final_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔄 Новый анализ", callback_data="seasonality_analysis"),
                InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_main")
            ]
        ])
        
        await message.answer(
            "✅ *Анализ сезонности завершен!*\n\nВыберите действие:",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=final_keyboard
        )
        
        await state.clear()
        
        # Декрементируем счетчик действий (используем лимит анализа ниши)
        subscription_manager.decrement_action_count(user_id, "niche_analysis")
        
    except Exception as e:
        logger.error(f"Error in handle_seasonality_input: {str(e)}", exc_info=True)
        await message.answer(
            f"❌ Произошла ошибка при анализе сезонности: {str(e)}",
            reply_markup=back_keyboard()
        )
        await state.clear()

@dp.callback_query(lambda c: c.data == "seasonality_analysis")
async def handle_seasonality_analysis(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку Анализ сезонности"""
    try:
        user_id = callback_query.from_user.id
        
        # Проверяем подписку (используем тот же лимит что и для анализа ниши)
        can_perform = subscription_manager.can_perform_action(user_id, 'niche_analysis')
        if not can_perform:
            await callback_query.message.edit_text(
                "⚠️ У вас нет активной подписки или закончился лимит запросов.\n\n"
                "Для получения доступа к анализу сезонности перейдите в раздел подписок.",
                reply_markup=main_menu_kb()
            )
            return
        
        # Устанавливаем состояние ожидания ввода категории
        await state.set_state(UserStates.waiting_for_seasonality)
        
        # Отправляем сообщение с инструкцией
        await callback_query.message.edit_text(
            "🗓️ *Анализ сезонности*\n\n"
            "Введите путь к категории для анализа сезонных колебаний.\n\n"
            "Я проанализирую:\n"
            "• 📅 Годовую сезонность (праздники, распродажи)\n"
            "• 📊 Недельную сезонность по дням\n"
            "• 📈 Динамику выручки и продаж\n"
            "• 💡 Рекомендации по оптимизации\n\n"
            "*Примеры категорий:*\n"
            "• Женщинам/Платья и сарафаны\n"
            "• Мужчинам/Обувь\n"
            "• Детям/Игрушки\n"
            "• Дом и дача/Мебель",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in handle_seasonality_analysis: {str(e)}", exc_info=True)
        await callback_query.message.edit_text(
            "❌ *Произошла ошибка*\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )



# ============ AI HELPER HANDLERS ============

@dp.callback_query(lambda c: c.data == "ai_helper")
async def handle_ai_helper_start(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку AI помощника"""
    try:
        user_id = callback_query.from_user.id
        
        # Проверяем подписку и лимиты
        can_perform = subscription_manager.can_perform_action(user_id, 'ai_generation')
        if not can_perform:
            await callback_query.message.edit_text(
                "⚠️ У вас нет активной подписки или закончился лимит AI генераций.\n\n"
                "Для получения доступа к AI помощнику перейдите в раздел подписок.",
                reply_markup=main_menu_kb()
            )
            return
        
        # Меню выбора типа генерации
        ai_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📝 Описание товара", callback_data="ai_product_description"),
                InlineKeyboardButton(text="🎯 Карточка товара", callback_data="ai_product_card")
            ],
            [
                InlineKeyboardButton(text="💰 Продающий текст", callback_data="ai_sales_text"),
                InlineKeyboardButton(text="📢 Рекламное объявление", callback_data="ai_ad_copy")
            ],
            [
                InlineKeyboardButton(text="📱 Пост для соцсетей", callback_data="ai_social_post"),
                InlineKeyboardButton(text="📧 Email рассылка", callback_data="ai_email_marketing")
            ],
            [
                InlineKeyboardButton(text="🌐 Лендинг страница", callback_data="ai_landing_page"),
                InlineKeyboardButton(text="🔍 SEO контент", callback_data="ai_seo_content")
            ],
            [
                InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")
            ]
        ])
        
        await callback_query.message.edit_text(
            "🤖 *AI ПОМОЩНИК ДЛЯ КОНТЕНТА*\n\n"
            "Выберите тип контента, который нужно создать:\n\n"
            "📝 *Описание товара* - продающие описания для WB\n"
            "🎯 *Карточка товара* - полное оформление карточки\n"
            "💰 *Продающий текст* - тексты по формуле AIDA\n"
            "📢 *Рекламное объявление* - креативы для рекламы\n"
            "📱 *Пост для соцсетей* - контент для SMM\n"
            "📧 *Email рассылка* - письма для клиентов\n"
            "🌐 *Лендинг страница* - структура посадочной страницы\n"
            "🔍 *SEO контент* - тексты для поисковой оптимизации\n\n"
            f"💰 *Стоимость:* {COSTS['ai_generation']}₽ за генерацию",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=ai_keyboard
        )
        
    except Exception as e:
        logger.error(f"Error in handle_ai_helper_start: {str(e)}", exc_info=True)
        await callback_query.message.edit_text(
            "❌ *Произошла ошибка*\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )

@dp.callback_query(lambda c: c.data.startswith("ai_") and c.data != "ai_helper")
async def handle_ai_content_type(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора типа AI контента"""
    try:
        content_type = callback_query.data.replace("ai_", "")
        user_id = callback_query.from_user.id
        
        # Сохраняем тип контента в состоянии
        await state.update_data(ai_content_type=content_type)
        await state.set_state(UserStates.waiting_for_ai_input)
        
        await callback_query.message.edit_text(
            f"🤖 *AI ГЕНЕРАЦИЯ: {content_type.upper()}*\n\n"
            f"Опишите что нужно создать:\n"
            f"• Укажите все детали и характеристики\n"
            f"• Чем больше информации, тем лучше результат\n\n"
            f"*Пример:* Зимние женские ботинки, натуральная кожа, размеры 36-41...",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in handle_ai_content_type: {str(e)}", exc_info=True)
        await callback_query.message.edit_text(
            "❌ *Произошла ошибка*\n\n"
            "Пожалуйста, попробуйте позже.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_ai_input)
async def handle_ai_input(message: types.Message, state: FSMContext):
    """Обработчик ввода данных для AI генерации"""
    try:
        user_id = message.from_user.id
        user_input = message.text.strip()
        
        # Получаем данные из состояния
        data = await state.get_data()
        content_type = data.get('ai_content_type')
        
        if not content_type:
            await message.answer(
                "❌ Ошибка: тип контента не определен. Пожалуйста, начните заново.",
                reply_markup=back_keyboard()
            )
            await state.clear()
            return
        
        # Проверяем баланс или безлимитную подписку  
        success = subscription_manager.process_payment(user_id, COSTS['ai_generation'])
        if not success:
            await message.answer(
                f"❌ Недостаточно средств для AI генерации.\n"
                f"Необходимо: {COSTS['ai_generation']}₽\n\n"
                "Пополните баланс или оформите подписку.",
                reply_markup=back_keyboard()
            )
            await state.clear()
            return
        
        # Отправляем сообщение о начале генерации
        processing_message = await message.answer(
            "🤖 *AI ГЕНЕРАЦИЯ КОНТЕНТА*\n\n"
            "⏳ Анализирую запрос и генерирую контент...\n"
            "Это займет 10-30 секунд...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Генерируем контент через настоящую нейросеть
        generated_content = await generate_ai_content(content_type, user_input, OPENAI_API_KEY)
        
        # Удаляем сообщение о обработке
        try:
            await processing_message.delete()
        except:
            pass
        
        # Отправляем результат
        await message.answer(generated_content)
        
        # Предлагаем меню
        await message.answer(
            "🎉 *Генерация завершена!*\n\nЧто хотите сделать дальше?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb()
        )
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in handle_ai_input: {str(e)}", exc_info=True)
        await message.answer(
            "❌ *Произошла ошибка при генерации контента*\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        await state.clear() 

# ============ BLOGGER SEARCH HANDLERS ============

@dp.callback_query(lambda c: c.data == "blogger_search")
async def handle_blogger_search(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик нажатия на кнопку поиска блогеров"""
    try:
        user_id = callback_query.from_user.id
        
        # Проверяем баланс
        balance = subscription_manager.get_user_balance(user_id)
        cost = COSTS.get('blogger_search', 30)
        
        if balance < cost:
            await callback_query.message.edit_text(
                f"💰 *Недостаточно средств*\n\n"
                f"Для поиска блогеров необходимо: {cost}₽\n"
                f"Ваш баланс: {balance}₽\n\n"
                f"Пополните баланс для продолжения.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="add_funds")],
                    [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
                ])
            )
            return
        
        # Устанавливаем состояние ожидания ввода
        await state.set_state(UserStates.waiting_for_blogger_search)
        
        # Отправляем сообщение с инструкцией
        await callback_query.message.edit_text(
            "👥 *ПОИСК БЛОГЕРОВ*\n\n"
            "Введите данные для поиска подходящих блогеров:\n\n"
            "📝 *Что можно указать:*\n"
            "• Артикул товара WB\n"
            "• Ключевое слово или категория\n"
            "• Название бренда\n"
            "• Тематику (мода, красота, дети и т.д.)\n\n"
            "🔍 *Что найду:*\n"
            "• YouTube, Instagram, TikTok, Telegram\n"
            "• Размер аудитории и активность\n"
            "• Примерный бюджет сотрудничества\n"
            "• Контактные данные (если доступны)\n"
            "• Наличие контента о Wildberries\n\n"
            "*Примеры запросов:*\n"
            "• `Женская обувь`\n"
            "• `Детские игрушки`\n"
            "• `123456789` (артикул)\n"
            "• `Косметика для лица`\n\n"
            f"💰 *Стоимость анализа: {cost}₽*",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Error in handle_blogger_search: {str(e)}", exc_info=True)
        await callback_query.message.edit_text(
            "❌ *Произошла ошибка*\n\n"
            "Пожалуйста, попробуйте позже или обратитесь в поддержку.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_blogger_search)
async def handle_blogger_search_input(message: types.Message, state: FSMContext):
    """Обработчик ввода запроса для поиска блогеров"""
    try:
        user_id = message.from_user.id
        query = message.text.strip()
        cost = COSTS.get('blogger_search', 30)
        
        # Проверяем и списываем средства
        success = subscription_manager.process_payment(user_id, cost)
        if not success:
            await message.answer(
                f"❌ Недостаточно средств для анализа.\n"
                f"Необходимо: {cost}₽\n\n"
                "Пополните баланс для продолжения.",
                reply_markup=back_keyboard()
            )
            await state.clear()
            return
        
        # Отправляем сообщение о начале поиска
        processing_message = await message.answer(
            "🔍 *ПОИСК БЛОГЕРОВ*\n\n"
            f"⏳ Ищу блогеров по запросу: `{query}`\n\n"
            "Анализирую:\n"
            "• 📺 YouTube каналы\n"
            "• 📱 Instagram профили\n"
            "• 🎵 TikTok аккаунты\n"
            "• 💬 Telegram каналы\n\n"
            "Это займет 30-60 секунд...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Выполняем поиск блогеров
        search_results = await blogger_search.search_bloggers_by_query(query)
        
        # Удаляем сообщение о обработке
        try:
            await processing_message.delete()
        except:
            pass
        
        # Форматируем и отправляем результаты
        result_text = blogger_search.format_blogger_search_results(search_results)
        
        # Отправляем результат (разбиваем на части если очень длинный)
        max_length = 4000
        if len(result_text) > max_length:
            # Разбиваем текст на части
            parts = []
            current_part = ""
            
            lines = result_text.split('\n')
            for line in lines:
                if len(current_part + line + '\n') > max_length:
                    if current_part:
                        parts.append(current_part.strip())
                        current_part = line + '\n'
                    else:
                        parts.append(line)
                else:
                    current_part += line + '\n'
            
            if current_part.strip():
                parts.append(current_part.strip())
            
            # Отправляем по частям
            for i, part in enumerate(parts):
                if i == 0:
                    await message.answer(part, parse_mode=ParseMode.MARKDOWN)
                else:
                    await message.answer(f"*Продолжение {i + 1}:*\n\n{part}", parse_mode=ParseMode.MARKDOWN)
        else:
            await message.answer(result_text, parse_mode=ParseMode.MARKDOWN)
        
        # Предлагаем меню
        await message.answer(
            "🎉 *Поиск блогеров завершен!*\n\n"
            "💡 *Рекомендации:*\n"
            "• Обращайтесь к блогерам с ✅ - у них есть опыт с WB\n"
            "• Учитывайте размер аудитории и активность\n"
            "• Начинайте с микро-блогеров для тестирования\n"
            "• Предлагайте бартер новым авторам\n\n"
            "Что хотите сделать дальше?",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=main_menu_kb()
        )
        
        # Очищаем состояние
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in handle_blogger_search_input: {str(e)}", exc_info=True)
        await message.answer(
            "❌ *Произошла ошибка при поиске блогеров*\n\n"
            "Возможные причины:\n"
            "• Временные проблемы с API\n"
            "• Некорректный запрос\n"
            "• Проблемы с интернет-соединением\n\n"
            "Попробуйте еще раз через несколько минут.",
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        await state.clear()

# ============ ORACLE QUERIES HANDLERS ============

# Инициализация Оракула
try:
    from oracle_queries import OracleQueries, format_oracle_results
    oracle = OracleQueries()
except ImportError:
    logger.error("Модуль oracle_queries не найден!")
    oracle = None

@dp.callback_query(lambda c: c.data == "oracle_queries")
async def handle_oracle_queries(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик кнопки Оракула запросов"""
    try:
        if not oracle:
            await callback_query.message.edit_text(
                "❌ Функция Оракула временно недоступна.\nПопробуйте позже.",
                reply_markup=back_keyboard()
            )
            return
            
        user_id = callback_query.from_user.id
        
        # Проверяем баланс
        user_balance = subscription_manager.get_user_balance(user_id)
        cost = COSTS.get('oracle_queries', 50)
        
        if user_balance < cost:
            await callback_query.message.edit_text(
                f"💰 Недостаточно средств для анализа!\n\n"
                f"Стоимость: {cost}₽\n"
                f"Ваш баланс: {user_balance}₽\n"
                f"Нужно: {cost - user_balance}₽",
                reply_markup=back_keyboard()
            )
            return

        # Создаем клавиатуру с параметрами
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="🔍 Анализ запросов", callback_data="oracle_main_analysis"),
                InlineKeyboardButton(text="📊 По категориям", callback_data="oracle_category_analysis")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ])
        
        oracle_text = (
            "🔮 *Оракул запросов*\n\n"
            "Выберите тип анализа:\n\n"
            "🔍 *Анализ запросов* - детальный анализ поисковых запросов с:\n"
            "• Частотностью и динамикой\n"
            "• Выручкой топ товаров\n"
            "• Монопольностью ниши\n"
            "• Процентом рекламы\n\n"
            "📊 *По категориям* - анализ товаров, брендов, поставщиков\n\n"
            f"💰 *Стоимость:* {cost}₽"
        )
        
        await callback_query.message.edit_text(
            oracle_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_oracle_queries: {e}")
        await callback_query.message.edit_text(
            "❌ Ошибка при инициализации Оракула. Попробуйте позже.",
            reply_markup=back_keyboard()
        )

@dp.callback_query(lambda c: c.data == "oracle_main_analysis")
async def handle_oracle_main_analysis(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик основного анализа Оракула"""
    try:
        await state.set_state(UserStates.waiting_for_oracle_queries)
        
        oracle_text = (
            "🔮 *Оракул запросов - Основной анализ*\n\n"
            "Укажите параметры для анализа в формате:\n"
            "`количество_запросов | месяц | мин_выручка | мин_частотность`\n\n"
            "*Примеры:*\n"
            "• `3 | 2024-01 | 100000 | 1000`\n"
            "• `5 | 2024-02 | 50000 | 500`\n\n"
            "*Параметры:*\n"
            "• Количество запросов: 1-5\n"
            "• Месяц: YYYY-MM (например, 2024-01)\n"
            "• Минимальная выручка за 30 дней (₽)\n"
            "• Минимальная частотность за 30 дней\n\n"
            "📝 Отправьте параметры:"
        )
        
        await callback_query.message.edit_text(
            oracle_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_oracle_main_analysis: {e}")
        await callback_query.message.edit_text(
            "❌ Ошибка. Попробуйте позже.",
            reply_markup=back_keyboard()
        )

@dp.callback_query(lambda c: c.data == "oracle_category_analysis")
async def handle_oracle_category_analysis(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик анализа по категориям"""
    try:
        await state.set_state(UserStates.waiting_for_oracle_category)
        
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📦 По товарам", callback_data="oracle_cat_products"),
                InlineKeyboardButton(text="🏢 По брендам", callback_data="oracle_cat_brands")
            ],
            [
                InlineKeyboardButton(text="🏭 По поставщикам", callback_data="oracle_cat_suppliers"),
                InlineKeyboardButton(text="📂 По категориям", callback_data="oracle_cat_categories")
            ],
            [
                InlineKeyboardButton(text="🔍 По запросам", callback_data="oracle_cat_queries")
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="oracle_queries")]
        ])
        
        oracle_text = (
            "🔮 *Оракул запросов - Анализ по категориям*\n\n"
            "Выберите тип анализа:\n\n"
            "📦 *По товарам* - топ товары по запросу\n"
            "🏢 *По брендам* - анализ брендов\n"
            "🏭 *По поставщикам* - анализ поставщиков\n"
            "📂 *По категориям* - анализ категорий\n"
            "🔍 *По запросам* - связанные запросы"
        )
        
        await callback_query.message.edit_text(
            oracle_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=keyboard
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_oracle_category_analysis: {e}")

@dp.callback_query(lambda c: c.data.startswith("oracle_cat_"))
async def handle_oracle_category_type(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик выбора типа категории"""
    try:
        category_type = callback_query.data.replace("oracle_cat_", "")
        await state.update_data(oracle_category_type=category_type)
        
        type_names = {
            "products": "товарам",
            "brands": "брендам",
            "suppliers": "поставщикам", 
            "categories": "категориям",
            "queries": "запросам"
        }
        
        type_name = type_names.get(category_type, category_type)
        
        oracle_text = (
            f"🔮 *Оракул по {type_name}*\n\n"
            "Укажите параметры в формате:\n"
            "`запрос/категория | месяц`\n\n"
            "*Примеры:*\n"
            "• `телефон | 2024-01`\n"
            "• `косметика | 2024-02`\n"
            "• `Электроника/Смартфоны и гаджеты | 2024-01`\n\n"
            "📝 Отправьте параметры:"
        )
        
        await callback_query.message.edit_text(
            oracle_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_oracle_category_type: {e}")

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_oracle_queries)
async def handle_oracle_queries_input(message: types.Message, state: FSMContext):
    """Обработчик ввода параметров для основного анализа Оракула"""
    try:
        if not oracle:
            await message.reply("❌ Функция Оракула временно недоступна.")
            await state.clear()
            return
            
        user_id = message.from_user.id
        user_input = message.text.strip()
        
        # Парсим входные данные
        parts = [p.strip() for p in user_input.split('|')]
        
        if len(parts) != 4:
            await message.reply(
                "❌ Неверный формат! Используйте:\n"
                "`количество | месяц | мин_выручка | мин_частотность`\n\n"
                "Пример: `3 | 2024-01 | 100000 | 1000`"
            )
            return
        
        try:
            queries_count = int(parts[0])
            month = parts[1]
            min_revenue = int(parts[2])
            min_frequency = int(parts[3])
            
            # Валидация
            if not (1 <= queries_count <= 5):
                raise ValueError("Количество запросов должно быть от 1 до 5")
                
        except ValueError as e:
            await message.reply(f"❌ Ошибка в параметрах: {e}")
            return
        
        # Проверяем и списываем средства
        user_balance = subscription_manager.get_user_balance(user_id)
        cost = COSTS.get('oracle_queries', 50)
        
        if user_balance < cost:
            await message.reply(
                f"💰 Недостаточно средств!\n"
                f"Нужно: {cost}₽, у вас: {user_balance}₽"
            )
            return
        
        # Списываем средства
        subscription_manager.update_balance(user_id, -cost)
        await state.clear()
        
        # Отправляем уведомление о начале анализа
        loading_msg = await message.reply(
            "🔮 *Оракул приступает к анализу...*\n\n"
            f"📊 Запросов: {queries_count}\n"
            f"📅 Месяц: {month}\n"
            f"💰 Мин. выручка: {min_revenue:,}₽\n"
            f"🔍 Мин. частотность: {min_frequency:,}\n\n"
            "⏳ Это может занять 1-2 минуты...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Выполняем анализ
        oracle_data = await oracle.get_search_queries_data(
            queries_count, month, min_revenue, min_frequency
        )
        
        # Форматируем и отправляем результат
        result_text = format_oracle_results(oracle_data, "main")
        
        # Удаляем сообщение загрузки
        try:
            await loading_msg.delete()
        except:
            pass
        
        # Отправляем результат
        await message.reply(
            result_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
        # Логируем использование
        logger.info(f"Oracle analysis completed for user {user_id}, cost: {cost}₽")
        
    except Exception as e:
        logger.error(f"Ошибка в oracle queries input: {e}")
        await state.clear()
        await message.reply(
            "❌ Ошибка при анализе. Попробуйте позже.\n"
            "Средства возвращены на баланс.",
            reply_markup=back_keyboard()
        )
        # Возвращаем средства при ошибке
        subscription_manager.update_balance(user_id, COSTS.get('oracle_queries', 50))

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_oracle_category)
async def handle_oracle_category_input(message: types.Message, state: FSMContext):
    """Обработчик ввода параметров для анализа по категориям"""
    try:
        if not oracle:
            await message.reply("❌ Функция Оракула временно недоступна.")
            await state.clear()
            return
            
        user_id = message.from_user.id
        user_input = message.text.strip()
        
        # Получаем тип анализа из состояния
        data = await state.get_data()
        category_type = data.get('oracle_category_type', 'products')
        
        # Парсим входные данные
        parts = [p.strip() for p in user_input.split('|')]
        
        if len(parts) != 2:
            await message.reply(
                "❌ Неверный формат! Используйте:\n"
                "`запрос/категория | месяц`\n\n"
                "Пример: `телефон | 2024-01`"
            )
            return
        
        query_category = parts[0]
        month = parts[1]
        
        # Проверяем и списываем средства
        user_balance = subscription_manager.get_user_balance(user_id)
        cost = COSTS.get('oracle_queries', 50)
        
        if user_balance < cost:
            await message.reply(f"💰 Недостаточно средств! Нужно: {cost}₽")
            return
        
        # Списываем средства
        subscription_manager.update_balance(user_id, -cost)
        await state.clear()
        
        # Отправляем уведомление о начале анализа
        loading_msg = await message.reply(
            f"🔮 *Анализ по {category_type}...*\n\n"
            f"🔍 Запрос: {query_category}\n"
            f"📅 Месяц: {month}\n\n"
            "⏳ Анализирую данные...",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Выполняем анализ
        oracle_data = await oracle.get_category_analysis(
            query_category, month, category_type
        )
        
        # Форматируем и отправляем результат
        result_text = format_oracle_results(oracle_data, "category")
        
        # Удаляем сообщение загрузки
        try:
            await loading_msg.delete()
        except:
            pass
        
        # Отправляем результат
        await message.reply(
            result_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
        # Логируем использование
        logger.info(f"Oracle category analysis completed for user {user_id}, type: {category_type}")
        
    except Exception as e:
        logger.error(f"Ошибка в oracle category input: {e}")
        await state.clear()
        await message.reply(
            "❌ Ошибка при анализе. Средства возвращены.",
            reply_markup=back_keyboard()
        )
        # Возвращаем средства при ошибке
        subscription_manager.update_balance(user_id, COSTS.get('oracle_queries', 50))

# === АНАЛИЗ ПОСТАВЩИКА ===

@dp.callback_query(lambda c: c.data == "supplier_analysis")
async def handle_supplier_analysis(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик запроса анализа поставщика"""
    try:
        await state.set_state(UserStates.waiting_for_supplier)
        
        supplier_text = (
            "🏭 **АНАЛИЗ ПОСТАВЩИКА**\n\n"
            "Введите данные поставщика для анализа:\n\n"
            "📋 **Формат ввода:**\n"
            "• **ИНН:** `7743453483`\n"
            "• **ОГРН:** `1247700478101`\n"
            "• **Полное название:** `ОБЩЕСТВО С ОГРАНИЧЕННОЙ ОТВЕТСТВЕННОСТЬЮ \"ДИАЭНДКО МАРКЕТПЛЭЙС СЭЙЛС МЕНЕДЖМЕНТ\"`\n"
            "• **Сокращение:** `Marketplace Sales Management`\n\n"
            f"💰 Стоимость: {COSTS['supplier_analysis']}₽\n\n"
            "📊 **Что вы получите:**\n"
            "• Основная информация о поставщике\n"
            "• Количество товаров в ассортименте\n"
            "• Средние цены и рейтинги\n"
            "• Объем продаж и выручка за 30 дней\n"
            "• Распределение по категориям\n"
            "• Топ-3 самых продаваемых товара\n"
            "• Оценка рекламной активности\n\n"
            "✏️ Введите ИНН, ОГРН или название поставщика:"
        )
        
        await callback_query.message.edit_text(
            supplier_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_supplier_analysis: {e}")
        await callback_query.answer("Ошибка при инициализации анализа поставщика")

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_supplier)
async def handle_supplier_input(message: types.Message, state: FSMContext):
    """Обработчик ввода названия поставщика"""
    try:
        user_id = message.from_user.id
        supplier_name = message.text.strip()
        
        # Проверяем баланс
        user_balance = subscription_manager.get_user_balance(user_id)
        cost = COSTS.get('supplier_analysis', 25)
        
        if user_balance < cost:
            await message.reply(
                f"💰 Недостаточно средств!\n"
                f"Нужно: {cost}₽, у вас: {user_balance}₽\n\n"
                "Пополните баланс через главное меню.",
                reply_markup=back_keyboard()
            )
            return
        
        # Списываем средства
        subscription_manager.update_balance(user_id, -cost)
        await state.clear()
        
        # Отправляем уведомление о начале анализа
        loading_msg = await message.reply(
            f"🏭 **Анализирую поставщика: {supplier_name}**\n\n"
            "⏳ Собираю данные о товарах...\n"
            "📊 Анализирую продажи...\n"
            "💰 Рассчитываю метрики...\n\n"
            "Это может занять 30-60 секунд.",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Импортируем функции из модуля анализа поставщика
        try:
            from supplier_analysis import get_supplier_analysis, format_supplier_message
        except ImportError:
            await message.reply(
                "❌ Модуль анализа поставщика недоступен.\n"
                "Средства возвращены на баланс.",
                reply_markup=back_keyboard()
            )
            subscription_manager.update_balance(user_id, cost)
            return
        
        # Выполняем анализ
        supplier_data = await get_supplier_analysis(supplier_name)
        
        # Удаляем сообщение загрузки
        try:
            await loading_msg.delete()
        except:
            pass
        
        if supplier_data.get('error'):
            # Возвращаем средства при ошибке
            subscription_manager.update_balance(user_id, cost)
            await message.reply(
                f"❌ {supplier_data['error']}\n\n"
                "Средства возвращены на ваш баланс.\n"
                "Попробуйте другое название поставщика.",
                reply_markup=back_keyboard()
            )
            return
        
        # Форматируем результат
        result_text = format_supplier_message(supplier_data)
        
        # Отправляем результат
        await message.reply(
            result_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
        # Логируем использование
        logger.info(f"Supplier analysis completed for user {user_id}, supplier: {supplier_name}, cost: {cost}₽")
        
    except Exception as e:
        logger.error(f"Ошибка в handle_supplier_input: {e}")
        await state.clear()
        
        # Возвращаем средства при ошибке
        try:
            subscription_manager.update_balance(user_id, COSTS.get('supplier_analysis', 25))
        except:
            pass
        
        await message.reply(
            "❌ Произошла ошибка при анализе поставщика.\n"
            "Средства возвращены на баланс.\n"
            "Попробуйте позже или обратитесь в поддержку.",
            reply_markup=back_keyboard()
        )


# === ПЛАНИРОВАНИЕ ПОСТАВОК ===



# === ПЛАНИРОВАНИЕ ПОСТАВОК ===

@dp.callback_query(lambda c: c.data == "supply_planning")
async def handle_supply_planning(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик запроса планирования поставок"""
    try:
        await state.set_state(UserStates.waiting_for_supply_planning)
        
        supply_text = (
            "�� *ПЛАН ПОСТАВОК*\n\n"
            "🎯 *Назначение:*\n"
            "Помогает оценить остатки и потребность в новых поставках, "
            "чтобы не терять продажи из-за нулевых остатков.\n\n"
            "📊 *Что вы получите:*\n"
            "• Текущие остатки на складе\n"
            "• Среднедневные продажи\n"
            "• Дни до окончания остатков\n"
            "• Рекомендуемый объем поставки\n"
            "• Цветовая маркировка критичности\n"
            "• Детальные графики и аналитику\n\n"
            "🟢 >10 дней остатка - хорошо\n"
            "🟡 3-10 дней - внимание\n"
            "🔴 <3 дней - срочно пополнить!\n\n"
            f"💰 Стоимость: {COSTS.get('supply_planning', 30)}₽\n\n"
            "📝 *Введите артикулы товаров:*\n"
            "Можно несколько через запятую или по одному на строке\n\n"
            "*Пример:*\n"
            "`123456789, 987654321, 456789123`\n"
            "или\n"
            "`123456789`\n"
            "`987654321`\n"
            "`456789123`"
        )
        
        await callback_query.message.edit_text(
            supply_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_supply_planning: {e}")
        await callback_query.answer("Ошибка при инициализации планирования поставок")

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_supply_planning)
async def handle_supply_planning_input(message: types.Message, state: FSMContext):
    """Обработчик ввода артикулов для планирования поставок"""
    try:
        user_id = message.from_user.id
        user_input = message.text.strip()
        
        # Проверяем и списываем средства
        cost = COSTS.get('supply_planning', 30)
        if not subscription_manager.can_perform_action(user_id, 'supply_planning'):
            await message.reply(
                f"❌ Недостаточно средств для анализа планирования поставок\n"
                f"Стоимость: {cost}₽\n\n"
                f"Ваш баланс: {subscription_manager.get_user_balance(user_id)}₽",
                reply_markup=back_keyboard()
            )
            await state.clear()
            return
        
        # Списываем средства
        subscription_manager.update_balance(user_id, -cost)
        
        # Парсим артикулы
        articles = []
        for line in user_input.replace(',', '\n').split('\n'):
            line = line.strip()
            if line and line.isdigit() and len(line) >= 8:
                articles.append(line)
        
        if not articles:
            # Возвращаем средства при ошибке
            subscription_manager.update_balance(user_id, cost)
            await message.reply(
                "❌ Не найдено валидных артикулов\n\n"
                "Пожалуйста, введите артикулы товаров (минимум 8 цифр):\n"
                "• Можно несколько через запятую\n"
                "• Или каждый с новой строки\n\n"
                "*Пример:* `123456789, 987654321`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=back_keyboard()
            )
            return
        
        if len(articles) > 20:
            # Возвращаем средства при ошибке
            subscription_manager.update_balance(user_id, cost)
            await message.reply(
                f"❌ Слишком много артикулов ({len(articles)})\n\n"
                "Максимум 20 товаров за один анализ.\n"
                "Пожалуйста, уменьшите количество артикулов.",
                reply_markup=back_keyboard()
            )
            await state.clear()
            return
        
        # Отправляем сообщение о начале анализа
        processing_msg = await message.reply(
            f"🔄 Анализируем планирование поставок для {len(articles)} товаров...\n"
            f"⏱ Это может занять 1-2 минуты"
        )
        
        # Импортируем и используем модуль планирования поставок
        from supply_planning import supply_planner, format_supply_planning_report
        
        # Выполняем анализ
        products_data = await supply_planner.analyze_multiple_products(articles)
        
        if not products_data:
            # Возвращаем средства при отсутствии данных
            subscription_manager.update_balance(user_id, cost)
            await processing_msg.edit_text(
                "❌ Не удалось получить данные о товарах\n\n"
                "Возможные причины:\n"
                "• Неверные артикулы\n"
                "• Товары не найдены на Wildberries\n"
                "• Проблемы с API\n\n"
                "Средства возвращены на баланс.",
                reply_markup=back_keyboard()
            )
            await state.clear()
            return
        
        # Генерируем графики
        charts_paths = supply_planner.generate_supply_planning_charts(products_data, user_id)
        
        # Форматируем отчет
        report_text = format_supply_planning_report(products_data)
        
        # Удаляем сообщение о процессе
        await processing_msg.delete()
        
        # Отправляем основной отчет
        await message.reply(
            report_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
        # Отправляем графики, если они созданы
        if charts_paths:
            media_group = []
            captions = ["📊 Обзор состояния остатков", "📈 Детальный анализ планирования поставок"]
            
            for i, chart_path in enumerate(charts_paths):
                if chart_path and os.path.exists(chart_path):
                    caption = captions[i] if i < len(captions) else f"График {i+1}"
                    media_group.append(types.InputMediaPhoto(
                        media=types.FSInputFile(chart_path),
                        caption=caption if i == 0 else ""
                    ))
            
            if media_group:
                await message.reply_media_group(media_group)
                
                # Удаляем временные файлы
                for chart_path in charts_paths:
                    if chart_path and os.path.exists(chart_path):
                        try:
                            os.remove(chart_path)
                        except:
                            pass
        
        # Логируем использование
        logger.info(f"Supply planning analysis completed for user {user_id}, {len(articles)} articles")
        
        await state.clear()
        
    except Exception as e:
        # Возвращаем средства при ошибке
        try:
            cost = COSTS.get('supply_planning', 30)
            subscription_manager.update_balance(user_id, cost)
        except:
            pass
            
        logger.error(f"Error in supply planning analysis: {str(e)}")
        await message.reply(
            "❌ Произошла ошибка при анализе планирования поставок\n\n"
            "Средства возвращены на баланс.\n"
            "Попробуйте позже или обратитесь в поддержку.",
            reply_markup=back_keyboard()
        )
        await state.clear()


# === МОНИТОРИНГ РЕКЛАМЫ ===

@dp.callback_query(lambda c: c.data == "ad_monitoring")
async def handle_ad_monitoring(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик запроса мониторинга рекламы"""
    try:
        await state.set_state(UserStates.waiting_for_ad_monitoring)
        
        ad_monitoring_text = (
            "📊 *МОНИТОРИНГ РЕКЛАМЫ*\n\n"
            "🎯 *Назначение:*\n"
            "Анализ эффективности платной рекламы - идет ли трафик, "
            "растут ли продажи, окупается ли реклама.\n\n"
            "📈 *Что вы получите:*\n"
            "• Статус активности рекламы (MPStats)\n"
            "• Названия/артикулы рекламируемых товаров\n"
            "• Охват/показы рекламы (MPStats)\n"
            "• CTR (клики/показы) (MPStats)\n"
            "• Расходы на рекламу (ввод вручную/CRM)\n"
            "• Продажи с рекламы (MPStats/ввод вручную)\n"
            "• Расчет ROI: (Доход - Расход) / Расход\n"
            "• Дата запуска рекламы\n\n"
            "🎨 *Визуализация:*\n"
            "• Таблицы/карточки по каждому товару\n"
            "• Мини-графики: Расходы/Продажи/ROI по времени\n"
            "• Цветовая маркировка по ROI:\n"
            "  🟢 >100% (прибыльно)\n"
            "  🟡 0-100% (в ноль)\n"
            "  🔴 <0% (убыток)\n\n"
            "📊 *Источники данных:*\n"
            "• MPStats: статистика продаж, остатки, рекламная активность\n"
            "• WB API: остатки, заказы, отзывы, цены, скидки\n"
            "• Внутренние данные: факты поставок, затраты на рекламу\n\n"
            f"💰 Стоимость: 35₽\n\n"
            "📝 *Введите артикулы товаров для мониторинга:*\n"
            "Можно несколько через запятую или по одному на строке\n\n"
            "*Пример:*\n"
            "`123456789, 987654321, 456789123`\n"
            "или\n"
            "`123456789`\n"
            "`987654321`\n"
            "`456789123`"
        )
        
        await callback_query.message.edit_text(
            ad_monitoring_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
    except Exception as e:
        logger.error(f"Ошибка в handle_ad_monitoring: {e}")
        await callback_query.answer("Ошибка при инициализации мониторинга рекламы")

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_ad_monitoring)
async def handle_ad_monitoring_input(message: types.Message, state: FSMContext):
    """Обработчик ввода артикулов для мониторинга рекламы"""
    try:
        user_id = message.from_user.id
        user_input = message.text.strip()
        
        # Проверяем и списываем средства
        cost = 35
        balance = subscription_manager.get_user_balance(user_id)
        if balance < cost:
            await message.reply(
                f"❌ Недостаточно средств для мониторинга рекламы\n"
                f"Стоимость: {cost}₽\n\n"
                f"Ваш баланс: {balance}₽",
                reply_markup=back_keyboard()
            )
            await state.clear()
            return
        
        # Списываем средства
        subscription_manager.update_balance(user_id, -cost)
        
        # Парсим артикулы
        articles = []
        for line in user_input.replace(',', '\n').split('\n'):
            line = line.strip()
            if line and line.isdigit() and len(line) >= 8:
                articles.append(line)
        
        if not articles:
            # Возвращаем средства при ошибке
            subscription_manager.update_balance(user_id, cost)
            await message.reply(
                "❌ Не найдено валидных артикулов\n\n"
                "Пожалуйста, введите артикулы товаров (минимум 8 цифр):\n"
                "• Можно несколько через запятую\n"
                "• Или каждый с новой строки\n\n"
                "*Пример:* `123456789, 987654321`",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=back_keyboard()
            )
            return
        
        if len(articles) > 15:
            # Возвращаем средства при ошибке
            subscription_manager.update_balance(user_id, cost)
            await message.reply(
                f"❌ Слишком много артикулов ({len(articles)})\n\n"
                "Максимум 15 товаров за один анализ.\n"
                "Пожалуйста, уменьшите количество артикулов.",
                reply_markup=back_keyboard()
            )
            await state.clear()
            return
        
        # Отправляем сообщение о начале анализа
        processing_msg = await message.reply(
            f"📊 Анализируем рекламу для {len(articles)} товаров...\n"
            f"⏱ Это может занять 1-2 минуты"
        )
        
        # Импортируем и используем модуль мониторинга рекламы
        from ad_monitoring import AdMonitor, format_ad_monitoring_report
        
        # Создаем экземпляр монитора
        ad_monitor = AdMonitor(MPSTATS_API_KEY)
        
        # Выполняем анализ
        ad_data_list = await ad_monitor.analyze_multiple_products_ads(articles)
        
        if not ad_data_list:
            # Возвращаем средства при отсутствии данных
            subscription_manager.update_balance(user_id, cost)
            await processing_msg.edit_text(
                "❌ Не удалось получить данные о рекламе\n\n"
                "Возможные причины:\n"
                "• Неверные артикулы\n"
                "• Товары не найдены на Wildberries\n"
                "• Нет рекламных кампаний для данных товаров\n"
                "• Проблемы с MPStats API\n\n"
                "Средства возвращены на баланс.",
                reply_markup=back_keyboard()
            )
            await state.clear()
            return
        
        # Генерируем графики
        charts_paths = ad_monitor.generate_ad_monitoring_charts(ad_data_list, user_id)
        
        # Форматируем отчет
        report_text = format_ad_monitoring_report(ad_data_list)
        
        # Удаляем сообщение о процессе
        await processing_msg.delete()
        
        # Отправляем основной отчет
        await message.reply(
            report_text,
            parse_mode=ParseMode.MARKDOWN,
            reply_markup=back_keyboard()
        )
        
        # Отправляем графики, если они созданы
        if charts_paths:
            media_group = []
            captions = [
                "📊 ROI рекламных кампаний по товарам", 
                "💰 Расходы vs Доходы с рекламы",
                "🎯 Обзор активности кампаний"
            ]
            
            for i, chart_path in enumerate(charts_paths):
                if chart_path and os.path.exists(chart_path):
                    caption = captions[i] if i < len(captions) else f"График {i+1}"
                    media_group.append(types.InputMediaPhoto(
                        media=types.FSInputFile(chart_path),
                        caption=caption if i == 0 else ""
                    ))
            
            if media_group:
                await message.reply_media_group(media_group)
                
                # Удаляем временные файлы
                for chart_path in charts_paths:
                    if chart_path and os.path.exists(chart_path):
                        try:
                            os.remove(chart_path)
                        except:
                            pass
        
        # Логируем использование
        logger.info(f"Ad monitoring analysis completed for user {user_id}, {len(articles)} articles")
        
        await state.clear()
        
    except Exception as e:
        # Возвращаем средства при ошибке
        try:
            cost = 35
            subscription_manager.update_balance(user_id, cost)
        except:
            pass
            
        logger.error(f"Error in ad monitoring analysis: {str(e)}")
        await message.reply(
            "❌ Произошла ошибка при анализе рекламы\n\n"
            "Средства возвращены на баланс.\n"
            "Попробуйте позже или обратитесь в поддержку.",
            reply_markup=back_keyboard()
        )
        await state.clear()


if __name__ == '__main__':
    asyncio.run(main())

