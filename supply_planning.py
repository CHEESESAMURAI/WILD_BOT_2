import logging
import requests
import json
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from datetime import datetime, timedelta
import io
import asyncio
from mpstats_browser_utils import mpstats_api_request, get_item_sales_browser
from wb_product_info import get_wb_product_info
import pandas as pd
import numpy as np

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Настройка шрифтов для графиков
plt.rcParams['font.family'] = ['DejaVu Sans']
plt.rcParams['font.size'] = 10
plt.rcParams['axes.unicode_minus'] = False

class SupplyPlanner:
    def __init__(self):
        self.target_stock_days = 15  # Целевой запас в днях
        self.min_stock_days = 3      # Минимальный остаток (красная зона)
        self.warning_stock_days = 10 # Предупреждение (желтая зона)
        
    async def analyze_product_supply_needs(self, article):
        """Анализ потребности в поставках для одного товара"""
        try:
            logger.info(f"Analyzing supply needs for article: {article}")
            
            # Получаем данные о товаре с WB
            wb_data = await get_wb_product_info(article)
            if not wb_data:
                logger.warning(f"No WB data for article {article}")
                return None
                
            # Получаем данные продаж из MPStats
            end_date = datetime.now().strftime('%Y-%m-%d')
            start_date = (datetime.now() - timedelta(days=30)).strftime('%Y-%m-%d')
            sales_data = await get_item_sales_browser(article, start_date, end_date)
            
            # Парсим данные товара
            product_info = self._parse_product_data(wb_data, sales_data, article)
            
            if product_info:
                # Рассчитываем показатели поставок
                supply_metrics = self._calculate_supply_metrics(product_info)
                product_info.update(supply_metrics)
                
            return product_info
            
        except Exception as e:
            logger.error(f"Error analyzing supply needs for {article}: {str(e)}")
            return None
    
    def _parse_product_data(self, wb_data, sales_data, article):
        """Парсинг данных о товаре"""
        try:
            product_info = {}
            
            if wb_data and isinstance(wb_data, dict):
                # WB API возвращает уже обработанные данные
                product_info['article'] = article
                product_info['name'] = wb_data.get('name', 'Товар не найден')
                
                # Получаем общие остатки из WB данных
                if 'stocks' in wb_data and 'total' in wb_data['stocks']:
                    product_info['current_stock'] = wb_data['stocks']['total']
                else:
                    product_info['current_stock'] = 0
                
                # Цена
                if 'price' in wb_data and 'current' in wb_data['price']:
                    product_info['price'] = wb_data['price']['current']
                else:
                    product_info['price'] = 0
                
                product_info['rating'] = wb_data.get('rating', 0)
                product_info['reviews_count'] = wb_data.get('feedbacks', 0)
                product_info['brand'] = wb_data.get('brand', 'Не указан')
                
            elif wb_data and isinstance(wb_data, list) and len(wb_data) > 0:
                # Старый формат - массив объектов
                product = wb_data[0]
                
                # Основная информация
                product_info['article'] = article
                product_info['name'] = product.get('name', 'Товар не найден')
                
                # Получаем общие остатки из WB данных
                total_stock = 0
                if 'stocks' in product:
                    # Новый формат данных WB с детальными остатками
                    total_stock = product['stocks'].get('total', 0)
                elif 'totalQuantity' in product:
                    # Альтернативное поле для общих остатков
                    total_stock = product.get('totalQuantity', 0)
                elif 'quantity' in product:
                    # Старый формат данных
                    total_stock = product.get('quantity', 0)
                
                product_info['current_stock'] = total_stock
                
                # Цена
                if 'price' in product and 'current' in product['price']:
                    product_info['price'] = product['price']['current']
                elif 'salePriceU' in product:
                    product_info['price'] = product.get('salePriceU', 0) / 100
                elif 'priceU' in product:
                    product_info['price'] = product.get('priceU', 0) / 100
                else:
                    product_info['price'] = 0
                
                product_info['rating'] = product.get('rating', 0)
                product_info['reviews_count'] = product.get('feedbacks', 0)
                product_info['brand'] = product.get('brand', 'Не указан')
                
            else:
                # Если данных WB нет, создаем базовую структуру
                product_info = {
                    'article': article,
                    'name': f'Товар {article}',
                    'current_stock': 0,
                    'price': 0,
                    'rating': 0,
                    'reviews_count': 0,
                    'brand': 'Не указан'
                }
            
            # Данные о продажах из MPStats
            if sales_data and isinstance(sales_data, list) and len(sales_data) > 0:
                # MPStats API возвращает прямо список данных
                product_info['daily_sales'] = self._calculate_daily_sales(sales_data)
            elif sales_data and 'data' in sales_data and sales_data['data']:
                # Альтернативный формат с обёрткой
                product_info['daily_sales'] = self._calculate_daily_sales(sales_data['data'])
            else:
                # Если MPStats недоступен, делаем примерную оценку на основе отзывов
                reviews = product_info.get('reviews_count', 0)
                if reviews > 0:
                    # Примерная оценка: 1 отзыв = 10-20 продаж, распределенных за время жизни товара
                    estimated_total_sales = reviews * 15
                    # Предполагаем, что товар продается уже минимум 60 дней
                    estimated_days = max(60, reviews)
                    product_info['daily_sales'] = estimated_total_sales / estimated_days
                else:
                    product_info['daily_sales'] = 0.5  # Минимальные продажи для новых товаров
            
            product_info['weekly_sales'] = product_info['daily_sales'] * 7
            product_info['monthly_sales'] = product_info['daily_sales'] * 30
                
            return product_info
            
        except Exception as e:
            logger.error(f"Error parsing product data: {str(e)}")
            return None
    
    def _calculate_daily_sales(self, sales_data):
        """Расчет среднедневных продаж"""
        try:
            if not sales_data:
                return 0
                
            # Берем данные за последние 30 дней для более точного расчета
            recent_sales = []
            
            for item in sales_data:
                if 'sales' in item and item['sales']:
                    recent_sales.append(item['sales'])
                    
            if recent_sales:
                # Рассчитываем среднедневные продажи
                avg_daily_sales = sum(recent_sales) / len(recent_sales)
                return avg_daily_sales
            
            return 0
            
        except Exception as e:
            logger.error(f"Error calculating daily sales: {str(e)}")
            return 0
    
    def _calculate_supply_metrics(self, product_info):
        """Расчет показателей планирования поставок"""
        try:
            metrics = {}
            
            current_stock = product_info.get('current_stock', 0)
            daily_sales = product_info.get('daily_sales', 0)
            
            # Дни до окончания остатков
            if daily_sales > 0:
                metrics['days_until_zero'] = current_stock / daily_sales
            else:
                metrics['days_until_zero'] = float('inf') if current_stock > 0 else 0
            
            # Статус запаса (цветовая маркировка)
            if metrics['days_until_zero'] < self.min_stock_days:
                metrics['stock_status'] = 'critical'  # 🔴
                metrics['status_emoji'] = '🔴'
                metrics['status_text'] = 'Критичный'
            elif metrics['days_until_zero'] < self.warning_stock_days:
                metrics['stock_status'] = 'warning'   # 🟡
                metrics['status_emoji'] = '🟡'
                metrics['status_text'] = 'Внимание'
            else:
                metrics['stock_status'] = 'good'      # 🟢
                metrics['status_emoji'] = '🟢'
                metrics['status_text'] = 'Хорошо'
            
            # Рекомендуемый объем поставки
            if daily_sales > 0:
                recommended_supply = max(0, (self.target_stock_days * daily_sales) - current_stock)
                metrics['recommended_supply'] = int(recommended_supply)
            else:
                metrics['recommended_supply'] = 0
            
            # Прогресс остатков (для прогресс-бара)
            if self.target_stock_days > 0:
                metrics['stock_progress'] = min(100, (metrics['days_until_zero'] / self.target_stock_days) * 100)
            else:
                metrics['stock_progress'] = 0
                
            # Планируемая дата окончания остатков
            if daily_sales > 0 and current_stock > 0:
                zero_date = datetime.now() + timedelta(days=metrics['days_until_zero'])
                metrics['estimated_zero_date'] = zero_date.strftime('%d.%m.%Y')
            else:
                metrics['estimated_zero_date'] = 'Не определена'
            
            return metrics
            
        except Exception as e:
            logger.error(f"Error calculating supply metrics: {str(e)}")
            return {}

    async def analyze_multiple_products(self, articles_list):
        """Анализ планирования поставок для нескольких товаров"""
        try:
            logger.info(f"Analyzing supply needs for {len(articles_list)} products")
            
            results = []
            
            for article in articles_list:
                try:
                    product_analysis = await self.analyze_product_supply_needs(article)
                    if product_analysis:
                        results.append(product_analysis)
                    
                    # Небольшая пауза между запросами
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.error(f"Error analyzing article {article}: {str(e)}")
                    continue
            
            # Сортируем по критичности (сначала критичные, потом предупреждения)
            results.sort(key=lambda x: (
                0 if x.get('stock_status') == 'critical' else
                1 if x.get('stock_status') == 'warning' else 2,
                x.get('days_until_zero', float('inf'))
            ))
            
            return results
            
        except Exception as e:
            logger.error(f"Error in multiple products analysis: {str(e)}")
            return []

    def generate_supply_planning_charts(self, products_data, user_id):
        """Генерация графиков для планирования поставок"""
        try:
            if not products_data:
                return None
                
            # График 1: Обзор статуса остатков
            status_chart = self._create_status_overview_chart(products_data, user_id)
            
            # График 2: Детальный анализ товаров
            details_chart = self._create_detailed_analysis_chart(products_data, user_id)
            
            return {
                'status_overview': status_chart,
                'detailed_analysis': details_chart
            }
            
        except Exception as e:
            logger.error(f"Error generating supply planning charts: {str(e)}")
            return None
    
    def _create_status_overview_chart(self, products_data, user_id):
        """Создание графика обзора статусов"""
        try:
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 8))
            
            # Подсчет товаров по статусам
            status_counts = {'critical': 0, 'warning': 0, 'good': 0}
            for product in products_data:
                status = product.get('stock_status', 'good')
                status_counts[status] += 1
            
            # График 1: Круговая диаграмма статусов
            labels = ['🔴 Критичный', '🟡 Внимание', '🟢 Хорошо']
            sizes = [status_counts['critical'], status_counts['warning'], status_counts['good']]
            colors = ['#ff4444', '#ffaa00', '#00aa44']
            
            # Исключаем нулевые значения
            non_zero_data = [(label, size, color) for label, size, color in zip(labels, sizes, colors) if size > 0]
            if non_zero_data:
                labels, sizes, colors = zip(*non_zero_data)
                
                wedges, texts, autotexts = ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.0f%%',
                                                  startangle=90, textprops={'fontsize': 10})
                ax1.set_title('Распределение товаров по статусу остатков', fontsize=12, fontweight='bold', pad=20)
            else:
                ax1.text(0.5, 0.5, 'Нет данных', ha='center', va='center', fontsize=12)
                ax1.set_title('Распределение товаров по статусу остатков', fontsize=12, fontweight='bold', pad=20)
            
            # График 2: Топ товаров требующих внимания
            critical_products = [p for p in products_data if p.get('stock_status') in ['critical', 'warning']]
            critical_products = sorted(critical_products, key=lambda x: x.get('days_until_zero', 0))[:10]
            
            if critical_products:
                y_pos = np.arange(len(critical_products))
                days_left = [p.get('days_until_zero', 0) for p in critical_products]
                names = [p.get('name', '')[:30] + '...' if len(p.get('name', '')) > 30 
                        else p.get('name', '') for p in critical_products]
                
                colors = ['#ff4444' if p.get('stock_status') == 'critical' else '#ffaa00' 
                         for p in critical_products]
                
                bars = ax2.barh(y_pos, days_left, color=colors, alpha=0.7)
                ax2.set_yticks(y_pos)
                ax2.set_yticklabels(names, fontsize=9)
                ax2.set_xlabel('Дней до окончания остатков')
                ax2.set_title('Товары требующие внимания', fontsize=12, fontweight='bold', pad=20)
                
                # Добавляем линию минимального порога
                ax2.axvline(x=self.min_stock_days, color='red', linestyle='--', alpha=0.7, 
                           label=f'Минимум ({self.min_stock_days} дней)')
                ax2.axvline(x=self.warning_stock_days, color='orange', linestyle='--', alpha=0.7,
                           label=f'Предупреждение ({self.warning_stock_days} дней)')
                ax2.legend()
                
                # Добавляем значения на бары
                for i, (bar, days) in enumerate(zip(bars, days_left)):
                    width = bar.get_width()
                    ax2.text(width + 0.1, bar.get_y() + bar.get_height()/2, 
                            f'{days:.1f}', ha='left', va='center', fontsize=8)
            else:
                ax2.text(0.5, 0.5, 'Все товары в норме!', ha='center', va='center', 
                        fontsize=12, transform=ax2.transAxes)
                ax2.set_title('Товары требующие внимания', fontsize=12, fontweight='bold', pad=20)
            
            plt.tight_layout()
            
            # Сохраняем график
            chart_path = f'supply_status_overview_{user_id}.png'
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_path
            
        except Exception as e:
            logger.error(f"Error creating status overview chart: {str(e)}")
            return None
    
    def _create_detailed_analysis_chart(self, products_data, user_id):
        """Создание детального графика анализа"""
        try:
            if not products_data:
                return None
                
            # Берем первые 15 товаров для детального отображения
            display_products = products_data[:15]
            
            fig, ax = plt.subplots(figsize=(16, max(8, len(display_products) * 0.6)))
            
            y_positions = np.arange(len(display_products))
            
            # Данные для графика
            current_stocks = [p.get('current_stock', 0) for p in display_products]
            recommended_supplies = [p.get('recommended_supply', 0) for p in display_products]
            days_left = [p.get('days_until_zero', 0) for p in display_products]
            
            # Создаем горизонтальный график
            bar_height = 0.35
            
            # Текущие остатки
            bars1 = ax.barh(y_positions - bar_height/2, current_stocks, bar_height, 
                           label='Текущий остаток', color='lightblue', alpha=0.8)
            
            # Рекомендуемые поставки
            bars2 = ax.barh(y_positions + bar_height/2, recommended_supplies, bar_height,
                           label='Рекомендуемая поставка', color='lightgreen', alpha=0.8)
            
            # Настраиваем оси
            product_names = []
            for p in display_products:
                name = p.get('name', '')[:25] + '...' if len(p.get('name', '')) > 25 else p.get('name', '')
                emoji = p.get('status_emoji', '🟢')
                days = p.get('days_until_zero', 0)
                product_names.append(f"{emoji} {name}\n({days:.1f} дней)")
            
            ax.set_yticks(y_positions)
            ax.set_yticklabels(product_names, fontsize=9)
            ax.set_xlabel('Количество единиц товара')
            ax.set_title('Детальный анализ планирования поставок', fontsize=14, fontweight='bold', pad=20)
            ax.legend()
            
            # Добавляем значения на бары
            for i, (bar1, bar2, stock, supply) in enumerate(zip(bars1, bars2, current_stocks, recommended_supplies)):
                if stock > 0:
                    ax.text(bar1.get_width() + max(current_stocks) * 0.01, bar1.get_y() + bar1.get_height()/2, 
                           f'{int(stock)}', ha='left', va='center', fontsize=8)
                if supply > 0:
                    ax.text(bar2.get_width() + max(recommended_supplies) * 0.01, bar2.get_y() + bar2.get_height()/2, 
                           f'{int(supply)}', ha='left', va='center', fontsize=8)
            
            plt.tight_layout()
            
            # Сохраняем график
            chart_path = f'supply_detailed_analysis_{user_id}.png'
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_path
            
        except Exception as e:
            logger.error(f"Error creating detailed analysis chart: {str(e)}")
            return None

