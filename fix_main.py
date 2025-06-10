#!/usr/bin/env python3

with open('new_bot.py', 'r') as f:
    content = f.read()

# Находим строку if __name__ == '__main__':
if_main_position = content.find("if __name__ == '__main__':")

# Вставляем функцию main перед этой строкой
main_function = """
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

"""

# Создаем новый контент файла
new_content = content[:if_main_position] + main_function + content[if_main_position:]

# Записываем обновленный контент
with open('new_bot.py', 'w') as f:
    f.write(new_content)

print("Функция main успешно добавлена в файл new_bot.py") 