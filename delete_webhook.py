import asyncio
import logging
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError

# Токен бота
BOT_TOKEN = "7984401479:AAHGKTVrRLxrJTuuehuGa4XsYmJ2bpCbe1U"

async def delete_webhook():
    bot = Bot(token=BOT_TOKEN)
    try:
        # Получаем информацию о webhook
        webhook_info = await bot.get_webhook_info()
        
        if webhook_info.url:
            print(f"Найден активный webhook: {webhook_info.url}")
            # Удаляем webhook
            await bot.delete_webhook()
            print("Webhook успешно удален")
        else:
            print("Webhook не найден")
    
    except TelegramAPIError as e:
        print(f"Ошибка при работе с API Telegram: {e}")
    finally:
        # Закрываем сессию бота
        await bot.session.close()

if __name__ == "__main__":
    asyncio.run(delete_webhook()) 