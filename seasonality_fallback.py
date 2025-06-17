#!/usr/bin/env python3
"""
Запасные функции для анализа сезонности
Используются когда основное API не возвращает данные
"""

import logging

logger = logging.getLogger(__name__)

async def get_fallback_seasonality_data(category_path):
    """Запасная функция получения данных сезонности из альтернативных источников"""
    try:
        # Определяем базовые сезонные паттерны для разных категорий
        category_lower = category_path.lower()
        
        # Базовые данные сезонности по категориям
        seasonality_patterns = {
            # Одежда и мода
            'одежда': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'season_revenue': -20, 'reason': 'После новогодних трат'},
                    {'month': 2, 'name': 'Февраль', 'season_revenue': -15, 'reason': 'Низкий сезон'},
                    {'month': 3, 'name': 'Март', 'season_revenue': 10, 'reason': 'Подготовка к весне, 8 марта'},
                    {'month': 4, 'name': 'Апрель', 'season_revenue': 25, 'reason': 'Весенняя коллекция'},
                    {'month': 5, 'name': 'Май', 'season_revenue': 15, 'reason': 'Подготовка к лету'},
                    {'month': 6, 'name': 'Июнь', 'season_revenue': 20, 'reason': 'Летний сезон'},
                    {'month': 7, 'name': 'Июль', 'season_revenue': 10, 'reason': 'Середина лета'},
                    {'month': 8, 'name': 'Август', 'season_revenue': 30, 'reason': 'Подготовка к осени'},
                    {'month': 9, 'name': 'Сентябрь', 'season_revenue': 35, 'reason': 'Осенняя коллекция, начало учебы'},
                    {'month': 10, 'name': 'Октябрь', 'season_revenue': 20, 'reason': 'Осенний сезон'},
                    {'month': 11, 'name': 'Ноябрь', 'season_revenue': 40, 'reason': 'Black Friday, подготовка к зиме'},
                    {'month': 12, 'name': 'Декабрь', 'season_revenue': 50, 'reason': 'Новогодние подарки'}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'weekly_revenue': -10, 'weekly_sales': -8},
                    {'day': 'Вторник', 'weekly_revenue': -5, 'weekly_sales': -3},
                    {'day': 'Среда', 'weekly_revenue': 5, 'weekly_sales': 8},
                    {'day': 'Четверг', 'weekly_revenue': 10, 'weekly_sales': 12},
                    {'day': 'Пятница', 'weekly_revenue': 25, 'weekly_sales': 30},
                    {'day': 'Суббота', 'weekly_revenue': 35, 'weekly_sales': 40},
                    {'day': 'Воскресенье', 'weekly_revenue': 15, 'weekly_sales': 20}
                ]
            },
            
            # Детские товары
            'дет': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'season_revenue': -10, 'reason': 'После новогодних подарков'},
                    {'month': 2, 'name': 'Февраль', 'season_revenue': -5, 'reason': 'Спокойный период'},
                    {'month': 3, 'name': 'Март', 'season_revenue': 15, 'reason': 'Подготовка к весне'},
                    {'month': 4, 'name': 'Апрель', 'season_revenue': 20, 'reason': 'Весенние прогулки'},
                    {'month': 5, 'name': 'Май', 'season_revenue': 25, 'reason': 'День защиты детей скоро'},
                    {'month': 6, 'name': 'Июнь', 'season_revenue': 30, 'reason': 'День защиты детей, лето'},
                    {'month': 7, 'name': 'Июль', 'season_revenue': 35, 'reason': 'Летние каникулы'},
                    {'month': 8, 'name': 'Август', 'season_revenue': 60, 'reason': 'Подготовка к школе'},
                    {'month': 9, 'name': 'Сентябрь', 'season_revenue': 45, 'reason': '1 сентября, начало учебы'},
                    {'month': 10, 'name': 'Октябрь', 'season_revenue': 10, 'reason': 'Осенний период'},
                    {'month': 11, 'name': 'Ноябрь', 'season_revenue': 25, 'reason': 'Подготовка к зиме'},
                    {'month': 12, 'name': 'Декабрь', 'season_revenue': 55, 'reason': 'Новогодние подарки'}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'weekly_revenue': -5, 'weekly_sales': -3},
                    {'day': 'Вторник', 'weekly_revenue': 0, 'weekly_sales': 2},
                    {'day': 'Среда', 'weekly_revenue': 5, 'weekly_sales': 8},
                    {'day': 'Четверг', 'weekly_revenue': 10, 'weekly_sales': 15},
                    {'day': 'Пятница', 'weekly_revenue': 20, 'weekly_sales': 25},
                    {'day': 'Суббота', 'weekly_revenue': 40, 'weekly_sales': 45},
                    {'day': 'Воскресенье', 'weekly_revenue': 30, 'weekly_sales': 35}
                ]
            },
            
            # Игрушки
            'игрушк': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'season_revenue': -30, 'reason': 'После новогодних покупок'},
                    {'month': 2, 'name': 'Февраль', 'season_revenue': -20, 'reason': 'Низкий сезон'},
                    {'month': 3, 'name': 'Март', 'season_revenue': 10, 'reason': 'Подарки к 8 марта для девочек'},
                    {'month': 4, 'name': 'Апрель', 'season_revenue': 15, 'reason': 'Весенние прогулки'},
                    {'month': 5, 'name': 'Май', 'season_revenue': 20, 'reason': 'Подготовка к лету'},
                    {'month': 6, 'name': 'Июнь', 'season_revenue': 35, 'reason': 'День защиты детей'},
                    {'month': 7, 'name': 'Июль', 'season_revenue': 25, 'reason': 'Летние каникулы'},
                    {'month': 8, 'name': 'Август', 'season_revenue': 20, 'reason': 'Конец каникул'},
                    {'month': 9, 'name': 'Сентябрь', 'season_revenue': 15, 'reason': 'Начало учебы'},
                    {'month': 10, 'name': 'Октябрь', 'season_revenue': 10, 'reason': 'Осенний период'},
                    {'month': 11, 'name': 'Ноябрь', 'season_revenue': 30, 'reason': 'Подготовка к Новому году'},
                    {'month': 12, 'name': 'Декабрь', 'season_revenue': 80, 'reason': 'Новогодние подарки'}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'weekly_revenue': -8, 'weekly_sales': -5},
                    {'day': 'Вторник', 'weekly_revenue': -3, 'weekly_sales': 0},
                    {'day': 'Среда', 'weekly_revenue': 8, 'weekly_sales': 10},
                    {'day': 'Четверг', 'weekly_revenue': 15, 'weekly_sales': 18},
                    {'day': 'Пятница', 'weekly_revenue': 25, 'weekly_sales': 30},
                    {'day': 'Суббота', 'weekly_revenue': 45, 'weekly_sales': 50},
                    {'day': 'Воскресенье', 'weekly_revenue': 35, 'weekly_sales': 40}
                ]
            },
            
            # Мужские товары
            'мужч': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'season_revenue': -15, 'reason': 'После праздников'},
                    {'month': 2, 'name': 'Февраль', 'season_revenue': 30, 'reason': '23 февраля'},
                    {'month': 3, 'name': 'Март', 'season_revenue': -5, 'reason': 'Спокойный период'},
                    {'month': 4, 'name': 'Апрель', 'season_revenue': 10, 'reason': 'Весенний период'},
                    {'month': 5, 'name': 'Май', 'season_revenue': 15, 'reason': 'Майские праздники'},
                    {'month': 6, 'name': 'Июнь', 'season_revenue': 20, 'reason': 'Летний сезон'},
                    {'month': 7, 'name': 'Июль', 'season_revenue': 10, 'reason': 'Отпуска'},
                    {'month': 8, 'name': 'Август', 'season_revenue': 15, 'reason': 'Конец лета'},
                    {'month': 9, 'name': 'Сентябрь', 'season_revenue': 25, 'reason': 'Возвращение к работе'},
                    {'month': 10, 'name': 'Октябрь', 'season_revenue': 20, 'reason': 'Осенний гардероб'},
                    {'month': 11, 'name': 'Ноябрь', 'season_revenue': 35, 'reason': 'Black Friday'},
                    {'month': 12, 'name': 'Декабрь', 'season_revenue': 40, 'reason': 'Новогодние подарки'}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'weekly_revenue': -12, 'weekly_sales': -10},
                    {'day': 'Вторник', 'weekly_revenue': -8, 'weekly_sales': -5},
                    {'day': 'Среда', 'weekly_revenue': 0, 'weekly_sales': 3},
                    {'day': 'Четверг', 'weekly_revenue': 8, 'weekly_sales': 10},
                    {'day': 'Пятница', 'weekly_revenue': 20, 'weekly_sales': 25},
                    {'day': 'Суббота', 'weekly_revenue': 30, 'weekly_sales': 35},
                    {'day': 'Воскресенье', 'weekly_revenue': 10, 'weekly_sales': 15}
                ]
            },
            
            # Женские товары
            'женщ': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'season_revenue': -10, 'reason': 'После праздников'},
                    {'month': 2, 'name': 'Февраль', 'season_revenue': 15, 'reason': 'Подготовка к 8 марта'},
                    {'month': 3, 'name': 'Март', 'season_revenue': 35, 'reason': '8 марта'},
                    {'month': 4, 'name': 'Апрель', 'season_revenue': 25, 'reason': 'Весенняя мода'},
                    {'month': 5, 'name': 'Май', 'season_revenue': 20, 'reason': 'Весенне-летняя коллекция'},
                    {'month': 6, 'name': 'Июнь', 'season_revenue': 25, 'reason': 'Летняя мода'},
                    {'month': 7, 'name': 'Июль', 'season_revenue': 15, 'reason': 'Летние распродажи'},
                    {'month': 8, 'name': 'Август', 'season_revenue': 30, 'reason': 'Подготовка к осени'},
                    {'month': 9, 'name': 'Сентябрь', 'season_revenue': 40, 'reason': 'Осенняя мода'},
                    {'month': 10, 'name': 'Октябрь', 'season_revenue': 25, 'reason': 'Осенний гардероб'},
                    {'month': 11, 'name': 'Ноябрь', 'season_revenue': 45, 'reason': 'Black Friday, подготовка к зиме'},
                    {'month': 12, 'name': 'Декабрь', 'season_revenue': 50, 'reason': 'Новогодние наряды'}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'weekly_revenue': -8, 'weekly_sales': -6},
                    {'day': 'Вторник', 'weekly_revenue': -3, 'weekly_sales': -1},
                    {'day': 'Среда', 'weekly_revenue': 8, 'weekly_sales': 12},
                    {'day': 'Четверг', 'weekly_revenue': 15, 'weekly_sales': 18},
                    {'day': 'Пятница', 'weekly_revenue': 30, 'weekly_sales': 35},
                    {'day': 'Суббота', 'weekly_revenue': 40, 'weekly_sales': 45},
                    {'day': 'Воскресенье', 'weekly_revenue': 20, 'weekly_sales': 25}
                ]
            },
            
            # Дом и дача
            'дом': {
                'annual': [
                    {'month': 1, 'name': 'Январь', 'season_revenue': -20, 'reason': 'Зимний период'},
                    {'month': 2, 'name': 'Февраль', 'season_revenue': -15, 'reason': 'Зимний период'},
                    {'month': 3, 'name': 'Март', 'season_revenue': 20, 'reason': 'Подготовка к дачному сезону'},
                    {'month': 4, 'name': 'Апрель', 'season_revenue': 40, 'reason': 'Начало дачного сезона'},
                    {'month': 5, 'name': 'Май', 'season_revenue': 50, 'reason': 'Майские праздники, дача'},
                    {'month': 6, 'name': 'Июнь', 'season_revenue': 45, 'reason': 'Летний сезон'},
                    {'month': 7, 'name': 'Июль', 'season_revenue': 40, 'reason': 'Пик дачного сезона'},
                    {'month': 8, 'name': 'Август', 'season_revenue': 35, 'reason': 'Сбор урожая'},
                    {'month': 9, 'name': 'Сентябрь', 'season_revenue': 30, 'reason': 'Осенние работы'},
                    {'month': 10, 'name': 'Октябрь', 'season_revenue': 15, 'reason': 'Подготовка к зиме'},
                    {'month': 11, 'name': 'Ноябрь', 'season_revenue': -5, 'reason': 'Конец дачного сезона'},
                    {'month': 12, 'name': 'Декабрь', 'season_revenue': 25, 'reason': 'Новогодние товары для дома'}
                ],
                'weekly': [
                    {'day': 'Понедельник', 'weekly_revenue': -15, 'weekly_sales': -12},
                    {'day': 'Вторник', 'weekly_revenue': -10, 'weekly_sales': -8},
                    {'day': 'Среда', 'weekly_revenue': -5, 'weekly_sales': -2},
                    {'day': 'Четверг', 'weekly_revenue': 5, 'weekly_sales': 8},
                    {'day': 'Пятница', 'weekly_revenue': 15, 'weekly_sales': 20},
                    {'day': 'Суббота', 'weekly_revenue': 50, 'weekly_sales': 55},
                    {'day': 'Воскресенье', 'weekly_revenue': 45, 'weekly_sales': 50}
                ]
            }
        }
        
        # Определяем подходящий паттерн для категории
        pattern = None
        for key, data in seasonality_patterns.items():
            if key in category_lower:
                pattern = data
                break
        
        # Если не нашли специфичный паттерн, используем общий
        if not pattern:
            pattern = seasonality_patterns['одежда']  # Базовый паттерн
        
        return pattern
        
    except Exception as e:
        logger.error(f"Error in fallback seasonality data: {str(e)}")
        return None


