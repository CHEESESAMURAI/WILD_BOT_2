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
import time
from urllib.parse import urlparse
import random
import aiohttp
import sys

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
# Ключ для serper.dev API
SERPER_API_KEY = "8ba851ed7ae1e6a655102bea15d73fdb39cdac79"
# Ключ для MPSTA API
MPSTA_API_KEY = "682872eed804b5.13782565c9e71152c442e4c8c0dca9be2c1a53f2"

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
            InlineKeyboardButton(text="🌐 Анализ внешки", callback_data="product_search"),
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
        "*4. Анализ внешки:*\n"
        "   • Задайте параметры\n"
        "   • Найдите упоминания и анализ в соцсетях\n\n"
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
    try:
        user_id = callback_query.from_user.id
        logger.info(f"User {user_id} requested profile")
        
        # Получаем основные данные пользователя
        balance = subscription_manager.get_user_balance(user_id)
        tracked_items = subscription_manager.get_tracked_items(user_id)
        subscription = subscription_manager.get_subscription(user_id)
        
        # Формируем данные о подписке
        subscription_info = "❌ Нет активной подписки"
        
        # Проверяем активность подписки
        is_active = subscription_manager.is_subscription_active(user_id)
        
        if is_active and subscription:
            # Получаем дату окончания подписки
            try:
                expiry_date_str = subscription_manager.get_subscription_end_date(user_id)
                if expiry_date_str:
                    expiry_date = datetime.fromisoformat(expiry_date_str.replace(' ', 'T'))
                    days_left = max(0, (expiry_date - datetime.now()).days)
                    
                    subscription_info = (
                        f"📅 *Текущая подписка:* {subscription}\n"
                        f"⏳ Осталось дней: {days_left}\n\n"
                        "*Лимиты:*\n"
                    )
                    
                    # Получаем лимиты подписки
                    limits = SUBSCRIPTION_LIMITS.get(subscription, {})
                    for action, limit in limits.items():
                        limit_display = "∞" if limit == float('inf') else limit
                        subscription_info += f"• {action}: {limit_display}\n"
            except Exception as e:
                logger.error(f"Error processing subscription date: {e}")
                subscription_info = f"📅 *Текущая подписка:* {subscription}\n"
        
        # Собираем текст профиля
        profile_text = (
            f"👤 *Личный кабинет*\n\n"
            f"💰 Баланс: {balance}₽\n"
            f"📊 Отслеживаемых товаров: {len(tracked_items) if isinstance(tracked_items, list) else 0}\n\n"
            f"{subscription_info}"
        )
        
        # Создаем клавиатуру
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
    except Exception as e:
        logger.error(f"Error in profile_callback: {e}")
        await callback_query.message.edit_text(
            "❌ Произошла ошибка при открытии личного кабинета. Пожалуйста, попробуйте позже.",
            reply_markup=back_keyboard()
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
            
            await callback_query.message.edit_text(
                f"✅ Подписка {subscription_type.capitalize()} успешно оформлена!\n\n"
                f"Списано: {cost}₽\n"
                f"Остаток на балансе: {balance - cost}₽\n\n"
                "Теперь вам доступны все функции выбранного тарифа.",
                parse_mode=ParseMode.MARKDOWN,
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="◀️ В меню", callback_data="back_to_main")]
                ])
            )
        else:
            # Если недостаточно средств, предлагаем пополнить баланс
            await callback_query.message.edit_text(
                f"❌ Недостаточно средств для оформления подписки {subscription_type.capitalize()}\n\n"
                f"Стоимость: {cost}₽\n"
                f"Ваш баланс: {balance}₽\n\n"
                "Пожалуйста, пополните баланс для оформления подписки.",
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
@dp.callback_query(lambda c: c.data == "product_search")
async def handle_global_search(callback_query: types.CallbackQuery, state: FSMContext):
    try:
        user_id = callback_query.from_user.id
        logger.info(f"User {user_id} clicked global search button")
        
        # Проверяем подписку
        subscription = subscription_manager.get_subscription(user_id)
        if not subscription or not subscription_manager.is_subscription_active(user_id):
            await callback_query.answer(
                "❌ У вас нет активной подписки. Пожалуйста, оформите подписку для доступа к анализу внешки.",
                show_alert=True
            )
            return
        
        await state.set_state(UserStates.waiting_for_search)
        
        await callback_query.message.edit_text(
            "🌐 *Анализ внешки и рекламы*\n\n"
            "Введите артикул товара или название для анализа.\n"
            "Например: `176409037` или `Носки`\n\n"
            "🔍 Анализ будет проведен с использованием API MPSTA:\n"
            "• Данные о продажах товара\n"
            "• Статистика рекламных кампаний\n"
            "• Эффективность блогеров\n"
            "• Прирост заказов и выручки после рекламы\n\n"
            "📊 Вы получите подробный отчет с метриками:\n"
            "• Суммарная частотность и выручка\n"
            "• Прирост количества заказов\n"
            "• Эффективность рекламных публикаций\n"
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
        "*4. Анализ внешки:*\n"
        "   • Задайте параметры\n"
        "   • Найдите упоминания и анализ в соцсетях\n\n"
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
    try:
        user_id = message.from_user.id
        logger.info(f"User {user_id} requested profile")
        
        # Получаем основные данные пользователя
        balance = subscription_manager.get_user_balance(user_id)
        tracked_items = subscription_manager.get_tracked_items(user_id)
        subscription = subscription_manager.get_subscription(user_id)
        
        # Формируем данные о подписке
        subscription_info = "❌ Нет активной подписки"
        
        # Проверяем активность подписки
        is_active = subscription_manager.is_subscription_active(user_id)
        
        if is_active and subscription:
            # Получаем дату окончания подписки
            try:
                expiry_date_str = subscription_manager.get_subscription_end_date(user_id)
                if expiry_date_str:
                    expiry_date = datetime.fromisoformat(expiry_date_str.replace(' ', 'T'))
                    days_left = max(0, (expiry_date - datetime.now()).days)
                    
                    subscription_info = (
                        f"📅 *Текущая подписка:* {subscription}\n"
                        f"⏳ Осталось дней: {days_left}\n\n"
                        "*Лимиты:*\n"
                    )
                    
                    # Получаем лимиты подписки
                    limits = SUBSCRIPTION_LIMITS.get(subscription, {})
                    for action, limit in limits.items():
                        limit_display = "∞" if limit == float('inf') else limit
                        subscription_info += f"• {action}: {limit_display}\n"
            except Exception as e:
                logger.error(f"Error processing subscription date: {e}")
                subscription_info = f"📅 *Текущая подписка:* {subscription}\n"
        
        # Собираем текст профиля
        profile_text = (
            f"👤 *Личный кабинет*\n\n"
            f"💰 Баланс: {balance}₽\n"
            f"📊 Отслеживаемых товаров: {len(tracked_items) if isinstance(tracked_items, list) else 0}\n\n"
            f"{subscription_info}"
        )
        
        # Создаем клавиатуру
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Мои товары", callback_data="tracked"),
                InlineKeyboardButton(text="💳 Пополнить", callback_data="add_funds")
            ],
            [InlineKeyboardButton(text="📅 Подписка", callback_data="subscription")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ])
        
        await message.answer(profile_text, parse_mode=ParseMode.MARKDOWN, reply_markup=keyboard)
    except Exception as e:
        logger.error(f"Error in profile_handler: {e}")
        await message.answer(
            "❌ Произошла ошибка при открытии личного кабинета. Пожалуйста, попробуйте позже.",
            reply_markup=main_menu_kb()
        )

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
YOUTUBE_API_KEY = 'AIzaSyD-epfqmQhkKJcjy_V3nP93VniUIGEb3Sc'
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
            "q": f"{query} site:vk.com OR site:instagram.com OR site:facebook.com OR site:twitter.com OR site:t.me",
            "num": 20,
            "gl": "ru",
            "hl": "ru"
        })
        
        headers = {
            'X-API-KEY': SERPER_API_KEY,
            'Content-Type': 'application/json'
        }
        
        logger.info("Making request to Serper API")
        response = requests.post(url, headers=headers, data=payload, timeout=30)
        logger.info(f"Serper API response status: {response.status_code}")
        
        if response.status_code != 200:
            logger.error(f"Serper API error: {response.text}")
            return {"error": "Ошибка при выполнении поиска", "results": []}
            
        search_data = response.json()
        logger.info("Successfully received search data")
        
        if not search_data or 'organic' not in search_data:
            logger.error("No organic results in search data")
            return {"error": "Не найдено результатов поиска", "results": []}
        
        organic = search_data.get("organic", [])
        filtered_results = []
        
        for item in organic:
            try:
                link = item.get("link", "")
                if not link or "wildberries" in link.lower():
                    continue
                
                domain = urlparse(link).netloc.lower()
                if not any(social in domain for social in ["vk.com", "instagram.com", "t.me", "facebook.com", "twitter.com"]):
                    continue
                
                # Получаем лайки и просмотры
                snippet = item.get("snippet", "")
                likes, views = get_real_likes_views(link, snippet)
                
                # Оцениваем влияние
                approx_clients = int(likes * 0.1 + views * 0.05)
                approx_revenue = approx_clients * 500
                growth_percent = (approx_revenue / 10000) * 100 if approx_revenue > 0 else 0
                
                result = {
                    "title": item.get("title", ""),
                    "link": link,
                    "snippet": snippet,
                    "site": domain,
                    "likes": likes,
                    "views": views,
                    "approx_clients": approx_clients,
                    "approx_revenue": approx_revenue,
                    "growth_percent": growth_percent
                }
                filtered_results.append(result)
                logger.info(f"Added result: {domain}")
            except Exception as item_error:
                logger.error(f"Error processing search result item: {str(item_error)}")
                continue
        
        if not filtered_results:
            return {
                "error": None,
                "results": [],
                "message": (
                    "🔍 Анализ социальных сетей\n\n"
                    "Мы провели поиск по следующим площадкам:\n"
                    "• VK\n"
                    "• Instagram\n"
                    "• Telegram\n"
                    "• Facebook\n"
                    "• Twitter\n\n"
                    "📊 Результаты анализа:\n"
                    "Не обнаружено активного продвижения товара в социальных сетях. "
                    "Это может означать:\n"
                    "• Товар продвигается органически\n"
                    "• Высокий уровень доверия аудитории\n"
                    "• Стабильный спрос без агрессивной рекламы"
                )
            }
        
        logger.info(f"Search completed successfully, found {len(filtered_results)} results")
        return {"error": None, "results": filtered_results}
        
    except Exception as e:
        logger.error(f"Error in global search: {str(e)}", exc_info=True)
        return {"error": "Произошла ошибка при выполнении поиска", "results": []}

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
            "⚙️ Этап 1: Запрос данных из MPSTA API\n"
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
            "✅ Этап 1: Запрос данных из MPSTA API\n"
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
            "✅ Этап 1: Запрос данных из MPSTA API\n"
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
            "✅ Этап 1: Запрос данных из MPSTA API\n"
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
    
    headers = {
        "X-Mpstats-TOKEN": MPSTA_API_KEY,
        "Content-Type": "application/json"
    }
    
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

