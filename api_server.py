import asyncio
import logging
from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import uvicorn
import json
from typing import Dict, List, Optional
from main import ProductCardAnalyzer, TrendAnalyzer
from niche_analyzer import NicheAnalyzer
import sqlite3
import sys
import os

# Добавляем текущий каталог в путь поиска модулей
sys.path.append(os.path.dirname(os.path.realpath(__file__)))

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('api_server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Инициализация анализаторов
try:
    product_analyzer = ProductCardAnalyzer()
    trend_analyzer = TrendAnalyzer()
    niche_analyzer = NicheAnalyzer()
    # Импортируем функции из new_bot.py для работы с MPSTAT
    from new_bot import get_wb_product_info, global_search_serper_detailed, get_mpsta_data, format_mpsta_results
    logger.info("Анализаторы успешно инициализированы")
except Exception as e:
    logger.error(f"Ошибка при инициализации анализаторов: {str(e)}")
    product_analyzer = None
    trend_analyzer = None
    niche_analyzer = None

app = FastAPI()

# Модели данных
class ProductRequest(BaseModel):
    article: str

class NicheRequest(BaseModel):
    keyword: str

class SearchRequest(BaseModel):
    query: str
    max_results: int = 10
    include_social: bool = True
    include_news: bool = False
    include_images: bool = False

class TrackRequest(BaseModel):
    user_id: int
    article: str

class RefreshRequest(BaseModel):
    user_id: int
    article_id: int

# Инициализация БД для отслеживания товаров
def init_db():
    try:
        conn = sqlite3.connect('tracked_articles.db')
        cursor = conn.cursor()
        
        # Создаем таблицу для отслеживаемых товаров
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracked_articles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            article TEXT,
            name TEXT,
            price REAL,
            stock INTEGER,
            sales_total INTEGER,
            sales_per_day REAL,
            last_updated TEXT,
            UNIQUE(user_id, article)
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"Ошибка при инициализации базы данных: {str(e)}")

# Эндпоинты API

@app.get("/health")
async def health_check():
    """Проверка работоспособности сервера"""
    return {
        "status": "ok", 
        "timestamp": datetime.now().isoformat(),
        "analyzers": {
            "product_analyzer": product_analyzer is not None,
            "trend_analyzer": trend_analyzer is not None,
            "niche_analyzer": niche_analyzer is not None
        }
    }

@app.get("/extended_analysis/{article}")
async def get_product_analysis(article: str):
    """Анализ товара по артикулу"""
    try:
        logger.info(f"Запрос расширенного анализа товара: {article}")
        
        # Сначала получаем данные через API Wildberries
        result = await get_wb_product_info(article)
        if not result:
            logger.error(f"Товар с артикулом {article} не найден")
            raise HTTPException(status_code=404, detail=f"Товар с артикулом {article} не найден в базе Wildberries")
        
        # Если возможно, обогащаем данными из MPSTAT
        try:
            mpsta_data = await get_mpsta_data(article)
            if mpsta_data and not mpsta_data.get("error"):
                mpsta_formatted = format_mpsta_results(mpsta_data)
                # Объединяем данные
                result.update({
                    "mpstat_data": mpsta_formatted
                })
                logger.info(f"Данные MPSTAT добавлены к анализу товара {article}")
        except Exception as mpsta_error:
            logger.warning(f"Не удалось получить данные MPSTAT для товара {article}: {str(mpsta_error)}")
        
        return result
    except HTTPException as he:
        logger.error(f"HTTP ошибка при анализе товара {article}: {str(he.detail)}")
        raise he
    except Exception as e:
        logger.error(f"Error analyzing product {article}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze_niche")
