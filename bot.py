import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from main import ProductCardAnalyzer, TrendAnalyzer

# Инициализация анализаторов
product_analyzer = ProductCardAnalyzer()
trend_analyzer = TrendAnalyzer()

# Токен вашего бота
BOT_TOKEN = "7774315895:AAFVVUfSBOw3t7WjGTM6KHFK160TveSGheA"

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start"""
    welcome_message = (
        "👋 Добро пожаловать в WHITESAMURAI!\n\n"
        "Я помогу вам анализировать товары на Wildberries.\n"
        "Просто отправьте мне артикул товара, и я проведу полный анализ.\n\n"
        "Доступные команды:\n"
        "/start - Показать это сообщение\n"
        "/help - Получить справку"
    )
    await update.message.reply_text(welcome_message)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /help"""
    help_text = (
        "🔍 Как пользоваться ботом:\n\n"
        "1. Отправьте артикул товара (только цифры)\n"
        "2. Бот проведет анализ и предоставит:\n"
        "   - Основную информацию о товаре\n"
        "   - Метрики продаж и прибыли\n"
        "   - Анализ трендов и сезонности\n"
        "   - Прогноз и рекомендации\n\n"
        "При возникновении вопросов обращайтесь к администратору."
    )
    await update.message.reply_text(help_text)

async def format_product_analysis(analysis):
    """Форматирует результаты анализа в читаемый вид"""
    if "error" in analysis:
        return f"❌ Ошибка при анализе: {analysis['error']}"
    
    product_info = analysis["product_info"]
    metrics = analysis["metrics"]
    risk_analysis = analysis["risk_analysis"]
    
    # Форматируем основную информацию
    result = (
        f"📊 *Анализ товара*\n\n"
        f"*Название:* {product_info.get('Название', 'Нет данных')}\n"
        f"*Цена:* {product_info.get('Цена', '0')} ₽\n"
        f"*Отзывы:* {product_info.get('Отзывы', '0')}\n\n"
        
        f"📈 *Метрики продаж:*\n"
        f"• За день: {metrics['daily_sales']} шт.\n"
        f"• Выручка: {metrics['revenue']['daily']:.0f} ₽\n"
        f"• Прибыль: {metrics['profit']['daily']:.0f} ₽\n"
        f"• Маржа: {metrics['margin_percent']:.1f}%\n\n"
        
        f"🔄 *Прогноз на месяц:*\n"
        f"• Продажи: {metrics['revenue']['monthly']:.0f} ₽\n"
        f"• Прибыль: {metrics['profit']['monthly']:.0f} ₽\n\n"
        
        f"⚠️ *Анализ рисков:*\n"
        f"• Уровень риска: {risk_analysis['risk_level']}\n"
        f"• Стабильность: {risk_analysis['stability_score']}/3\n"
        f"• Ценовой фактор: {risk_analysis['price_score']}/3\n"
        f"• Маржинальность: {risk_analysis['margin_score']}/3\n\n"
    )
    
    # Добавляем рекомендации
    if risk_analysis['recommendations']:
        result += "📝 *Рекомендации:*\n"
        for rec in risk_analysis['recommendations']:
            result += f"• {rec}\n"
    
    return result

async def format_trend_analysis(analysis):
    """Форматирует результаты анализа трендов в читаемый вид"""
    if "error" in analysis:
        return f"❌ Ошибка при анализе трендов: {analysis['error']}"
    
    trend = analysis["trend_analysis"]
    seasonality = analysis["seasonality_analysis"]
    forecast = analysis["forecast"]
    
    result = (
        f"📊 *Анализ трендов*\n\n"
        f"*Тренд продаж:*\n"
        f"• Направление: {trend['trend_direction']}\n"
        f"• Средние продажи: {trend['avg_sales']:.1f} шт.\n"
        f"• Средняя цена: {trend['avg_price']:.0f} ₽\n\n"
        
        f"🌊 *Сезонность:*\n"
        f"• Уровень: {seasonality['seasonality_level']}\n"
        f"• Вариация: {seasonality['coefficient_of_variation']:.1f}%\n\n"
        
        f"🔮 *Прогноз на 7 дней:*\n"
        f"• Продажи: {sum(forecast['sales_forecast']):.0f} шт.\n"
        f"• Средняя цена: {sum(forecast['price_forecast'])/len(forecast['price_forecast']):.0f} ₽\n"
        f"• Доверительный интервал: {forecast['confidence_interval']['lower_bound']:.0f} - "
        f"{forecast['confidence_interval']['upper_bound']:.0f} шт.\n"
    )
    
    return result

async def analyze_article(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик сообщений с артикулом"""
    article = update.message.text.strip()
    
    # Проверяем, что сообщение содержит только цифры
    if not article.isdigit():
        await update.message.reply_text(
            "❌ Пожалуйста, отправьте только цифры артикула товара."
        )
        return
    
    # Отправляем сообщение о начале анализа
    status_message = await update.message.reply_text(
        "🔄 Начинаю анализ товара...\n"
        "Это может занять несколько секунд."
    )
    
    try:
        # Получаем анализ товара
        product_analysis = await product_analyzer.analyze_product(article)
        product_text = await format_product_analysis(product_analysis)
        await status_message.edit_text(product_text, parse_mode='Markdown')
        
        # Получаем анализ трендов
        trend_analysis = await trend_analyzer.analyze_trends(article)
        trend_text = await format_trend_analysis(trend_analysis)
        await update.message.reply_text(trend_text, parse_mode='Markdown')
        
    except Exception as e:
        await status_message.edit_text(
            f"❌ Произошла ошибка при анализе:\n{str(e)}"
        )

async def main():
    """Запуск бота"""
    # Создаем приложение
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Добавляем обработчики
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, analyze_article))
    
    # Запускаем бота
    print("Запуск бота...")
    await application.initialize()
    await application.start()
    await application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nБот остановлен")
    except Exception as e:
        print(f"Произошла ошибка: {e}") 