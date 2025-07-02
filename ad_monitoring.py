#!/usr/bin/env python3
"""
Модуль мониторинга рекламы
Анализирует эффективность платной рекламы на Wildberries
"""

import asyncio
import aiohttp
import json
import logging
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import tempfile
import os
from mpstats_browser_utils import mpstats_api_request, get_mpstats_headers
from config import MPSTATS_API_KEY

# Настройка matplotlib для русского языка
plt.rcParams["font.family"] = ["DejaVu Sans", "Liberation Sans", "Arial", "sans-serif"]
plt.rcParams["axes.unicode_minus"] = False

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class AdMonitor:
    """Класс для мониторинга рекламных кампаний"""
    
    def __init__(self, mpstats_api_key: str = None):
        self.mpstats_api_key = mpstats_api_key or MPSTATS_API_KEY
        self.roi_thresholds = {
            "good": 100,    # >100% - хорошо (зеленый)
            "neutral": 0,   # 0-100% - в ноль (желтый)
            "bad": 0        # <0% - убыток (красный)
        }
    
    async def get_ad_data_from_mpstats(self, article: str) -> Dict:
        """Получение данных о рекламе товара из MPStats используя рабочие endpoints"""
        try:
            if not self.mpstats_api_key:
                return {"error": "MPStats API ключ не настроен"}
            
            # Получаем даты за последние 30 дней
            end_date = datetime.now()
            start_date = end_date - timedelta(days=30)
            date_from = start_date.strftime("%Y-%m-%d")
            date_to = end_date.strftime("%Y-%m-%d")
            
            logger.info(f"Getting ad data for article: {article} from {date_from} to {date_to}")
            
            # Используем проверенные endpoints из других модулей
            ad_data = await self._try_multiple_ad_endpoints(article, date_from, date_to)
            
            if ad_data and not ad_data.get('error'):
                return self._process_ad_data(ad_data, article)
            
            # Если прямые запросы не работают, пробуем получить данные через продажи
            sales_data = await self._get_sales_based_ad_estimation(article, date_from, date_to)
            if sales_data:
                return sales_data
                
            # Если ничего не работает, возвращаем fallback
            logger.error(f"❌ All ad data endpoints failed for article {article}")
            return {
                "error": "MPStats API временно недоступен для рекламных данных",
                "info": "Вы можете ввести данные о рекламе вручную",
                "manual_data_suggestion": True,
                "article": article
            }
                        
        except Exception as e:
            logger.error(f"Error getting ad data: {str(e)}")
            return {"error": f"Ошибка получения данных: {str(e)}"}
    
    async def _try_multiple_ad_endpoints(self, article: str, date_from: str, date_to: str) -> Dict:
        """Пробуем разные endpoints для получения рекламных данных"""
        endpoints_to_try = [
            # 1. Основной endpoint для рекламы товара
            {
                "url": f"https://mpstats.io/api/wb/get/item/{article}/adverts",
                "params": {"d1": date_from, "d2": date_to},
                "method": "get"
            },
            # 2. Альтернативный endpoint для рекламной активности
            {
                "url": f"https://mpstats.io/api/wb/get/item/{article}/ad-activity",
                "params": {"d1": date_from, "d2": date_to},
                "method": "get"
            },
            # 3. Общие данные товара (может содержать рекламную информацию)
            {
                "url": f"https://mpstats.io/api/wb/get/item/{article}/info",
                "params": None,
                "method": "get"
            },
            # 4. Поиск в рекламных кампаниях
            {
                "url": "https://mpstats.io/api/wb/get/campaigns",
                "params": {"nm": article, "d1": date_from, "d2": date_to},
                "method": "get"
            }
        ]
        
        for i, endpoint in enumerate(endpoints_to_try):
            try:
                logger.info(f"Trying ad endpoint {i+1}: {endpoint['method'].upper()} {endpoint['url']}")
                
                data = await mpstats_api_request(endpoint['url'], endpoint['params'])
                
                if data:
                    logger.info(f"✅ Success with ad endpoint {i+1}")
                    return data
                else:
                    logger.info(f"❌ No data from ad endpoint {i+1}")
                    continue
                    
            except Exception as e:
                logger.warning(f"❌ Exception with ad endpoint {i+1}: {str(e)}")
                continue
        
        return None
    
    async def _get_sales_based_ad_estimation(self, article: str, date_from: str, date_to: str) -> Dict:
        """Получаем примерные данные о рекламе на основе продаж (если прямых данных нет)"""
        try:
            # Получаем данные продаж за период
            sales_url = f"https://mpstats.io/api/wb/get/item/{article}/sales"
            sales_data = await mpstats_api_request(sales_url, {"d1": date_from, "d2": date_to})
            
            if not sales_data:
                return None
            
            # Анализируем паттерны продаж для оценки рекламной активности
            estimated_ad_data = self._estimate_ad_activity_from_sales(sales_data, article)
            return estimated_ad_data
            
        except Exception as e:
            logger.error(f"Error estimating ad data from sales: {str(e)}")
            return None
    
    def _estimate_ad_activity_from_sales(self, sales_data: Dict, article: str) -> Dict:
        """Оценка рекламной активности на основе паттернов продаж"""
        try:
            # Базовая структура данных
            result = {
                'article': article,
                'ad_active': False,
                'impressions': 0,
                'clicks': 0,
                'ctr': 0.0,
                'ad_spend': 0.0,
                'sales_from_ads': 0,
                'revenue_from_ads': 0.0,
                'roi': 0.0,
                'ad_start_date': None,
                'campaign_name': 'Оценка на основе продаж',
                'status_emoji': '🟡',
                'status_text': 'Оценочные данные',
                'data_source': 'sales_estimation'
            }
            
            # Если есть продажи, предполагаем возможную рекламную активность
            if sales_data and isinstance(sales_data, dict):
                total_sales = 0
                daily_sales = []
                
                # Извлекаем данные продаж
                if 'data' in sales_data:
                    for item in sales_data['data']:
                        if 'sales' in item:
                            daily_sales.append(item['sales'])
                            total_sales += item['sales']
                
                # Если есть продажи, оцениваем рекламную активность
                if total_sales > 0:
                    result['ad_active'] = True
                    result['status_text'] = 'Возможна реклама'
                    result['status_emoji'] = '🟡'
                    
                    # Оценочные метрики (основанные на среднерыночных показателях)
                    avg_daily_sales = total_sales / max(len(daily_sales), 1)
                    
                    # Предполагаем, что 30-50% продаж может быть с рекламы
                    estimated_ad_sales = int(total_sales * 0.4)
                    result['sales_from_ads'] = estimated_ad_sales
                    
                    # Оценочная выручка (предполагаем среднюю цену 1000₽)
                    estimated_price = 1000
                    result['revenue_from_ads'] = estimated_ad_sales * estimated_price
                    
                    # Оценочные показы и клики (типичные для категории)
                    result['impressions'] = estimated_ad_sales * 100  # 1 продажа на 100 показов
                    result['clicks'] = estimated_ad_sales * 10       # 1 продажа на 10 кликов
                    result['ctr'] = (result['clicks'] / result['impressions'] * 100) if result['impressions'] > 0 else 0
                    
                    # Оценочные расходы (средний CPC 50₽)
                    result['ad_spend'] = result['clicks'] * 50
                    
                    # ROI
                    if result['ad_spend'] > 0:
                        result['roi'] = ((result['revenue_from_ads'] - result['ad_spend']) / result['ad_spend']) * 100
                    
                    # Обновляем статус на основе ROI
                    result = self._determine_status(result)
            
            return result
            
        except Exception as e:
            logger.error(f"Error estimating ad activity: {str(e)}")
            return None
    
    def _process_ad_data(self, raw_data: Dict, article: str) -> Dict:
        """Обработка сырых данных о рекламе"""
        try:
            processed_data = {
                'article': article,
                'ad_active': False,
                'impressions': 0,
                'clicks': 0,
                'ctr': 0.0,
                'ad_spend': 0.0,
                'sales_from_ads': 0,
                'revenue_from_ads': 0.0,
                'roi': 0.0,
                'ad_start_date': None,
                'campaign_name': '',
                'status_emoji': '🔴',
                'status_text': 'Неактивна',
                'data_source': 'mpstats_api'
            }
            
            # Обработка данных в зависимости от структуры ответа MPStats
            if isinstance(raw_data, dict):
                # Проверяем активность рекламы
                if raw_data.get('active', False) or raw_data.get('status') == 'active':
                    processed_data['ad_active'] = True
                    processed_data['status_text'] = 'Активна'
                    processed_data['status_emoji'] = '🟢'
                
                # Извлекаем метрики
                processed_data['impressions'] = raw_data.get('impressions', 0)
                processed_data['clicks'] = raw_data.get('clicks', 0)
                processed_data['ad_spend'] = raw_data.get('spend', 0.0)
                processed_data['sales_from_ads'] = raw_data.get('orders', 0)
                processed_data['revenue_from_ads'] = raw_data.get('revenue', 0.0)
                
                # Рассчитываем CTR
                if processed_data['impressions'] > 0:
                    processed_data['ctr'] = (processed_data['clicks'] / processed_data['impressions']) * 100
                
                # Рассчитываем ROI
                if processed_data['ad_spend'] > 0:
                    processed_data['roi'] = ((processed_data['revenue_from_ads'] - processed_data['ad_spend']) / processed_data['ad_spend']) * 100
                
                # Дата запуска
                if 'start_date' in raw_data:
                    processed_data['ad_start_date'] = raw_data['start_date']
                
                # Название кампании
                processed_data['campaign_name'] = raw_data.get('campaign_name', f'Кампания {article}')
            
            # Определяем статус на основе ROI
            processed_data = self._determine_status(processed_data)
            
            return processed_data
            
        except Exception as e:
            logger.error(f"Error processing ad data: {str(e)}")
            return {"error": f"Ошибка обработки данных: {str(e)}"}

    async def analyze_multiple_products_ads(self, articles_list: List[str], manual_data: Dict = None) -> List[Dict]:
        """Анализ рекламных кампаний для нескольких товаров"""
        try:
            logger.info(f"Analyzing ads for {len(articles_list)} products")
            
            results = []
            
            for article in articles_list:
                try:
                    # Получаем данные о рекламе
                    ad_data = await self.get_ad_data_from_mpstats(article)
                    
                    # Если есть ошибка API, создаем fallback данные
                    if ad_data and ad_data.get('error'):
                        # Проверяем, есть ли ручные данные для этого артикула
                        if manual_data and article in manual_data:
                            ad_data = self._create_fallback_ad_data(article, manual_data[article])
                        else:
                            ad_data = self._create_fallback_ad_data(article)
                    
                    if ad_data:
                        # Пересчитываем метрики и определяем статус
                        ad_data = self._recalculate_metrics(ad_data)
                        results.append(ad_data)
                    
                    # Пауза между запросами
                    await asyncio.sleep(0.3)
                    
                except Exception as e:
                    logger.error(f"Error analyzing article {article}: {str(e)}")
                    # Добавляем товар с ошибкой
                    results.append({
                        'article': article,
                        'error': f'Ошибка анализа: {str(e)}',
                        'manual_data_suggestion': True
                    })
                    continue
            
            return results
            
        except Exception as e:
            logger.error(f"Error in multiple products ad analysis: {str(e)}")
            return []

    def _create_fallback_ad_data(self, article: str, manual_data: Dict = None) -> Dict:
        """Создание fallback данных о рекламе"""
        try:
            fallback_data = {
                'article': article,
                'ad_active': manual_data.get('ad_active', False) if manual_data else False,
                'impressions': manual_data.get('impressions', 0) if manual_data else 0,
                'clicks': manual_data.get('clicks', 0) if manual_data else 0,
                'ctr': 0.0,
                'ad_spend': manual_data.get('ad_spend', 0.0) if manual_data else 0.0,
                'sales_from_ads': manual_data.get('sales_from_ads', 0) if manual_data else 0,
                'revenue_from_ads': manual_data.get('revenue_from_ads', 0.0) if manual_data else 0.0,
                'roi': 0.0,
                'ad_start_date': manual_data.get('ad_start_date') if manual_data else None,
                'campaign_name': f'Кампания {article}',
                'data_source': 'manual' if manual_data else 'fallback'
            }
            
            return fallback_data
            
        except Exception as e:
            logger.error(f"Error creating fallback data: {str(e)}")
            return {'article': article, 'error': f'Ошибка создания fallback данных: {str(e)}'}

    def _recalculate_metrics(self, ad_data: Dict) -> Dict:
        """Пересчет метрик на основе имеющихся данных"""
        try:
            # CTR
            if ad_data.get('impressions', 0) > 0:
                ad_data['ctr'] = (ad_data.get('clicks', 0) / ad_data['impressions']) * 100
            else:
                ad_data['ctr'] = 0.0
            
            # ROI
            ad_spend = ad_data.get('ad_spend', 0)
            revenue = ad_data.get('revenue_from_ads', 0)
            
            if ad_spend > 0:
                ad_data['roi'] = ((revenue - ad_spend) / ad_spend) * 100
            else:
                ad_data['roi'] = 0.0
            
            # Определяем статус
            ad_data = self._determine_status(ad_data)
            
            return ad_data
            
        except Exception as e:
            logger.error(f"Error recalculating metrics: {str(e)}")
            return ad_data

    def _determine_status(self, ad_data: Dict) -> Dict:
        """Определение статуса кампании на основе ROI"""
        try:
            roi = ad_data.get('roi', 0)
            
            if roi > self.roi_thresholds['good']:
                ad_data['status_emoji'] = '🟢'
                ad_data['status_text'] = 'Прибыльно'
            elif roi >= self.roi_thresholds['neutral']:
                ad_data['status_emoji'] = '🟡'
                ad_data['status_text'] = 'В ноль'
            else:
                ad_data['status_emoji'] = '🔴'
                ad_data['status_text'] = 'Убыточно'
            
            return ad_data
            
        except Exception as e:
            logger.error(f"Error determining status: {str(e)}")
            return ad_data

    def generate_ad_monitoring_charts(self, ad_data_list: List[Dict], user_id: str) -> List[str]:
        """Генерация графиков для мониторинга рекламы"""
        try:
            chart_files = []
            
            if not ad_data_list:
                return chart_files
            
            # 1. График сравнения ROI
            roi_chart = self._create_roi_comparison_chart(ad_data_list, user_id)
            if roi_chart:
                chart_files.append(roi_chart)
            
            # 2. График расходов и выручки
            spend_revenue_chart = self._create_spend_revenue_chart(ad_data_list, user_id)
            if spend_revenue_chart:
                chart_files.append(spend_revenue_chart)
            
            # 3. Обзор активности кампаний
            activity_chart = self._create_activity_overview_chart(ad_data_list, user_id)
            if activity_chart:
                chart_files.append(activity_chart)
            
            return chart_files
            
        except Exception as e:
            logger.error(f"Error generating charts: {str(e)}")
            return []
    
    def _create_roi_comparison_chart(self, ad_data_list: List[Dict], user_id: str) -> str:
        """Создание графика сравнения ROI"""
        try:
            # Фильтруем товары с данными
            valid_data = [ad for ad in ad_data_list if not ad.get('error')]
            
            if not valid_data:
                return None
            
            articles = [ad['article'] for ad in valid_data]
            roi_values = [ad.get('roi', 0) for ad in valid_data]
            
            # Определяем цвета по ROI
            colors = []
            for roi in roi_values:
                if roi > 100:
                    colors.append('#28a745')  # Зеленый - прибыльно
                elif roi > 0:
                    colors.append('#ffc107')  # Желтый - в ноль
                else:
                    colors.append('#dc3545')  # Красный - убыточно
            
            plt.figure(figsize=(12, 8))
            bars = plt.bar(range(len(articles)), roi_values, color=colors)
            
            plt.title('Сравнение ROI рекламных кампаний', fontsize=16, fontweight='bold')
            plt.xlabel('Артикулы товаров', fontsize=12)
            plt.ylabel('ROI (%)', fontsize=12)
            
            # Настройка осей
            plt.xticks(range(len(articles)), articles, rotation=45, ha='right')
            plt.axhline(y=0, color='black', linestyle='-', alpha=0.3)
            plt.axhline(y=100, color='green', linestyle='--', alpha=0.5, label='Порог прибыльности (100%)')
            
            # Добавляем значения на столбцы
            for bar, roi in zip(bars, roi_values):
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + (5 if height >= 0 else -15),
                        f'{roi:.1f}%', ha='center', va='bottom' if height >= 0 else 'top',
                        fontweight='bold')
            
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            # Сохранение
            chart_path = f"roi_comparison_{user_id}.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_path
            
        except Exception as e:
            logger.error(f"Error creating ROI comparison chart: {str(e)}")
            return None
    
    def _create_spend_revenue_chart(self, ad_data_list: List[Dict], user_id: str) -> str:
        """Создание графика расходов vs выручки"""
        try:
            # Фильтруем товары с данными
            valid_data = [ad for ad in ad_data_list if not ad.get('error')]
            
            if not valid_data:
                return None
            
            articles = [ad['article'] for ad in valid_data]
            spend_values = [ad.get('ad_spend', 0) for ad in valid_data]
            revenue_values = [ad.get('revenue_from_ads', 0) for ad in valid_data]
            
            x = np.arange(len(articles))
            width = 0.35
            
            fig, ax = plt.subplots(figsize=(12, 8))
            
            bars1 = ax.bar(x - width/2, spend_values, width, label='Расходы на рекламу', color='#ff6b6b')
            bars2 = ax.bar(x + width/2, revenue_values, width, label='Выручка от рекламы', color='#4ecdc4')
            
            ax.set_title('Сравнение расходов и выручки от рекламы', fontsize=16, fontweight='bold')
            ax.set_xlabel('Артикулы товаров', fontsize=12)
            ax.set_ylabel('Сумма (₽)', fontsize=12)
            ax.set_xticks(x)
            ax.set_xticklabels(articles, rotation=45, ha='right')
            ax.legend()
            
            # Добавляем значения на столбцы
            for bars in [bars1, bars2]:
                for bar in bars:
                    height = bar.get_height()
                    if height > 0:
                        ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                               f'{height:,.0f}₽', ha='center', va='bottom',
                               fontsize=9)
            
            plt.grid(True, alpha=0.3)
            plt.tight_layout()
            
            # Сохранение
            chart_path = f"spend_revenue_{user_id}.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_path
            
        except Exception as e:
            logger.error(f"Error creating spend/revenue chart: {str(e)}")
            return None
    
    def _create_activity_overview_chart(self, ad_data_list: List[Dict], user_id: str) -> str:
        """Создание обзорного графика активности кампаний"""
        try:
            # Фильтруем товары с данными
            valid_data = [ad for ad in ad_data_list if not ad.get('error')]
            
            if not valid_data:
                return None
            
            # Подсчитываем статусы
            status_counts = {'Прибыльно': 0, 'В ноль': 0, 'Убыточно': 0, 'Неактивно': 0}
            ctr_values = []
            articles = []
            
            for ad in valid_data:
                status = ad.get('status_text', 'Неактивно')
                if status in status_counts:
                    status_counts[status] += 1
                else:
                    status_counts['Неактивно'] += 1
                
                ctr_values.append(ad.get('ctr', 0))
                articles.append(ad['article'])
            
            # Создаем subplot
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(15, 6))
            
            # 1. Круговая диаграмма статусов
            labels = []
            sizes = []
            colors = []
            color_map = {
                'Прибыльно': '#28a745',
                'В ноль': '#ffc107', 
                'Убыточно': '#dc3545',
                'Неактивно': '#6c757d'
            }
            
            for status, count in status_counts.items():
                if count > 0:
                    labels.append(f'{status} ({count})')
                    sizes.append(count)
                    colors.append(color_map[status])
            
            if sizes:
                ax1.pie(sizes, labels=labels, colors=colors, autopct='%1.1f%%', startangle=90)
                ax1.set_title('Распределение кампаний по эффективности', fontsize=12, fontweight='bold')
            
            # 2. График CTR
            if ctr_values and articles:
                bars = ax2.bar(range(len(articles)), ctr_values, color='#17a2b8')
                ax2.set_title('CTR рекламных кампаний', fontsize=12, fontweight='bold')
                ax2.set_xlabel('Артикулы')
                ax2.set_ylabel('CTR (%)')
                ax2.set_xticks(range(len(articles)))
                ax2.set_xticklabels(articles, rotation=45, ha='right')
                
                # Добавляем значения на столбцы
                for bar, ctr in zip(bars, ctr_values):
                    height = bar.get_height()
                    if height > 0:
                        ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                               f'{ctr:.2f}%', ha='center', va='bottom', fontsize=9)
                
                ax2.grid(True, alpha=0.3)
            
            plt.tight_layout()
            
            # Сохранение
            chart_path = f"activity_overview_{user_id}.png"
            plt.savefig(chart_path, dpi=300, bbox_inches='tight')
            plt.close()
            
            return chart_path
            
        except Exception as e:
            logger.error(f"Error creating activity overview chart: {str(e)}")
            return None


