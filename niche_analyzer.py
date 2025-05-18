import numpy as np
import matplotlib.pyplot as plt
import tempfile
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
import asyncio
import aiohttp
from datetime import datetime, timedelta
import json

@dataclass
class NicheAnalysisResult:
    total_sales: float
    avg_price: float
    median_price: float
    sellers_count: int
    brands_count: int
    competition_index: float
    margin_estimate: float
    products_count: int
    daily_sales_volume: float
    weekly_sales_volume: float
    monthly_sales_volume: float

class NicheAnalyzer:
    def __init__(self):
        self.wb_commission = 0.15  # стандартная комиссия WB
        self._session = None
        self.cache = {}
        self.cache_timeout = 3600  # 1 час
    
    @property
    def session(self):
        if self._session is None:
            self._session = aiohttp.ClientSession()
        return self._session
    
    async def analyze_category(self, category_name: str) -> Dict:
        """Анализирует категорию и возвращает полный отчет с графиками"""
        try:
            # Получаем данные о товарах в категории
            products = await self._get_category_products(category_name)
            if not products:
                return None
            
            # Анализируем данные
            analysis = self._analyze_products(products)
            
            # Создаем графики
            charts = {
                'price_distribution': self._create_price_distribution_chart(products),
                'sales_volume': self._create_sales_volume_chart(products),
                'competition': self._create_competition_chart(analysis)
            }
            
            # Формируем рекомендации
            recommendations = self._generate_recommendations(analysis)
            
            # Формируем итоговый отчет
            return {
                'market_volume': analysis.monthly_sales_volume,
                'products_count': analysis.products_count,
                'avg_price': analysis.avg_price,
                'avg_rating': self._calculate_average_rating(products),
                'trends': {
                    'sales_trend': self._analyze_sales_trend(products),
                    'potential': self._assess_potential(analysis)
                },
                'risks': self._identify_risks(analysis),
                'recommendations': recommendations,
                'charts': charts
            }
            
        except Exception as e:
            print(f"Error analyzing category: {str(e)}")
            return None
    
    def _analyze_products(self, products: List[Dict]) -> NicheAnalysisResult:
        """Анализирует список товаров и возвращает метрики"""
        prices = [p['price'] for p in products]
        daily_sales = [p['daily_sales'] for p in products]
        sellers = set(p['seller'] for p in products)
        brands = set(p['brand'] for p in products)
        
        total_sales = sum(daily_sales)
        avg_price = np.mean(prices)
        median_price = np.median(prices)
        
        daily_volume = sum(p['price'] * p['daily_sales'] for p in products)
        weekly_volume = daily_volume * 7
        monthly_volume = daily_volume * 30
        
        competition_index = len(sellers) / (total_sales if total_sales > 0 else 1)
        avg_margin = self._calculate_average_margin(products)
        
        return NicheAnalysisResult(
            total_sales=total_sales,
            avg_price=avg_price,
            median_price=median_price,
            sellers_count=len(sellers),
            brands_count=len(brands),
            competition_index=competition_index,
            margin_estimate=avg_margin,
            products_count=len(products),
            daily_sales_volume=daily_volume,
            weekly_sales_volume=weekly_volume,
            monthly_sales_volume=monthly_volume
        )
    
    def _create_price_distribution_chart(self, products: List[Dict]) -> str:
        """Создает график распределения цен"""
        prices = [p['price'] for p in products]
        
        plt.figure(figsize=(10, 6))
        plt.hist(prices, bins=20, edgecolor='black')
        plt.title('Распределение цен в категории')
        plt.xlabel('Цена (₽)')
        plt.ylabel('Количество товаров')
        plt.grid(True)
        
        # Сохраняем график во временный файл
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        plt.savefig(temp_file.name)
        plt.close()
        
        return temp_file.name
    
    def _create_sales_volume_chart(self, products: List[Dict]) -> str:
        """Создает график объема продаж"""
        # Группируем продажи по месяцам
        monthly_sales = {}
        for product in products:
            date = datetime.strptime(product['date'], '%Y-%m-%d')
            month_key = date.strftime('%Y-%m')
            if month_key not in monthly_sales:
                monthly_sales[month_key] = 0
            monthly_sales[month_key] += product['daily_sales'] * product['price']
        
        months = sorted(monthly_sales.keys())
        sales = [monthly_sales[m] for m in months]
        
        plt.figure(figsize=(10, 6))
        plt.plot(months, sales, marker='o')
        plt.title('Объем продаж по месяцам')
        plt.xlabel('Месяц')
        plt.ylabel('Объем продаж (₽)')
        plt.xticks(rotation=45)
        plt.grid(True)
        
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        plt.savefig(temp_file.name)
        plt.close()
        
        return temp_file.name
    
    def _create_competition_chart(self, analysis: NicheAnalysisResult) -> str:
        """Создает график уровня конкуренции"""
        metrics = {
            'Количество продавцов': analysis.sellers_count,
            'Количество брендов': analysis.brands_count,
            'Индекс конкуренции': analysis.competition_index
        }
        
        plt.figure(figsize=(10, 6))
        plt.bar(metrics.keys(), metrics.values())
        plt.title('Метрики конкуренции')
        plt.xticks(rotation=45)
        plt.grid(True)
        
        temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
        plt.savefig(temp_file.name)
        plt.close()
        
        return temp_file.name
    
    def _generate_recommendations(self, analysis: NicheAnalysisResult) -> List[str]:
        """Генерирует рекомендации на основе анализа"""
        recommendations = []
        
        # Анализ конкуренции
        if analysis.competition_index > 0.5:
            recommendations.append("Высокий уровень конкуренции - рекомендуется найти нишу с меньшей конкуренцией")
        elif analysis.competition_index < 0.2:
            recommendations.append("Низкий уровень конкуренции - хорошая возможность для входа в нишу")
        
        # Анализ маржинальности
        if analysis.margin_estimate > 0.3:
            recommendations.append("Высокая маржинальность - хороший потенциал для прибыли")
        elif analysis.margin_estimate < 0.1:
            recommendations.append("Низкая маржинальность - рекомендуется искать более маржинальные товары")
        
        # Анализ объема рынка
        if analysis.monthly_sales_volume > 10000000:
            recommendations.append("Большой объем рынка - хорошие перспективы для роста")
        elif analysis.monthly_sales_volume < 1000000:
            recommendations.append("Небольшой объем рынка - рекомендуется проверить потенциал роста")
        
        return recommendations
    
    def _identify_risks(self, analysis: NicheAnalysisResult) -> List[str]:
        """Определяет риски на основе анализа"""
        risks = []
        
        if analysis.competition_index > 0.7:
            risks.append("Очень высокая конкуренция")
        if analysis.margin_estimate < 0.1:
            risks.append("Низкая маржинальность")
        if analysis.sellers_count > 1000:
            risks.append("Перенасыщение рынка")
        if analysis.monthly_sales_volume < 500000:
            risks.append("Небольшой объем рынка")
        
        return risks
    
    def _analyze_sales_trend(self, products: List[Dict]) -> str:
        """Анализирует тренд продаж"""
        # Простая логика определения тренда
        if len(products) > 1000:
            return "Растущий"
        elif len(products) > 500:
            return "Стабильный"
        else:
            return "Снижающийся"
    
    def _assess_potential(self, analysis: NicheAnalysisResult) -> str:
        """Оценивает потенциал ниши"""
        if analysis.monthly_sales_volume > 10000000 and analysis.margin_estimate > 0.2:
            return "Высокий"
        elif analysis.monthly_sales_volume > 5000000 and analysis.margin_estimate > 0.15:
            return "Средний"
        else:
            return "Низкий"
    
    def _calculate_average_rating(self, products: List[Dict]) -> float:
        """Рассчитывает средний рейтинг товаров"""
        ratings = [p.get('rating', 0) for p in products if p.get('rating')]
        return np.mean(ratings) if ratings else 0.0
    
    async def _get_category_products(self, category_name: str) -> List[Dict]:
        """Получает товары из категории"""
        # TODO: Реализовать реальный парсинг WB
        # Временная заглушка для тестирования
        return [
            {
                'price': 1000,
                'daily_sales': 10,
                'seller': 'Seller1',
                'brand': 'Brand1',
                'rating': 4.5,
                'date': '2024-03-01'
            },
            # ... больше тестовых данных
        ]
    
    def _calculate_average_margin(self, products: List[Dict]) -> float:
        """Рассчитывает среднюю маржинальность"""
        margins = []
        for product in products:
            price = product['price']
            cost = price * 0.5  # Примерная себестоимость 50% от цены
            revenue = price * (1 - self.wb_commission)
            margin = revenue - cost
            margins.append(margin)
        return np.mean(margins) if margins else 0.0

    async def get_niche_trends(self, keyword: str, period_days: int = 30) -> Dict:
        """Анализ трендов в нише"""
        try:
            products = await self._get_products_by_keyword(keyword)
            
            # Расчет трендов (заглушка)
            growth_rate = 0.0
            seasonality_index = 1.0
            stability_score = 0.8
            
            return {
                "growth_rate": growth_rate,
                "seasonality_index": seasonality_index,
                "stability_score": stability_score,
                "is_growing": growth_rate > 0,
                "risk_level": "Средний" if stability_score > 0.5 else "Высокий"
            }
            
        except Exception as e:
            raise Exception(f"Ошибка при анализе трендов: {str(e)}") 