async def analyze_niche(request: NicheRequest):
    """Анализ ниши по ключевому слову"""
    try:
        logger.info(f"Запрос анализа ниши: {request.keyword}")
        if not niche_analyzer:
            raise HTTPException(status_code=503, detail="Анализатор ниш недоступен")
            
        result = await niche_analyzer.analyze_category(request.keyword)
        if not result:
            raise HTTPException(status_code=404, detail="Ниша не найдена")
        
        # Обогащаем данными из MPSTAT
        try:
            mpsta_data = await get_mpsta_data(request.keyword)
            if mpsta_data and not mpsta_data.get("error"):
                mpsta_formatted = format_mpsta_results(mpsta_data)
                # Объединяем данные
                result.update({
                    "mpstat_data": mpsta_formatted
                })
                logger.info(f"Данные MPSTAT добавлены к анализу ниши {request.keyword}")
        except Exception as mpsta_error:
            logger.warning(f"Не удалось получить данные MPSTAT для ниши {request.keyword}: {str(mpsta_error)}")
        
        return result
    except HTTPException as he:
        raise he
    except Exception as e:
        logger.error(f"Error analyzing niche {request.keyword}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/analyze_category")
async def analyze_category(request: NicheRequest):
    """Анализ категории по ключевому слову"""
    try:
        logger.info(f"Запрос анализа категории: {request.keyword}")
        if not niche_analyzer:
            raise HTTPException(status_code=503, detail="Анализатор ниш недоступен")
            
        result = await niche_analyzer.analyze_category(request.keyword)
        if not result:
            raise HTTPException(status_code=404, detail="Категория не найдена")
        
        # Обогащаем данными из MPSTAT
        try:
            mpsta_data = await get_mpsta_data(request.keyword)
            if mpsta_data and not mpsta_data.get("error"):
                mpsta_formatted = format_mpsta_results(mpsta_data)
                # Объединяем данные
                result.update({
                    "mpstat_data": mpsta_formatted
                })
                logger.info(f"Данные MPSTAT добавлены к анализу категории {request.keyword}")
        except Exception as mpsta_error:
            logger.warning(f"Не удалось получить данные MPSTAT для категории {request.keyword}: {str(mpsta_error)}")
        
        return result
    except Exception as e:
        logger.error(f"Error analyzing category {request.keyword}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/search")
async def search(request: SearchRequest):
    """Глобальный поиск товаров"""
    try:
        logger.info(f"Глобальный поиск по запросу: {request.query}")
        # Напрямую используем функцию для глобального поиска из new_bot.py
        result = await global_search_serper_detailed(request.query)
        return result
    except Exception as e:
        logger.error(f"Error searching for {request.query}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tracked_items")