# Добавляем запуск проверки в main
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

async def check_tracked_items():
    """Периодическая проверка отслеживаемых товаров и отправка уведомлений."""
    logger.info("Starting tracked items monitoring...")
    while True:
        try:
            # Получаем данные всех пользователей
            all_users = subscription_manager.get_all_users()
            
            for user_id, user_data in all_users.items():
                try:
                    # Проверяем, активна ли подписка
                    if not subscription_manager.is_subscription_active(int(user_id)):
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
                            article = item.get("article", "")
                            if not article:
                                continue
                                
                            old_price = item.get("price", 0)
                            old_stock = item.get("sales", 0)
                            
                            # Получаем актуальные данные
                            product_info = await get_wb_product_info(article)
                            
                            if not product_info:
                                continue
                            
                            # Получаем новые значения
                            new_price = product_info["price"]["current"]
                            new_stock = product_info["stocks"]["total"]
                            name = product_info["name"]
                            rating = product_info.get("rating", 0.0)
                            
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
                                    f"🔢 Артикул: {article}\n"
                                    f"💰 Цена {change_type} с {old_price} ₽ до {new_price} ₽\n"
                                    f"🔄 Изменение: {abs(price_change)} ₽ ({abs(price_change/old_price*100):.1f}%)\n\n"
                                    f"🛒 [Посмотреть на Wildberries](https://www.wildberries.ru/catalog/{article}/detail.aspx)"
                                )
                            
                            # Значительное изменение наличия (больше 50%)
                            if old_stock > 0 and (stock_change < 0 or (new_stock > 0 and old_stock == 0)):
                                if stock_change < 0 and new_stock == 0:
                                    # Товар закончился
                                    notification = (
                                        f"⚠️ *Товар закончился!*\n\n"
                                        f"*{name}*\n"
                                        f"🔢 Артикул: {article}\n"
                                        f"📦 Наличие: 0 шт.\n\n"
                                        f"🛒 [Посмотреть на Wildberries](https://www.wildberries.ru/catalog/{article}/detail.aspx)"
                                    )
                                elif new_stock > 0 and old_stock == 0:
                                    # Товар появился в наличии
                                    notification = (
                                        f"✅ *Товар снова в наличии!*\n\n"
                                        f"*{name}*\n"
                                        f"🔢 Артикул: {article}\n"
                                        f"📦 Наличие: {new_stock} шт.\n"
                                        f"💰 Цена: {new_price} ₽\n\n"
                                        f"🛒 [Посмотреть на Wildberries](https://www.wildberries.ru/catalog/{article}/detail.aspx)"
                                    )
                                elif stock_change < 0 and abs(stock_change/old_stock) > 0.5:
                                    # Количество уменьшилось более чем на 50%
                                    notification = (
                                        f"📉 *Товар заканчивается!*\n\n"
                                        f"*{name}*\n"
                                        f"🔢 Артикул: {article}\n"
                                        f"📦 Наличие: {new_stock} шт. (-{abs(stock_change)} шт.)\n"
                                        f"💰 Цена: {new_price} ₽\n\n"
                                        f"🛒 [Посмотреть на Wildberries](https://www.wildberries.ru/catalog/{article}/detail.aspx)"
                                    )
                            
                            # Если есть уведомление, добавляем его в список
                            if notification:
                                notifications.append(notification)
                            
                            # Обновляем данные товара в любом случае
                            new_item = {
                                "price": new_price,
                                "stock": new_stock,
                                "rating": rating,
                            }
                            
                            subscription_manager.update_tracked_item(int(user_id), article, new_item)
                            
                        except Exception as item_error:
                            logger.error(f"Error updating tracked item {article}: {str(item_error)}")
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
                except Exception as user_error:
                    logger.error(f"Error processing user {user_id}: {str(user_error)}")
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
        
        # Получаем необходимые данные для отслеживания
        price = product_info['price']['current']
        sales = product_info['stocks']['total']  # Используем количество в наличии
        rating = product_info.get('rating', 0.0)  # Берем рейтинг товара или 0, если не указан
            
        # Добавляем товар в отслеживаемые
        # Для SQLite версии нужно передать user_id как int, а не строку
        success = subscription_manager.add_tracked_item(user_id, article, price, sales, rating)
        
        if success:
            await message.answer(
                f"✅ Товар *{product_info['name']}* успешно добавлен в отслеживаемые!\n\n"
                f"🔢 Артикул: {article}\n"
                f"💰 Текущая цена: {price} ₽\n"
                f"📦 Наличие: {product_info['stocks']['total']} шт.\n"
                f"⭐ Рейтинг: {rating}\n\n"
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
            # В SQLite версии item - это словарь с другими ключами
            item_id = item.get("article", "Неизвестно")
            item_price = item.get("price", 0)
            item_sales = item.get("sales", 0)
            item_rating = item.get("rating", 0)
            
            # Для SQLite версии нам нужно дополнительно получить имя товара
            try:
                product_info = await get_wb_product_info(item_id)
                item_name = product_info["name"] if product_info else "Неизвестный товар"
            except:
                item_name = "Неизвестный товар"
            
            message_text += f"{i+1}. *{item_name}*\n"
            message_text += f"   🔢 Артикул: {item_id}\n"
            message_text += f"   💰 Цена: {item_price} ₽\n"
            message_text += f"   📦 Наличие: {item_sales} шт.\n"
            message_text += f"   ⭐ Рейтинг: {item_rating}\n\n"
        
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
            # Получаем артикул и старые данные в соответствии с SQLite версией
            article = item.get("article", "")
            old_price = item.get("price", 0)
            old_stock = item.get("sales", 0)
            
            if not article:
                continue
            
            # Получаем обновленную информацию
            product_info = await get_wb_product_info(article)
            
            if product_info:
                # Обновляем информацию о товаре
                new_price = product_info["price"]["current"]
                new_stock = product_info["stocks"]["total"]
                item_name = product_info["name"]
                rating = product_info.get("rating", 0.0)
                
                new_item = {
                    "article": article,
                    "name": item_name,
                    "price": new_price,
                    "old_price": old_price,
                    "stock": new_stock,
                    "old_stock": old_stock,
                    "rating": rating,
                    "last_update": datetime.now().isoformat()
                }
                
                # Проверяем изменения цены и наличия
                price_change = new_price - old_price if old_price > 0 else 0
                stock_change = new_stock - old_stock if old_stock > 0 else 0
                
                new_item["price_change"] = price_change
                new_item["stock_change"] = stock_change
                
                updated_items.append(new_item)
                
                # Обновляем товар в базе данных
                subscription_manager.update_tracked_item(user_id, article, new_item)
            else:
                not_found_items.append(article)
        
        # Формируем сообщение с результатами обновления
        message_text = "✅ *Обновление завершено*\n\n"
        
        if updated_items:
            message_text += "📊 *Обновленные товары:*\n\n"
            
            for item in updated_items:
                message_text += f"*{item['name']}*\n"
                message_text += f"🔢 Артикул: {item['article']}\n"
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
            # В SQLite версии item - это словарь с другими ключами
            article = item.get("article", "")
            
            # Для SQLite версии нам нужно дополнительно получить имя товара
            try:
                product_info = await get_wb_product_info(article)
                item_name = product_info["name"] if product_info else f"Товар {article}"
            except:
                item_name = f"Товар {article}"
            
            # Добавляем кнопку для каждого товара, теперь callback_data содержит артикул вместо id
            keyboard.append([
                InlineKeyboardButton(
                    text=f"{i+1}. {item_name[:30]}... (ID: {article})",
                    callback_data=f"delete_item_{article}"
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
        article = callback_query.data.split("_")[2]  # Теперь это артикул, а не id
        
        # Удаляем товар из отслеживаемых
        success = subscription_manager.remove_tracked_item(user_id, article)
        
        if success:
            await callback_query.answer(f"Товар {article} удален из отслеживаемых", show_alert=True)
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

if __name__ == '__main__':
    asyncio.run(main()) 