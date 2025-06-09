import asyncio
import json
from product_mpstat import get_product_mpstat_info
from new_bot import format_product_analysis

async def test():
    article = "360832704"
    result = await get_product_mpstat_info(article)
    print("Результат API MPSTAT:")
    print(json.dumps(result, indent=2))
    
    print("\n\n----------- Форматированный результат для пользователя -----------\n")
    formatted = await format_product_analysis(result, article)
    print(formatted)

if __name__ == "__main__":
    asyncio.run(test())