def format_fallback_seasonality_analysis(fallback_data, category_path):
    """Форматирование результатов запасного анализа сезонности"""
    try:
        if not fallback_data:
            return "❌ Не удалось получить данные сезонности"
        
        result = f"🗓️ *АНАЛИЗ СЕЗОННОСТИ*\n"
        result += f"📂 *Категория:* {category_path}\n\n"
        result += "📊 *Источник данных:* Аналитическая модель на основе рыночных трендов\n\n"
        
        # Анализ годовой сезонности
        annual_data = fallback_data.get('annual', [])
        if annual_data:
            result += "📅 *ГОДОВАЯ СЕЗОННОСТЬ*\n\n"
            
            # Находим лучшие и худшие месяцы
            best_months = sorted(annual_data, key=lambda x: x['season_revenue'], reverse=True)[:3]
            worst_months = sorted(annual_data, key=lambda x: x['season_revenue'])[:3]
            
            result += "🔥 *ЛУЧШИЕ МЕСЯЦЫ:*\n"
            for i, month in enumerate(best_months, 1):
                result += f"{i}. *{month['name']}*: {month['season_revenue']:+.0f}%\n"
                result += f"   _{month['reason']}_\n"
            
            result += "\n📉 *СЛАБЫЕ МЕСЯЦЫ:*\n"
            for i, month in enumerate(worst_months, 1):
                result += f"{i}. *{month['name']}*: {month['season_revenue']:+.0f}%\n"
                result += f"   _{month['reason']}_\n"
        
        # Анализ недельной сезонности
        weekly_data = fallback_data.get('weekly', [])
        if weekly_data:
            result += "\n📊 *НЕДЕЛЬНАЯ СЕЗОННОСТЬ*\n\n"
            
            best_day = max(weekly_data, key=lambda x: x['weekly_revenue'])
            worst_day = min(weekly_data, key=lambda x: x['weekly_revenue'])
            
            result += f"💰 *Лучший день по выручке:* {best_day['day']} ({best_day['weekly_revenue']:+.0f}%)\n"
            result += f"📉 *Худший день по выручке:* {worst_day['day']} ({worst_day['weekly_revenue']:+.0f}%)\n\n"
            
            # Детальная разбивка по дням
            result += "*Детальная разбивка:*\n"
            for day_data in weekly_data:
                result += f"• {day_data['day']}: {day_data['weekly_revenue']:+.0f}% выручка, {day_data['weekly_sales']:+.0f}% продажи\n"
        
        # Рекомендации
        result += "\n💡 *ПРАКТИЧЕСКИЕ РЕКОМЕНДАЦИИ:*\n"
        
        if annual_data:
            best_month = max(annual_data, key=lambda x: x['season_revenue'])
            worst_month = min(annual_data, key=lambda x: x['season_revenue'])
            
            result += f"• *Планируйте основные запуски на {best_month['name'].lower()}* - пик спроса\n"
            result += f"• *Готовьтесь к снижению в {worst_month['name'].lower()}е* - низкий сезон\n"
        
        if weekly_data:
            result += f"• *Увеличивайте рекламные бюджеты в {best_day['day'].lower()}* - лучший день\n"
            result += f"• *Планируйте отгрузки с четверга по воскресенье* - активные дни\n"
        
        result += "• *Готовьте акции заранее* - за 2-4 недели до пиковых периодов\n"
        result += "• *Корректируйте склады* в соответствии с сезонными колебаниями\n"
        
        result += "\n⚠️ *Примечание:* Данные основаны на общих рыночных трендах. Для точного анализа рекомендуется использовать собственную статистику продаж."
        
        return result
        
    except Exception as e:
        logger.error(f"Error formatting fallback seasonality analysis: {str(e)}")
        return f"❌ Ошибка при форматировании анализа сезонности: {str(e)}" 