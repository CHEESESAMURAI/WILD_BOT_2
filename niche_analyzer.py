import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass

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
        
    async def analyze_niche(self, keyword: str, days: int = 30) -> NicheAnalysisResult:
        """Анализ ниши по ключевому слову"""
        try:
            # Получаем товары из категории (заглушка, нужно реализовать)
            products = await self._get_products_by_keyword(keyword)
            
            # Базовые метрики
            prices = [p['price'] for p in products]
            daily_sales = [p['daily_sales'] for p in products]
            sellers = set(p['seller'] for p in products)
            brands = set(p['brand'] for p in products)
            
            # Расчет метрик
            total_sales = sum(daily_sales)
            avg_price = np.mean(prices)
            median_price = np.median(prices)
            
            # Объем продаж
            daily_volume = sum(p['price'] * p['daily_sales'] for p in products)
            weekly_volume = daily_volume * 7
            monthly_volume = daily_volume * 30
            
            # Конкуренция и маржинальность
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
            
        except Exception as e:
            raise Exception(f"Ошибка при анализе ниши: {str(e)}")
    
    async def _get_products_by_keyword(self, keyword: str) -> List[Dict]:
        """Получение товаров по ключевому слову (заглушка)"""
        # TODO: Реализовать реальный парсинг WB
        return []
    
    def _calculate_average_margin(self, products: List[Dict]) -> float:
        """Расчет средней маржинальности"""
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