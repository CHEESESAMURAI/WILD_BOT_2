async def get_external_ads_data(query):
    """Получение данных о внешней рекламе товаров через MPSTAT API"""
    try:
        # URL для запроса данных о внешней рекламе
        url = f"https://mpstats.io/api/wb/get/external-ads?query={query}"
        
        # Заголовки запроса
        headers = {
            "X-Mpstats-TOKEN": MPSTA_API_KEY,
            "Content-Type": "application/json"
        }
        
        logger.info(f"Sending request to MPSTATS API: {url}")
        
        # Выполняем запрос к API
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Successfully got external ads data for query: {query}")
                    return data
                else:
                    logger.error(f"Error getting external ads data: {response.status} - {await response.text()}")
                    return {"error": f"Ошибка API: {response.status}"}
    except Exception as e:
        logger.error(f"Exception getting external ads data: {str(e)}")
        return {"error": f"Ошибка при получении данных о внешней рекламе: {str(e)}"}

def format_external_analysis(data):
    """Форматирует данные о внешней рекламе в удобный для отображения вид"""
    try:
        if "error" in data:
            return f"❌ Ошибка: {data['error']}", []
        
        query = data.get("query", "")
        is_article = data.get("is_article", False)
        product_info = data.get("product_info", {})
        ad_items = data.get("ad_items", [])
        bloggers_data = data.get("bloggers_data", {})
        
        # Результат будет содержать текстовый отчет и список файлов с графиками
        chart_files = []
        
        # Заголовок отчета
        if is_article:
            product_name = product_info.get("name", "")
            brand = product_info.get("brand", "")
            result = f"📊 *Анализ внешней рекламы*\n\n"
            result += f"*Артикул:* {query}\n"
            if product_name:
                result += f"*Товар:* {product_name}\n"
            if brand:
                result += f"*Бренд:* {brand}\n"
        else:
            result = f"📊 *Анализ внешней рекламы по запросу:* {query}\n\n"
        
        if not ad_items:
            result += "\n⚠️ *Не найдено данных о рекламных публикациях.*"
            return result, chart_files
        
        # Информация о найденных публикациях
        result += f"\n📣 *Найдено публикаций:* {len(ad_items)}\n"
        
        # Таблица с данными о публикациях
        result += "\n*Таблица публикаций:*\n"
        result += "```\n"
        result += "№  | Площадка | Блогер | Дата | Частотность | Выручка | Заказы | Прирост(%)\n"
        result += "---|-----------|---------|---------|---------|---------|---------|---------\n"
        
        # Ограничиваем количество публикаций в таблице (не более 10)
        for i, ad in enumerate(ad_items[:10], 1):
            platform = ad.get("platform", "—")
            blogger = ad.get("blogger", {}).get("name", "—")
            date = ad.get("date", "—")
            if date and "T" in date:
                date = date.split("T")[0]
            
            total_frequency = ad.get("total_frequency_3days", 0)
            total_revenue = ad.get("total_revenue_3days", 0)
            orders = ad.get("orders", 0)
            growth_percent = ad.get("sales_growth_percent", 0)
            
            # Форматируем данные для таблицы
            result += f"{i} | {platform[:8]}... | {blogger[:8]}... | {date} | {total_frequency} | {total_revenue:,.0f}₽ | {orders} | {growth_percent:.1f}%\n"
        
        result += "```\n"
        
        # Если публикаций больше 10, добавляем примечание
        if len(ad_items) > 10:
            result += f"_Показаны первые 10 из {len(ad_items)} публикаций_\n"
        
        # Заключение и рекомендации
        result += "\n📋 *Выводы и рекомендации:*\n"
        
        if bloggers_data:
            # Находим блогеров с наилучшими показателями
            best_growth_bloggers = sorted(bloggers_data.items(), key=lambda x: x[1]["avg_growth_percent"], reverse=True)
            best_freq_bloggers = sorted(bloggers_data.items(), key=lambda x: x[1]["avg_frequency"], reverse=True)
            
            if best_growth_bloggers:
                top_blogger = best_growth_bloggers[0]
                result += f"• Лучший результат по приросту продаж показал блогер *{top_blogger[0]}* " \
                          f"(средний прирост {top_blogger[1]['avg_growth_percent']:.1f}%).\n"
            
            if best_freq_bloggers:
                top_freq_blogger = best_freq_bloggers[0]
                result += f"• Наибольшую частотность обеспечил блогер *{top_freq_blogger[0]}* " \
                          f"(в среднем {top_freq_blogger[1]['avg_frequency']:.1f} продаж).\n"
            
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

