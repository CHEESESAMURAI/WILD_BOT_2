import aiohttp
import asyncio
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API ключ Telemetr
TELEMETR_API_KEY = "uHx9T1YIeFSdgryRBLx3ZPlMcObkG7sN9S85u3bvZxjYMLK0IFjpsjtVcdpbbsDjyCXRYj9T4BOix"

async def get_telemetr_data(article: str) -> Optional[Dict[str, Any]]:
    """
    Получение данных о внешней рекламе товара через API Telemetr
    """
    url = "https://api.telemetr.me/api/v1/wb/external-ads"
    
    # Параметры запроса
    params = {
        "article": article,
        "date_from": (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d"),
        "date_to": datetime.now().strftime("%Y-%m-%d")
    }
    
    # Заголовки запроса
    headers = {
        "Authorization": f"Bearer {TELEMETR_API_KEY}",
        "Content-Type": "application/json",
        "Accept": "application/json"
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            # Отправляем GET запрос
            async with session.get(url, params=params, headers=headers) as response:
                logger.info(f"Telemetr API Request URL: {response.url}")
                logger.info(f"Telemetr API Request Headers: {headers}")
                logger.info(f"Telemetr API Response Status: {response.status}")
                
                response_text = await response.text()
                logger.info(f"Telemetr API Response Body: {response_text}")
                
                if response.status == 200:
                    return json.loads(response_text)
                else:
                    logger.error(f"Telemetr API Error: {response.status} - {response_text}")
                    return None
                    
    except Exception as e:
        logger.error(f"Error getting Telemetr data: {str(e)}")
        return None

async def main():
    """Тестирование API Telemetr"""
    article = "307819738"
    
    print("\nТестирование API Telemetr...")
    print(f"Артикул: {article}")
    
    # Получаем данные
    data = await get_telemetr_data(article)
    
    if data:
        print("\nРезультаты:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print("\nНе удалось получить данные")

if __name__ == "__main__":
    asyncio.run(main()) 