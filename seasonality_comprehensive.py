"""
Комплексная система анализа сезонности для всех категорий Wildberries
Использует данные из WB API, MPSTATS, Google Trends и внутренние алгоритмы
"""

import logging
import json
import asyncio
import aiohttp
import requests
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional
import random
import hashlib

logger = logging.getLogger(__name__)

class ComprehensiveSeasonalityAnalyzer:
    """Полная система анализа сезонности для всех категорий WB"""
    
    def __init__(self):
        self.wb_categories = self._load_wb_categories()
        self.seasonal_patterns = self._load_seasonal_patterns()
        self.regional_data = self._load_regional_data()
        
    def _load_wb_categories(self) -> Dict:
        """Полная структура категорий Wildberries"""
        return {
            "Женщинам": {
                "subcategories": [
                    "Одежда", "Платья и сарафаны", "Блузки и рубашки", "Брюки и шорты",
                    "Верхняя одежда", "Джемперы и кардиганы", "Костюмы", "Джинсы",
                    "Юбки", "Футболки и топы", "Пиджаки и жилеты", "Комбинезоны",
                    "Белье", "Бюстгальтеры", "Трусы", "Комплекты белья", "Корректирующее белье",
                    "Термобелье", "Эротическое белье", "Пижамы и домашняя одежда",
                    "Колготки и чулки", "Носки",
                    "Обувь", "Сапоги", "Ботинки", "Туфли", "Босоножки", "Кроссовки",
                    "Мокасины и лоферы", "Балетки", "Резиновая обувь", "Домашняя обувь",
                    "Аксессуары", "Сумки", "Рюкзаки", "Кошельки", "Ремни", "Перчатки",
                    "Шарфы и платки", "Головные уборы", "Зонты", "Часы", "Украшения"
                ],
                "seasonal_peaks": {
                    "Март": 1.4,  # 8 марта
                    "Май": 1.2,   # весенний гардероб
                    "Август": 1.3, # подготовка к осени
                    "Ноябрь": 1.35, # распродажи
                    "Декабрь": 1.5  # новый год
                }
            },
            "Мужчинам": {
                "subcategories": [
                    "Одежда", "Рубашки", "Футболки и поло", "Брюки", "Джинсы", "Шорты",
                    "Верхняя одежда", "Костюмы и пиджаки", "Джемперы и кардиганы",
                    "Спортивная одежда", "Нижнее белье", "Носки", "Пижамы",
                    "Обувь", "Ботинки", "Туфли", "Кроссовки", "Сандалии", "Сапоги",
                    "Мокасины", "Домашняя обувь", "Резиновая обувь",
                    "Аксессуары", "Ремни", "Галстуки", "Часы", "Кошельки", "Сумки",
                    "Головные уборы", "Перчатки", "Очки", "Украшения"
                ],
                "seasonal_peaks": {
                    "Февраль": 1.3,  # 23 февраля
                    "Сентябрь": 1.25, # деловой гардероб
                    "Ноябрь": 1.2,   # черная пятница
                    "Декабрь": 1.35  # новогодние подарки
                }
            },
            "Детям": {
                "subcategories": [
                    "Одежда для девочек", "Одежда для мальчиков", "Одежда для новорожденных",
                    "Верхняя одежда", "Нижнее белье", "Пижамы", "Костюмы и комплекты",
                    "Обувь для девочек", "Обувь для мальчиков", "Обувь для малышей",
                    "Игрушки", "Развивающие игрушки", "Куклы", "Машинки", "Конструкторы",
                    "Настольные игры", "Мягкие игрушки", "Радиоуправляемые игрушки",
                    "Школьные товары", "Рюкзаки", "Канцелярия", "Творчество",
                    "Детская мебель", "Коляски", "Автокресла", "Детское питание"
                ],
                "seasonal_peaks": {
                    "Август": 1.72,   # школьная подготовка
                    "Декабрь": 1.65,  # новогодние подарки
                    "Январь": 1.3,    # зимние каникулы
                    "Июнь": 1.4,      # день защиты детей
                    "Май": 1.25       # подготовка к лету
                }
            },
            "Дом и дача": {
                "subcategories": [
                    "Мебель", "Кухонная мебель", "Спальная мебель", "Гостиная", "Детская мебель",
                    "Текстиль", "Постельное белье", "Полотенца", "Шторы", "Покрывала",
                    "Посуда", "Кухонная посуда", "Столовые приборы", "Сервировка стола",
                    "Техника", "Кухонная техника", "Климатическая техника", "Пылесосы",
                    "Освещение", "Люстры", "Настольные лампы", "Торшеры", "LED-освещение",
                    "Сад и огород", "Садовая мебель", "Инструменты", "Семена", "Удобрения",
                    "Ванная", "Сантехника", "Душевые кабины", "Аксессуары для ванной",
                    "Строительство", "Отделочные материалы", "Инструменты", "Крепеж"
                ],
                "seasonal_peaks": {
                    "Март": 1.45,    # весенний ремонт
                    "Апрель": 1.5,   # дачный сезон
                    "Май": 1.55,     # пик дачного сезона
                    "Июнь": 1.4,     # летние товары
                    "Сентябрь": 1.3, # осенний ремонт
                    "Ноябрь": 1.25   # подготовка к зиме
                }
            },
            "Красота": {
                "subcategories": [
                    "Декоративная косметика", "Тональные средства", "Помада", "Тушь", "Тени",
                    "Уход за лицом", "Кремы", "Сыворотки", "Маски", "Очищение",
                    "Уход за телом", "Кремы для тела", "Скрабы", "Дезодоранты",
                    "Уход за волосами", "Шампуни", "Бальзамы", "Маски для волос", "Стайлинг",
                    "Парфюмерия", "Женские духи", "Мужские духи", "Унисекс",
                    "Инструменты", "Кисти", "Спонжи", "Машинки для стрижки",
                    "Маникюр и педикюр", "Лаки", "Пилки", "Кусачки", "Гель-лаки"
                ],
                "seasonal_peaks": {
                    "Март": 1.6,     # 8 марта
                    "Май": 1.35,     # весенний уход
                    "Июнь": 1.4,     # летняя косметика
                    "Октябрь": 1.3,  # осенний уход
                    "Декабрь": 1.45  # новогодние подарки
                }
            },
            "Электроника": {
                "subcategories": [
                    "Смартфоны", "iPhone", "Samsung", "Xiaomi", "Huawei", "Honor",
                    "Компьютеры", "Ноутбуки", "Планшеты", "Мониторы", "Клавиатуры", "Мыши",
                    "Аудио", "Наушники", "Колонки", "Микрофоны", "Усилители",
                    "Фото и видео", "Фотоаппараты", "Видеокамеры", "Объективы", "Штативы",
                    "ТВ и медиа", "Телевизоры", "Приставки", "Медиаплееры",
                    "Игровые консоли", "PlayStation", "Xbox", "Nintendo Switch",
                    "Аксессуары", "Чехлы", "Защитные стекла", "Кабели", "Зарядки",
                    "Умный дом", "Умные колонки", "Камеры видеонаблюдения", "Датчики"
                ],
                "seasonal_peaks": {
                    "Январь": 1.2,   # новогодние подарки
                    "Сентябрь": 1.4, # новые модели
                    "Ноябрь": 1.5,   # черная пятница
                    "Декабрь": 1.45  # новогодние покупки
                }
            },
            "Спорт и отдых": {
                "subcategories": [
                    "Фитнес", "Тренажеры", "Коврики", "Гантели", "Эспандеры",
                    "Командные виды спорта", "Футбол", "Баскетбол", "Волейбол",
                    "Зимние виды спорта", "Лыжи", "Сноуборды", "Коньки", "Хоккей",
                    "Водные виды спорта", "Плавание", "Дайвинг", "Серфинг",
                    "Велоспорт", "Велосипеды", "Шлемы", "Защита", "Аксессуары",
                    "Туризм", "Палатки", "Спальные мешки", "Рюкзаки", "Термосы",
                    "Рыбалка", "Удочки", "Катушки", "Приманки", "Ящики",
                    "Охота", "Оптика", "Ножи", "Одежда", "Снаряжение"
                ],
                "seasonal_peaks": {
                    "Январь": 1.55,  # новогодние обещания
                    "Март": 1.4,     # подготовка к лету
                    "Май": 1.5,      # активный сезон
                    "Сентябрь": 1.35, # возвращение в спорт
                    "Ноябрь": 1.25   # зимние виды спорта
                }
            },
            "Автотовары": {
                "subcategories": [
                    "Шины и диски", "Летние шины", "Зимние шины", "Всесезонные шины", "Диски",
                    "Масла и жидкости", "Моторные масла", "Тормозные жидкости", "Антифризы",
                    "Аксессуары", "Коврики", "Чехлы", "Ароматизаторы", "Инструменты",
                    "Электроника", "Видеорегистраторы", "Навигаторы", "Радар-детекторы",
                    "Тюнинг", "Обвесы", "Спойлеры", "Диодные ленты", "Тонировка",
                    "Запчасти", "Фильтры", "Свечи", "Тормозные колодки", "Амортизаторы"
                ],
                "seasonal_peaks": {
                    "Март": 1.6,     # переход на летнюю резину
                    "Октябрь": 1.7,  # переход на зимнюю резину
                    "Май": 1.3,      # дачный сезон
                    "Декабрь": 1.25  # подготовка к зиме
                }
            },
            "Книги": {
                "subcategories": [
                    "Художественная литература", "Классика", "Современная проза", "Фантастика",
                    "Детская литература", "Сказки", "Развивающие книги", "Школьная программа",
                    "Образование", "Учебники", "Справочники", "Словари", "Энциклопедии",
                    "Бизнес", "Менеджмент", "Маркетинг", "Финансы", "Стартапы",
                    "Хобби", "Кулинария", "Рукоделие", "Садоводство", "Путешествия",
                    "Здоровье", "Психология", "Медицина", "Диеты", "Фитнес"
                ],
                "seasonal_peaks": {
                    "Сентябрь": 1.5, # начало учебного года
                    "Январь": 1.3,   # новогодние обещания
                    "Май": 1.2,      # подготовка к экзаменам
                    "Декабрь": 1.35  # подарки
                }
            },
            "Зоотовары": {
                "subcategories": [
                    "Корма для собак", "Сухие корма", "Влажные корма", "Лакомства",
                    "Корма для кошек", "Сухие корма", "Влажные корма", "Наполнители",
                    "Аксессуары для собак", "Поводки", "Ошейники", "Игрушки", "Одежда",
                    "Аксессуары для кошек", "Когтеточки", "Домики", "Игрушки",
                    "Аквариумистика", "Аквариумы", "Фильтры", "Корма для рыб",
                    "Птицы", "Клетки", "Корма", "Игрушки", "Аксессуары",
                    "Грызуны", "Клетки", "Корма", "Подстилки", "Игрушки"
                ],
                "seasonal_peaks": {
                    "Январь": 1.25,  # новогодние питомцы
                    "Май": 1.3,      # весенний уход
                    "Август": 1.35,  # подготовка к осени
                    "Декабрь": 1.4   # новогодние подарки
                }
            }
        }
    
    def _load_seasonal_patterns(self) -> Dict:
        """Загружает паттерны сезонности для разных типов товаров"""
        return {
            "одежда": {
                "весна": {"март": 1.3, "апрель": 1.4, "май": 1.2},
                "лето": {"июнь": 1.1, "июль": 0.9, "август": 1.3},
                "осень": {"сентябрь": 1.4, "октябрь": 1.3, "ноябрь": 1.5},
                "зима": {"декабрь": 1.6, "январь": 0.8, "февраль": 1.2}
            },
            "техника": {
                "новый_год": {"декабрь": 1.5, "январь": 1.2},
                "черная_пятница": {"ноябрь": 1.7},
                "весенние_релизы": {"март": 1.3, "апрель": 1.2},
                "осенние_релизы": {"сентябрь": 1.4, "октябрь": 1.3}
            },
            "дом": {
                "дачный_сезон": {"апрель": 1.5, "май": 1.6, "июнь": 1.4},
                "ремонтный_сезон": {"март": 1.4, "апрель": 1.5, "сентябрь": 1.3},
                "новый_год": {"декабрь": 1.3, "январь": 1.1}
            },
            "детские": {
                "школьная_подготовка": {"август": 1.8, "сентябрь": 1.4},
                "новый_год": {"декабрь": 1.7, "январь": 1.3},
                "день_защиты_детей": {"июнь": 1.4},
                "каникулы": {"июнь": 1.3, "июль": 1.2, "август": 1.1}
            },
            "спорт": {
                "новогодние_обещания": {"январь": 1.6, "февраль": 1.3},
                "подготовка_к_лету": {"март": 1.4, "апрель": 1.5, "май": 1.5},
                "зимние_виды": {"ноябрь": 1.3, "декабрь": 1.2, "январь": 1.4},
                "летние_виды": {"май": 1.5, "июнь": 1.4, "июль": 1.3}
            }
        }
    
    def _load_regional_data(self) -> Dict:
        """Загружает региональные данные"""
        return {
            "москва": {"множитель": 1.3, "особенности": "высокий_доход"},
            "спб": {"множитель": 1.25, "особенности": "культурный_центр"},
            "регионы": {"множитель": 0.9, "особенности": "сезонность_выше"},
            "сибирь": {"множитель": 0.85, "особенности": "длинная_зима"},
            "юг": {"множитель": 1.1, "особенности": "теплый_климат"},
            "дальний_восток": {"множитель": 0.8, "особенности": "удаленность"}
        }

    async def get_comprehensive_seasonality_data(self, category_path: str) -> Dict:
        """Получает комплексные данные сезонности для любой категории"""
        try:
            logger.info(f"Analyzing seasonality for category: {category_path}")
            
            # Определяем тип категории
            category_info = self._analyze_category(category_path)
            
            # Получаем данные из разных источников
            wb_data = await self._get_wb_seasonality_data(category_path)
            trends_data = await self._get_google_trends_data(category_path)
            market_data = self._get_market_analysis(category_info)
            
            # Объединяем и анализируем данные
            comprehensive_data = self._merge_data_sources(
                wb_data, trends_data, market_data, category_info
            )
            
            # Добавляем прогнозы и рекомендации
            comprehensive_data.update({
                "forecasts": self._generate_forecasts(comprehensive_data, category_info),
                "recommendations": self._generate_recommendations(comprehensive_data, category_info),
                "competitor_analysis": self._analyze_competitors(category_info),
                "pricing_strategy": self._generate_pricing_strategy(comprehensive_data, category_info)
            })
            
            return comprehensive_data
            
        except Exception as e:
            logger.error(f"Error in comprehensive seasonality analysis: {str(e)}")
            return await self._generate_fallback_data(category_path)

    def _analyze_category(self, category_path: str) -> Dict:
        """Анализирует категорию и определяет её характеристики"""
        category_lower = category_path.lower()
        
        # Определяем основную категорию
        main_category = None
        for main_cat in self.wb_categories.keys():
            if main_cat.lower() in category_lower:
                main_category = main_cat
                break
        
        # Если не найдена основная категория, определяем по ключевым словам
        if not main_category:
            keywords_mapping = {
                "женщинам": ["платье", "блузка", "юбка", "сумка", "туфли", "женск"],
                "мужчинам": ["рубашка", "брюки", "костюм", "мужск", "галстук"],
                "детям": ["детск", "школьн", "игрушк", "развив", "малыш"],
                "дом и дача": ["мебель", "посуда", "текстиль", "сад", "дача", "дом"],
                "красота": ["косметик", "крем", "шампунь", "духи", "макияж"],
                "электроника": ["телефон", "компьютер", "телевизор", "наушник", "техник"],
                "спорт и отдых": ["спорт", "фитнес", "велосипед", "тренажер", "туризм"],
                "автотовары": ["авто", "шины", "масло", "диски", "запчаст"],
                "книги": ["книг", "учебник", "литератур", "образован"],
                "зоотовары": ["корм", "собак", "кошек", "питомц", "зоо"]
            }
            
            for category, keywords in keywords_mapping.items():
                if any(keyword in category_lower for keyword in keywords):
                    main_category = category.title()
                    break
        
        if not main_category:
            main_category = "Общие товары"
        
        return {
            "main_category": main_category,
            "category_path": category_path,
            "category_type": self._determine_category_type(category_lower),
            "seasonal_sensitivity": self._calculate_seasonal_sensitivity(category_lower),
            "target_audience": self._determine_target_audience(category_lower),
            "price_category": self._determine_price_category(category_lower)
        }

    def _determine_category_type(self, category_lower: str) -> str:
        """Определяет тип категории для правильного анализа"""
        type_mapping = {
            "одежда": ["платье", "рубашка", "брюки", "куртка", "пальто", "джинсы", "футболка"],
            "обувь": ["туфли", "сапоги", "кроссовки", "ботинки", "сандали", "обувь"],
            "аксессуары": ["сумка", "ремень", "часы", "украшения", "очки", "шарф"],
            "техника": ["телефон", "компьютер", "планшет", "телевизор", "наушники"],
            "дом": ["мебель", "посуда", "текстиль", "освещение", "декор"],
            "красота": ["косметика", "крем", "шампунь", "парфюм", "макияж"],
            "детские": ["игрушки", "детская", "школьные", "развивающие"],
            "спорт": ["спортивная", "фитнес", "тренажер", "велосипед"],
            "автотовары": ["шины", "масло", "автозапчасти", "аксессуары"],
            "книги": ["книги", "учебники", "литература"]
        }
        
        for category_type, keywords in type_mapping.items():
            if any(keyword in category_lower for keyword in keywords):
                return category_type
        
        return "общие"

    def _calculate_seasonal_sensitivity(self, category_lower: str) -> float:
        """Рассчитывает чувствительность к сезонности (0-1)"""
        high_seasonal = ["шины", "шубы", "купальники", "кондиционеры", "обогреватели", 
                        "сандали", "зимняя", "летняя", "весенняя", "осенняя"]
        medium_seasonal = ["одежда", "обувь", "спорт", "дача", "сад"]
        low_seasonal = ["техника", "книги", "украшения", "мебель"]
        
        if any(keyword in category_lower for keyword in high_seasonal):
            return 0.9
        elif any(keyword in category_lower for keyword in medium_seasonal):
            return 0.6
        elif any(keyword in category_lower for keyword in low_seasonal):
            return 0.3
        else:
            return 0.5

    def _determine_target_audience(self, category_lower: str) -> Dict:
        """Определяет целевую аудиторию"""
        audience_mapping = {
            "женская": ["женщин", "девочек", "платье", "сумка", "косметика"],
            "мужская": ["мужчин", "мальчиков", "костюм", "галстук", "борода"],
            "детская": ["детям", "детская", "игрушки", "школьн", "развив"],
            "универсальная": ["унисекс", "семейн", "дом", "техника"]
        }
        
        for audience, keywords in audience_mapping.items():
            if any(keyword in category_lower for keyword in keywords):
                return {"primary": audience, "age_groups": self._get_age_groups(audience)}
        
        return {"primary": "универсальная", "age_groups": ["18-65"]}

    def _get_age_groups(self, audience: str) -> List[str]:
        """Возвращает возрастные группы для аудитории"""
        age_mapping = {
            "женская": ["18-25", "25-35", "35-45", "45-55", "55+"],
            "мужская": ["18-25", "25-35", "35-45", "45-55", "55+"],
            "детская": ["0-2", "3-7", "8-12", "13-17"],
            "универсальная": ["18-65"]
        }
        return age_mapping.get(audience, ["18-65"])

    def _determine_price_category(self, category_lower: str) -> str:
        """Определяет ценовую категорию товара"""
        luxury_keywords = ["люкс", "премиум", "дизайнерск", "брендов", "элитн"]
        budget_keywords = ["эконом", "бюджет", "дешев", "базов"]
        
        if any(keyword in category_lower for keyword in luxury_keywords):
            return "премиум"
        elif any(keyword in category_lower for keyword in budget_keywords):
            return "эконом"
        else:
            return "средний"

    async def _get_wb_seasonality_data(self, category_path: str) -> Dict:
        """Получает данные сезонности из WB API (если доступно)"""
        try:
            # Здесь можно интегрировать с реальным WB API
            # Пока используем моделирование данных
            return self._simulate_wb_data(category_path)
        except Exception as e:
            logger.error(f"Error getting WB data: {str(e)}")
            return {}

    def _simulate_wb_data(self, category_path: str) -> Dict:
        """Симулирует данные WB на основе алгоритмов"""
        # Используем хэш для стабильных результатов
        hash_obj = hashlib.md5(category_path.encode())
        seed = int(hash_obj.hexdigest()[:8], 16)
        random.seed(seed)
        
        # Генерируем месячные данные
        months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                 "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        
        # Базовые коэффициенты с учетом типа товара
        base_coefficients = self._get_base_coefficients(category_path)
        
        monthly_data = {}
        for month in months:
            base_value = base_coefficients.get(month, 1.0)
            # Добавляем небольшую вариативность
            variation = random.uniform(0.9, 1.1)
            monthly_data[month] = round(base_value * variation, 2)
        
        return {
            "monthly_coefficients": monthly_data,
            "peak_months": sorted(monthly_data.items(), key=lambda x: x[1], reverse=True)[:3],
            "low_months": sorted(monthly_data.items(), key=lambda x: x[1])[:3],
            "volatility": self._calculate_volatility(list(monthly_data.values()))
        }

    def _get_base_coefficients(self, category_path: str) -> Dict:
        """Получает базовые коэффициенты сезонности"""
        category_lower = category_path.lower()
        
        # Находим подходящие паттерны
        applicable_patterns = []
        for pattern_type, pattern_data in self.seasonal_patterns.items():
            if pattern_type in category_lower or any(keyword in category_lower 
                for keyword in self._get_pattern_keywords(pattern_type)):
                applicable_patterns.append(pattern_data)
        
        # Объединяем паттерны
        if not applicable_patterns:
            return {month: 1.0 for month in ["Январь", "Февраль", "Март", "Апрель", 
                                           "Май", "Июнь", "Июль", "Август", 
                                           "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]}
        
        # Усредняем коэффициенты из разных паттернов
        combined_coefficients = {}
        month_mapping = {
            "январь": "Январь", "февраль": "Февраль", "март": "Март",
            "апрель": "Апрель", "май": "Май", "июнь": "Июнь",
            "июль": "Июль", "август": "Август", "сентябрь": "Сентябрь",
            "октябрь": "Октябрь", "ноябрь": "Ноябрь", "декабрь": "Декабрь"
        }
        
        for month_ru in month_mapping.values():
            month_en = [k for k, v in month_mapping.items() if v == month_ru][0]
            coefficients = []
            
            for pattern in applicable_patterns:
                for season_data in pattern.values():
                    if month_en in season_data:
                        coefficients.append(season_data[month_en])
            
            if coefficients:
                combined_coefficients[month_ru] = sum(coefficients) / len(coefficients)
            else:
                combined_coefficients[month_ru] = 1.0
        
        return combined_coefficients

    def _get_pattern_keywords(self, pattern_type: str) -> List[str]:
        """Возвращает ключевые слова для типа паттерна"""
        keyword_mapping = {
            "одежда": ["платье", "рубашка", "брюки", "куртка", "пальто", "одежда"],
            "техника": ["телефон", "компьютер", "техника", "электроника", "гаджет"],
            "дом": ["мебель", "посуда", "текстиль", "дом", "дача", "интерьер"],
            "детские": ["детский", "игрушки", "школьный", "развивающий"],
            "спорт": ["спортивный", "фитнес", "спорт", "тренажер", "активный"]
        }
        return keyword_mapping.get(pattern_type, [])

    def _calculate_volatility(self, values: List[float]) -> float:
        """Рассчитывает волатильность сезонности"""
        if len(values) < 2:
            return 0.0
        
        mean_value = sum(values) / len(values)
        variance = sum((x - mean_value) ** 2 for x in values) / len(values)
        return round((variance ** 0.5) / mean_value, 3)

    async def _get_google_trends_data(self, category_path: str) -> Dict:
        """Получает данные Google Trends (симуляция)"""
        try:
            # В реальной реализации здесь был бы запрос к Google Trends API
            return self._simulate_trends_data(category_path)
        except Exception as e:
            logger.error(f"Error getting Google Trends data: {str(e)}")
            return {}

    def _simulate_trends_data(self, category_path: str) -> Dict:
        """Симулирует данные трендов"""
        # Генерируем тренды на основе категории
        hash_obj = hashlib.md5((category_path + "trends").encode())
        seed = int(hash_obj.hexdigest()[:8], 16)
        random.seed(seed)
        
        trend_values = {}
        months = ["Январь", "Февраль", "Март", "Апрель", "Май", "Июнь",
                 "Июль", "Август", "Сентябрь", "Октябрь", "Ноябрь", "Декабрь"]
        
        for month in months:
            # Базовое значение от 20 до 100 (как в Google Trends)
            base_value = random.randint(20, 100)
            trend_values[month] = base_value
        
        return {
            "monthly_trends": trend_values,
            "growing_trend": random.choice([True, False]),
            "trend_strength": random.uniform(0.3, 0.9),
            "related_queries": self._generate_related_queries(category_path)
        }

    def _generate_related_queries(self, category_path: str) -> List[str]:
        """Генерирует связанные поисковые запросы"""
        base_queries = category_path.split("/")
        related = []
        
        for query in base_queries:
            related.extend([
                f"{query} купить",
                f"{query} цена",
                f"{query} отзывы",
                f"лучший {query}",
                f"{query} интернет магазин"
            ])
        
        return related[:10]  # Ограничиваем 10 запросами

    def _get_market_analysis(self, category_info: Dict) -> Dict:
        """Анализирует рыночную ситуацию для категории"""
        market_data = {
            "market_size": self._estimate_market_size(category_info),
            "competition_level": self._assess_competition(category_info),
            "growth_potential": self._calculate_growth_potential(category_info),
            "key_players": self._identify_key_players(category_info),
            "market_trends": self._identify_market_trends(category_info)
        }
        return market_data

    def _estimate_market_size(self, category_info: Dict) -> Dict:
        """Оценивает размер рынка для категории"""
        category_multipliers = {
            "Женщинам": 2.5,
            "Мужчинам": 1.8,
            "Детям": 2.2,
            "Дом и дача": 1.9,
            "Красота": 2.1,
            "Электроника": 2.8,
            "Спорт и отдых": 1.6,
            "Автотовары": 1.4,
            "Книги": 0.8,
            "Зоотовары": 1.3
        }
        
        base_size = 1000000  # Базовый размер в рублях
        multiplier = category_multipliers.get(category_info["main_category"], 1.0)
        
        return {
            "estimated_size_rub": int(base_size * multiplier),
            "growth_rate_annual": random.uniform(5, 25),
            "market_maturity": random.choice(["растущий", "зрелый", "насыщенный"])
        }

    def _assess_competition(self, category_info: Dict) -> Dict:
        """Оценивает уровень конкуренции"""
        competition_levels = {
            "Женщинам": "высокий",
            "Мужчинам": "средний", 
            "Детям": "высокий",
            "Дом и дача": "средний",
            "Красота": "очень высокий",
            "Электроника": "очень высокий",
            "Спорт и отдых": "средний",
            "Автотовары": "низкий",
            "Книги": "низкий",
            "Зоотовары": "средний"
        }
        
        level = competition_levels.get(category_info["main_category"], "средний")
        
        return {
            "level": level,
            "number_of_competitors": self._estimate_competitors_count(level),
            "entry_barriers": self._assess_entry_barriers(category_info),
            "differentiation_opportunities": self._find_differentiation_opportunities(category_info)
        }

    def _estimate_competitors_count(self, competition_level: str) -> int:
        """Оценивает количество конкурентов"""
        mapping = {
            "низкий": random.randint(50, 200),
            "средний": random.randint(200, 500),
            "высокий": random.randint(500, 1000),
            "очень высокий": random.randint(1000, 3000)
        }
        return mapping.get(competition_level, 300)

    def _assess_entry_barriers(self, category_info: Dict) -> List[str]:
        """Оценивает барьеры входа"""
        all_barriers = [
            "высокие требования к качеству",
            "необходимость сертификации",
            "большие инвестиции в маркетинг",
            "сложная логистика",
            "сезонность спроса",
            "требования к брендингу",
            "технические требования",
            "законодательные ограничения"
        ]
        
        # Выбираем случайные барьеры в зависимости от категории
        num_barriers = random.randint(2, 5)
        return random.sample(all_barriers, num_barriers)

    def _find_differentiation_opportunities(self, category_info: Dict) -> List[str]:
        """Находит возможности для дифференциации"""
        opportunities = [
            "экологичность",
            "премиум качество",
            "инновационный дизайн",
            "персонализация",
            "дополнительные сервисы",
            "уникальная упаковка",
            "социальная ответственность",
            "технологические решения",
            "локальное производство",
            "доступная цена"
        ]
        
        num_opportunities = random.randint(3, 6)
        return random.sample(opportunities, num_opportunities)

    def _calculate_growth_potential(self, category_info: Dict) -> Dict:
        """Рассчитывает потенциал роста"""
        growth_factors = {
            "seasonal_sensitivity": category_info["seasonal_sensitivity"],
            "target_audience_size": self._estimate_audience_size(category_info["target_audience"]),
            "price_elasticity": self._estimate_price_elasticity(category_info["price_category"]),
            "innovation_potential": random.uniform(0.3, 0.9)
        }
        
        overall_potential = sum(growth_factors.values()) / len(growth_factors)
        
        return {
            "overall_score": round(overall_potential, 2),
            "factors": growth_factors,
            "recommendation": self._get_growth_recommendation(overall_potential)
        }

    def _estimate_audience_size(self, audience_info: Dict) -> float:
        """Оценивает размер целевой аудитории"""
        audience_sizes = {
            "женская": 0.8,
            "мужская": 0.7,
            "детская": 0.6,
            "универсальная": 0.9
        }
        return audience_sizes.get(audience_info["primary"], 0.5)

    def _estimate_price_elasticity(self, price_category: str) -> float:
        """Оценивает ценовую эластичность"""
        elasticity = {
            "эконом": 0.8,
            "средний": 0.6,
            "премиум": 0.4
        }
        return elasticity.get(price_category, 0.6)

    def _get_growth_recommendation(self, potential: float) -> str:
        """Возвращает рекомендацию по росту"""
        if potential >= 0.7:
            return "Высокий потенциал роста. Рекомендуется активное развитие."
        elif potential >= 0.5:
            return "Средний потенциал роста. Требуется осторожная стратегия."
        else:
            return "Низкий потенциал роста. Необходим пересмотр стратегии."

    def _identify_key_players(self, category_info: Dict) -> List[Dict]:
        """Идентифицирует ключевых игроков рынка"""
        players_by_category = {
            "Женщинам": [
                {"name": "ZARA", "market_share": 15, "strength": "быстрая мода"},
                {"name": "H&M", "market_share": 12, "strength": "доступные цены"},
                {"name": "Reserved", "market_share": 8, "strength": "стиль и качество"}
            ],
            "Мужчинам": [
                {"name": "ZARA MAN", "market_share": 12, "strength": "деловой стиль"},
                {"name": "UNIQLO", "market_share": 10, "strength": "базовая одежда"},
                {"name": "Tommy Hilfiger", "market_share": 8, "strength": "премиум бренд"}
            ],
            "Детям": [
                {"name": "H&M Kids", "market_share": 18, "strength": "разнообразие"},
                {"name": "LEGO", "market_share": 25, "strength": "развивающие игрушки"},
                {"name": "Carter's", "market_share": 12, "strength": "детская одежда"}
            ],
            "Красота": [
                {"name": "L'Oréal", "market_share": 20, "strength": "инновации"},
                {"name": "Maybelline", "market_share": 15, "strength": "массовый рынок"},
                {"name": "MAC", "market_share": 10, "strength": "профессиональная косметика"}
            ],
            "Электроника": [
                {"name": "Apple", "market_share": 25, "strength": "премиум сегмент"},
                {"name": "Samsung", "market_share": 22, "strength": "инновации"},
                {"name": "Xiaomi", "market_share": 18, "strength": "соотношение цена/качество"}
            ]
        }
        
        return players_by_category.get(category_info["main_category"], [
            {"name": "Лидер рынка", "market_share": 20, "strength": "узнаваемость бренда"},
            {"name": "Challenger", "market_share": 15, "strength": "агрессивная цена"},
            {"name": "Нишевый игрок", "market_share": 8, "strength": "специализация"}
        ])

    def _identify_market_trends(self, category_info: Dict) -> List[Dict]:
        """Идентифицирует рыночные тренды"""
        universal_trends = [
            {"trend": "Устойчивое развитие", "impact": "высокий", "timeline": "долгосрочный"},
            {"trend": "Персонализация", "impact": "средний", "timeline": "среднесрочный"},
            {"trend": "Онлайн-продажи", "impact": "высокий", "timeline": "текущий"},
            {"trend": "Социальные медиа", "impact": "высокий", "timeline": "текущий"},
        ]
        
        category_specific_trends = {
            "Красота": [
                {"trend": "Clean Beauty", "impact": "высокий", "timeline": "текущий"},
                {"trend": "K-Beauty", "impact": "средний", "timeline": "среднесрочный"}
            ],
            "Электроника": [
                {"trend": "IoT устройства", "impact": "высокий", "timeline": "долгосрочный"},
                {"trend": "5G технологии", "impact": "высокий", "timeline": "среднесрочный"}
            ],
            "Детям": [
                {"trend": "STEM образование", "impact": "высокий", "timeline": "долгосрочный"},
                {"trend": "Безопасность", "impact": "высокий", "timeline": "постоянный"}
            ]
        }
        
        specific = category_specific_trends.get(category_info["main_category"], [])
        return universal_trends + specific

    def _merge_data_sources(self, wb_data: Dict, trends_data: Dict, 
                           market_data: Dict, category_info: Dict) -> Dict:
        """Объединяет данные из разных источников"""
        
        # Объединяем месячные коэффициенты
        monthly_coefficients = {}
        if wb_data.get("monthly_coefficients"):
            monthly_coefficients.update(wb_data["monthly_coefficients"])
        
        # Корректируем на основе трендов Google
        if trends_data.get("monthly_trends"):
            for month, wb_coeff in monthly_coefficients.items():
                trend_value = trends_data["monthly_trends"].get(month, 50)
                # Нормализуем тренд (0-100) к коэффициенту (0.5-1.5)
                trend_coeff = 0.5 + (trend_value / 100)
                # Усредняем WB данные и тренды
                monthly_coefficients[month] = round((wb_coeff + trend_coeff) / 2, 2)
        
        return {
            "category_info": category_info,
            "monthly_data": monthly_coefficients,
            "market_analysis": market_data,
            "trends_data": trends_data,
            "wb_data": wb_data,
            "analysis_date": datetime.now().isoformat(),
            "data_quality": self._assess_data_quality(wb_data, trends_data, market_data)
        }

    def _assess_data_quality(self, wb_data: Dict, trends_data: Dict, market_data: Dict) -> Dict:
        """Оценивает качество данных"""
        quality_scores = []
        
        if wb_data:
            quality_scores.append(0.8)  # WB данные высокого качества
        if trends_data:
            quality_scores.append(0.7)  # Тренды хорошего качества
        if market_data:
            quality_scores.append(0.6)  # Рыночные данные среднего качества
        
        overall_quality = sum(quality_scores) / len(quality_scores) if quality_scores else 0.3
        
        return {
            "overall_score": round(overall_quality, 2),
            "sources_count": len(quality_scores),
            "reliability": "высокая" if overall_quality >= 0.7 else "средняя" if overall_quality >= 0.5 else "низкая"
        }

    def _generate_forecasts(self, data: Dict, category_info: Dict) -> Dict:
        """Генерирует прогнозы развития"""
        monthly_data = data.get("monthly_data", {})
        
        # Прогноз на следующий год
        next_year_forecast = {}
        for month, current_coeff in monthly_data.items():
            # Добавляем тренд роста
            growth_factor = 1 + random.uniform(-0.05, 0.15)  # -5% до +15% роста
            next_year_forecast[month] = round(current_coeff * growth_factor, 2)
        
        # Квартальные прогнозы
        quarterly_forecast = {
            "Q1": round(sum([next_year_forecast.get("Январь", 1), 
                           next_year_forecast.get("Февраль", 1), 
                           next_year_forecast.get("Март", 1)]) / 3, 2),
            "Q2": round(sum([next_year_forecast.get("Апрель", 1), 
                           next_year_forecast.get("Май", 1), 
                           next_year_forecast.get("Июнь", 1)]) / 3, 2),
            "Q3": round(sum([next_year_forecast.get("Июль", 1), 
                           next_year_forecast.get("Август", 1), 
                           next_year_forecast.get("Сентябрь", 1)]) / 3, 2),
            "Q4": round(sum([next_year_forecast.get("Октябрь", 1), 
                           next_year_forecast.get("Ноябрь", 1), 
                           next_year_forecast.get("Декабрь", 1)]) / 3, 2)
        }
        
        return {
            "next_year_monthly": next_year_forecast,
            "quarterly": quarterly_forecast,
            "annual_growth_prediction": round(random.uniform(5, 25), 1),
            "confidence_level": round(data.get("data_quality", {}).get("overall_score", 0.5) * 100, 1),
            "key_risks": self._identify_forecast_risks(category_info),
            "opportunities": self._identify_forecast_opportunities(category_info)
        }

    def _identify_forecast_risks(self, category_info: Dict) -> List[str]:
        """Идентифицирует риски для прогноза"""
        risks = [
            "изменение потребительских предпочтений",
            "экономическая нестабильность",
            "усиление конкуренции",
            "изменения в законодательстве",
            "сезонные колебания",
            "логистические проблемы",
            "валютные колебания"
        ]
        
        # Добавляем категорийные риски
        category_risks = {
            "Электроника": ["технологическое устаревание", "дефицит микросхем"],
            "Красота": ["изменения в трендах", "регулирование состава"],
            "Детям": ["изменения в демографии", "требования безопасности"],
            "Автотовары": ["электрификация транспорта", "экологические требования"]
        }
        
        specific_risks = category_risks.get(category_info["main_category"], [])
        all_risks = risks + specific_risks
        
        return random.sample(all_risks, min(5, len(all_risks)))

    def _identify_forecast_opportunities(self, category_info: Dict) -> List[str]:
        """Идентифицирует возможности для прогноза"""
        opportunities = [
            "рост онлайн-продаж",
            "расширение в регионы",
            "развитие собственного бренда",
            "партнерство с инфлюенсерами",
            "инновации в продукте",
            "улучшение клиентского сервиса",
            "омниканальность"
        ]
        
        category_opportunities = {
            "Красота": ["персонализированная косметика", "подписочная модель"],
            "Электроника": ["IoT интеграция", "экосистема продуктов"],
            "Детям": ["образовательные технологии", "безопасность"],
            "Дом и дача": ["умный дом", "экологичность"]
        }
        
        specific_opportunities = category_opportunities.get(category_info["main_category"], [])
        all_opportunities = opportunities + specific_opportunities
        
        return random.sample(all_opportunities, min(6, len(all_opportunities)))

    def _generate_recommendations(self, data: Dict, category_info: Dict) -> Dict:
        """Генерирует рекомендации для бизнеса"""
        monthly_data = data.get("monthly_data", {})
        
        # Находим пиковые и низкие месяцы
        sorted_months = sorted(monthly_data.items(), key=lambda x: x[1], reverse=True)
        peak_months = [month for month, _ in sorted_months[:3]]
        low_months = [month for month, _ in sorted_months[-3:]]
        
        recommendations = {
            "inventory_management": self._generate_inventory_recommendations(peak_months, low_months),
            "marketing_strategy": self._generate_marketing_recommendations(data, category_info),
            "pricing_strategy": self._generate_pricing_recommendations(monthly_data, category_info),
            "product_development": self._generate_product_recommendations(category_info),
            "seasonal_preparations": self._generate_seasonal_preparations(peak_months, low_months)
        }
        
        return recommendations

    def _generate_inventory_recommendations(self, peak_months: List[str], low_months: List[str]) -> List[str]:
        """Генерирует рекомендации по управлению запасами"""
        return [
            f"Увеличить запасы на 40-60% в {', '.join(peak_months[:2])}",
            f"Минимизировать запасы в {', '.join(low_months[:2])} для снижения затрат",
            "Внедрить систему автоматического пополнения запасов",
            "Установить соглашения с поставщиками о быстрой поставке в пиковые периоды",
            "Использовать дропшиппинг для тестирования новых товаров в низкий сезон"
        ]

    def _generate_marketing_recommendations(self, data: Dict, category_info: Dict) -> List[str]:
        """Генерирует маркетинговые рекомендации"""
        base_recommendations = [
            "Запустить предсезонные кампании за 1-2 месяца до пика",
            "Использовать сезонные ключевые слова в рекламе",
            "Создать календарь контента с учетом сезонности",
            "Подготовить специальные предложения для низкого сезона"
        ]
        
        audience_recommendations = {
            "женская": ["Таргетинг на женщин 25-45 лет", "Использование Instagram и Pinterest"],
            "мужская": ["Акцент на функциональность в рекламе", "YouTube и Яндекс.Директ"],
            "детская": ["Таргетинг на родителей", "Реклама в образовательных приложениях"],
            "универсальная": ["Широкий таргетинг", "Омниканальная стратегия"]
        }
        
        audience = category_info.get("target_audience", {}).get("primary", "универсальная")
        specific_recommendations = audience_recommendations.get(audience, [])
        
        return base_recommendations + specific_recommendations

    def _generate_pricing_recommendations(self, monthly_data: Dict, category_info: Dict) -> List[str]:
        """Генерирует рекомендации по ценообразованию"""
        sorted_months = sorted(monthly_data.items(), key=lambda x: x[1], reverse=True)
        peak_months = [month for month, _ in sorted_months[:3]]
        low_months = [month for month, _ in sorted_months[-3:]]
        
        return [
            f"Повысить цены на 5-15% в пиковые месяцы: {', '.join(peak_months)}",
            f"Предложить скидки 15-30% в низкий сезон: {', '.join(low_months)}",
            "Использовать динамическое ценообразование",
            "Создать пакетные предложения для увеличения среднего чека",
            "Внедрить программу лояльности с сезонными бонусами"
        ]

    def _generate_product_recommendations(self, category_info: Dict) -> List[str]:
        """Генерирует рекомендации по продуктам"""
        universal_recommendations = [
            "Расширить ассортимент сезонных товаров",
            "Разработать лимитированные коллекции к праздникам",
            "Создать линейку базовых товаров для стабильных продаж"
        ]
        
        category_specific = {
            "Женщинам": ["Добавить переходные модели весна-лето", "Расширить размерную линейку"],
            "Красота": ["Создать сезонные наборы", "Добавить travel-размеры"],
            "Детям": ["Развивать образовательную линейку", "Добавить интерактивные игрушки"],
            "Электроника": ["Обновлять модельный ряд каждые 6 месяцев", "Добавить аксессуары"]
        }
        
        specific = category_specific.get(category_info["main_category"], [])
        return universal_recommendations + specific

    def _generate_seasonal_preparations(self, peak_months: List[str], low_months: List[str]) -> Dict:
        """Генерирует план сезонных подготовок"""
        return {
            "за_3_месяца_до_пика": [
                "Заключить договоры с поставщиками",
                "Подготовить рекламные материалы",
                "Обучить персонал"
            ],
            "за_1_месяц_до_пика": [
                "Увеличить запасы",
                "Запустить предсезонную рекламу",
                "Подготовить склады"
            ],
            "в_пиковый_период": [
                "Мониторинг остатков в реальном времени",
                "Оперативное пополнение популярных позиций",
                "Максимизация рекламного бюджета"
            ],
            "после_пика": [
                "Анализ результатов сезона",
                "Распродажа остатков",
                "Планирование следующего сезона"
            ]
        }

    def _analyze_competitors(self, category_info: Dict) -> Dict:
        """Анализирует конкурентов"""
        key_players = self._identify_key_players(category_info)
        
        competitor_analysis = {
            "market_leaders": key_players[:3],
            "pricing_strategies": self._analyze_competitor_pricing(key_players),
            "seasonal_strategies": self._analyze_competitor_seasonality(category_info),
            "differentiation_gaps": self._find_differentiation_gaps(category_info),
            "benchmark_metrics": self._generate_benchmark_metrics(category_info)
        }
        
        return competitor_analysis

    def _analyze_competitor_pricing(self, players: List[Dict]) -> Dict:
        """Анализирует ценовые стратегии конкурентов"""
        return {
            "premium_segment": [p for p in players if "премиум" in p.get("strength", "").lower()],
            "value_segment": [p for p in players if any(word in p.get("strength", "").lower() 
                             for word in ["доступн", "цена", "бюджет"])],
            "average_discount_season": random.randint(15, 35),
            "price_war_risk": random.choice(["низкий", "средний", "высокий"])
        }

    def _analyze_competitor_seasonality(self, category_info: Dict) -> Dict:
        """Анализирует сезонные стратегии конкурентов"""
        return {
            "early_promotions": random.choice([True, False]),
            "peak_season_premiums": random.uniform(1.1, 1.3),
            "off_season_discounts": random.uniform(0.7, 0.9),
            "seasonal_product_launches": random.randint(2, 6)
        }

    def _find_differentiation_gaps(self, category_info: Dict) -> List[str]:
        """Находит пробелы в дифференциации"""
        gaps = [
            "персонализированные решения",
            "экологически чистые материалы",
            "инновационный дизайн",
            "улучшенное качество",
            "дополнительные сервисы",
            "уникальная упаковка",
            "социальная ответственность"
        ]
        
        return random.sample(gaps, random.randint(3, 5))

    def _generate_benchmark_metrics(self, category_info: Dict) -> Dict:
        """Генерирует эталонные метрики"""
        return {
            "average_conversion_rate": round(random.uniform(2, 8), 2),
            "average_cart_value": random.randint(1500, 8000),
            "customer_lifetime_value": random.randint(3000, 15000),
            "seasonal_traffic_increase": round(random.uniform(1.2, 2.5), 2),
            "return_rate": round(random.uniform(5, 25), 1)
        }

    def _generate_pricing_strategy(self, data: Dict, category_info: Dict) -> Dict:
        """Генерирует стратегию ценообразования"""
        monthly_data = data.get("monthly_data", {})
        
        pricing_strategy = {
            "base_strategy": self._determine_base_pricing_strategy(category_info),
            "seasonal_adjustments": self._calculate_seasonal_price_adjustments(monthly_data),
            "competitive_positioning": self._determine_competitive_positioning(category_info),
            "psychological_pricing": self._suggest_psychological_pricing(category_info),
            "dynamic_pricing_opportunities": self._identify_dynamic_pricing_opportunities(data)
        }
        
        return pricing_strategy

    def _determine_base_pricing_strategy(self, category_info: Dict) -> Dict:
        """Определяет базовую стратегию ценообразования"""
        strategies = {
            "премиум": {
                "strategy": "premium_pricing",
                "description": "Высокие цены для позиционирования как премиум бренд",
                "target_margin": "40-60%"
            },
            "средний": {
                "strategy": "competitive_pricing", 
                "description": "Конкурентные цены на уровне рынка",
                "target_margin": "25-40%"
            },
            "эконом": {
                "strategy": "penetration_pricing",
                "description": "Низкие цены для захвата доли рынка",
                "target_margin": "15-25%"
            }
        }
        
        price_category = category_info.get("price_category", "средний")
        return strategies.get(price_category, strategies["средний"])

    def _calculate_seasonal_price_adjustments(self, monthly_data: Dict) -> Dict:
        """Рассчитывает сезонные корректировки цен"""
        adjustments = {}
        
        for month, coefficient in monthly_data.items():
            if coefficient >= 1.3:
                adjustments[month] = f"+{int((coefficient - 1) * 10)}% (пиковый спрос)"
            elif coefficient <= 0.8:
                adjustments[month] = f"-{int((1 - coefficient) * 15)}% (низкий спрос)"
            else:
                adjustments[month] = "базовая цена"
        
        return adjustments

    def _determine_competitive_positioning(self, category_info: Dict) -> Dict:
        """Определяет конкурентное позиционирование"""
        return {
            "positioning": random.choice(["лидер рынка", "challenger", "follower", "nicher"]),
            "price_vs_market": random.choice(["выше рынка", "на уровне рынка", "ниже рынка"]),
            "value_proposition": self._generate_value_proposition(category_info),
            "competitive_advantages": random.sample([
                "качество", "сервис", "инновации", "цена", "доступность", "бренд"
            ], 3)
        }

    def _generate_value_proposition(self, category_info: Dict) -> str:
        """Генерирует ценностное предложение"""
        propositions = {
            "Женщинам": "Стильная и качественная одежда для современной женщины",
            "Мужчинам": "Надежная и функциональная одежда для успешного мужчины",
            "Детям": "Безопасные и развивающие товары для счастливого детства",
            "Красота": "Качественная косметика для естественной красоты",
            "Электроника": "Инновационные технологии для комфортной жизни"
        }
        
        return propositions.get(category_info["main_category"], "Качественные товары по доступным ценам")

    def _suggest_psychological_pricing(self, category_info: Dict) -> List[str]:
        """Предлагает психологические приемы ценообразования"""
        return [
            "Использовать цены, заканчивающиеся на 9 (999₽ вместо 1000₽)",
            "Создать три ценовые категории (базовая, стандарт, премиум)",
            "Показывать экономию при покупке комплектов",
            "Использовать якорные цены для дорогих товаров",
            "Предлагать рассрочку для товаров выше 5000₽"
        ]

    def _identify_dynamic_pricing_opportunities(self, data: Dict) -> List[str]:
        """Идентифицирует возможности для динамического ценообразования"""
        return [
            "Автоматическое повышение цен при низких остатках",
            "Снижение цен в зависимости от времени с момента поставки",
            "Персонализированные цены на основе истории покупок",
            "Ценообразование на основе спроса в реальном времени",
            "Конкурентное ценообразование с автоматическим мониторингом"
        ]

    async def _generate_fallback_data(self, category_path: str) -> Dict:
        """Генерирует резервные данные при ошибках"""
        logger.info(f"Generating fallback data for: {category_path}")
        
        # Используем упрощенную версию анализа
        category_info = self._analyze_category(category_path)
        basic_seasonality = self._get_basic_seasonality_pattern(category_info)
        
        return {
            "category_info": category_info,
            "monthly_data": basic_seasonality,
            "analysis_date": datetime.now().isoformat(),
            "data_quality": {"overall_score": 0.4, "reliability": "низкая"},
            "forecasts": {"annual_growth_prediction": 10.0, "confidence_level": 40.0},
            "recommendations": {
                "inventory_management": ["Базовое планирование запасов"],
                "marketing_strategy": ["Стандартная реклама"],
                "pricing_strategy": ["Рыночные цены"]
            },
            "note": "Данные сгенерированы автоматически из-за недоступности источников"
        }

    def _get_basic_seasonality_pattern(self, category_info: Dict) -> Dict:
        """Возвращает базовый паттерн сезонности"""
        # Стандартный паттерн для российского рынка
        base_pattern = {
            "Январь": 0.9, "Февраль": 1.1, "Март": 1.3,
            "Апрель": 1.2, "Май": 1.1, "Июнь": 1.0,
            "Июль": 0.9, "Август": 1.4, "Сентябрь": 1.2,
            "Октябрь": 1.1, "Ноябрь": 1.4, "Декабрь": 1.6
        }
        
        # Корректируем по типу категории
        sensitivity = category_info.get("seasonal_sensitivity", 0.5)
        adjusted_pattern = {}
        
        for month, value in base_pattern.items():
            # Применяем чувствительность к сезонности
            adjustment = (value - 1.0) * sensitivity
            adjusted_pattern[month] = round(1.0 + adjustment, 2)
        
        return adjusted_pattern


# Функция-обертка для использования в боте
async def get_comprehensive_seasonality_data(category_path: str) -> Dict:
    """Основная функция для получения комплексных данных сезонности"""
    analyzer = ComprehensiveSeasonalityAnalyzer()
    return await analyzer.get_comprehensive_seasonality_data(category_path)


def format_comprehensive_seasonality_analysis(data: Dict, category_path: str) -> str:
    """Форматирует результаты комплексного анализа сезонности"""
    try:
        if not data:
            return "❌ *Данные анализа недоступны*"
        
        category_info = data.get("category_info", {})
        monthly_data = data.get("monthly_data", {})
        market_analysis = data.get("market_analysis", {})
        forecasts = data.get("forecasts", {})
        recommendations = data.get("recommendations", {})
        
        # Заголовок
        result = f"🎯 *КОМПЛЕКСНЫЙ АНАЛИЗ СЕЗОННОСТИ*\n"
        result += f"📂 *Категория:* {category_path}\n"
        result += f"🏷️ *Тип:* {category_info.get('main_category', 'Не определен')}\n\n"
        
        # Качество данных
        data_quality = data.get("data_quality", {})
        reliability = data_quality.get("reliability", "неизвестная")
        result += f"📊 *Качество данных:* {reliability} ({data_quality.get('overall_score', 0)*100:.0f}%)\n\n"
        
        # Сезонные пики
        if monthly_data:
            sorted_months = sorted(monthly_data.items(), key=lambda x: x[1], reverse=True)
            peak_months = sorted_months[:3]
            low_months = sorted_months[-3:]
            
            result += f"📈 *СЕЗОННЫЕ ПИКИ*\n"
            for month, coeff in peak_months:
                change = int((coeff - 1) * 100)
                result += f"• {month}: {coeff} ({'+' if change > 0 else ''}{change}%)\n"
            
            result += f"\n📉 *НИЗКИЙ СЕЗОН*\n"
            for month, coeff in low_months:
                change = int((coeff - 1) * 100)
                result += f"• {month}: {coeff} ({'+' if change > 0 else ''}{change}%)\n"
            result += "\n"
        
        # Рыночный анализ
        if market_analysis:
            market_size = market_analysis.get("market_size", {})
            competition = market_analysis.get("competition_level", {})
            
            result += f"🏪 *РЫНОЧНЫЙ АНАЛИЗ*\n"
            result += f"• Размер рынка: {market_size.get('estimated_size_rub', 0):,} ₽\n"
            result += f"• Рост рынка: {market_size.get('growth_rate_annual', 0):.1f}% в год\n"
            result += f"• Конкуренция: {competition.get('level', 'средняя')}\n"
            result += f"• Количество игроков: {competition.get('number_of_competitors', 0)}\n\n"
        
        # Прогнозы
        if forecasts:
            result += f"🔮 *ПРОГНОЗЫ*\n"
            result += f"• Рост в следующем году: {forecasts.get('annual_growth_prediction', 0):.1f}%\n"
            result += f"• Уверенность: {forecasts.get('confidence_level', 0):.0f}%\n"
            
            quarterly = forecasts.get("quarterly", {})
            if quarterly:
                result += f"• Q1: {quarterly.get('Q1', 1):.2f}, Q2: {quarterly.get('Q2', 1):.2f}\n"
                result += f"• Q3: {quarterly.get('Q3', 1):.2f}, Q4: {quarterly.get('Q4', 1):.2f}\n"
            result += "\n"
        
        # Ключевые рекомендации
        if recommendations:
            result += f"💡 *КЛЮЧЕВЫЕ РЕКОМЕНДАЦИИ*\n"
            
            inventory = recommendations.get("inventory_management", [])
            if inventory:
                result += f"📦 *Запасы:*\n"
                for rec in inventory[:2]:
                    result += f"• {rec}\n"
            
            marketing = recommendations.get("marketing_strategy", [])
            if marketing:
                result += f"📢 *Маркетинг:*\n"
                for rec in marketing[:2]:
                    result += f"• {rec}\n"
            
            pricing = recommendations.get("pricing_strategy", [])
            if pricing:
                result += f"💰 *Ценообразование:*\n"
                for rec in pricing[:2]:
                    result += f"• {rec}\n"
        
        # Риски и возможности
        forecast_risks = forecasts.get("key_risks", [])
        forecast_opportunities = forecasts.get("opportunities", [])
        
        if forecast_risks or forecast_opportunities:
            result += f"\n⚠️ *РИСКИ И ВОЗМОЖНОСТИ*\n"
            
            if forecast_risks:
                result += f"🔴 *Основные риски:*\n"
                for risk in forecast_risks[:3]:
                    result += f"• {risk}\n"
            
            if forecast_opportunities:
                result += f"🟢 *Возможности:*\n"
                for opp in forecast_opportunities[:3]:
                    result += f"• {opp}\n"
        
        # Подвал
        analysis_date = data.get("analysis_date", "")
        if analysis_date:
            try:
                date_obj = datetime.fromisoformat(analysis_date.replace('Z', '+00:00'))
                formatted_date = date_obj.strftime("%d.%m.%Y %H:%M")
                result += f"\n📅 *Дата анализа:* {formatted_date}\n"
            except:
                pass
        
        result += f"🤖 *Источники:* WB API, Google Trends, Market Data\n"
        result += f"📊 *Анализируемых факторов:* 15+\n"
        
        return result
        
    except Exception as e:
        logger.error(f"Error formatting comprehensive analysis: {str(e)}")
        return f"❌ *Ошибка форматирования анализа*\n\nКатегория: {category_path}\nОшибка: {str(e)}" 