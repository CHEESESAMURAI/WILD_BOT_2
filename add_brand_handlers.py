#!/usr/bin/env python3
"""
Скрипт для добавления обработчиков анализа бренда в new_bot.py
"""

def main():
    # Добавление состояния ожидания бренда
    add_state_for_brand()
    
    # Добавление обработчиков для кнопки анализа бренда
    add_brand_handlers()
    
    print("Обработчики анализа бренда успешно добавлены!")

def add_state_for_brand():
    """Добавляет состояние waiting_for_brand в класс UserStates"""
    file_path = '/Users/user/Desktop/WILD-BOT 5/new_bot.py'
    
    with open(file_path, 'r', encoding='utf-8') as file:
        lines = file.readlines()
    
    new_lines = []
    for line in lines:
        new_lines.append(line)
        if 'viewing_search_results = State()' in line:
            new_lines.append('    waiting_for_brand = State()  # Состояние для ожидания ввода бренда\n')
    
    with open(file_path, 'w', encoding='utf-8') as file:
        file.writelines(new_lines)

def add_brand_handlers():
    """Добавляет обработчики для анализа бренда"""
    file_path = '/Users/user/Desktop/WILD-BOT 5/new_bot.py'
    
    # Код обработчиков
    handlers_code = '''
@dp.callback_query(lambda c: c.data == 'brand_analysis')
async def handle_brand_analysis(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает запрос на анализ бренда."""
    user_id = callback_query.from_user.id
    
    # Проверяем подписку
    can_perform = await check_subscription(user_id)
    if not can_perform:
        await callback_query.message.answer("⚠️ У вас нет активной подписки или закончился лимит запросов. Перейдите в раздел подписок для получения доступа.", reply_markup=main_menu_kb())
        await callback_query.answer()
        return
    
    # Переходим в состояние ожидания бренда
    await state.set_state(UserStates.waiting_for_brand)
    await callback_query.message.answer("Введите название бренда для анализа:", reply_markup=back_keyboard())
    await callback_query.answer()

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_brand)
async def handle_brand_name(message: types.Message, state: FSMContext):
    """Обрабатывает ввод названия бренда."""
    try:
        user_id = message.from_user.id
        brand_name = message.text.strip()
        
        # Отправляем сообщение о начале анализа
        processing_msg = await message.answer("⏳ Анализирую бренд, это может занять до 30 секунд...")
        
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
            'brand_sales_chart': "📈 Динамика продаж бренда — изменение объема продаж и выручки по дням",
            'brand_competitors_chart': "🥊 Сравнение с конкурентами — сопоставление по количеству товаров и продажам",
            'brand_categories_chart': "📁 Распределение по категориям — показывает долю товаров бренда в разных категориях"
        }
        
        # Отправляем графики бренда, если они есть
        if brand_chart_paths:
            await message.answer("📊 ГРАФИКИ ПО БРЕНДУ:", reply_markup=back_keyboard())
            
            for chart_path in brand_chart_paths:
                chart_name = chart_path.replace('.png', '')
                caption = brand_chart_descriptions.get(chart_name, f"График: {chart_name}")
                
                with open(chart_path, 'rb') as photo:
                    await message.answer_photo(photo, caption=caption)
        
        await state.clear()
        
    except Exception as e:
        logger.error(f"Error in handle_brand_name: {str(e)}", exc_info=True)
        await message.answer(f"❌ Произошла ошибка при анализе бренда: {str(e)}", reply_markup=back_keyboard())
        await state.clear()
'''
    
    # Ищем место перед обработчиком глобального поиска
    with open(file_path, 'r', encoding='utf-8') as file:
        content = file.read()
    
    position = content.find('@dp.callback_query(lambda c: c.data == "product_search")')
    if position == -1:
        position = content.find('@dp.callback_query(lambda c: c.data == "track_item")')
    
    if position != -1:
        new_content = content[:position] + handlers_code + '\n' + content[position:]
        
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(new_content)
    else:
        print("Не удалось найти место для вставки обработчиков!")

if __name__ == "__main__":
    main() 