async def get_tracked_items(user_id: int):
    """Получение отслеживаемых товаров пользователя"""
    try:
        conn = sqlite3.connect('tracked_articles.db')
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT id, article, name, price, stock, sales_total, sales_per_day, last_updated 
        FROM tracked_articles 
        WHERE user_id = ?
        ''', (user_id,))
        
        items = []
        for row in cursor.fetchall():
            items.append({
                'id': row[0],
                'article': row[1],
                'name': row[2],
                'price': row[3],
                'stock': row[4],
                'salesTotal': row[5],
                'salesPerDay': row[6],
                'lastUpdated': row[7]
            })
        
        conn.close()
        return items
    except Exception as e:
        logger.error(f"Error getting tracked items for user {user_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/track_item")
async def track_item(request: TrackRequest):
    """Добавление товара для отслеживания"""
    try:
        # Получаем информацию о товаре через функцию из new_bot.py
        product_info = await get_wb_product_info(request.article)
        if not product_info:
            raise HTTPException(status_code=404, detail="Товар не найден")
        
        conn = sqlite3.connect('tracked_articles.db')
        cursor = conn.cursor()
        
        # Проверяем, не отслеживается ли уже этот товар
        cursor.execute('SELECT id FROM tracked_articles WHERE user_id = ? AND article = ?', 
                      (request.user_id, request.article))
        
        if cursor.fetchone():
            conn.close()
            raise HTTPException(status_code=400, detail="Этот товар уже отслеживается")
        
        # Получаем текущую цену из product_info
        price = product_info.get('price', {}).get('current', 0)
        if isinstance(product_info.get('price'), (int, float)):
            price = product_info.get('price', 0)
            
        # Получаем данные о продажах
        sales_total = product_info.get('sales', {}).get('total', 0)
        sales_per_day = product_info.get('sales', {}).get('today', 0)
        
        # Получаем данные об остатках
        stock = product_info.get('stocks', {}).get('total', 0)
        
        # Добавляем товар в отслеживаемые
        cursor.execute('''
        INSERT INTO tracked_articles (user_id, article, name, price, stock, sales_total, sales_per_day, last_updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.user_id,
            request.article,
            product_info.get('name', f'Товар {request.article}'),
            price,
            stock,
            sales_total,
            sales_per_day,
            datetime.now().isoformat()
        ))
        
        conn.commit()
        last_id = cursor.lastrowid
        
        # Получаем добавленный товар
        cursor.execute('''
        SELECT id, article, name, price, stock, sales_total, sales_per_day, last_updated 
        FROM tracked_articles 
        WHERE id = ?
        ''', (last_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            'id': row[0],
            'article': row[1],
            'name': row[2],
            'price': row[3],
            'stock': row[4],
            'salesTotal': row[5],
            'salesPerDay': row[6],
            'lastUpdated': row[7]
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error tracking item {request.article}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/untrack_item")
async def untrack_item(user_id: int, article_id: int):
    """Удаление товара из отслеживаемых"""
    try:
        conn = sqlite3.connect('tracked_articles.db')
        cursor = conn.cursor()
        
        # Удаляем товар
        cursor.execute('DELETE FROM tracked_articles WHERE user_id = ? AND id = ?', 
                      (user_id, article_id))
        
        if cursor.rowcount == 0:
            conn.close()
            raise HTTPException(status_code=404, detail="Товар не найден")
        
        conn.commit()
        conn.close()
        
        return {"success": True}
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error untracking item {article_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/refresh_tracked_item")
async def refresh_tracked_item(request: RefreshRequest):
    """Обновление данных отслеживаемого товара"""
    try:
        conn = sqlite3.connect('tracked_articles.db')
        cursor = conn.cursor()
        
        # Получаем артикул для обновления
        cursor.execute('SELECT article FROM tracked_articles WHERE id = ? AND user_id = ?', 
                      (request.article_id, request.user_id))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            raise HTTPException(status_code=404, detail="Товар не найден")
        
        article = row[0]
        
        # Получаем актуальную информацию о товаре через функцию из new_bot.py
        product_info = await get_wb_product_info(article)
        if not product_info:
            raise HTTPException(status_code=404, detail="Не удалось получить информацию о товаре")
        
        # Получаем текущую цену из product_info
        price = product_info.get('price', {}).get('current', 0)
        if isinstance(product_info.get('price'), (int, float)):
            price = product_info.get('price', 0)
            
        # Получаем данные о продажах
        sales_total = product_info.get('sales', {}).get('total', 0)
        sales_per_day = product_info.get('sales', {}).get('today', 0)
        
        # Получаем данные об остатках
        stock = product_info.get('stocks', {}).get('total', 0)
        
        # Обновляем данные
        cursor.execute('''
        UPDATE tracked_articles 
        SET price = ?, stock = ?, sales_total = ?, sales_per_day = ?, last_updated = ?
        WHERE id = ? AND user_id = ?
        ''', (
            price,
            stock,
            sales_total,
            sales_per_day,
            datetime.now().isoformat(),
            request.article_id,
            request.user_id
        ))
        
        conn.commit()
        
        # Получаем обновленные данные
        cursor.execute('''
        SELECT id, article, name, price, stock, sales_total, sales_per_day, last_updated 
        FROM tracked_articles 
        WHERE id = ?
        ''', (request.article_id,))
        
        row = cursor.fetchone()
        conn.close()
        
        return {
            'id': row[0],
            'article': row[1],
            'name': row[2],
            'price': row[3],
            'stock': row[4],
            'salesTotal': row[5],
            'salesPerDay': row[6],
            'lastUpdated': row[7]
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error refreshing item {request.article_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000) 