def format_supply_planning_report(products_data):
    """Форматирование отчета по планированию поставок"""
    try:
        if not products_data:
            return "❌ *Данные о товарах не найдены*\n\nПроверьте правильность артикулов и попробуйте снова."
        
        # Статистика по статусам
        status_counts = {'critical': 0, 'warning': 0, 'good': 0}
        total_recommended_supply = 0
        
        for product in products_data:
            status = product.get('stock_status', 'good')
            status_counts[status] += 1
            total_recommended_supply += product.get('recommended_supply', 0)
        
        # Заголовок отчета
        report = f"📦 *ПЛАН ПОСТАВОК*\n\n"
        
        # Общая статистика
        total_products = len(products_data)
        report += f"📊 *Общая статистика:*\n"
        report += f"• Всего товаров: {total_products}\n"
        report += f"🔴 Критичные: {status_counts['critical']} товаров\n"
        report += f"🟡 Требуют внимания: {status_counts['warning']} товаров\n"
        report += f"🟢 В норме: {status_counts['good']} товаров\n"
        report += f"📦 Общий объем рекомендуемых поставок: {int(total_recommended_supply)} единиц\n\n"
        
        # Критичные товары (требуют немедленных поставок)
        critical_products = [p for p in products_data if p.get('stock_status') == 'critical']
        if critical_products:
            report += f"🚨 *СРОЧНО ТРЕБУЮТ ПОСТАВКИ ({len(critical_products)} товаров):*\n\n"
            for product in critical_products[:10]:  # Показываем первые 10
                name = product.get('name', 'Неизвестный товар')[:40]
                article = product.get('article', '')
                current_stock = product.get('current_stock', 0)
                days_left = product.get('days_until_zero', 0)
                recommended = product.get('recommended_supply', 0)
                daily_sales = product.get('daily_sales', 0)
                
                report += f"🔴 *{name}*\n"
                report += f"   Артикул: `{article}`\n"
                report += f"   Остаток: {int(current_stock)} шт. (на {days_left:.1f} дней)\n"
                report += f"   Продажи: {daily_sales:.1f} шт/день\n"
                report += f"   ➡️ Рекомендуем поставить: *{int(recommended)} шт.*\n\n"
            
            if len(critical_products) > 10:
                report += f"... и ещё {len(critical_products) - 10} товаров\n\n"
        
        # Товары на контроле
        warning_products = [p for p in products_data if p.get('stock_status') == 'warning']
        if warning_products:
            report += f"⚠️ *НА КОНТРОЛЕ ({len(warning_products)} товаров):*\n\n"
            for product in warning_products[:5]:  # Показываем первые 5
                name = product.get('name', 'Неизвестный товар')[:40]
                article = product.get('article', '')
                current_stock = product.get('current_stock', 0)
                days_left = product.get('days_until_zero', 0)
                recommended = product.get('recommended_supply', 0)
                daily_sales = product.get('daily_sales', 0)
                
                report += f"🟡 *{name}*\n"
                report += f"   Артикул: `{article}`\n"
                report += f"   Остаток: {int(current_stock)} шт. (на {days_left:.1f} дней)\n"
                report += f"   Продажи: {daily_sales:.1f} шт/день\n"
                report += f"   ➡️ Планируемая поставка: {int(recommended)} шт.\n\n"
            
            if len(warning_products) > 5:
                report += f"... и ещё {len(warning_products) - 5} товаров\n\n"
        
        # Товары в норме - ПОКАЗЫВАЕМ ДЕТАЛИ
        good_products = [p for p in products_data if p.get('stock_status') == 'good']
        if good_products:
            avg_days = sum(p.get('days_until_zero', 0) for p in good_products) / len(good_products)
            report += f"✅ *ТОВАРЫ В НОРМЕ ({len(good_products)} товаров):*\n"
            
            # Добавляем детали для товаров в норме (первые 10)
            for product in good_products[:10]:
                name = product.get('name', 'Неизвестный товар')[:40]
                article = product.get('article', '')
                current_stock = product.get('current_stock', 0)
                days_left = product.get('days_until_zero', 0)
                daily_sales = product.get('daily_sales', 0)
                recommended = product.get('recommended_supply', 0)
                price = product.get('price', 0)
                brand = product.get('brand', '')
                
                report += f"\n🟢 *{name}*\n"
                report += f"   Бренд: {brand}\n"
                report += f"   Артикул: `{article}`\n"
                report += f"   Цена: {price}₽\n"
                report += f"   Остаток: {int(current_stock)} шт. (на {days_left:.1f} дней)\n"
                report += f"   Продажи: {daily_sales:.1f} шт/день\n"
                if recommended > 0:
                    report += f"   ➡️ Рекомендуемая поставка: {int(recommended)} шт.\n"
                else:
                    report += f"   ✅ Поставки не требуются\n"
            
            if len(good_products) > 10:
                report += f"\n... и ещё {len(good_products) - 10} товаров\n"
            
            report += f"\n*Средний запас:* {avg_days:.1f} дней\n\n"
        
        # Рекомендации
        report += f"💡 *РЕКОМЕНДАЦИИ:*\n"
        if critical_products:
            report += f"🔴 Срочно организуйте поставки для {len(critical_products)} критичных товаров\n"
        if warning_products:
            report += f"🟡 Запланируйте поставки для {len(warning_products)} товаров на контроле\n"
        if good_products:
            report += f"🟢 Товары в норме - отслеживайте динамику продаж\n"
        report += f"📊 Отслеживайте продажи для корректировки планов\n"
        report += f"⏰ Обновляйте анализ еженедельно\n\n"
        
        report += f"🕐 *Отчет сформирован:* {datetime.now().strftime('%d.%m.%Y в %H:%M')}"
        
        return report
        
    except Exception as e:
        logger.error(f"Error formatting supply planning report: {str(e)}")
        return "❌ Ошибка при формировании отчета по планированию поставок"

# Создаем глобальный экземпляр планировщика
supply_planner = SupplyPlanner()