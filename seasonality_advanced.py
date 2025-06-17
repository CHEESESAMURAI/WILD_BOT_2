#!/usr/bin/env python3
"""
Расширенная аналитическая модель для анализа сезонности
Включает детальные данные по всем категориям, праздникам, региональным особенностям и трендам
"""

import logging
import random
from datetime import datetime, timedelta
import math

logger = logging.getLogger(__name__)

class AdvancedSeasonalityAnalyzer:
    """Продвинутый анализатор сезонности"""
    
    def __init__(self):
        self.russian_holidays = {
            1: [1, 2, 3, 4, 5, 6, 7, 8],  # Новогодние каникулы
            2: [23],  # День защитника Отечества
            3: [8],   # Международный женский день
            5: [1, 9], # Праздник Весны и Труда, День Победы
            6: [12],  # День России
            11: [4],  # День народного единства
        }
        
        self.regional_coefficients = {
            'moscow': 1.2,      # Москва - повышенная покупательская способность
            'spb': 1.15,        # СПб - высокая покупательская способность
            'regions': 1.0,     # Регионы - базовый уровень
            'south': 0.95,      # Юг - немного ниже среднего
            'siberia': 0.9,     # Сибирь - ниже среднего
            'far_east': 0.85    # Дальний Восток - самый низкий
        }
        
        self.weather_impact = {
            'winter_clothing': {'12': 1.4, '1': 1.5, '2': 1.3, '3': 0.8},
            'summer_clothing': {'5': 1.2, '6': 1.4, '7': 1.5, '8': 1.3},
            'home_garden': {'3': 1.1, '4': 1.4, '5': 1.5, '6': 1.3, '7': 1.2},
            'toys_outdoor': {'5': 1.2, '6': 1.4, '7': 1.5, '8': 1.3, '9': 0.8}
        }

    async def get_advanced_seasonality_data(self, category_path):
        """Получение расширенных данных сезонности"""
        try:
            category_lower = category_path.lower()
            
            # Определяем тип категории
            category_type = self._determine_category_type(category_lower)
            
            # Получаем базовые паттерны
            base_pattern = self._get_base_patterns()[category_type]
            
            # Применяем модификаторы
            enhanced_annual = self._enhance_annual_data(base_pattern['annual'], category_type)
            enhanced_weekly = self._enhance_weekly_data(base_pattern['weekly'], category_type)
            
            # Добавляем дополнительную аналитику
            trend_analysis = self._generate_trend_analysis(category_type)
            competitive_analysis = self._generate_competitive_analysis(category_type)
            price_recommendations = self._generate_price_recommendations(enhanced_annual)
            marketing_calendar = self._generate_marketing_calendar(enhanced_annual, category_type)
            regional_insights = self._generate_regional_insights(category_type)
            
            return {
                'annual': enhanced_annual,
                'weekly': enhanced_weekly,
                'trend_analysis': trend_analysis,
                'competitive_analysis': competitive_analysis,
                'price_recommendations': price_recommendations,
                'marketing_calendar': marketing_calendar,
                'regional_insights': regional_insights,
                'category_type': category_type
            }
            
        except Exception as e:
            logger.error(f"Error in advanced seasonality analysis: {str(e)}")
            return None

    def _determine_category_type(self, category_lower):
        """Определение типа категории"""
        if any(word in category_lower for word in ['дет', 'ребен', 'малыш']):
            return 'children'
        elif any(word in category_lower for word in ['игрушк', 'игры']):
            return 'toys'
        elif any(word in category_lower for word in ['женщ', 'девочк', 'леди']):
            return 'women'
        elif any(word in category_lower for word in ['мужч', 'мальчик']):
            return 'men'
        elif any(word in category_lower for word in ['одежд', 'обув', 'аксесс']):
            return 'fashion'
        elif any(word in category_lower for word in ['дом', 'дач', 'сад', 'быт']):
            return 'home_garden'
        elif any(word in category_lower for word in ['красот', 'косметик', 'парфюм']):
            return 'beauty'
        elif any(word in category_lower for word in ['спорт', 'фитнес', 'туризм']):
            return 'sports'
        elif any(word in category_lower for word in ['электрон', 'гаджет', 'техник']):
            return 'electronics'
        elif any(word in category_lower for word in ['автомобил', 'мото', 'запчаст']):
            return 'auto'
        else:
            return 'general'

    def _get_base_patterns(self):
        """Базовые паттерны сезонности для категорий"""
        return {
            'children': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'base_revenue': -10, 'sales_volume': -8, 'avg_price': 102},
                    {'month': 2, 'name': 'Февраль', 'base_revenue': -5, 'sales_volume': -3, 'avg_price': 98},
                    {'month': 3, 'name': 'Март', 'base_revenue': 15, 'sales_volume': 18, 'avg_price': 105},
                    {'month': 4, 'name': 'Апрель', 'base_revenue': 20, 'sales_volume': 22, 'avg_price': 103},
                    {'month': 5, 'name': 'Май', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 101},
                    {'month': 6, 'name': 'Июнь', 'base_revenue': 30, 'sales_volume': 35, 'avg_price': 99},
                    {'month': 7, 'name': 'Июль', 'base_revenue': 35, 'sales_volume': 40, 'avg_price': 97},
                    {'month': 8, 'name': 'Август', 'base_revenue': 60, 'sales_volume': 65, 'avg_price': 108},
                    {'month': 9, 'name': 'Сентябрь', 'base_revenue': 45, 'sales_volume': 50, 'avg_price': 106},
                    {'month': 10, 'name': 'Октябрь', 'base_revenue': 10, 'sales_volume': 12, 'avg_price': 102},
                    {'month': 11, 'name': 'Ноябрь', 'base_revenue': 25, 'sales_volume': 30, 'avg_price': 104},
                    {'month': 12, 'name': 'Декабрь', 'base_revenue': 55, 'sales_volume': 60, 'avg_price': 110}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'revenue': -5, 'sales': -3, 'traffic': -8},
                    {'day': 'Вторник', 'revenue': 0, 'sales': 2, 'traffic': -2},
                    {'day': 'Среда', 'revenue': 5, 'sales': 8, 'traffic': 5},
                    {'day': 'Четверг', 'revenue': 10, 'sales': 15, 'traffic': 12},
                    {'day': 'Пятница', 'revenue': 20, 'sales': 25, 'traffic': 22},
                    {'day': 'Суббота', 'revenue': 40, 'sales': 45, 'traffic': 50},
                    {'day': 'Воскресенье', 'revenue': 30, 'sales': 35, 'traffic': 40}
                ]
            },
            'toys': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'base_revenue': -30, 'sales_volume': -25, 'avg_price': 95},
                    {'month': 2, 'name': 'Февраль', 'base_revenue': -20, 'sales_volume': -15, 'avg_price': 97},
                    {'month': 3, 'name': 'Март', 'base_revenue': 10, 'sales_volume': 15, 'avg_price': 102},
                    {'month': 4, 'name': 'Апрель', 'base_revenue': 15, 'sales_volume': 20, 'avg_price': 100},
                    {'month': 5, 'name': 'Май', 'base_revenue': 20, 'sales_volume': 25, 'avg_price': 99},
                    {'month': 6, 'name': 'Июнь', 'base_revenue': 35, 'sales_volume': 40, 'avg_price': 98},
                    {'month': 7, 'name': 'Июль', 'base_revenue': 25, 'sales_volume': 30, 'avg_price': 96},
                    {'month': 8, 'name': 'Август', 'base_revenue': 20, 'sales_volume': 25, 'avg_price': 98},
                    {'month': 9, 'name': 'Сентябрь', 'base_revenue': 15, 'sales_volume': 20, 'avg_price': 100},
                    {'month': 10, 'name': 'Октябрь', 'base_revenue': 10, 'sales_volume': 15, 'avg_price': 101},
                    {'month': 11, 'name': 'Ноябрь', 'base_revenue': 30, 'sales_volume': 35, 'avg_price': 105},
                    {'month': 12, 'name': 'Декабрь', 'base_revenue': 80, 'sales_volume': 85, 'avg_price': 115}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'revenue': -8, 'sales': -5, 'traffic': -10},
                    {'day': 'Вторник', 'revenue': -3, 'sales': 0, 'traffic': -5},
                    {'day': 'Среда', 'revenue': 8, 'sales': 10, 'traffic': 8},
                    {'day': 'Четверг', 'revenue': 15, 'sales': 18, 'traffic': 15},
                    {'day': 'Пятница', 'revenue': 25, 'sales': 30, 'traffic': 28},
                    {'day': 'Суббота', 'revenue': 45, 'sales': 50, 'traffic': 55},
                    {'day': 'Воскресенье', 'revenue': 35, 'sales': 40, 'traffic': 45}
                ]
            },
            'women': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'base_revenue': -10, 'sales_volume': -8, 'avg_price': 98},
                    {'month': 2, 'name': 'Февраль', 'base_revenue': 15, 'sales_volume': 18, 'avg_price': 102},
                    {'month': 3, 'name': 'Март', 'base_revenue': 35, 'sales_volume': 40, 'avg_price': 108},
                    {'month': 4, 'name': 'Апрель', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 105},
                    {'month': 5, 'name': 'Май', 'base_revenue': 20, 'sales_volume': 22, 'avg_price': 103},
                    {'month': 6, 'name': 'Июнь', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 104},
                    {'month': 7, 'name': 'Июль', 'base_revenue': 15, 'sales_volume': 18, 'avg_price': 99},
                    {'month': 8, 'name': 'Август', 'base_revenue': 30, 'sales_volume': 32, 'avg_price': 106},
                    {'month': 9, 'name': 'Сентябрь', 'base_revenue': 40, 'sales_volume': 42, 'avg_price': 107},
                    {'month': 10, 'name': 'Октябрь', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 104},
                    {'month': 11, 'name': 'Ноябрь', 'base_revenue': 45, 'sales_volume': 48, 'avg_price': 109},
                    {'month': 12, 'name': 'Декабрь', 'base_revenue': 50, 'sales_volume': 52, 'avg_price': 112}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'revenue': -8, 'sales': -6, 'traffic': -10},
                    {'day': 'Вторник', 'revenue': -3, 'sales': -1, 'traffic': -3},
                    {'day': 'Среда', 'revenue': 8, 'sales': 12, 'traffic': 10},
                    {'day': 'Четверг', 'revenue': 15, 'sales': 18, 'traffic': 16},
                    {'day': 'Пятница', 'revenue': 30, 'sales': 35, 'traffic': 32},
                    {'day': 'Суббота', 'revenue': 40, 'sales': 45, 'traffic': 48},
                    {'day': 'Воскресенье', 'revenue': 20, 'sales': 25, 'traffic': 28}
                ]
            },
            'men': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'base_revenue': -15, 'sales_volume': -12, 'avg_price': 95},
                    {'month': 2, 'name': 'Февраль', 'base_revenue': 30, 'sales_volume': 35, 'avg_price': 108},
                    {'month': 3, 'name': 'Март', 'base_revenue': -5, 'sales_volume': -2, 'avg_price': 98},
                    {'month': 4, 'name': 'Апрель', 'base_revenue': 10, 'sales_volume': 12, 'avg_price': 102},
                    {'month': 5, 'name': 'Май', 'base_revenue': 15, 'sales_volume': 18, 'avg_price': 103},
                    {'month': 6, 'name': 'Июнь', 'base_revenue': 20, 'sales_volume': 22, 'avg_price': 104},
                    {'month': 7, 'name': 'Июль', 'base_revenue': 10, 'sales_volume': 12, 'avg_price': 101},
                    {'month': 8, 'name': 'Август', 'base_revenue': 15, 'sales_volume': 18, 'avg_price': 102},
                    {'month': 9, 'name': 'Сентябрь', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 105},
                    {'month': 10, 'name': 'Октябрь', 'base_revenue': 20, 'sales_volume': 22, 'avg_price': 104},
                    {'month': 11, 'name': 'Ноябрь', 'base_revenue': 35, 'sales_volume': 38, 'avg_price': 107},
                    {'month': 12, 'name': 'Декабрь', 'base_revenue': 40, 'sales_volume': 42, 'avg_price': 109}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'revenue': -12, 'sales': -10, 'traffic': -15},
                    {'day': 'Вторник', 'revenue': -8, 'sales': -5, 'traffic': -8},
                    {'day': 'Среда', 'revenue': 0, 'sales': 3, 'traffic': 2},
                    {'day': 'Четверг', 'revenue': 8, 'sales': 10, 'traffic': 8},
                    {'day': 'Пятница', 'revenue': 20, 'sales': 25, 'traffic': 22},
                    {'day': 'Суббота', 'revenue': 30, 'sales': 35, 'traffic': 38},
                    {'day': 'Воскресенье', 'revenue': 10, 'sales': 15, 'traffic': 18}
                ]
            },
            'fashion': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'base_revenue': -15, 'sales_volume': -12, 'avg_price': 96},
                    {'month': 2, 'name': 'Февраль', 'base_revenue': 5, 'sales_volume': 8, 'avg_price': 100},
                    {'month': 3, 'name': 'Март', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 106},
                    {'month': 4, 'name': 'Апрель', 'base_revenue': 30, 'sales_volume': 32, 'avg_price': 107},
                    {'month': 5, 'name': 'Май', 'base_revenue': 20, 'sales_volume': 22, 'avg_price': 104},
                    {'month': 6, 'name': 'Июнь', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 105},
                    {'month': 7, 'name': 'Июль', 'base_revenue': 10, 'sales_volume': 12, 'avg_price': 98},
                    {'month': 8, 'name': 'Август', 'base_revenue': 35, 'sales_volume': 38, 'avg_price': 108},
                    {'month': 9, 'name': 'Сентябрь', 'base_revenue': 40, 'sales_volume': 42, 'avg_price': 109},
                    {'month': 10, 'name': 'Октябрь', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 105},
                    {'month': 11, 'name': 'Ноябрь', 'base_revenue': 45, 'sales_volume': 48, 'avg_price': 110},
                    {'month': 12, 'name': 'Декабрь', 'base_revenue': 50, 'sales_volume': 52, 'avg_price': 112}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'revenue': -10, 'sales': -8, 'traffic': -12},
                    {'day': 'Вторник', 'revenue': -5, 'sales': -2, 'traffic': -5},
                    {'day': 'Среда', 'revenue': 5, 'sales': 8, 'traffic': 6},
                    {'day': 'Четверг', 'revenue': 12, 'sales': 15, 'traffic': 12},
                    {'day': 'Пятница', 'revenue': 25, 'sales': 30, 'traffic': 28},
                    {'day': 'Суббота', 'revenue': 38, 'sales': 42, 'traffic': 45},
                    {'day': 'Воскресенье', 'revenue': 18, 'sales': 22, 'traffic': 25}
                ]
            },
            'home_garden': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'base_revenue': -20, 'sales_volume': -18, 'avg_price': 94},
                    {'month': 2, 'name': 'Февраль', 'base_revenue': -15, 'sales_volume': -12, 'avg_price': 96},
                    {'month': 3, 'name': 'Март', 'base_revenue': 20, 'sales_volume': 25, 'avg_price': 104},
                    {'month': 4, 'name': 'Апрель', 'base_revenue': 40, 'sales_volume': 45, 'avg_price': 108},
                    {'month': 5, 'name': 'Май', 'base_revenue': 50, 'sales_volume': 55, 'avg_price': 110},
                    {'month': 6, 'name': 'Июнь', 'base_revenue': 45, 'sales_volume': 48, 'avg_price': 108},
                    {'month': 7, 'name': 'Июль', 'base_revenue': 40, 'sales_volume': 42, 'avg_price': 106},
                    {'month': 8, 'name': 'Август', 'base_revenue': 35, 'sales_volume': 38, 'avg_price': 105},
                    {'month': 9, 'name': 'Сентябрь', 'base_revenue': 30, 'sales_volume': 32, 'avg_price': 104},
                    {'month': 10, 'name': 'Октябрь', 'base_revenue': 15, 'sales_volume': 18, 'avg_price': 102},
                    {'month': 11, 'name': 'Ноябрь', 'base_revenue': -5, 'sales_volume': -2, 'avg_price': 98},
                    {'month': 12, 'name': 'Декабрь', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 105}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'revenue': -15, 'sales': -12, 'traffic': -18},
                    {'day': 'Вторник', 'revenue': -10, 'sales': -8, 'traffic': -12},
                    {'day': 'Среда', 'revenue': -5, 'sales': -2, 'traffic': -5},
                    {'day': 'Четверг', 'revenue': 5, 'sales': 8, 'traffic': 6},
                    {'day': 'Пятница', 'revenue': 15, 'sales': 20, 'traffic': 18},
                    {'day': 'Суббота', 'revenue': 50, 'sales': 55, 'traffic': 60},
                    {'day': 'Воскресенье', 'revenue': 45, 'sales': 50, 'traffic': 55}
                ]
            },
            'beauty': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'base_revenue': -5, 'sales_volume': -3, 'avg_price': 98},
                    {'month': 2, 'name': 'Февраль', 'base_revenue': 10, 'sales_volume': 12, 'avg_price': 102},
                    {'month': 3, 'name': 'Март', 'base_revenue': 40, 'sales_volume': 45, 'avg_price': 108},
                    {'month': 4, 'name': 'Апрель', 'base_revenue': 20, 'sales_volume': 22, 'avg_price': 104},
                    {'month': 5, 'name': 'Май', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 105},
                    {'month': 6, 'name': 'Июнь', 'base_revenue': 30, 'sales_volume': 32, 'avg_price': 106},
                    {'month': 7, 'name': 'Июль', 'base_revenue': 20, 'sales_volume': 22, 'avg_price': 103},
                    {'month': 8, 'name': 'Август', 'base_revenue': 15, 'sales_volume': 18, 'avg_price': 102},
                    {'month': 9, 'name': 'Сентябрь', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 104},
                    {'month': 10, 'name': 'Октябрь', 'base_revenue': 30, 'sales_volume': 32, 'avg_price': 105},
                    {'month': 11, 'name': 'Ноябрь', 'base_revenue': 35, 'sales_volume': 38, 'avg_price': 107},
                    {'month': 12, 'name': 'Декабрь', 'base_revenue': 45, 'sales_volume': 48, 'avg_price': 109}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'revenue': -6, 'sales': -4, 'traffic': -8},
                    {'day': 'Вторник', 'revenue': -2, 'sales': 0, 'traffic': -2},
                    {'day': 'Среда', 'revenue': 6, 'sales': 8, 'traffic': 6},
                    {'day': 'Четверг', 'revenue': 12, 'sales': 15, 'traffic': 12},
                    {'day': 'Пятница', 'revenue': 28, 'sales': 32, 'traffic': 30},
                    {'day': 'Суббота', 'revenue': 35, 'sales': 38, 'traffic': 40},
                    {'day': 'Воскресенье', 'revenue': 18, 'sales': 22, 'traffic': 25}
                ]
            },
            'sports': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'base_revenue': 20, 'sales_volume': 25, 'avg_price': 104},
                    {'month': 2, 'name': 'Февраль', 'base_revenue': 15, 'sales_volume': 18, 'avg_price': 102},
                    {'month': 3, 'name': 'Март', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 105},
                    {'month': 4, 'name': 'Апрель', 'base_revenue': 35, 'sales_volume': 38, 'avg_price': 107},
                    {'month': 5, 'name': 'Май', 'base_revenue': 45, 'sales_volume': 50, 'avg_price': 109},
                    {'month': 6, 'name': 'Июнь', 'base_revenue': 40, 'sales_volume': 42, 'avg_price': 108},
                    {'month': 7, 'name': 'Июль', 'base_revenue': 35, 'sales_volume': 38, 'avg_price': 106},
                    {'month': 8, 'name': 'Август', 'base_revenue': 30, 'sales_volume': 32, 'avg_price': 105},
                    {'month': 9, 'name': 'Сентябрь', 'base_revenue': 40, 'sales_volume': 42, 'avg_price': 107},
                    {'month': 10, 'name': 'Октябрь', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 104},
                    {'month': 11, 'name': 'Ноябрь', 'base_revenue': 30, 'sales_volume': 32, 'avg_price': 105},
                    {'month': 12, 'name': 'Декабрь', 'base_revenue': 35, 'sales_volume': 38, 'avg_price': 106}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'revenue': 10, 'sales': 12, 'traffic': 8},
                    {'day': 'Вторник', 'revenue': 15, 'sales': 18, 'traffic': 15},
                    {'day': 'Среда', 'revenue': 20, 'sales': 22, 'traffic': 20},
                    {'day': 'Четверг', 'revenue': 18, 'sales': 20, 'traffic': 18},
                    {'day': 'Пятница', 'revenue': 12, 'sales': 15, 'traffic': 12},
                    {'day': 'Суббота', 'revenue': 25, 'sales': 28, 'traffic': 30},
                    {'day': 'Воскресенье', 'revenue': 22, 'sales': 25, 'traffic': 28}
                ]
            },
            'electronics': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'base_revenue': -10, 'sales_volume': -8, 'avg_price': 96},
                    {'month': 2, 'name': 'Февраль', 'base_revenue': 5, 'sales_volume': 8, 'avg_price': 100},
                    {'month': 3, 'name': 'Март', 'base_revenue': 15, 'sales_volume': 18, 'avg_price': 102},
                    {'month': 4, 'name': 'Апрель', 'base_revenue': 10, 'sales_volume': 12, 'avg_price': 101},
                    {'month': 5, 'name': 'Май', 'base_revenue': 20, 'sales_volume': 22, 'avg_price': 103},
                    {'month': 6, 'name': 'Июнь', 'base_revenue': 15, 'sales_volume': 18, 'avg_price': 102},
                    {'month': 7, 'name': 'Июль', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 104},
                    {'month': 8, 'name': 'Август', 'base_revenue': 30, 'sales_volume': 32, 'avg_price': 105},
                    {'month': 9, 'name': 'Сентябрь', 'base_revenue': 35, 'sales_volume': 38, 'avg_price': 106},
                    {'month': 10, 'name': 'Октябрь', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 104},
                    {'month': 11, 'name': 'Ноябрь', 'base_revenue': 50, 'sales_volume': 55, 'avg_price': 110},
                    {'month': 12, 'name': 'Декабрь', 'base_revenue': 60, 'sales_volume': 62, 'avg_price': 112}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'revenue': -5, 'sales': -3, 'traffic': -8},
                    {'day': 'Вторник', 'revenue': 0, 'sales': 2, 'traffic': 0},
                    {'day': 'Среда', 'revenue': 8, 'sales': 10, 'traffic': 8},
                    {'day': 'Четверг', 'revenue': 15, 'sales': 18, 'traffic': 15},
                    {'day': 'Пятница', 'revenue': 25, 'sales': 28, 'traffic': 25},
                    {'day': 'Суббота', 'revenue': 30, 'sales': 32, 'traffic': 35},
                    {'day': 'Воскресенье', 'revenue': 20, 'sales': 22, 'traffic': 25}
                ]
            },
            'auto': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'base_revenue': -20, 'sales_volume': -18, 'avg_price': 94},
                    {'month': 2, 'name': 'Февраль', 'base_revenue': -10, 'sales_volume': -8, 'avg_price': 96},
                    {'month': 3, 'name': 'Март', 'base_revenue': 10, 'sales_volume': 12, 'avg_price': 102},
                    {'month': 4, 'name': 'Апрель', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 105},
                    {'month': 5, 'name': 'Май', 'base_revenue': 35, 'sales_volume': 38, 'avg_price': 107},
                    {'month': 6, 'name': 'Июнь', 'base_revenue': 40, 'sales_volume': 42, 'avg_price': 108},
                    {'month': 7, 'name': 'Июль', 'base_revenue': 45, 'sales_volume': 48, 'avg_price': 109},
                    {'month': 8, 'name': 'Август', 'base_revenue': 35, 'sales_volume': 38, 'avg_price': 106},
                    {'month': 9, 'name': 'Сентябрь', 'base_revenue': 20, 'sales_volume': 22, 'avg_price': 103},
                    {'month': 10, 'name': 'Октябрь', 'base_revenue': 10, 'sales_volume': 12, 'avg_price': 101},
                    {'month': 11, 'name': 'Ноябрь', 'base_revenue': -5, 'sales_volume': -2, 'avg_price': 98},
                    {'month': 12, 'name': 'Декабрь', 'base_revenue': 15, 'sales_volume': 18, 'avg_price': 102}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'revenue': -10, 'sales': -8, 'traffic': -12},
                    {'day': 'Вторник', 'revenue': -5, 'sales': -3, 'traffic': -5},
                    {'day': 'Среда', 'revenue': 5, 'sales': 8, 'traffic': 5},
                    {'day': 'Четверг', 'revenue': 10, 'sales': 12, 'traffic': 10},
                    {'day': 'Пятница', 'revenue': 15, 'sales': 18, 'traffic': 15},
                    {'day': 'Суббота', 'revenue': 35, 'sales': 38, 'traffic': 40},
                    {'day': 'Воскресенье', 'revenue': 25, 'sales': 28, 'traffic': 30}
                ]
            },
            'general': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'base_revenue': -15, 'sales_volume': -12, 'avg_price': 96},
                    {'month': 2, 'name': 'Февраль', 'base_revenue': -5, 'sales_volume': -2, 'avg_price': 98},
                    {'month': 3, 'name': 'Март', 'base_revenue': 10, 'sales_volume': 12, 'avg_price': 102},
                    {'month': 4, 'name': 'Апрель', 'base_revenue': 15, 'sales_volume': 18, 'avg_price': 103},
                    {'month': 5, 'name': 'Май', 'base_revenue': 20, 'sales_volume': 22, 'avg_price': 104},
                    {'month': 6, 'name': 'Июнь', 'base_revenue': 15, 'sales_volume': 18, 'avg_price': 102},
                    {'month': 7, 'name': 'Июль', 'base_revenue': 10, 'sales_volume': 12, 'avg_price': 101},
                    {'month': 8, 'name': 'Август', 'base_revenue': 25, 'sales_volume': 28, 'avg_price': 105},
                    {'month': 9, 'name': 'Сентябрь', 'base_revenue': 30, 'sales_volume': 32, 'avg_price': 106},
                    {'month': 10, 'name': 'Октябрь', 'base_revenue': 20, 'sales_volume': 22, 'avg_price': 104},
                    {'month': 11, 'name': 'Ноябрь', 'base_revenue': 35, 'sales_volume': 38, 'avg_price': 107},
                    {'month': 12, 'name': 'Декабрь', 'base_revenue': 40, 'sales_volume': 42, 'avg_price': 108}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'revenue': -8, 'sales': -6, 'traffic': -10},
                    {'day': 'Вторник', 'revenue': -3, 'sales': -1, 'traffic': -3},
                    {'day': 'Среда', 'revenue': 5, 'sales': 8, 'traffic': 5},
                    {'day': 'Четверг', 'revenue': 10, 'sales': 12, 'traffic': 10},
                    {'day': 'Пятница', 'revenue': 20, 'sales': 25, 'traffic': 22},
                    {'day': 'Суббота', 'revenue': 35, 'sales': 38, 'traffic': 40},
                    {'day': 'Воскресенье', 'revenue': 25, 'sales': 28, 'traffic': 30}
                ]
            }
        }

    def _enhance_annual_data(self, base_annual, category_type):
        """Улучшение годовых данных с учетом дополнительных факторов"""
        enhanced = []
        for month_data in base_annual:
            month = month_data['month']
            
            # Применяем праздничные коэффициенты
            holiday_boost = self._get_holiday_boost(month, category_type)
            
            # Применяем погодные факторы
            weather_factor = self._get_weather_factor(month, category_type)
            
            # Применяем макроэкономические факторы
            macro_factor = self._get_macro_factor(month)
            
            # Рассчитываем итоговые показатели
            final_revenue = month_data['base_revenue'] * holiday_boost * weather_factor * macro_factor
            final_sales = month_data['sales_volume'] * holiday_boost * weather_factor
            
            enhanced_month = {
                'month': month,
                'name': month_data['name'],
                'season_revenue': round(final_revenue, 1),
                'sales_volume': round(final_sales, 1),
                'avg_price': month_data['avg_price'],
                'holiday_boost': round((holiday_boost - 1) * 100, 1),
                'weather_impact': round((weather_factor - 1) * 100, 1),
                'macro_impact': round((macro_factor - 1) * 100, 1),
                'reason': self._get_month_reason(month, category_type),
                'competition_level': self._get_competition_level(month, category_type),
                'recommended_budget': self._calculate_budget_recommendation(final_revenue)
            }
            enhanced.append(enhanced_month)
        
        return enhanced 

    def _enhance_weekly_data(self, base_weekly, category_type):
        """Улучшение недельных данных"""
        enhanced = []
        for day_data in base_weekly:
            day_name = day_data['day']
            
            # Применяем факторы выходных/рабочих дней
            weekend_factor = 1.2 if day_name in ['Суббота', 'Воскресенье'] else 1.0
            
            # Применяем факторы покупательского поведения
            behavior_factor = self._get_behavior_factor(day_name, category_type)
            
            enhanced_day = {
                'day': day_name,
                'weekly_revenue': round(day_data['revenue'] * weekend_factor * behavior_factor, 1),
                'weekly_sales': round(day_data['sales'] * weekend_factor * behavior_factor, 1),
                'traffic': round(day_data['traffic'] * weekend_factor, 1),
                'conversion_rate': self._calculate_conversion_rate(day_name, category_type),
                'avg_check': self._calculate_avg_check(day_name, category_type),
                'peak_hours': self._get_peak_hours(day_name),
                'recommended_promotions': self._get_promotion_recommendations(day_name, category_type)
            }
            enhanced.append(enhanced_day)
        
        return enhanced

    def _get_holiday_boost(self, month, category_type):
        """Расчет праздничного буста"""
        boost = 1.0
        
        if month in self.russian_holidays:
            if category_type == 'toys' and month == 12:
                boost = 1.8  # Новый год - максимальный буст для игрушек
            elif category_type == 'women' and month == 3:
                boost = 1.4  # 8 марта
            elif category_type == 'men' and month == 2:
                boost = 1.3  # 23 февраля
            elif category_type == 'children' and month in [8, 9]:
                boost = 1.5  # Подготовка к школе
            else:
                boost = 1.2  # Общий праздничный буст
        
        return boost

    def _get_weather_factor(self, month, category_type):
        """Расчет погодного фактора"""
        month_str = str(month)
        
        if category_type in ['fashion', 'women', 'men'] and month in [11, 12, 1, 2]:
            return 1.3  # Зимняя одежда
        elif category_type in ['toys', 'children'] and month in [6, 7, 8]:
            return 1.2  # Летние игрушки
        elif category_type == 'home_garden' and month in [4, 5, 6]:
            return 1.4  # Дачный сезон
        
        return 1.0

    def _get_macro_factor(self, month):
        """Макроэкономический фактор (зарплаты, премии)"""
        if month in [12, 1]:  # Премии и 13-я зарплата
            return 1.15
        elif month in [6, 7]:  # Отпускные
            return 1.1
        elif month in [2, 3]:  # После праздников
            return 0.95
        return 1.0

    def _get_month_reason(self, month, category_type):
        """Получение причины сезонности месяца"""
        reasons = {
            1: {
                'children': 'После новогодних подарков, зимние каникулы',
                'toys': 'Спад после новогодних продаж',
                'women': 'Послепраздничный период, планирование бюджета',
                'men': 'Спокойный период после праздников'
            },
            3: {
                'women': '8 марта - главный праздник для женщин',
                'children': 'Подготовка к весне, обновление гардероба',
                'toys': 'Подарки к 8 марта для девочек'
            },
            8: {
                'children': 'Подготовка к школе - пик продаж',
                'toys': 'Покупки к началу учебного года'
            },
            12: {
                'toys': 'Новогодние подарки - пик года',
                'children': 'Новогодние праздники и подарки',
                'women': 'Новогодние наряды и подарки'
            }
        }
        
        return reasons.get(month, {}).get(category_type, 'Стандартный сезонный паттерн')

    def _get_competition_level(self, month, category_type):
        """Уровень конкуренции в месяце"""
        high_competition_months = {
            'toys': [11, 12],
            'children': [8, 9],
            'women': [3, 11, 12],
            'fashion': [3, 4, 8, 9, 11, 12]
        }
        
        if month in high_competition_months.get(category_type, []):
            return 'Высокий'
        elif month in [1, 2, 6, 7]:
            return 'Низкий'
        else:
            return 'Средний'

    def _calculate_budget_recommendation(self, revenue_change):
        """Рекомендация по рекламному бюджету"""
        if revenue_change > 40:
            return 'Увеличить на 50-70%'
        elif revenue_change > 20:
            return 'Увеличить на 30-50%'
        elif revenue_change > 0:
            return 'Увеличить на 10-30%'
        else:
            return 'Уменьшить на 20-40%'

    def _get_behavior_factor(self, day_name, category_type):
        """Фактор покупательского поведения"""
        if category_type == 'women' and day_name == 'Пятница':
            return 1.3  # Женщины чаще делают покупки в пятницу
        elif category_type in ['children', 'toys'] and day_name in ['Суббота', 'Воскресенье']:
            return 1.4  # Родители покупают детям в выходные
        elif category_type == 'home_garden' and day_name in ['Суббота', 'Воскресенье']:
            return 1.5  # Дачники активны в выходные
        return 1.0

    def _calculate_conversion_rate(self, day_name, category_type):
        """Расчет конверсии по дням"""
        base_conversion = {
            'children': 3.5, 'toys': 2.8, 'women': 4.2,
            'men': 3.1, 'fashion': 3.8, 'home_garden': 3.0,
            'beauty': 4.5, 'sports': 3.3, 'electronics': 2.9,
            'auto': 2.1
        }.get(category_type, 3.2)
        
        day_modifiers = {
            'Понедельник': 0.8, 'Вторник': 0.9, 'Среда': 1.0,
            'Четверг': 1.1, 'Пятница': 1.3, 'Суббота': 1.4, 'Воскресенье': 1.2
        }
        
        return round(base_conversion * day_modifiers.get(day_name, 1.0), 2)

    def _calculate_avg_check(self, day_name, category_type):
        """Расчет среднего чека"""
        base_check = {
            'children': 2500, 'toys': 1800, 'women': 3200,
            'men': 3800, 'fashion': 3500, 'home_garden': 4200,
            'beauty': 2800, 'sports': 5500, 'electronics': 12000,
            'auto': 3500
        }.get(category_type, 3000)
        
        weekend_multiplier = 1.15 if day_name in ['Суббота', 'Воскресенье'] else 1.0
        
        return round(base_check * weekend_multiplier)

    def _get_peak_hours(self, day_name):
        """Пиковые часы покупок"""
        if day_name in ['Суббота', 'Воскресенье']:
            return '11:00-15:00, 18:00-21:00'
        else:
            return '12:00-14:00, 18:00-22:00'

    def _get_promotion_recommendations(self, day_name, category_type):
        """Рекомендации по акциям"""
        if day_name == 'Понедельник':
            return 'Скидки на старт недели (-10-15%)'
        elif day_name == 'Пятница':
            return 'Пятничные распродажи (-20-25%)'
        elif day_name in ['Суббота', 'Воскресенье']:
            return 'Семейные скидки, бонусы за покупку от суммы'
        else:
            return 'Стандартные акции (-5-10%)'

    def _generate_trend_analysis(self, category_type):
        """Генерация анализа трендов"""
        trends = {
            'children': [
                'Экологичность и безопасность материалов (+25% к спросу)',
                'Развивающие и обучающие товары (+30% к продажам)',
                'Товары для активного отдыха (+20% летом)',
                'Персонализированные товары (+15% круглый год)'
            ],
            'toys': [
                'STEM-игрушки и конструкторы (+40% к спросу)',
                'Коллекционные игрушки (+25% среди взрослых)',
                'Интерактивные и умные игрушки (+35% к продажам)',
                'Настольные игры для семьи (+30% в выходные)'
            ],
            'women': [
                'Sustainable fashion (+20% к интересу)',
                'Базовый гардероб и капсульные коллекции (+25%)',
                'Комфортная одежда для дома (+30% после COVID)',
                'Винтаж и секонд-хенд (+15% среди молодежи)'
            ],
            'men': [
                'Функциональная одежда (+22% к спросу)',
                'Минимализм и базовые вещи (+18%)',
                'Спортивный стиль в повседневности (+25%)',
                'Качественные аксессуары (+20%)'
            ],
            'fashion': [
                'Устойчивая мода (+30% к интересу)',
                'Гендерно-нейтральная одежда (+15%)',
                'Локальные бренды (+20%)',
                'Персонализация и кастомизация (+25%)'
            ],
            'beauty': [
                'K-beauty и азиатские бренды (+35%)',
                'Натуральная и органическая косметика (+40%)',
                'Мужская косметика (+50% рост)',
                'Инклюзивность в цветовой палитре (+28%)'
            ],
            'sports': [
                'Женский фитнес и йога (+45%)',
                'Домашние тренировки (+60% после пандемии)',
                'Функциональная спортивная одежда (+35%)',
                'Восстановительные технологии (+30%)'
            ],
            'electronics': [
                'Умные устройства для дома (+50%)',
                'Мобильные аксессуары (+40%)',
                'Экологичная электроника (+25%)',
                'Образовательные гаджеты (+35%)'
            ],
            'auto': [
                'Электромобили и гибриды (+80%)',
                'Умные автоаксессуары (+45%)',
                'Экологичные автохимия (+30%)',
                'DIY и тюнинг (+25%)'
            ],
            'home_garden': [
                'Умный дом и автоматизация (+55%)',
                'Вертикальное озеленение (+40%)',
                'Экологичные материалы (+35%)',
                'Компактные решения (+30%)'
            ]
        }
        
        return {
            'current_trends': trends.get(category_type, ['Стандартные рыночные тренды']),
            'growth_potential': self._calculate_growth_potential(category_type),
            'market_saturation': self._get_market_saturation(category_type),
            'innovation_opportunities': self._get_innovation_opportunities(category_type)
        }

    def _generate_competitive_analysis(self, category_type):
        """Анализ конкурентной среды"""
        return {
            'market_leaders': self._get_market_leaders(category_type),
            'price_positioning': self._get_price_positioning(category_type),
            'differentiation_factors': self._get_differentiation_factors(category_type),
            'market_gaps': self._get_market_gaps(category_type)
        }

    def _generate_price_recommendations(self, annual_data):
        """Рекомендации по ценообразованию"""
        recommendations = []
        
        for month in annual_data:
            if month['season_revenue'] > 30:
                price_strategy = 'Премиум цены (+10-15% к базе)'
            elif month['season_revenue'] > 10:
                price_strategy = 'Умеренное повышение (+5-10%)'
            elif month['season_revenue'] < -10:
                price_strategy = 'Агрессивные скидки (-15-25%)'
            else:
                price_strategy = 'Базовые цены'
            
            recommendations.append({
                'month': month['name'],
                'strategy': price_strategy,
                'competition': month['competition_level']
            })
        
        return recommendations

    def _generate_marketing_calendar(self, annual_data, category_type):
        """Календарь маркетинговых активностей"""
        calendar = []
        
        for month in annual_data:
            month_num = month['month']
            
            # Определяем тип активности
            if month['season_revenue'] > 40:
                activity_type = 'Максимальная активность'
                budget_allocation = '25-30% годового бюджета'
            elif month['season_revenue'] > 20:
                activity_type = 'Высокая активность'
                budget_allocation = '15-20% годового бюджета'
            elif month['season_revenue'] > 0:
                activity_type = 'Средняя активность'
                budget_allocation = '8-12% годового бюджета'
            else:
                activity_type = 'Минимальная активность'
                budget_allocation = '3-5% годового бюджета'
            
            calendar.append({
                'month': month['name'],
                'activity_type': activity_type,
                'budget_allocation': budget_allocation,
                'recommended_channels': self._get_marketing_channels(month_num, category_type),
                'content_themes': self._get_content_themes(month_num, category_type)
            })
        
        return calendar

    def _generate_regional_insights(self, category_type):
        """Региональные особенности"""
        return {
            'moscow_spb': {
                'multiplier': 1.2,
                'peak_months': 'Март, Ноябрь, Декабрь',
                'preferences': 'Премиум сегмент, быстрая доставка'
            },
            'regions': {
                'multiplier': 1.0,
                'peak_months': 'Август, Декабрь',
                'preferences': 'Цена-качество, практичность'
            },
            'south': {
                'multiplier': 0.95,
                'peak_months': 'Май-Сентябрь',
                'preferences': 'Летние товары, длинный сезон'
            }
        }

    # Вспомогательные методы для генерации данных
    def _calculate_growth_potential(self, category_type):
        growth_rates = {
            'children': 'Высокий (12-15% в год)',
            'toys': 'Средний (8-10% в год)',
            'women': 'Высокий (15-20% в год)',
            'electronics': 'Очень высокий (20-25% в год)'
        }
        return growth_rates.get(category_type, 'Средний (8-12% в год)')

    def _get_market_saturation(self, category_type):
        saturation = {
            'children': 'Средняя (60-70%)',
            'toys': 'Высокая (80-85%)',
            'women': 'Средняя (65-75%)',
            'electronics': 'Низкая (40-50%)'
        }
        return saturation.get(category_type, 'Средняя (60-70%)')

    def _get_innovation_opportunities(self, category_type):
        opportunities = {
            'children': ['Экотовары', 'Персонализация', 'Умные технологии'],
            'toys': ['AR/VR игрушки', 'Образовательные наборы', 'DIY конструкторы'],
            'women': ['Размерная инклюзивность', 'Eco-fashion', 'Технологичные ткани']
        }
        return opportunities.get(category_type, ['Цифровизация', 'Персонализация'])

    def _get_market_leaders(self, category_type):
        """Лидеры рынка по категориям"""
        leaders = {
            'children': ['H&M Kids', 'Zara Kids', 'Next', 'Acoola'],
            'toys': ['LEGO', 'Hasbro', 'Simba', 'Играем Вместе'],
            'women': ['Zara', 'H&M', 'Reserved', 'Mango'],
            'men': ['Zara Man', 'H&M', 'Mark & Spencer', 'Reserved'],
            'fashion': ['Zara', 'H&M', 'Uniqlo', 'COS'],
            'beauty': ['L\'Oréal', 'Maybelline', 'NYX', 'Essence'],
            'sports': ['Nike', 'Adidas', 'Puma', 'Reebok'],
            'electronics': ['Apple', 'Samsung', 'Xiaomi', 'Huawei'],
            'auto': ['Bosch', 'Mann Filter', 'DENSO', 'NGK'],
            'home_garden': ['IKEA', 'Leroy Merlin', 'Hoff', 'Castorama']
        }
        return leaders.get(category_type, ['Лидер 1', 'Лидер 2', 'Лидер 3'])

    def _get_marketing_channels(self, month, category_type):
        if month in [11, 12]:  # Предновогодний период
            return ['Contextual ads', 'Social media', 'Email marketing', 'Influencers']
        elif month in [3, 8]:  # Сезонные пики
            return ['Social media', 'Display ads', 'Video marketing']
        else:
            return ['SEO', 'Content marketing', 'Retargeting']

    def _get_content_themes(self, month, category_type):
        themes = {
            3: ['Весенние новинки', '8 марта', 'Обновление гардероба'],
            8: ['Подготовка к школе', 'Back to school', 'Осенние коллекции'],
            12: ['Новогодние подарки', 'Праздничная мода', 'Распродажи']
        }
        return themes.get(month, ['Сезонные тренды', 'Новинки', 'Лайфстайл'])

    # Недостающие методы класса
    def _get_price_positioning(self, category_type):
        """Позиционирование по ценам"""
        positioning = {
            'children': 'Средний+ сегмент (1500-4000₽)',
            'toys': 'Широкий диапазон (300-8000₽)',
            'women': 'Массовый рынок (800-5000₽)',
            'men': 'Средний сегмент (1200-4500₽)',
            'fashion': 'Массовый+ сегмент (1000-6000₽)',
            'beauty': 'Средний сегмент (500-3000₽)',
            'sports': 'Средний+ сегмент (2000-8000₽)',
            'electronics': 'Премиум сегмент (5000-50000₽)',
            'auto': 'Широкий диапазон (500-15000₽)',
            'home_garden': 'Средний сегмент (800-5000₽)'
        }
        return positioning.get(category_type, 'Средний сегмент (1000-3000₽)')

    def _get_differentiation_factors(self, category_type):
        """Факторы дифференциации"""
        factors = {
            'children': ['Безопасность', 'Экологичность', 'Развивающий эффект'],
            'toys': ['Качество материалов', 'Образовательная ценность', 'Долговечность'],
            'women': ['Стиль', 'Качество ткани', 'Посадка', 'Тренды'],
            'men': ['Практичность', 'Качество', 'Функциональность'],
            'fashion': ['Дизайн', 'Качество материалов', 'Соответствие трендам'],
            'beauty': ['Натуральность', 'Эффективность', 'Упаковка'],
            'sports': ['Функциональность', 'Технологии', 'Бренд'],
            'electronics': ['Технические характеристики', 'Инновации', 'Надежность'],
            'auto': ['Совместимость', 'Качество', 'Гарантия'],
            'home_garden': ['Практичность', 'Долговечность', 'Дизайн']
        }
        return factors.get(category_type, ['Качество', 'Цена', 'Дизайн'])

    def _get_market_gaps(self, category_type):
        """Ниши на рынке"""
        gaps = {
            'children': ['Подростковая мода 12-16 лет', 'Спортивная одежда для детей'],
            'toys': ['STEM для девочек', 'Экологичные игрушки', 'Коллекционные серии'],
            'women': ['Размеры 50+', 'Офисная мода', 'Спортивные луки'],
            'men': ['Большие размеры', 'Умная одежда', 'Эко-материалы'],
            'fashion': ['Унисекс линии', 'Адаптивная одежда', 'Локальные бренды'],
            'beauty': ['Мужская косметика', 'K-beauty', 'Веганская косметика'],
            'sports': ['Женский фитнес', 'Экстремальные виды спорта', 'Восстановление'],
            'electronics': ['IoT устройства', 'Экологичная электроника', 'Образование'],
            'auto': ['Электромобили', 'Тюнинг', 'Vintage запчасти'],
            'home_garden': ['Умный дом', 'Вертикальное озеленение', 'Мини-сады']
        }
        return gaps.get(category_type, ['Персонализация', 'Экологичность'])

