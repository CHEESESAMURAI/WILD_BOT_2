#!/usr/bin/env python3
"""
Тестовый файл для отладки supply planning
"""

import asyncio
import logging
import traceback

# Настройка логирования
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

async def test_supply_planning():
    """Тест функции supply planning"""
    try:
        print("🔍 Starting supply planning test...")
        
        # Импортируем модули
        from supply_planning import supply_planner, format_supply_planning_report
        
        # Тестовые артикулы
        articles = ['360832704']
        print(f"📝 Testing with articles: {articles}")
        
        # Имитируем пользователя
        user_id = 12345
        
        print(f"🔄 Calling supply_planner.analyze_multiple_products...")
        products_data = await supply_planner.analyze_multiple_products(articles)
        print(f"📊 Result: {products_data}")
        
        if not products_data:
            print("❌ No products data returned")
            return False
        
        print(f"📈 Generating charts...")
        charts_paths = supply_planner.generate_supply_planning_charts(products_data, user_id)
        print(f"📈 Charts: {charts_paths}")
        
        print(f"📝 Formatting report...")
        report_text = format_supply_planning_report(products_data)
        print(f"📝 Report length: {len(report_text)} chars")
        
        print("✅ All functions work correctly!")
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"❌ Exception type: {e.__class__.__name__}")
        print(f"❌ Traceback: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    asyncio.run(test_supply_planning())
