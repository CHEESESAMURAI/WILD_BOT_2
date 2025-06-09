import asyncio
import logging
from product_data_merger import get_combined_product_info
from product_data_formatter import format_enhanced_product_analysis, generate_daily_charts
import json

# Настройка логирования
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_enhanced_product_analysis(article):
    """Тестирует функции объединения и форматирования данных о продукте."""
    try:
        # Получаем объединенные данные
        logger.info(f"Getting combined product info for article {article}")
        product_info = await get_combined_product_info(article)
        
        if not product_info:
            logger.error("Failed to get product info")
            return
        
        # Сохраняем данные в JSON-файл для анализа
        with open(f"product_info_{article}.json", "w", encoding="utf-8") as f:
            json.dump(product_info, f, ensure_ascii=False, indent=2)
        logger.info(f"Saved raw product info to product_info_{article}.json")
        
        # Форматируем данные
        logger.info("Formatting product info")
        formatted_result = await format_enhanced_product_analysis(product_info, article)
        
        # Выводим отформатированный результат
        print("\n" + "="*50 + "\n")
        print(formatted_result)
        print("\n" + "="*50 + "\n")
        
        # Генерируем графики
        logger.info("Generating daily charts")
        chart_paths = generate_daily_charts(product_info)
        logger.info(f"Generated {len(chart_paths)} charts")
        
        # Выводим пути к графикам
        if chart_paths:
            print("Созданные графики:")
            for path in chart_paths:
                print(f"- {path}")
        
    except Exception as e:
        logger.error(f"Error in test_enhanced_product_analysis: {str(e)}", exc_info=True)

if __name__ == "__main__":
    # Артикул для тестирования
    article = "360832704"
    
    # Запускаем тест
    asyncio.run(test_enhanced_product_analysis(article)) 