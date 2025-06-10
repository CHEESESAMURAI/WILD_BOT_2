import aiohttp
import asyncio
import json
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# API ключ
MPSTATS_API_KEY = "68431d2ac72ea4.96910328a56006b24a55daf65db03835d5fe5b4d"

async def test_external_ads():
    """Тестирование запроса данных о внешней рекламе (POST)"""
    article = "307819738"
    url = "https://mpstats.io/api/wb/get/external-ads"
    
    headers = {
        "X-Mpstats-TOKEN": MPSTATS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://mpstats.io",
        "Referer": "https://mpstats.io/"
    }
    
    body = {
        "query": article,
        "path": "Одежда/Женская одежда/Платья"
    }
    
    logger.info(f"Testing external ads POST request for article: {article}")
    logger.info(f"URL: {url}")
    logger.info(f"Headers: {headers}")
    logger.info(f"Body: {body}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response headers: {response.headers}")
                logger.info(f"Response body: {response_text}")
                
                if response.status == 200:
                    data = json.loads(response_text)
                    logger.info("Success! Got response data:")
                    logger.info(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    logger.error(f"Error: {response.status} - {response_text}")
    except Exception as e:
        logger.error(f"Exception: {str(e)}")

async def test_category_data():
    """Тестирование запроса данных по категории"""
    url = "https://mpstats.io/api/wb/get/category"
    
    headers = {
        "X-Mpstats-TOKEN": MPSTATS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://mpstats.io",
        "Referer": "https://mpstats.io/"
    }
    
    params = {
        "path": "Одежда/Женская одежда/Платья",
        "d1": "2024-03-10",
        "d2": "2024-04-10"
    }
    
    logger.info("Testing category data request")
    logger.info(f"URL: {url}")
    logger.info(f"Headers: {headers}")
    logger.info(f"Params: {params}")
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response headers: {response.headers}")
                logger.info(f"Response body: {response_text}")
                
                if response.status == 200:
                    data = json.loads(response_text)
                    logger.info("Success! Got response data:")
                    logger.info(json.dumps(data, indent=2, ensure_ascii=False))
                else:
                    logger.error(f"Error: {response.status} - {response_text}")
    except Exception as e:
        logger.error(f"Exception: {str(e)}")

async def test_external_ads_get_query_only():
    """GET-запрос только с query"""
    article = "307819738"
    url = "https://mpstats.io/api/wb/get/external-ads"
    headers = {
        "X-Mpstats-TOKEN": MPSTATS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://mpstats.io",
        "Referer": "https://mpstats.io/"
    }
    params = {"query": article}
    logger.info("GET only query param...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, params=params) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response body: {response_text}")
    except Exception as e:
        logger.error(f"Exception: {str(e)}")

async def test_external_ads_post_query_only():
    """POST-запрос только с query в body"""
    article = "307819738"
    url = "https://mpstats.io/api/wb/get/external-ads"
    headers = {
        "X-Mpstats-TOKEN": MPSTATS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://mpstats.io",
        "Referer": "https://mpstats.io/"
    }
    body = {"query": article}
    logger.info("POST only query param...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response body: {response_text}")
    except Exception as e:
        logger.error(f"Exception: {str(e)}")

async def test_external_ads_post_path_array():
    """POST с path как массив строк"""
    article = "307819738"
    url = "https://mpstats.io/api/wb/get/external-ads"
    headers = {
        "X-Mpstats-TOKEN": MPSTATS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://mpstats.io",
        "Referer": "https://mpstats.io/"
    }
    body = {
        "query": article,
        "path": ["Одежда", "Женская одежда", "Платья"]
    }
    logger.info("POST path as array...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response body: {response_text}")
    except Exception as e:
        logger.error(f"Exception: {str(e)}")

async def test_external_ads_post_path_in_category():
    """POST с path внутри category-объекта"""
    article = "307819738"
    url = "https://mpstats.io/api/wb/get/external-ads"
    headers = {
        "X-Mpstats-TOKEN": MPSTATS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://mpstats.io",
        "Referer": "https://mpstats.io/"
    }
    body = {
        "query": article,
        "category": {"path": ["Одежда", "Женская одежда", "Платья"]}
    }
    logger.info("POST path in category object...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response body: {response_text}")
    except Exception as e:
        logger.error(f"Exception: {str(e)}")

async def test_external_ads_post_article_param():
    """POST с article вместо query"""
    article = "307819738"
    url = "https://mpstats.io/api/wb/get/external-ads"
    headers = {
        "X-Mpstats-TOKEN": MPSTATS_API_KEY,
        "Content-Type": "application/json",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Origin": "https://mpstats.io",
        "Referer": "https://mpstats.io/"
    }
    body = {
        "article": article,
        "path": ["Одежда", "Женская одежда", "Платья"]
    }
    logger.info("POST article param...")
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body) as response:
                response_text = await response.text()
                logger.info(f"Response status: {response.status}")
                logger.info(f"Response body: {response_text}")
    except Exception as e:
        logger.error(f"Exception: {str(e)}")

async def main():
    """Запуск тестов"""
    logger.info("Starting API tests...")
    
    # Тестируем запрос внешней рекламы
    await test_external_ads()
    
    # Тестируем запрос данных категории
    await test_category_data()

    # Тестируем GET-запрос только с query
    await test_external_ads_get_query_only()

    # Тестируем POST-запрос только с query в body
    await test_external_ads_post_query_only()

    # Тестируем POST с path как массив строк
    await test_external_ads_post_path_array()

    # Тестируем POST с path внутри category-объекта
    await test_external_ads_post_path_in_category()

    # Тестируем POST с article вместо query
    await test_external_ads_post_article_param()

if __name__ == "__main__":
    asyncio.run(main()) 