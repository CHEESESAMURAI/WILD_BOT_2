#!/usr/bin/env python3
"""
Скрипт для обновления всех модулей, использующих MPSTATS API на браузерный подход
"""
import os
import re

def find_mpstats_files():
    """Находит все файлы, использующие MPSTATS API"""
    mpstats_files = []
    
    # Сканируем текущую директорию
    for file in os.listdir('.'):
        if file.endswith('.py') and file != __file__:
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    content = f.read()
                    if 'mpstats.io/api' in content:
                        mpstats_files.append(file)
            except Exception as e:
                print(f"Ошибка чтения файла {file}: {e}")
    
    return mpstats_files

def update_headers_in_file(filename):
    """Обновляет заголовки MPSTATS в файле"""
    try:
        with open(filename, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Добавляем импорт браузерных утилит в начало если его нет
        if 'from mpstats_browser_utils import' not in content:
            # Находим место после import-ов
            import_lines = []
            other_lines = []
            in_imports = True
            
            for line in content.split('\n'):
                if line.strip().startswith('import ') or line.strip().startswith('from ') or line.strip() == '':
                    if in_imports:
                        import_lines.append(line)
                    else:
                        other_lines.append(line)
                else:
                    in_imports = False
                    other_lines.append(line)
            
            # Добавляем импорт браузерных утилит
            import_lines.append('from mpstats_browser_utils import get_mpstats_headers, mpstats_api_request')
            
            content = '\n'.join(import_lines + other_lines)
        
        # Заменяем старые заголовки на новые
        old_headers_patterns = [
            r'headers\s*=\s*{\s*["\']X-Mpstats-TOKEN["\']:\s*MPSTATS_API_KEY[^}]*}',
            r'["\']X-Mpstats-TOKEN["\']:\s*MPSTATS_API_KEY,?\s*["\']Content-Type["\']:\s*["\']application/json["\']',
            r'["\']Content-Type["\']:\s*["\']application/json["\'][^}]*["\']X-Mpstats-TOKEN["\']:\s*MPSTATS_API_KEY'
        ]
        
        for pattern in old_headers_patterns:
            content = re.sub(pattern, 'headers = get_mpstats_headers()', content, flags=re.MULTILINE | re.DOTALL)
        
        # Заменяем прямые вызовы aiohttp на универсальные функции там где возможно
        # Это более сложное обновление, оставим для ручного редактирования
        
        return content
        
    except Exception as e:
        print(f"Ошибка обновления файла {filename}: {e}")
        return None

def main():
    """Основная функция обновления"""
    print("🔄 Поиск файлов, использующих MPSTATS API...")
    
    mpstats_files = find_mpstats_files()
    
    print(f"📁 Найдено файлов: {len(mpstats_files)}")
    for file in mpstats_files:
        print(f"  • {file}")
    
    print("\n🔧 Файлы которые нужно обновить вручную:")
    
    key_functions = [
        "get_mpsta_data",
        "get_seasonality_annual_data", 
        "get_seasonality_weekly_data",
        "get_mpstats_category_data",
        "get_external_ads_data"
    ]
    
    # Основные файлы для ручного обновления
    priority_files = [
        "new_bot.py",
        "mpstats_item_sales.py", 
        "product_data_merger.py",
        "product_mpstat.py",
        "brand_analysis.py",
        "niche_analysis_functions.py"
    ]
    
    for file in priority_files:
        if os.path.exists(file):
            print(f"\n📝 {file}:")
            print("  Рекомендуемые изменения:")
            print("  1. Добавить: from mpstats_browser_utils import get_mpstats_headers, mpstats_api_request")
            print("  2. Заменить заголовки на: headers = get_mpstats_headers()")
            print("  3. Использовать: data = await mpstats_api_request(url, params)")
    
    print("\n✅ Ключевые улучшения браузерного подхода:")
    print("🌐 Правильные User-Agent и Referer заголовки")
    print("🔧 Единообразная обработка ошибок") 
    print("⚡ Оптимизированные таймауты")
    print("📊 Улучшенное логирование")
    print("🛡️ Лучшая обработка исключений")
    
    print(f"\n🎯 Уже обновлены и работают:")
    print("✅ Oracle Queries (oracle_queries.py)")
    print("✅ Браузерные утилиты (mpstats_browser_utils.py)")
    print("✅ Тестовые функции")
    
    print(f"\n📋 Для полного обновления нужно:")
    print("1. Обновить функции в new_bot.py (основной бот)")
    print("2. Обновить модули анализа продуктов")
    print("3. Обновить модули сезонности") 
    print("4. Протестировать все функции")

if __name__ == "__main__":
    main() 