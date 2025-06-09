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
        
        # Декрементируем счетчик действий
        subscription_manager.decrement_action_count(user_id, "brand_analysis")
        
    except Exception as e:
        logger.error(f"Error in handle_brand_name: {str(e)}", exc_info=True)
        await message.answer(f"❌ Произошла ошибка при анализе бренда: {str(e)}", reply_markup=back_keyboard())
        await state.clear() 