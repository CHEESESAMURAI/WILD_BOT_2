#!/usr/bin/env python3

# Читаем файл
with open('new_bot.py', 'r') as f:
    content = f.read()

# 1. Добавляем стоимость планирования поставок
if "'supply_planning': 30" not in content:
    content = content.replace(
        "'supplier_analysis': 25  # Добавляем стоимость анализа поставщика",
        "'supplier_analysis': 25,  # Добавляем стоимость анализа поставщика\n    'supply_planning': 30  # Добавляем стоимость планирования поставок"
    )

# 2. Добавляем кнопку в меню если её нет
if '"📦 План поставок"' not in content:
    content = content.replace(
        'InlineKeyboardButton(text="🔍 Анализ внешки", callback_data="external_analysis"),\n            InlineKeyboardButton(text="🌐 Глобальный поиск", callback_data="product_search")',
        'InlineKeyboardButton(text="📦 План поставок", callback_data="supply_planning"),\n            InlineKeyboardButton(text="🔍 Анализ внешки", callback_data="external_analysis")\n        ],\n        [\n            InlineKeyboardButton(text="🌐 Глобальный поиск", callback_data="product_search"),\n            InlineKeyboardButton(text="📱 Отслеживание", callback_data="track_item")\n        ],\n        [\n            InlineKeyboardButton(text="📦 Отслеживаемые", callback_data="tracked"),\n            InlineKeyboardButton(text="👤 Личный кабинет", callback_data="profile")\n        ],\n        [\n            InlineKeyboardButton(text="💳 Пополнить баланс", callback_data="add_funds"),\n            InlineKeyboardButton(text="📅 Подписка", callback_data="subscription")\n        ],\n        [\n            InlineKeyboardButton(text="📊 Статистика", callback_data="stats"),\n            InlineKeyboardButton(text="🗓️ Анализ сезонности", callback_data="seasonality_analysis")\n        ],\n        [\n            InlineKeyboardButton(text="🤖 Помощь с нейронкой", callback_data="ai_helper"),\n            InlineKeyboardButton(text="👥 Поиск блогеров", callback_data="blogger_search")\n        ],\n        [\n            InlineKeyboardButton(text="🔮 Оракул запросов", callback_data="oracle_queries"),\n            InlineKeyboardButton(text="ℹ️ Помощь", callback_data="help")'
    )

# 3. Добавляем в справку
if '"• План поставок:' not in content:
    content = content.replace(
        'f"• Поиск блогеров: {COSTS[\'blogger_search\']}₽"',
        'f"• Поиск блогеров: {COSTS[\'blogger_search\']}₽\\n"\n        f"• План поставок: {COSTS[\'supply_planning\']}₽"'
    )

# 4. Добавляем обработчики
if 'handle_supply_planning' not in content:
    insert_pos = content.find('if __name__ == \'__main__\':')
    if insert_pos != -1:
        handlers = '''
# === ПЛАНИРОВАНИЕ ПОСТАВОК ===

@dp.callback_query(lambda c: c.data == "supply_planning")
async def handle_supply_planning(callback_query: types.CallbackQuery, state: FSMContext):
    """Обработчик запроса планирования поставок"""
    try:
        await state.set_state(UserStates.waiting_for_supply_planning)
        
        supply_text = (
            "📦 *ПЛАН ПОСТАВОК*\\n\\n"
            "🎯 *Назначение:*\\n"
            "Помогает оценить остатки и потребность в новых поставках, "
            "чтобы не терять продажи из-за нулевых остатков.\\n\\n"
            "📊 *Что вы получите:*\\n"
            "• Текущие остатки на складе\\n"
            "• Среднедневные продажи\\n"
            "• Дни до окончания остатков\\n"
            "• Рекомендуемый объем поставки\\n"
            "• Цветовая маркировка критичности\\n"
            "• Детальные графики и аналитику\\n\\n"
            "🟢 >10 дней остатка - хорошо\\n"
            "🟡 3-10 дней - внимание\\n"
            "🔴 <3 дней - срочно пополнить!\\n\\n"
            f"💰 Стоимость: {COSTS.get('supply_planning', 30)}₽\\n\\n"
            "📝 *Введите артикулы товаров:*\\n"
            "Можно несколько через запятую или по одному на строке\\n\\n"
            "*Пример:*\\n"
            "`123456789, 987654321, 456789123`\\n"
            "или\\n"
            "`123456789`\\n"
            "`987654321`\\n"
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
    await message.reply("🚧 Функция планирования поставок находится в разработке.\\nСкоро будет доступна!", reply_markup=back_keyboard())
    await state.clear()


'''
        content = content[:insert_pos] + handlers + content[insert_pos:]

# Сохраняем файл
with open('new_bot.py', 'w') as f:
    f.write(content)

print("✅ Изменения применены успешно!")
