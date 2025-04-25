from typing import List, Dict, Optional
from dataclasses import dataclass
import numpy as np

@dataclass
class ProductSearchCriteria:
    min_sales: int = 10
    max_competition: float = 0.5
    min_margin: float = 30.0
    min_rating: float = 4.0
    min_reviews: int = 10

@dataclass
class ProductSearchResult:
    article: str
    name: str
    price: float
    sales: int
    margin: float
    competition_index: float
    rating: float
    reviews: int
    score: float

class ProfitableProductFinder:
    def __init__(self):
        self.wb_commission = 0.15
    
    async def search_products(self, criteria: ProductSearchCriteria) -> List[ProductSearchResult]:
        """Поиск прибыльных товаров по заданным критериям"""
        try:
            # Получаем список товаров (заглушка)
            products = await self._get_products()
            
            # Фильтруем товары по критериям
            filtered_products = []
            for product in products:
                if (product['sales'] >= criteria.min_sales and
                    product['competition_index'] <= criteria.max_competition and
                    self._calculate_margin(product) >= criteria.min_margin and
                    product['rating'] >= criteria.min_rating and
                    product['reviews'] >= criteria.min_reviews):
                    
                    # Рассчитываем общий скор товара
                    score = self._calculate_product_score(product)
                    
                    filtered_products.append(
                        ProductSearchResult(
                            article=product['article'],
                            name=product['name'],
                            price=product['price'],
                            sales=product['sales'],
                            margin=self._calculate_margin(product),
                            competition_index=product['competition_index'],
                            rating=product['rating'],
                            reviews=product['reviews'],
                            score=score
                        )
                    )
            
            # Сортируем по скору
            filtered_products.sort(key=lambda x: x.score, reverse=True)
            
            return filtered_products[:50]  # Возвращаем топ-50 товаров
            
        except Exception as e:
            raise Exception(f"Ошибка при поиске товаров: {str(e)}")
    
    def _calculate_margin(self, product: Dict) -> float:
        """Расчет маржинальности товара"""
        price = product['price']
        cost = price * 0.5  # Примерная себестоимость 50% от цены
        revenue = price * (1 - self.wb_commission)
        margin = ((revenue - cost) / price) * 100
        return margin
    
    def _calculate_product_score(self, product: Dict) -> float:
        """Расчет общего скора товара"""
        # Веса для разных метрик
        weights = {
            'sales': 0.4,
            'margin': 0.3,
            'rating': 0.2,
            'competition': 0.1
        }
        
        # Нормализуем метрики
        normalized_sales = min(1.0, product['sales'] / 100)  # Максимум 100 продаж в день
        normalized_margin = self._calculate_margin(product) / 100
        normalized_rating = product['rating'] / 5
        normalized_competition = 1 - product['competition_index']  # Меньше конкуренция - лучше
        
        # Считаем взвешенный скор
        score = (
            weights['sales'] * normalized_sales +
            weights['margin'] * normalized_margin +
            weights['rating'] * normalized_rating +
            weights['competition'] * normalized_competition
        )
        
        return score
    
    async def _get_products(self) -> List[Dict]:
        """Получение списка товаров (заглушка)"""
        # TODO: Реализовать реальный парсинг WB
        return []
    
    async def get_category_stats(self, products: List[ProductSearchResult]) -> Dict:
        """Получение статистики по найденным товарам"""
        if not products:
            return {
                "count": 0,
                "avg_price": 0,
                "avg_sales": 0,
                "avg_margin": 0,
                "total_revenue": 0
            }
        
        prices = [p.price for p in products]
        sales = [p.sales for p in products]
        margins = [p.margin for p in products]
        
        return {
            "count": len(products),
            "avg_price": np.mean(prices),
            "avg_sales": np.mean(sales),
            "avg_margin": np.mean(margins),
            "total_revenue": sum(p.price * p.sales for p in products)
        } 