# Основная функция для получения расширенных данных
async def get_advanced_fallback_seasonality_data(category_path):
    """Главная функция получения расширенных данных сезонности"""
    analyzer = AdvancedSeasonalityAnalyzer()
    return await analyzer.get_advanced_seasonality_data(category_path)

def format_advanced_seasonality_analysis(advanced_data, category_path):
    """Форматирование результатов расширенного анализа сезонности"""
    try:
        if not advanced_data:
            return "❌ Не удалось получить данные сезонности"
        
        result = f"🗓️ *РАСШИРЕННЫЙ АНАЛИЗ СЕЗОННОСТИ*\n"
        result += f"📂 *Категория:* {category_path}\n"
        result += f"🎯 *Тип категории:* {advanced_data['category_type'].upper()}\n\n"
        result += "📊 *Источник:* Продвинутая аналитическая модель\n\n"
        
        # Анализ годовой сезонности
        annual_data = advanced_data.get('annual', [])
        if annual_data:
            result += "📅 *ГОДОВАЯ СЕЗОННОСТЬ*\n\n"
            
            # ТОП-3 лучших месяца
            best_months = sorted(annual_data, key=lambda x: x['season_revenue'], reverse=True)[:3]
            result += "🔥 *ТОП-3 ЛУЧШИХ МЕСЯЦА:*\n"
            for i, month in enumerate(best_months, 1):
                result += f"{i}. *{month['name']}*: {month['season_revenue']:+.1f}% выручка\n"
                result += f"   💰 Средняя цена: {month['avg_price']}% от базы\n"
                result += f"   🏆 Конкуренция: {month['competition_level']}\n"
                result += f"   💡 {month['reason']}\n"
                result += f"   📈 Бюджет: {month['recommended_budget']}\n\n"
        
        # Недельная сезонность
        weekly_data = advanced_data.get('weekly', [])
        if weekly_data:
            result += "📊 *НЕДЕЛЬНАЯ СЕЗОННОСТЬ*\n\n"
            
            best_day = max(weekly_data, key=lambda x: x['weekly_revenue'])
            result += f"💎 *Лучший день:* {best_day['day']} ({best_day['weekly_revenue']:+.1f}%)\n"
            result += f"🎯 *Конверсия:* {best_day['conversion_rate']}%\n"
            result += f"💸 *Средний чек:* {best_day['avg_check']:,} ₽\n"
            result += f"⏰ *Пик активности:* {best_day['peak_hours']}\n\n"
            
            result += "*📋 ДЕТАЛЬНАЯ РАЗБИВКА ПО ДНЯМ:*\n"
            for day in weekly_data:
                result += f"• *{day['day']}*: {day['weekly_revenue']:+.1f}% выручка, {day['conversion_rate']}% конверсия\n"
                result += f"  🎪 {day['recommended_promotions']}\n"
        
        # Трендовый анализ
        trend_analysis = advanced_data.get('trend_analysis', {})
        if trend_analysis:
            result += f"\n🚀 *ТРЕНДОВЫЙ АНАЛИЗ*\n\n"
            result += f"📈 *Потенциал роста:* {trend_analysis['growth_potential']}\n"
            result += f"📊 *Насыщенность рынка:* {trend_analysis['market_saturation']}\n\n"
            
            result += "*🔥 АКТУАЛЬНЫЕ ТРЕНДЫ:*\n"
            for trend in trend_analysis['current_trends'][:3]:
                result += f"• {trend}\n"
            
            result += f"\n*💡 ВОЗМОЖНОСТИ ДЛЯ ИННОВАЦИЙ:*\n"
            for opportunity in trend_analysis['innovation_opportunities']:
                result += f"• {opportunity}\n"
        
        # Конкурентный анализ
        competitive = advanced_data.get('competitive_analysis', {})
        if competitive:
            result += f"\n⚔️ *КОНКУРЕНТНЫЙ АНАЛИЗ*\n\n"
            result += f"*👑 Лидеры рынка:*\n"
            for leader in competitive['market_leaders'][:3]:
                result += f"• {leader}\n"
        
        # Ценовые рекомендации
        price_recs = advanced_data.get('price_recommendations', [])
        if price_recs:
            result += f"\n💰 *ЦЕНОВЫЕ СТРАТЕГИИ*\n\n"
            
            # Показываем только ключевые месяцы
            key_months = [p for p in price_recs if p['month'] in ['Март', 'Август', 'Ноябрь', 'Декабрь']]
            for rec in key_months:
                result += f"*{rec['month']}:* {rec['strategy']}\n"
        
        # Маркетинговый календарь
        marketing_cal = advanced_data.get('marketing_calendar', [])
        if marketing_cal:
            result += f"\n📅 *МАРКЕТИНГОВЫЙ КАЛЕНДАРЬ*\n\n"
            
            high_activity_months = [m for m in marketing_cal if 'Максимальная' in m['activity_type'] or 'Высокая' in m['activity_type']]
            for month in high_activity_months[:4]:
                result += f"*{month['month']}* - {month['activity_type']}\n"
                result += f"💸 Бюджет: {month['budget_allocation']}\n"
                result += f"📢 Каналы: {', '.join(month['recommended_channels'][:2])}\n\n"
        
        # Региональные особенности
        regional = advanced_data.get('regional_insights', {})
        if regional:
            result += f"🗺️ *РЕГИОНАЛЬНЫЕ ОСОБЕННОСТИ*\n\n"
            result += f"*🏙️ Москва/СПб:* множитель {regional['moscow_spb']['multiplier']}\n"
            result += f"  Пики: {regional['moscow_spb']['peak_months']}\n"
            result += f"*🌍 Регионы:* множитель {regional['regions']['multiplier']}\n"
            result += f"  Особенности: {regional['regions']['preferences']}\n"
        
        # Общие рекомендации
        result += f"\n💡 *КЛЮЧЕВЫЕ РЕКОМЕНДАЦИИ:*\n"
        
        if annual_data:
            best_month = max(annual_data, key=lambda x: x['season_revenue'])
            worst_month = min(annual_data, key=lambda x: x['season_revenue'])
            
            result += f"🎯 Максимальные инвестиции в {best_month['name']} ({best_month['season_revenue']:+.1f}%)\n"
            result += f"💤 Минимальная активность в {worst_month['name']} ({worst_month['season_revenue']:+.1f}%)\n"
            result += f"📊 Планируйте 60-70% годового бюджета на топ-3 месяца\n"
            result += f"🎪 Активные промо в выходные дни\n"
            result += f"📱 Усиленная работа с соцсетями в пиковые периоды\n"
        
        result += f"\n🎓 *ИСТОЧНИКИ ДАННЫХ:*\n"
        result += f"• Анализ российского e-commerce рынка\n"
        result += f"• Праздничные и сезонные паттерны\n"
        result += f"• Макроэкономические факторы\n"
        result += f"• Поведенческие тренды покупателей\n"
        result += f"• Конкурентная среда и ценообразование\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error formatting advanced seasonality analysis: {str(e)}")
        return "❌ Ошибка форматирования расширенного анализа"

# Добавляем недостающие методы в класс
AdvancedSeasonalityAnalyzer._get_price_positioning = AdvancedSeasonalityAnalyzer._get_price_positioning
AdvancedSeasonalityAnalyzer._get_differentiation_factors = AdvancedSeasonalityAnalyzer._get_differentiation_factors  
AdvancedSeasonalityAnalyzer._get_market_gaps = AdvancedSeasonalityAnalyzer._get_market_gaps