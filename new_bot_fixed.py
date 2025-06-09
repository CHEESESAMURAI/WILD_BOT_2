@dp.callback_query(lambda c: c.data == 'brand_analysis')
async def handle_brand_analysis(callback_query: types.CallbackQuery, state: FSMContext):
    """Обрабатывает запрос на анализ бренда."""
    user_id = callback_query.from_user.id
    
    # Проверяем подписку
    can_perform = subscription_manager.can_perform_action(user_id, "brand_analysis")
    if not can_perform:
        await callback_query.message.answer("⚠️ У вас нет активной подписки или закончился лимит запросов. Перейдите в раздел подписок для получения доступа.", reply_markup=main_menu_kb())
        await callback_query.answer()
        return
    
    # Переходим в состояние ожидания бренда
    await state.set_state(UserStates.waiting_for_brand)
    await callback_query.message.edit_text("Введите название бренда для анализа:", reply_markup=back_keyboard())
    await callback_query.answer() 