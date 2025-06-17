#!/usr/bin/env python3
"""
Тест интеграции комплексной системы анализа сезонности
"""

import asyncio
import logging

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def test_comprehensive_seasonality():
    """Тестирует комплексную систему анализа сезонности"""
    
    try:
        # Импорт системы
        from seasonality_comprehensive import get_comprehensive_seasonality_data, format_comprehensive_seasonality_analysis
        logger.info("✅ Комплексная система анализа сезонности загружена успешно")
        
        # Тестовые категории
        test_categories = [
            "Женщинам",
            "Мужчинам/Обувь", 
            "Детям/Игрушки",
            "Красота/Уход за лицом",
            "Электроника/Смартфоны",
            "Дом и дача/Мебель",
            "Спорт и отдых/Фитнес",
            "Автотовары/Шины",
            "Книги",
            "Зоотовары"
        ]
        
        logger.info(f"🔍 Тестирую {len(test_categories)} категорий")
        
        for i, category in enumerate(test_categories, 1):
            logger.info(f"📊 Тест {i}/{len(test_categories)}: {category}")
            
            try:
                # Получаем данные
                data = await get_comprehensive_seasonality_data(category)
                
                if data:
                    # Форматируем результат
                    formatted = format_comprehensive_seasonality_analysis(data, category)
                    
                    # Проверяем результат
                    if len(formatted) > 1000:
                        logger.info(f"✅ {category}: Анализ успешен ({len(formatted)} символов)")
                        
                        # Показываем первые строки результата
                        lines = formatted.split('\n')[:10]
                        preview = '\n'.join(lines)
                        logger.info(f"📝 Превью результата:\n{preview}...")
                        
                    else:
                        logger.warning(f"⚠️ {category}: Результат слишком короткий ({len(formatted)} символов)")
                        
                else:
                    logger.error(f"❌ {category}: Данные не получены")
                    
            except Exception as e:
                logger.error(f"❌ {category}: Ошибка - {str(e)}")
            
            # Небольшая пауза между тестами
            await asyncio.sleep(0.5)
        
        logger.info("🎉 Тестирование завершено!")
        
    except ImportError as e:
        logger.error(f"❌ Не удалось импортировать комплексную систему: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Ошибка тестирования: {e}")
        return False
    
    return True

async def test_specific_category():
    """Тестирует конкретную категорию подробно"""
    
    try:
        from seasonality_comprehensive import get_comprehensive_seasonality_data, format_comprehensive_seasonality_analysis
        
        category = "Женщинам/Платья и сарафаны"
        logger.info(f"🔍 Подробный тест категории: {category}")
        
        # Получаем данные
        data = await get_comprehensive_seasonality_data(category)
        
        if data:
            logger.info("✅ Данные получены успешно")
            
            # Показываем структуру данных
            logger.info("📊 Структура данных:")
            for key in data.keys():
                logger.info(f"  • {key}: {type(data[key])}")
            
            # Форматируем результат
            formatted = format_comprehensive_seasonality_analysis(data, category)
            
            logger.info(f"📝 Результат ({len(formatted)} символов):")
            print("=" * 80)
            print(formatted)
            print("=" * 80)
            
        else:
            logger.error("❌ Данные не получены")
            
    except Exception as e:
        logger.error(f"❌ Ошибка подробного теста: {e}")

if __name__ == "__main__":
    print("🚀 Запуск тестирования комплексной системы анализа сезонности")
    
    # Запускаем основные тесты
    asyncio.run(test_comprehensive_seasonality())
    
    print("\n" + "="*80)
    print("🔍 ПОДРОБНЫЙ ТЕСТ КАТЕГОРИИ")
    print("="*80)
    
    # Запускаем подробный тест
    asyncio.run(test_specific_category()) 