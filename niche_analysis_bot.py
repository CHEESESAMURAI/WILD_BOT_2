import asyncio
from typing import Dict, List
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.enums import ChatAction

from niche_analysis import NicheAnalyzer, RealTimeMonitor
from niche_db import NicheDatabase
from niche_visualization import NicheVisualizer
from category_analyzer import CategoryAnalyzer

# Initialize components
niche_analyzer = NicheAnalyzer()
niche_db = NicheDatabase()
niche_visualizer = NicheVisualizer()

# Bot token
BOT_TOKEN = "6458024697:AAHAPSC6KvZaaAgtmkCy08Id0Pq3o87IG-A"
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# State tracking
pending_action = {}  # Dictionary to store user actions
pending_niche_analysis = set()
pending_niche_report = set()
pending_niche_dashboard = set()

def get_niche_menu_kb():
    """Get keyboard for niche analysis menu"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Анализ категории", callback_data="niche_analyze")],
        [InlineKeyboardButton(text="📊 Отчет по категории", callback_data="niche_report")],
        [InlineKeyboardButton(text="📈 Интерактивная панель", callback_data="niche_dashboard")],
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

@dp.message(Command("niche"))
async def niche_command(message: types.Message):
    """Handle /niche command"""
    await message.answer(
        "🔍 *Анализ ниш и конкурентов*\n\n"
        "Выберите действие:",
        reply_markup=get_niche_menu_kb()
    )

@dp.callback_query(lambda c: c.data == "niche_analyze")
async def niche_analyze_handler(callback: types.CallbackQuery):
    """Handle niche analysis request"""
    user_id = callback.from_user.id
    pending_action[user_id] = {"action": "analysis_category"}
    await callback.message.edit_text(
        "Введите URL категории Wildberries для анализа:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="niche_back")]
        ])
    )

def escape_markdown(text: str) -> str:
    """Escape markdown special characters"""
    escape_chars = '_*[]()~`>#+-=|{}.!'
    return "".join(f"\\{c}" if c in escape_chars else c for c in str(text))

def back_kb():
    """Get back button keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back")]
    ])

def main_menu_kb():
    """Get main menu keyboard"""
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔍 Анализ категории", callback_data="niche_analyze")],
        [InlineKeyboardButton(text="📊 Отчет по категории", callback_data="niche_report")],
        [InlineKeyboardButton(text="🔙 В главное меню", callback_data="back")]
    ])

async def analyze_wb_category(category_url: str) -> str:
    """Analyze Wildberries category and return formatted report"""
    analyzer = CategoryAnalyzer()
    try:
        results = await analyzer.analyze_category(category_url)
        
        if results.get("status") == "error":
            return f"❌ Ошибка при анализе категории: {results.get('error', 'Неизвестная ошибка')}"
        
        stats = results["statistics"]
        trends = results["trends"]
        opportunities = results["opportunities"]
        
        # Format the analysis results
        report = [
            f"📊 *Анализ категории: {escape_markdown(results['category_name'])}*\n",
            f"📦 Всего товаров: {results['total_products']}\n",
            "\n💰 *Ценовая статистика:*",
            f"• Минимальная цена: {stats['price_stats']['min']} ₽",
            f"• Максимальная цена: {stats['price_stats']['max']} ₽",
            f"• Средняя цена: {int(stats['price_stats']['mean'])} ₽",
            f"• Медианная цена: {int(stats['price_stats']['median'])} ₽\n",
            "\n📈 *Продажи:*",
            f"• Всего продаж: {stats['sales_stats']['total']}",
            f"• Средние продажи в день: {int(stats['sales_stats']['avg_daily'])}\n",
            "\n⭐ *Рейтинги:*",
            f"• Средний рейтинг: {stats['rating_stats']['avg_rating']:.1f}",
            f"• Среднее количество отзывов: {int(stats['rating_stats']['avg_reviews'])}\n",
            "\n📊 *Тренды:*",
            f"• Тренд цен: {_translate_trend(trends['price_trend'])}",
            f"• Тренд продаж: {_translate_trend(trends['sales_trend'])}",
            f"• Уровень конкуренции: {_translate_competition(trends['competition_level'])}\n",
            "\n💡 *Возможности:*"
        ]
        
        if opportunities:
            for opp in opportunities:
                confidence_percent = int(opp['confidence'] * 100)
                report.append(f"• {escape_markdown(opp['description'])} (уверенность: {confidence_percent}%)")
        else:
            report.append("• Явных возможностей не обнаружено")
        
        return "\n".join(report)
    finally:
        analyzer.close()

def _translate_trend(trend: str) -> str:
    """Translate trend to Russian"""
    translations = {
        "rising": "↗️ Растущий",
        "falling": "↘️ Падающий",
        "neutral": "➡️ Стабильный"
    }
    return translations.get(trend, "❓ Неизвестно")

def _translate_competition(level: str) -> str:
    """Translate competition level to Russian"""
    translations = {
        "high": "🔴 Высокий",
        "medium": "🟡 Средний",
        "low": "🟢 Низкий"
    }
    return translations.get(level, "❓ Неизвестно")

@dp.message()
async def text_handler(message: types.Message):
    user_id = message.from_user.id
    if user_id in pending_action:
        action = pending_action[user_id]["action"]

        if action == "analysis_category":
            category_url = message.text.strip()
            if not category_url.startswith("https://www.wildberries.ru/catalog/"):
                await message.answer(
                    "❌ Пожалуйста, введите корректную ссылку на категорию Wildberries\n"
                    "Пример: https://www.wildberries.ru/catalog/muzhchinam/odezhda/tolstovki",
                    reply_markup=back_kb()
                )
                return

            await message.answer("⏳ Анализируем категорию, это может занять некоторое время...")
            try:
                analysis_result = await analyze_wb_category(category_url)
                await message.answer(analysis_result, reply_markup=main_menu_kb())
            except Exception as e:
                await message.answer(
                    f"❌ Произошла ошибка при анализе категории: {str(e)}",
                    reply_markup=main_menu_kb()
                )
            finally:
                pending_action.pop(user_id, None)
            return

        # ... rest of the existing message handler code ...

@dp.callback_query(lambda c: c.data == "niche_report")
async def niche_report_handler(callback: types.CallbackQuery):
    """Handle niche report request"""
    await callback.message.edit_text(
        "Введите URL категории для получения отчета:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="niche_back")]
        ])
    )
    pending_niche_report.add(callback.message.chat.id)

@dp.callback_query(lambda c: c.data == "niche_dashboard")
async def niche_dashboard_handler(callback: types.CallbackQuery):
    """Handle interactive dashboard request"""
    await callback.message.edit_text(
        "Введите URL категории для отображения интерактивной панели:",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="niche_back")]
        ])
    )
    pending_niche_dashboard.add(callback.message.chat.id)

@dp.callback_query(lambda c: c.data == "niche_back")
async def niche_back_handler(callback: types.CallbackQuery):
    """Handle back button in niche menu"""
    await callback.message.edit_text(
        "🔍 *Анализ ниш и конкурентов*\n\n"
        "Выберите действие:",
        reply_markup=get_niche_menu_kb()
    )

async def main():
    """Main function to run the bot"""
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main()) 