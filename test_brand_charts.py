import json
from product_data_formatter import generate_brand_charts

# Загружаем информацию о товаре
with open('product_info_360832704.json', 'r') as f:
    product_info = json.load(f)

# Генерируем графики бренда
chart_paths = generate_brand_charts(product_info)

# Выводим результат
print("Сгенерированные графики бренда:")
for path in chart_paths:
    print(f"- {path}") 