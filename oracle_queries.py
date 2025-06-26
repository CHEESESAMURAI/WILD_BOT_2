#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import aiohttp
import asyncio
import logging
from typing import Dict, List, Optional, Any, Tuple
import json
from datetime import datetime, timedelta
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib import rcParams
import seaborn as sns
import pandas as pd
import numpy as np
from urllib.parse import quote_plus
import calendar
from calendar import monthrange
from config import MPSTATS_API_KEY

logger = logging.getLogger(__name__)

# Настройка matplotlib для русского языка
rcParams['font.family'] = 'DejaVu Sans'
plt.style.use('seaborn-v0_8')

class OracleQueries:
    """Класс для работы с Оракулом запросов"""
    
    def __init__(self):
        self.api_key = MPSTATS_API_KEY
        self.base_url = "https://mpstats.io/api/wb/get"
        self.categories_url = "https://mpstats.io/api/wb/get/categories"
        # Рабочий URL для категорий
        self.category_url = "https://mpstats.io/api/wb/get/category"
        self.categories_list_url = "https://mpstats.io/api/wb/get/categories"
    
    async def get_search_queries_data(self, 
                                    queries_count: int, 
                                    month: str,
                                    min_revenue: int = 0,
                                    min_frequency: int = 0) -> Dict[str, Any]:
        """
        Основной анализ поисковых запросов
        Формат: количество | месяц | мин_выручка | мин_частота
        """
        try:
            # Парсим дату
            start_date, end_date = self._parse_month(month)
            
            logger.info(f"Запрос Oracle: {queries_count} запросов за {month}")
            
            # Получаем топ категории для анализа популярных товаров
            popular_categories = await self._get_popular_categories(start_date, end_date)
            
            if not popular_categories:
                return {"error": "Не удалось получить данные по категориям"}
            
            # Анализируем товары в популярных категориях
            results = []
            for category in popular_categories[:queries_count]:
                category_data = await self._get_category_data(category, start_date, end_date)
                if category_data and category_data.get('data'):
                    # Фильтруем по критериям
                    filtered_products = self._filter_products(
                        category_data['data'], 
                        min_revenue, 
                        min_frequency
                    )
                    
                    if filtered_products:
                        analysis = self._analyze_category_products(filtered_products, category)
                        if analysis['total_revenue'] >= min_revenue:
                            results.append(analysis)
            
            return {
                "results": results[:queries_count],
                "total_found": len(results),
                "period": f"{start_date} - {end_date}",
                "criteria": f"мин. выручка: {min_revenue}₽, мин. частота: {min_frequency}"
            }
            
        except Exception as e:
            logger.error(f"Ошибка в get_search_queries_data: {e}")
            return {"error": f"Ошибка анализа: {str(e)}"}

    async def get_category_analysis(self, 
                                  query: str, 
                                  month: str, 
                                  analysis_type: str) -> Dict[str, Any]:
        """
        Анализ по категориям
        Типы: products, brands, suppliers, categories, queries
        """
        try:
            start_date, end_date = self._parse_month(month)
            
            logger.info(f"Анализ категории {analysis_type}: {query} за {month}")
            
            if analysis_type == "categories":
                # Поиск категории по названию
                category_path = await self._find_category_path(query)
                if not category_path:
                    return {"error": f"Категория '{query}' не найдена"}
                
                category_data = await self._get_category_data(category_path, start_date, end_date)
                if not category_data or not category_data.get('data'):
                    return {"error": "Данные по категории не найдены"}
                
                return self._analyze_category_detailed(category_data['data'], query, analysis_type)
            
            else:
                # Для других типов анализа ищем в популярных категориях
                return await self._search_across_categories(query, start_date, end_date, analysis_type)
                
        except Exception as e:
            logger.error(f"Ошибка в get_category_analysis: {e}")
            return {"error": f"Ошибка анализа категории: {str(e)}"}

    async def _get_popular_categories(self, start_date: str, end_date: str) -> List[str]:
        """Получает список популярных категорий"""
        try:
            headers = {
                "X-Mpstats-TOKEN": self.api_key,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*"
            }
            
            # Список основных категорий для анализа
            main_categories = [
                "Женщинам/Одежда",
                "Мужчинам/Одежда", 
                "Электроника",
                "Красота",
                "Дом/Товары для дома",
                "Спорт",
                "Детям",
                "Автотовары",
                "Обувь/Женская обувь",
                "Обувь/Мужская обувь"
            ]
            
            return main_categories
            
        except Exception as e:
            logger.error(f"Ошибка получения популярных категорий: {e}")
            return []

    async def _get_category_data(self, category_path: str, start_date: str, end_date: str) -> Dict[str, Any]:
        """Получает данные по конкретной категории"""
        try:
            headers = {
                "X-Mpstats-TOKEN": self.api_key,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*"
            }
            
            params = {
                "d1": start_date,
                "d2": end_date,
                "path": category_path
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.category_url,
                    headers=headers,
                    params=params
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        logger.info(f"Получены данные для категории {category_path}: {len(data.get('data', []))} товаров")
                        return data
                    else:
                        logger.error(f"Ошибка API для категории {category_path}: {response.status}")
                        return {}
                        
        except Exception as e:
            logger.error(f"Ошибка получения данных категории {category_path}: {e}")
            return {}

    async def _find_category_path(self, query: str) -> Optional[str]:
        """Находит путь к категории по названию"""
        try:
            headers = {
                "X-Mpstats-TOKEN": self.api_key,
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                "Accept": "application/json, text/plain, */*"
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    self.categories_list_url,
                    headers=headers
                ) as response:
                    if response.status == 200:
                        categories = await response.json()
                        
                        # Поиск категории по названию
                        query_lower = query.lower()
                        for category in categories:
                            if isinstance(category, dict) and 'path' in category:
                                if query_lower in category['path'].lower():
                                    return category['path']
                                    
                        # Если точного совпадения нет, ищем частичные совпадения
                        for category in categories:
                            if isinstance(category, dict) and 'path' in category:
                                path_parts = category['path'].lower().split('/')
                                if any(query_lower in part for part in path_parts):
                                    return category['path']
                    
            return None
            
        except Exception as e:
            logger.error(f"Ошибка поиска категории {query}: {e}")
            return None

    async def _search_across_categories(self, query: str, start_date: str, end_date: str, analysis_type: str) -> Dict[str, Any]:
        """Поиск по всем популярным категориям"""
        try:
            results = []
            popular_categories = await self._get_popular_categories(start_date, end_date)
            
            for category_path in popular_categories[:5]:  # Ограничиваем поиск топ-5 категориями
                category_data = await self._get_category_data(category_path, start_date, end_date)
                if category_data and category_data.get('data'):
                    # Ищем по критериям в зависимости от типа анализа
                    found_items = self._search_in_category_data(category_data['data'], query, analysis_type)
                    if found_items:
                        results.extend(found_items)
            
            # Группируем и сортируем результаты
            grouped_results = self._group_search_results(results, analysis_type)
            
            return {
                "results": grouped_results[:15],  # Топ-15 результатов
                "total_found": len(grouped_results),
                "search_query": query,
                "analysis_type": analysis_type,
                "period": f"{start_date} - {end_date}"
            }
            
        except Exception as e:
            logger.error(f"Ошибка поиска по категориям: {e}")
            return {"error": f"Ошибка поиска: {str(e)}"}

    def _search_in_category_data(self, products: List[Dict], query: str, analysis_type: str) -> List[Dict]:
        """Поиск в данных категории по типу анализа"""
        results = []
        query_lower = query.lower()
        
        for product in products:
            match_found = False
            
            if analysis_type == "products":
                # Поиск в названии товара
                if query_lower in product.get('name', '').lower():
                    match_found = True
            elif analysis_type == "brands":
                # Поиск по бренду
                if query_lower in product.get('brand', '').lower():
                    match_found = True
            elif analysis_type == "suppliers":
                # Поиск по поставщику
                if query_lower in product.get('seller', '').lower():
                    match_found = True
            elif analysis_type == "queries":
                # Поиск по ключевым словам (в названии и описании)
                if (query_lower in product.get('name', '').lower() or 
                    query_lower in product.get('subject', '').lower()):
                    match_found = True
            
            if match_found:
                results.append({
                    'name': product.get('name', ''),
                    'brand': product.get('brand', ''),
                    'seller': product.get('seller', ''),
                    'revenue': product.get('revenue', 0),
                    'sales': product.get('sales', 0),
                    'price': product.get('final_price', 0),
                    'category': product.get('category', ''),
                    'rating': product.get('rating', 0),
                    'comments': product.get('comments', 0)
                })
        
        return results

    def _group_search_results(self, results: List[Dict], analysis_type: str) -> List[Dict]:
        """Группирует результаты поиска по типу анализа"""
        if not results:
            return []
        
        if analysis_type == "brands":
            # Группируем по брендам
            brands = {}
            for item in results:
                brand = item['brand']
                if brand not in brands:
                    brands[brand] = {
                        'name': brand,
                        'total_revenue': 0,
                        'total_sales': 0,
                        'products_count': 0,
                        'avg_price': 0
                    }
                brands[brand]['total_revenue'] += item['revenue']
                brands[brand]['total_sales'] += item['sales']
                brands[brand]['products_count'] += 1
                brands[brand]['avg_price'] = brands[brand]['total_revenue'] / brands[brand]['total_sales'] if brands[brand]['total_sales'] > 0 else 0
            
            return sorted(brands.values(), key=lambda x: x['total_revenue'], reverse=True)
            
        elif analysis_type == "suppliers":
            # Группируем по поставщикам
            suppliers = {}
            for item in results:
                supplier = item['seller']
                if supplier not in suppliers:
                    suppliers[supplier] = {
                        'name': supplier,
                        'total_revenue': 0,
                        'total_sales': 0,
                        'products_count': 0,
                        'avg_price': 0
                    }
                suppliers[supplier]['total_revenue'] += item['revenue']
                suppliers[supplier]['total_sales'] += item['sales']
                suppliers[supplier]['products_count'] += 1
                suppliers[supplier]['avg_price'] = suppliers[supplier]['total_revenue'] / suppliers[supplier]['total_sales'] if suppliers[supplier]['total_sales'] > 0 else 0
            
            return sorted(suppliers.values(), key=lambda x: x['total_revenue'], reverse=True)
        
        else:
            # Для товаров и запросов - сортируем по выручке
            return sorted(results, key=lambda x: x['revenue'], reverse=True)

    def _filter_products(self, products: List[Dict], min_revenue: int, min_frequency: int) -> List[Dict]:
        """Фильтрует товары по критериям"""
        filtered = []
        for product in products:
            revenue = product.get('revenue', 0)
            sales = product.get('sales', 0)
            
            if revenue >= min_revenue and sales >= min_frequency:
                filtered.append(product)
        
        return filtered

    def _analyze_category_products(self, products: List[Dict], category: str) -> Dict[str, Any]:
        """Анализирует товары в категории"""
        if not products:
            return {}
        
        total_revenue = sum(p.get('revenue', 0) for p in products)
        total_sales = sum(p.get('sales', 0) for p in products)
        avg_price = total_revenue / total_sales if total_sales > 0 else 0
        
        # Топ-3 товара по выручке
        top_products = sorted(products, key=lambda x: x.get('revenue', 0), reverse=True)[:3]
        
        # Анализ монополизации
        top_3_revenue = sum(p.get('revenue', 0) for p in top_products)
        monopoly_level = (top_3_revenue / total_revenue * 100) if total_revenue > 0 else 0
        
        # Процент рекламы (товары с высокими позициями)
        ad_products = [p for p in products if p.get('search_position_avg', 0) > 0]
        ad_percentage = (len(ad_products) / len(products) * 100) if products else 0
        
        return {
            'category': category,
            'products_count': len(products),
            'total_revenue': total_revenue,
            'total_sales': total_sales,
            'avg_price': avg_price,
            'monopoly_level': monopoly_level,
            'ad_percentage': ad_percentage,
            'top_products': [
                {
                    'name': p.get('name', '')[:50] + '...' if len(p.get('name', '')) > 50 else p.get('name', ''),
                    'brand': p.get('brand', ''),
                    'revenue': p.get('revenue', 0),
                    'sales': p.get('sales', 0),
                    'price': p.get('final_price', 0)
                } for p in top_products
            ]
        }

    def _analyze_category_detailed(self, products: List[Dict], category_name: str, analysis_type: str) -> Dict[str, Any]:
        """Детальный анализ категории"""
        if not products:
            return {"error": "Нет данных для анализа"}
        
        # Сортируем по выручке
        sorted_products = sorted(products, key=lambda x: x.get('revenue', 0), reverse=True)
        top_15 = sorted_products[:15]
        
        results = []
        for product in top_15:
            lost_revenue = product.get('lost_profit', 0)
            results.append({
                'name': product.get('name', '')[:50] + '...' if len(product.get('name', '')) > 50 else product.get('name', ''),
                'brand': product.get('brand', ''),
                'revenue': product.get('revenue', 0),
                'lost_revenue': lost_revenue,
                'orders': product.get('sales', 0),
                'price': product.get('final_price', 0),
                'rating': product.get('rating', 0)
            })
        
        total_revenue = sum(p.get('revenue', 0) for p in products)
        total_orders = sum(p.get('sales', 0) for p in products)
        
        return {
            'category': category_name,
            'analysis_type': analysis_type,
            'total_products': len(products),
            'total_revenue': total_revenue,
            'total_orders': total_orders,
            'top_15': results
        }

    def _parse_month(self, month_str: str) -> Tuple[str, str]:
        """Парсит месяц в формате YYYY-MM или MM.YYYY в даты"""
        try:
            if '-' in month_str:
                year, month = month_str.split('-')
            elif '.' in month_str:
                month, year = month_str.split('.')
            else:
                # Если только год
                if len(month_str) == 4:
                    year = month_str
                    month = "01"
                else:
                    raise ValueError("Неверный формат месяца")
            
            year = int(year)
            month = int(month)
            
            # Получаем первый и последний день месяца
            first_day = datetime(year, month, 1)
            last_day_num = monthrange(year, month)[1]
            last_day = datetime(year, month, last_day_num)
            
            return first_day.strftime('%Y-%m-%d'), last_day.strftime('%Y-%m-%d')
            
        except Exception as e:
            logger.error(f"Ошибка парсинга даты {month_str}: {e}")
            # Возвращаем текущий месяц по умолчанию
            now = datetime.now()
            first_day = datetime(now.year, now.month, 1)
            last_day_num = monthrange(now.year, now.month)[1]
            last_day = datetime(now.year, now.month, last_day_num)
            return first_day.strftime('%Y-%m-%d'), last_day.strftime('%Y-%m-%d')

def format_oracle_results(data: Dict[str, Any], analysis_type: str = "main") -> str:
    """Форматирует результаты анализа Oracle"""
    
    if "error" in data:
        return f"❌ {data['error']}"
    
    if analysis_type == "main":
        return _format_main_analysis(data)
    else:
        return _format_category_analysis(data)

def _format_main_analysis(data: Dict[str, Any]) -> str:
    """Форматирует основной анализ"""
    if not data.get('results'):
        return f"🔮 Оракул по запросам\n\n📅 Период: {data.get('period', '')}\n📊 Найдено: 0\n\n❌ Данные не найдены."
    
    message = f"🔮 Оракул по запросам\n\n"
    message += f"📅 Период: {data.get('period', '')}\n"
    message += f"📊 Найдено: {len(data['results'])}\n"
    message += f"🔍 Критерии: {data.get('criteria', '')}\n\n"
    
    for i, result in enumerate(data['results'][:5], 1):
        message += f"🏆 {i}. Категория: {result['category']}\n"
        message += f"💰 Выручка: {result['total_revenue']:,.0f}₽\n"
        message += f"📦 Продаж: {result['total_sales']:,.0f}\n"
        message += f"💵 Средняя цена: {result['avg_price']:,.0f}₽\n"
        message += f"🎯 Монополизация: {result['monopoly_level']:.1f}%\n"
        message += f"📢 Реклама: {result['ad_percentage']:.1f}%\n"
        
        if result.get('top_products'):
            message += "🔝 Топ товары:\n"
            for j, product in enumerate(result['top_products'][:3], 1):
                message += f"  {j}. {product['name']} - {product['revenue']:,.0f}₽\n"
        
        message += "\n"
    
    return message

def _format_category_analysis(data: Dict[str, Any]) -> str:
    """Форматирует анализ по категории"""
    if not data.get('results') and not data.get('top_15'):
        return f"🔮 Оракул по категории\n\n📅 Период: {data.get('period', '')}\n📊 Найдено: 0\n\n❌ Данные не найдены."
    
    message = f"🔮 Оракул по категории\n\n"
    
    if data.get('results'):
        # Анализ поиска
        message += f"🔍 Запрос: {data.get('search_query', '')}\n"
        message += f"📊 Тип: {data.get('analysis_type', '')}\n"
        message += f"📅 Период: {data.get('period', '')}\n"
        message += f"📈 Найдено: {len(data['results'])}\n\n"
        
        for i, item in enumerate(data['results'][:10], 1):
            if data.get('analysis_type') in ['brands', 'suppliers']:
                message += f"{i}. {item['name']}\n"
                message += f"💰 Выручка: {item['total_revenue']:,.0f}₽\n"
                message += f"📦 Продаж: {item['total_sales']:,.0f}\n"
                message += f"🏪 Товаров: {item['products_count']}\n\n"
            else:
                message += f"{i}. {item['name']}\n"
                message += f"🏷️ Бренд: {item['brand']}\n"
                message += f"💰 Выручка: {item['revenue']:,.0f}₽\n"
                message += f"📦 Продаж: {item['sales']:,.0f}\n\n"
    
    elif data.get('top_15'):
        # Детальный анализ категории
        message += f"📂 Категория: {data.get('category', '')}\n"
        message += f"📅 Период: {data.get('period', '')}\n"
        message += f"📊 Товаров всего: {data.get('total_products', 0)}\n"
        message += f"💰 Общая выручка: {data.get('total_revenue', 0):,.0f}₽\n"
        message += f"📦 Заказов: {data.get('total_orders', 0):,.0f}\n\n"
        
        message += "🏆 Топ-15 товаров:\n\n"
        for i, item in enumerate(data['top_15'], 1):
            message += f"{i}. {item['name']}\n"
            message += f"🏷️ {item['brand']}\n"
            message += f"💰 {item['revenue']:,.0f}₽ | 📦 {item['orders']:,.0f}\n"
            if item.get('lost_revenue', 0) > 0:
                message += f"📉 Упущено: {item['lost_revenue']:,.0f}₽\n"
            message += "\n"
    
    return message 