@dp.message(lambda message: message.text and message.text.strip(), UserStates.waiting_for_external)
async def handle_external_input(message: types.Message, state: FSMContext):
    query = message.text.strip()
    user_id = message.from_user.id
    
    logger.info(f"User {user_id} requested external analysis for: {query}")
    
    # Проверяем баланс пользователя
    balance = subscription_manager.get_user_balance(user_id)
    if balance < COSTS["external_analysis"]:
        await message.reply(
            f"❌ *Недостаточно средств для анализа внешней рекламы*\n\n"
            f"Стоимость операции: {COSTS['external_analysis']}₽\n"
            f"Ваш баланс: {balance}₽\n\n"
            f"Пожалуйста, пополните баланс.",
            parse_mode=ParseMode.MARKDOWN
        )
        return
    
    # Отправляем сообщение о начале анализа
    loading_msg = await message.reply("🔍 *Анализирую внешнюю рекламу...*", parse_mode=ParseMode.MARKDOWN)
    
    try:
        # Списываем средства с баланса пользователя
        subscription_manager.deduct_balance(user_id, COSTS["external_analysis"])
        
        # Определяем, является ли запрос артикулом или названием товара
        is_article = query.isdigit() and len(query) >= 6
        
        # Получаем данные о внешней рекламе
        external_data = {"query": query, "is_article": is_article, "ad_items": []}
        
        if is_article:
            # Для артикула сначала получаем информацию о товаре
            product_info = await get_wb_product_info(query)
            external_data["product_info"] = product_info
            
            # Затем получаем данные о внешней рекламе
            ad_data = await get_external_ads_data(query)
            if "error" not in ad_data:
                external_data["ad_items"] = ad_data.get("items", [])
            else:
                external_data["error"] = ad_data["error"]
        else:
            # Для поискового запроса (названия товара) получаем данные о внешней рекламе
            ad_data = await get_external_ads_data(query)
            if "error" not in ad_data:
                external_data["ad_items"] = ad_data.get("items", [])
            else:
                external_data["error"] = ad_data["error"]
        
        # Анализируем данные о блогерах
        if external_data["ad_items"]:
            bloggers_data = {}
            for ad in external_data["ad_items"]:
                blogger_name = ad.get("blogger", {}).get("name", "Неизвестно")
                growth_percent = ad.get("sales_growth_percent", 0)
                frequency = ad.get("total_frequency_3days", 0)
                
                if blogger_name not in bloggers_data:
                    bloggers_data[blogger_name] = {
                        "publications": 0,
                        "total_growth": 0,
                        "avg_growth_percent": 0,
                        "total_frequency": 0,
                        "avg_frequency": 0
                    }
                
                bloggers_data[blogger_name]["publications"] += 1
                bloggers_data[blogger_name]["total_growth"] += growth_percent
                bloggers_data[blogger_name]["total_frequency"] += frequency
            
            # Вычисляем средние значения
            for blogger, data in bloggers_data.items():
                if data["publications"] > 0:
                    data["avg_growth_percent"] = data["total_growth"] / data["publications"]
                    data["avg_frequency"] = data["total_frequency"] / data["publications"]
            
            external_data["bloggers_data"] = bloggers_data
        
        # Форматируем результаты анализа
        result_text, chart_files = format_external_analysis(external_data)
        
        # Отправляем результаты анализа
        await loading_msg.delete()
        await message.reply(result_text, parse_mode=ParseMode.MARKDOWN)
        
        # Если есть графики, отправляем их
        if chart_files:
            media = []
            
            for chart_file in chart_files:
                try:
                    photo = FSInputFile(chart_file)
                    media.append(InputMediaPhoto(media=photo))
                except Exception as e:
                    logger.error(f"Error adding chart to media group: {str(e)}")
            
            if media:
                try:
                    await bot.send_media_group(chat_id=message.chat.id, media=media)
                except Exception as e:
                    logger.error(f"Error sending media group: {str(e)}")
        
        # Добавляем запись в историю анализов пользователя
        new_analysis = {
            "type": "external",
            "query": query,
            "timestamp": datetime.now().isoformat(),
            "result": result_text
        }
        
        user_data = await state.get_data()
        analyses_history = user_data.get("analyses_history", [])
        analyses_history.append(new_analysis)
        
        # Ограничиваем историю 10 последними анализами
        if len(analyses_history) > 10:
            analyses_history = analyses_history[-10:]
        
        await state.update_data(analyses_history=analyses_history)
        
        # Очищаем состояние
        await state.clear()
    
    except Exception as e:
        logger.error(f"Error in external analysis: {str(e)}", exc_info=True)
        
        await message.reply(
            "❌ *Произошла ошибка при анализе внешней рекламы*\n\n"
            f"Детали ошибки: {str(e)}",
            parse_mode=ParseMode.MARKDOWN
        )
        
        # Возвращаем средства пользователю в случае ошибки
        subscription_manager.add_balance(user_id, COSTS["external_analysis"])
    
    # Отправляем клавиатуру главного меню
    await message.answer("Выберите действие:", reply_markup=main_menu_kb())