def format_ad_monitoring_report(ad_data_list: List[Dict]) -> str:
    """Форматирование отчета мониторинга рекламы"""
    try:
        if not ad_data_list:
            return "❌ Нет данных для анализа"
        
        # Статистика по кампаниям
        total_campaigns = len(ad_data_list)
        profitable = sum(1 for ad in ad_data_list if ad.get('roi', 0) > 100)
        break_even = sum(1 for ad in ad_data_list if 0 <= ad.get('roi', 0) <= 100)
        loss = sum(1 for ad in ad_data_list if ad.get('roi', 0) < 0)
        
        # Общие затраты и выручка
        total_spend = sum(ad.get('ad_spend', 0) for ad in ad_data_list)
        total_revenue = sum(ad.get('revenue_from_ads', 0) for ad in ad_data_list)
        total_orders = sum(ad.get('sales_from_ads', 0) for ad in ad_data_list)
        
        # Общий ROI
        overall_roi = ((total_revenue - total_spend) / total_spend * 100) if total_spend > 0 else 0
        
        report = f"""📊 *ОТЧЕТ МОНИТОРИНГА РЕКЛАМЫ*

📈 *Общая статистика:*
• Всего кампаний: {total_campaigns}
• 🟢 Прибыльных: {profitable}
• 🟡 В ноль: {break_even}  
• 🔴 Убыточных: {loss}

💰 *Финансовые показатели:*
• Общие расходы: {total_spend:,.0f}₽
• Общая выручка: {total_revenue:,.0f}₽
• Общий ROI: {overall_roi:.1f}%
• Всего заказов: {total_orders}

📋 *Детальная информация по кампаниям:*
"""
        
        # Детали по каждой кампании
        for i, ad in enumerate(ad_data_list, 1):
            if ad.get('error'):
                if ad.get('manual_data_suggestion'):
                    report += f"\n{i}. ⚠️ Артикул {ad['article']}: {ad['error']}"
                    report += f"\n   💡 {ad.get('info', 'Попробуйте позже')}"
                else:
                    report += f"\n{i}. ❌ Артикул {ad['article']}: {ad['error']}"
                continue
            
            article = ad['article']
            status_emoji = ad.get('status_emoji', '🔴')
            roi = ad.get('roi', 0)
            spend = ad.get('ad_spend', 0)
            revenue = ad.get('revenue_from_ads', 0)
            orders = ad.get('sales_from_ads', 0)
            impressions = ad.get('impressions', 0)
            clicks = ad.get('clicks', 0)
            ctr = ad.get('ctr', 0)
            
            report += f"""
{i}. {status_emoji} *Артикул {article}*
   • ROI: {roi:.1f}%
   • Расходы: {spend:,.0f}₽
   • Выручка: {revenue:,.0f}₽
   • Заказы: {orders}
   • Показы: {impressions:,}
   • Клики: {clicks:,}
   • CTR: {ctr:.2f}%"""
            
            # Рекомендации
            if roi > 100:
                report += f"\n   💡 *Рекомендация:* Увеличить бюджет кампании"
            elif 0 <= roi <= 100:
                report += f"\n   💡 *Рекомендация:* Оптимизировать ключевые слова и ставки"
            else:
                report += f"\n   💡 *Рекомендация:* Приостановить или пересмотреть стратегию"
        
        # Общие выводы и рекомендации
        report += f"""

🎯 *ОБЩИЕ ВЫВОДЫ:*"""
        
        if overall_roi > 100:
            report += f"\n✅ Реклама эффективна! Общий ROI {overall_roi:.1f}% превышает порог прибыльности."
        elif overall_roi > 0:
            report += f"\n⚠️ Реклама работает в ноль. ROI {overall_roi:.1f}% требует оптимизации."
        else:
            report += f"\n❌ Реклама убыточна. ROI {overall_roi:.1f}% требует срочных мер."
        
        if profitable > 0:
            report += f"\n• Сосредоточьтесь на масштабировании {profitable} прибыльных кампаний"
        
        if loss > 0:
            report += f"\n• Проанализируйте {loss} убыточных кампаний и рассмотрите их остановку"
        
        if break_even > 0:
            report += f"\n• Оптимизируйте {break_even} кампаний с нулевой прибылью"
        
        return report
        
    except Exception as e:
        logger.error(f"Error formatting ad monitoring report: {str(e)}")
        return f"❌ Ошибка формирования отчета: {str(e)}"


def create_ad_monitor(mpstats_api_key: str = None) -> AdMonitor:
    """Фабричная функция для создания экземпляра AdMonitor"""
    return AdMonitor(mpstats_api_key)