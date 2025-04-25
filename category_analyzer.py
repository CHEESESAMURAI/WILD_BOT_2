import requests
from bs4 import BeautifulSoup
import json
from typing import Dict, List, Optional, Any
import pandas as pd
from datetime import datetime
import asyncio
import aiohttp
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import re
import time
import random
import ssl
import os
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CategoryAnalyzer:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.max_retries = 5
        self.retry_delay = 3
        self.page_load_timeout = 60
        self.element_timeout = 30
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        self.is_initialized = False
        self.lari_to_rub_rate = 35.0  # Примерный курс 1 лари = 35 рублей

    async def initialize_driver(self):
        """Initialize WebDriver with improved settings"""
        try:
            chrome_options = Options()
            chrome_options.add_argument('--headless=new')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # Add additional options for stability
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-infobars')
            chrome_options.add_argument('--disable-notifications')
            chrome_options.add_argument('--disable-popup-blocking')
            chrome_options.add_argument('--disable-web-security')
            chrome_options.add_argument('--ignore-certificate-errors')
            chrome_options.add_argument('--ignore-ssl-errors')
            chrome_options.add_argument('--disable-site-isolation-trials')
            chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
            
            # Add user agent
            chrome_options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set timeouts
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.wait = WebDriverWait(self.driver, self.element_timeout)
            
            # Test the driver
            self.driver.get("https://www.wildberries.ru")
            await asyncio.sleep(5)  # Wait for initial load
            
            # Verify page load
            try:
                self.wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
                logger.info("WebDriver successfully initialized")
                return True
            except TimeoutException:
                logger.warning("Initial page load timeout, retrying...")
                await self.close_driver()
                return False
                
        except Exception as e:
            logger.error(f"Error initializing WebDriver: {e}")
            if self.driver:
                await self.close_driver()
            return False

    async def close_driver(self):
        """Закрытие WebDriver"""
        if self.driver:
            try:
                # Сначала пытаемся закрыть все окна
                try:
                    self.driver.close()
                except Exception as e:
                    logger.warning(f"Error closing windows: {e}")
                
                # Затем закрываем драйвер
                try:
                    self.driver.quit()
                except Exception as e:
                    logger.warning(f"Error quitting driver: {e}")
                
                self.driver = None
                self.wait = None
                logger.info("WebDriver успешно закрыт")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
                self.driver = None
                self.wait = None

    async def ensure_driver(self):
        """Проверка и инициализация WebDriver при необходимости"""
        if not self.driver or not self.wait:
            await self.initialize_driver()

    def _extract_category_id(self, url: str) -> str:
        """Extract category ID and parameters from Wildberries URL"""
        # Extract the path after /catalog/
        match = re.search(r'/catalog/([^?]+)', url)
        if not match:
            raise ValueError("Invalid Wildberries category URL")
        
        path = match.group(1).rstrip('/')
        path_parts = path.split('/')
        
        # For men's clothing category
        if path_parts[0] == 'muzhchinam':
            if len(path_parts) >= 3 and path_parts[1] == 'odezhda':
                # Map specific clothing types
                clothing_type_map = {
                    'tolstovki': '8132',  # Category ID for sweatshirts
                    'futbolki': '8131',   # Category ID for t-shirts
                    'rubashki': '8133',   # Category ID for shirts
                    'dzhinsy': '8134',    # Category ID for jeans
                    'bryuki': '8135'      # Category ID for pants
                }
                if path_parts[2] in clothing_type_map:
                    return f"muzhchinam/odezhda/{path_parts[2]}"
            return "muzhchinam/odezhda"
            
        # Map other main categories
        category_mapping = {
            'zhenshchinam': 'zhenshchinam/odezhda',
            'detyam': 'detyam/odezhda',
            'aksessuary': 'aksessuary',
            'elektronika': 'elektronika',
            'dom-i-dacha': 'dom-i-dacha',
            'krasota': 'krasota'
        }
        
        return category_mapping.get(path_parts[0], 'catalog')

    async def _get_exchange_rate(self) -> float:
        """Получение актуального курса лари к рублю"""
        try:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            async with aiohttp.ClientSession() as session:
                # Используем API для получения курса
                async with session.get('https://api.exchangerate-api.com/v4/latest/GEL', ssl=ssl_context) as response:
                    if response.status == 200:
                        data = await response.json()
                        return data['rates']['RUB']
        except Exception as e:
            logger.error(f"Error getting exchange rate: {e}")
            return self.lari_to_rub_rate  # Возвращаем дефолтный курс в случае ошибки
        return self.lari_to_rub_rate

    async def _get_category_info(self, url: str) -> Dict:
        """Get basic category information"""
        try:
            # Загружаем страницу через Selenium для получения динамического контента
            await self.ensure_driver()
            self.driver.get(url)
            
            # Ждем загрузки страницы
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )
            
            # Получаем название категории из хлебных крошек
            try:
                breadcrumbs = self.driver.find_elements(By.CLASS_NAME, "breadcrumbs__item")
                if breadcrumbs:
                    # Берем последний элемент из хлебных крошек
                    category_name = breadcrumbs[-1].text.strip()
                    if not category_name:
                        # Если название пустое, пробуем получить из заголовка
                        title = self.driver.title
                        category_name = title.split(' в ')[0].strip() if ' в ' in title else "Толстовки"
                else:
                    # Если хлебные крошки не найдены, пробуем получить из заголовка
                    title = self.driver.title
                    category_name = title.split(' в ')[0].strip() if ' в ' in title else "Толстовки"
                
                # Если название все еще пустое, используем значение по умолчанию
                if not category_name:
                    category_name = "Толстовки"
                
                logger.info(f"Found category name: {category_name}")
                
            except Exception as e:
                logger.error(f"Error getting category name: {e}")
                category_name = "Толстовки"
            
            return {
                "name": category_name,
                "url": url
            }
        except Exception as e:
            logger.error(f"Error getting category info: {str(e)}")
            return {"name": "Толстовки", "url": url}

    async def _get_category_products(self, url: str) -> List[Dict]:
        """Получение списка товаров из категории"""
        try:
            await self.ensure_driver()
            self.driver.get(url)
            logger.info(f"Opened URL: {url}")
            
            # Ждем загрузку страницы
            self.wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
            logger.info("Page load complete")
            
            # Даем дополнительное время для загрузки динамического контента
            await asyncio.sleep(5)
            
            # Прокручиваем страницу для загрузки всех товаров
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 5
            
            while scroll_attempts < max_scroll_attempts:
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                await asyncio.sleep(2)
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                logger.info(f"Scroll attempt {scroll_attempts + 1}: height changed from {last_height} to {new_height}")
                if new_height == last_height:
                    break
                last_height = new_height
                scroll_attempts += 1
            
            # Find product cards with improved error handling
            logger.info("Trying to find product cards...")
            try:
                # First wait for the product grid to be present
                product_grid = self.wait.until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "div[class*='product-grid']"))
                )
                logger.info("Product grid found")
                
                # Then wait for individual cards with a shorter timeout
                short_wait = WebDriverWait(self.driver, 10)
                product_cards = short_wait.until(
                    EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[class*='product-card__main']"))
                )
                logger.info(f"Found {len(product_cards)} product cards")
                
                if not product_cards:
                    logger.warning("No product cards found, trying alternative selector")
                    # Try alternative selector
                    product_cards = short_wait.until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, "div[class*='product-card']"))
                    )
                    logger.info(f"Found {len(product_cards)} product cards with alternative selector")
                
            except TimeoutException:
                logger.error("Timeout while waiting for product cards")
                # Take a screenshot for debugging
                try:
                    self.driver.save_screenshot("debug_screenshot.png")
                    logger.info("Debug screenshot saved")
                except Exception as e:
                    logger.error(f"Failed to save debug screenshot: {e}")
                raise
            except Exception as e:
                logger.error(f"Error finding product cards: {e}")
                raise
            
            products = []
            for index, card in enumerate(product_cards):
                try:
                    logger.info(f"Processing card {index + 1}")
                    
                    # Get article ID with improved error handling
                    article = None
                    try:
                        # First try to get from data-nm-id attribute
                        article = card.get_attribute('data-nm-id')
                        if not article:
                            # If not found, try to get from the link
                            link_element = card.find_element(By.CSS_SELECTOR, "a[href*='/catalog/']")
                            href = link_element.get_attribute('href')
                            article = href.split('/catalog/')[1].split('/')[0]
                    except Exception as e:
                        logger.warning(f"Error getting article ID for card {index + 1}: {e}")
                        continue
                    
                    if not article:
                        logger.warning(f"No article found for card {index + 1}")
                        continue
                    
                    logger.info(f"Found article ID: {article}")
                    
                    # Get price
                    try:
                        price_element = card.find_element(By.CSS_SELECTOR, "span[class*='price-block__final-price']")
                        price_text = price_element.text.replace("₽", "").replace(" ", "").strip()
                        price = float(''.join(c for c in price_text if c.isdigit() or c == '.'))
                        logger.info(f"Found price: {price}")
                    except Exception as e:
                        try:
                            # Fallback to alternative price selector
                            price_element = card.find_element(By.CSS_SELECTOR, "span[class*='price']")
                            price_text = price_element.text.replace("₽", "").replace(" ", "").strip()
                            price = float(''.join(c for c in price_text if c.isdigit() or c == '.'))
                            logger.info(f"Found price using fallback selector: {price}")
                        except Exception as e:
                            logger.error(f"Error getting price for card {index + 1}: {e}")
                            continue
                    
                    # Получаем рейтинг
                    rating = 0
                    try:
                        rating_element = card.find_element(By.CSS_SELECTOR, "span[class*='rating']")
                        rating_style = rating_element.get_attribute('style')
                        if rating_style and 'width:' in rating_style:
                            width = float(rating_style.split('width:')[1].split('%')[0])
                            rating = width / 20
                            logger.info(f"Found rating: {rating}")
                    except Exception as e:
                        logger.warning(f"Error getting rating for card {index + 1}: {e}")
                    
                    # Получаем количество отзывов
                    reviews = 0
                    try:
                        reviews_element = card.find_element(By.CSS_SELECTOR, "span[class*='count']")
                        reviews_text = reviews_element.text.strip()
                        if reviews_text:
                            reviews = int(''.join(filter(str.isdigit, reviews_text)))
                            logger.info(f"Found reviews: {reviews}")
                    except Exception as e:
                        logger.warning(f"Error getting reviews for card {index + 1}: {e}")
                    
                    # Получаем продажи
                    sales = 0
                    try:
                        sales_element = card.find_element(By.CSS_SELECTOR, "span[class*='sold']")
                        sales_text = sales_element.text.strip()
                        if sales_text:
                            sales = int(''.join(filter(str.isdigit, sales_text)))
                            logger.info(f"Found sales: {sales}")
                    except Exception as e:
                        logger.warning(f"Error getting sales for card {index + 1}: {e}")
                    
                    # Добавляем товар в список
                    products.append({
                        "article": article,
                        "price": price,
                        "rating": rating,
                        "reviews": reviews,
                        "sales": sales
                    })
                    logger.info(f"Successfully added product {index + 1}")
                    
                except Exception as e:
                    logger.error(f"Error processing card {index + 1}: {e}")
                    continue
            
            logger.info(f"Successfully processed {len(products)} products")
            return products
            
        except Exception as e:
            logger.error(f"Error getting category products: {e}")
            return []

    async def analyze_category(self, url: str) -> dict:
        """Анализ категории"""
        try:
            # Получаем данные о категории
            category_data = await self._get_category_info(url)
            if not category_data:
                return {
                    'total_products': 0,
                    'price_stats': {
                        'min': 0,
                        'max': 0,
                        'avg': 0,
                        'median': 0
                    },
                    'sales_stats': {
                        'total': 0,
                        'avg_per_day': 0
                    },
                    'rating_stats': {
                        'avg': 0,
                        'avg_reviews': 0
                    },
                    'trends': {
                        'price': 0,
                        'sales': 0,
                        'competition': 0
                    },
                    'opportunities': "Нет данных для анализа"
                }
            
            # Получаем товары (синхронный вызов)
            products = await self._get_category_products(url)
            if not products:
                return {
                    'total_products': 0,
                    'price_stats': {
                        'min': 0,
                        'max': 0,
                        'avg': 0,
                        'median': 0
                    },
                    'sales_stats': {
                        'total': 0,
                        'avg_per_day': 0
                    },
                    'rating_stats': {
                        'avg': 0,
                        'avg_reviews': 0
                    },
                    'trends': {
                        'price': 0,
                        'sales': 0,
                        'competition': 0
                    },
                    'opportunities': "Нет данных для анализа"
                }
            
            # Рассчитываем статистику
            price_stats = self._calculate_price_stats(products)
            sales_stats = self._calculate_sales_stats(products)
            rating_stats = self._calculate_rating_stats(products)
            trends = self._calculate_trends(products)
            opportunities = self._find_opportunities(products, price_stats, sales_stats, rating_stats)
            
            return {
                'total_products': len(products),
                'price_stats': price_stats,
                'sales_stats': sales_stats,
                'rating_stats': rating_stats,
                'trends': trends,
                'opportunities': opportunities
            }
            
        except Exception as e:
            logger.error(f"Error analyzing category: {e}")
            return {
                'total_products': 0,
                'price_stats': {
                    'min': 0,
                    'max': 0,
                    'avg': 0,
                    'median': 0
                },
                'sales_stats': {
                    'total': 0,
                    'avg_per_day': 0
                },
                'rating_stats': {
                    'avg': 0,
                    'avg_reviews': 0
                },
                'trends': {
                    'price': 0,
                    'sales': 0,
                    'competition': 0
                },
                'opportunities': "Произошла ошибка при анализе категории"
            }

    def _calculate_price_stats(self, products: List[Dict]) -> Dict:
        """Расчет статистики цен"""
        if not products:
            return {'min': 0, 'max': 0, 'avg': 0, 'median': 0}
        
        prices = [p['price'] for p in products]
        return {
            'min': int(min(prices)),
            'max': int(max(prices)),
            'avg': int(sum(prices) / len(prices)),
            'median': int(sorted(prices)[len(prices) // 2])
        }

    def _calculate_sales_stats(self, products: List[Dict]) -> Dict:
        """Расчет статистики продаж"""
        if not products:
            return {'total': 0, 'avg_per_day': 0}
        
        sales = [p['sales'] for p in products]
        total_sales = sum(sales)
        avg_per_day = int(total_sales / 30)  # Предполагаем 30 дней
        
        return {
            'total': total_sales,
            'avg_per_day': avg_per_day
        }

    def _calculate_rating_stats(self, products: List[Dict]) -> Dict:
        """Расчет статистики рейтингов"""
        if not products:
            return {'avg': 0, 'avg_reviews': 0}
        
        # Фильтруем товары с ненулевым рейтингом
        rated_products = [p for p in products if p['rating'] > 0]
        
        if not rated_products:
            return {'avg': 0, 'avg_reviews': 0}
        
        ratings = [p['rating'] for p in rated_products]
        reviews = [p['reviews'] for p in rated_products]
        
        # Проверяем, что рейтинги в диапазоне 0-5
        valid_ratings = [r for r in ratings if 0 <= r <= 5]
        
        if not valid_ratings:
            return {'avg': 0, 'avg_reviews': 0}
        
        # Проверяем, что отзывы положительные
        valid_reviews = [r for r in reviews if r > 0]
        
        if not valid_reviews:
            return {'avg': round(sum(valid_ratings) / len(valid_ratings), 1), 'avg_reviews': 0}
        
        return {
            'avg': round(sum(valid_ratings) / len(valid_ratings), 1),
            'avg_reviews': int(sum(valid_reviews) / len(valid_reviews))
        }

    def _calculate_trends(self, products: List[Dict]) -> Dict:
        """Расчет трендов"""
        if not products:
            return {
                "price": 0,
                "sales": 0,
                "competition": 0
            }
        
        # Рассчитываем тренд цен
        prices = [p["price"] for p in products]
        if min(prices) > 0:
            price_trend = ((max(prices) - min(prices)) / min(prices)) * 100
            # Ограничиваем максимальный тренд цен до 50%
            price_trend = min(price_trend, 50)
        else:
            price_trend = 0
        
        # Рассчитываем тренд продаж
        sales = [p["sales"] for p in products]
        if min(sales) > 0:
            sales_trend = ((max(sales) - min(sales)) / min(sales)) * 100
            # Ограничиваем максимальный тренд продаж до 100%
            sales_trend = min(sales_trend, 100)
        else:
            sales_trend = 0
        
        # Рассчитываем уровень конкуренции
        # Учитываем количество товаров, разброс цен и средний рейтинг
        price_range = max(prices) - min(prices)
        avg_rating = sum(p["rating"] for p in products) / len(products)
        
        # Нормализуем рейтинг (4.0 = 0, 5.0 = 1)
        rating_factor = max(0, min(1, (avg_rating - 4.0) * 2))
        
        # Рассчитываем уровень конкуренции (0-100)
        competition_level = (
            (price_range / min(prices)) * 40 +  # Ценовой фактор (40%)
            (1 - rating_factor) * 30 +  # Рейтинговый фактор (30%)
            (len(products) / 100) * 30  # Фактор количества товаров (30%)
        )
        
        # Ограничиваем уровень конкуренции до 50
        competition_level = min(competition_level, 50)
        
        return {
            "price": round(price_trend, 2),
            "sales": round(sales_trend, 2),
            "competition": round(competition_level, 2)
        }

    def _find_opportunities(self, products: List[Dict], price_stats: Dict, sales_stats: Dict, rating_stats: Dict) -> List[Dict]:
        """Поиск рыночных возможностей"""
        opportunities = []
        
        if not products:
            return opportunities
        
        # Анализируем конкуренцию
        prices = [p["price"] for p in products]
        avg_price = sum(prices) / len(prices)
        price_range = max(prices) - min(prices)
        
        if price_range / avg_price < 0.3:
            opportunities.append({
                "description": "Низкая конкуренция в категории",
                "confidence": 0.8
            })
        
        # Анализируем ценовые сегменты
        price_segments = {
            "low": len([p for p in prices if p < avg_price * 0.7]),
            "medium": len([p for p in prices if avg_price * 0.7 <= p <= avg_price * 1.3]),
            "high": len([p for p in prices if p > avg_price * 1.3])
        }
        
        if price_segments["low"] < price_segments["medium"] * 0.3:
            opportunities.append({
                "description": "Возможность выхода в нижний ценовой сегмент",
                "confidence": 0.7
            })
        
        if price_segments["high"] < price_segments["medium"] * 0.3:
            opportunities.append({
                "description": "Возможность выхода в премиальный сегмент",
                "confidence": 0.7
            })
        
        # Анализируем рейтинги
        ratings = [p["rating"] for p in products if p["rating"] > 0]
        if ratings:
            avg_rating = sum(ratings) / len(ratings)
            
            if avg_rating < 4.5:
                opportunities.append({
                    "description": "Возможность улучшения качества для повышения рейтинга",
                    "confidence": 0.6
                })
        
        # Анализируем продажи
        sales = [p["sales"] for p in products if p["sales"] > 0]
        if sales:
            avg_sales = sum(sales) / len(sales)
            max_sales = max(sales)
            
            if avg_sales < max_sales * 0.3:
                opportunities.append({
                    "description": "Возможность увеличения продаж через маркетинг",
                    "confidence": 0.7
                })
        
        # Анализируем отзывы
        reviews = [p["reviews"] for p in products if p["reviews"] > 0]
        if reviews:
            avg_reviews = sum(reviews) / len(reviews)
            
            if avg_reviews < 100:
                opportunities.append({
                    "description": "Возможность увеличения количества отзывов через программы лояльности",
                    "confidence": 0.6
                })
        
        # Если нет возможностей, добавляем общую рекомендацию
        if not opportunities:
            opportunities.append({
                "description": "Категория требует дополнительного анализа для выявления возможностей",
                "confidence": 0.5
            })
        
        return opportunities

    def analyze_category_competition(self, products: List[Dict]) -> Dict:
        """Анализ конкуренции в категории"""
        df = pd.DataFrame(products)
        
        if df.empty:
            return {
                "competition_level": "unknown",
                "competition_score": 0,
                "competition_factors": []
            }
        
        # Анализ количества товаров
        total_products = len(df)
        competition_factors = []
        
        if total_products > 1000:
            competition_factors.append({
                "factor": "high_product_count",
                "description": "Высокое количество товаров в категории",
                "impact": "high"
            })
        elif total_products < 100:
            competition_factors.append({
                "factor": "low_product_count",
                "description": "Низкое количество товаров в категории",
                "impact": "low"
            })
        
        # Анализ ценовой конкуренции
        if 'price' in df.columns:
            price_range = df['price'].max() - df['price'].min()
            price_std = df['price'].std()
            
            if price_std > price_range * 0.5:
                competition_factors.append({
                    "factor": "high_price_variation",
                    "description": "Высокий разброс цен в категории",
                    "impact": "medium"
                })
        
        # Анализ рейтингов
        if 'rating' in df.columns:
            avg_rating = df['rating'].mean()
            if avg_rating > 4.5:
                competition_factors.append({
                    "factor": "high_ratings",
                    "description": "Высокие рейтинги товаров",
                    "impact": "high"
                })
        
        # Анализ продаж
        if 'sales' in df.columns:
            sales_std = df['sales'].std()
            sales_mean = df['sales'].mean()
            
            if sales_std > sales_mean * 2:
                competition_factors.append({
                    "factor": "high_sales_variation",
                    "description": "Высокий разброс в продажах",
                    "impact": "medium"
                })
        
        # Расчет общего уровня конкуренции
        competition_score = 0
        for factor in competition_factors:
            if factor["impact"] == "high":
                competition_score += 2
            elif factor["impact"] == "medium":
                competition_score += 1
        
        # Определение уровня конкуренции
        competition_level = "medium"
        if competition_score >= 4:
            competition_level = "high"
        elif competition_score <= 1:
            competition_level = "low"
        
        return {
            "competition_level": competition_level,
            "competition_score": competition_score,
            "competition_factors": competition_factors
        }

    def analyze_price_segments(self, products: List[Dict]) -> Dict:
        """Анализ ценовых сегментов"""
        df = pd.DataFrame(products)
        
        if df.empty or 'price' not in df.columns:
            return {
                "segments": [],
                "segment_stats": {}
            }
        
        # Конвертируем цены в рубли
        df['price_rub'] = df['price'] / 100
        
        # Разделяем на сегменты
        price_segments = pd.qcut(df['price_rub'], q=5, duplicates='drop')
        segment_stats = {}
        
        for segment in price_segments.unique():
            segment_data = df[price_segments == segment]
            
            stats = {
                "product_count": len(segment_data),
                "avg_price": int(segment_data['price_rub'].mean()),
                "min_price": int(segment_data['price_rub'].min()),
                "max_price": int(segment_data['price_rub'].max()),
                "avg_rating": round(float(segment_data['rating'].mean()), 1) if 'rating' in segment_data.columns else 0,
                "avg_sales": int(segment_data['sales'].mean()) if 'sales' in segment_data.columns else 0,
                "avg_reviews": int(segment_data['reviews'].mean()) if 'reviews' in segment_data.columns else 0
            }
            
            segment_stats[str(segment)] = stats
        
        return {
            "segments": [str(seg) for seg in price_segments.unique()],
            "segment_stats": segment_stats
        }

    def analyze_brand_competition(self, products: List[Dict]) -> Dict:
        """Анализ конкуренции между брендами"""
        df = pd.DataFrame(products)
        
        if df.empty or 'brand' not in df.columns:
            return {
                "brand_stats": {},
                "top_brands": []
            }
        
        # Группируем по брендам
        brand_stats = {}
        for brand in df['brand'].unique():
            brand_data = df[df['brand'] == brand]
            
            stats = {
                "product_count": len(brand_data),
                "avg_price": int(brand_data['price'].mean() / 100),
                "avg_rating": round(float(brand_data['rating'].mean()), 1) if 'rating' in brand_data.columns else 0,
                "total_sales": int(brand_data['sales'].sum()) if 'sales' in brand_data.columns else 0,
                "avg_reviews": int(brand_data['reviews'].mean()) if 'reviews' in brand_data.columns else 0
            }
            
            brand_stats[brand] = stats
        
        # Определяем топ брендов по продажам
        if 'sales' in df.columns:
            top_brands = df.groupby('brand')['sales'].sum().nlargest(5).index.tolist()
        else:
            top_brands = []
        
        return {
            "brand_stats": brand_stats,
            "top_brands": top_brands
        }

    def visualize_data(self, data: List[Dict[str, Any]], category_name: str):
        """Визуализация данных"""
        try:
            # Создаем директорию для графиков, если её нет
            os.makedirs('plots', exist_ok=True)
            
            # Подготавливаем данные
            prices = [item['price']/100 for item in data]  # Конвертируем в рубли
            ratings = [item['rating'] for item in data if item['rating'] > 0]
            sales = [item['sales'] for item in data if item['sales'] > 0]
            reviews = [item['reviews'] for item in data if item['reviews'] > 0]
            
            # Создаем фигуру с подграфиками
            fig = plt.figure(figsize=(20, 15))
            gs = fig.add_gridspec(3, 2)
            
            # 1. Распределение цен
            ax1 = fig.add_subplot(gs[0, 0])
            sns.histplot(prices, bins=30, ax=ax1)
            ax1.set_title('Распределение цен', fontsize=12, pad=10)
            ax1.set_xlabel('Цена (₽)')
            ax1.set_ylabel('Количество товаров')
            
            # Добавляем вертикальные линии для среднего и медианного значений
            ax1.axvline(np.mean(prices), color='red', linestyle='--', label='Среднее')
            ax1.axvline(np.median(prices), color='green', linestyle='--', label='Медиана')
            ax1.legend()
            
            # Добавляем аннотации с ценовой статистикой
            price_stats = f'Мин: {int(min(prices))}₽\nМакс: {int(max(prices))}₽\nСреднее: {int(np.mean(prices))}₽\nМедиана: {int(np.median(prices))}₽'
            ax1.text(0.02, 0.98, price_stats, transform=ax1.transAxes, 
                    verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # 2. Корреляция цены и рейтинга
            ax2 = fig.add_subplot(gs[0, 1])
            if ratings:
                sns.scatterplot(x=prices, y=ratings, ax=ax2)
                ax2.set_title('Корреляция цены и рейтинга', fontsize=12, pad=10)
                ax2.set_xlabel('Цена (₽)')
                ax2.set_ylabel('Рейтинг')
                
                # Добавляем линию тренда
                z = np.polyfit(prices, ratings, 1)
                p = np.poly1d(z)
                ax2.plot(prices, p(prices), "r--", alpha=0.8)
                
                # Добавляем аннотации с рейтингом
                rating_stats = f'Средний рейтинг: {np.mean(ratings):.1f}\nМедианный рейтинг: {np.median(ratings):.1f}'
                ax2.text(0.02, 0.98, rating_stats, transform=ax2.transAxes, 
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # 3. Топ-10 товаров по продажам
            ax3 = fig.add_subplot(gs[1, 0])
            if sales:
                top_sales = sorted(data, key=lambda x: x['sales'], reverse=True)[:10]
                sns.barplot(x=[item['sales'] for item in top_sales], 
                          y=[item['name'][:30] + '...' for item in top_sales], 
                          ax=ax3)
                ax3.set_title('Топ-10 товаров по продажам', fontsize=12, pad=10)
                ax3.set_xlabel('Количество продаж')
                ax3.set_ylabel('Название товара')
                
                # Добавляем аннотации с продажами
                sales_stats = f'Всего продаж: {sum(sales)}\nСредние продажи: {int(np.mean(sales))}\nМедианные продажи: {int(np.median(sales))}'
                ax3.text(0.02, 0.98, sales_stats, transform=ax3.transAxes, 
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # 4. Распределение рейтингов
            ax4 = fig.add_subplot(gs[1, 1])
            if ratings:
                sns.histplot(ratings, bins=20, ax=ax4)
                ax4.set_title('Распределение рейтингов', fontsize=12, pad=10)
                ax4.set_xlabel('Рейтинг')
                ax4.set_ylabel('Количество товаров')
                
                # Добавляем вертикальные линии для среднего и медианного значений
                ax4.axvline(np.mean(ratings), color='red', linestyle='--', label='Среднее')
                ax4.axvline(np.median(ratings), color='green', linestyle='--', label='Медиана')
                ax4.legend()
                
                # Добавляем аннотации с отзывами
                if reviews:
                    review_stats = f'Средние отзывы: {int(np.mean(reviews))}\nМедианные отзывы: {int(np.median(reviews))}'
                    ax4.text(0.02, 0.98, review_stats, transform=ax4.transAxes, 
                            verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # 5. Корреляция рейтинга и отзывов
            ax5 = fig.add_subplot(gs[2, 0])
            if ratings and reviews:
                sns.scatterplot(x=ratings, y=reviews, ax=ax5)
                ax5.set_title('Корреляция рейтинга и количества отзывов', fontsize=12, pad=10)
                ax5.set_xlabel('Рейтинг')
                ax5.set_ylabel('Количество отзывов')
                
                # Добавляем линию тренда
                z = np.polyfit(ratings, reviews, 1)
                p = np.poly1d(z)
                ax5.plot(ratings, p(ratings), "r--", alpha=0.8)
            
            # 6. Корреляция цены и продаж
            ax6 = fig.add_subplot(gs[2, 1])
            if sales:
                sns.scatterplot(x=prices, y=sales, ax=ax6)
                ax6.set_title('Корреляция цены и продаж', fontsize=12, pad=10)
                ax6.set_xlabel('Цена (₽)')
                ax6.set_ylabel('Количество продаж')
                
                # Добавляем линию тренда
                z = np.polyfit(prices, sales, 1)
                p = np.poly1d(z)
                ax6.plot(prices, p(prices), "r--", alpha=0.8)
                
                # Добавляем аннотации с корреляцией
                correlation = np.corrcoef(prices, sales)[0, 1]
                corr_stats = f'Корреляция: {correlation:.2f}'
                ax6.text(0.02, 0.98, corr_stats, transform=ax6.transAxes, 
                        verticalalignment='top', bbox=dict(boxstyle='round', facecolor='white', alpha=0.8))
            
            # Настраиваем общий заголовок
            fig.suptitle(f'Анализ категории "{category_name}"', fontsize=16, y=0.95)
            
            # Сохраняем график
            plt.tight_layout()
            plt.savefig(f'plots/{category_name}_analysis.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            logger.info(f"Графики сохранены в директорию 'plots/{category_name}_analysis.png'")
            
        except Exception as e:
            logger.error(f"Ошибка при создании графиков: {e}") 

    async def search_by_article(self, article_id: str) -> dict:
        """Поиск товара по артикулу"""
        try:
            await self.ensure_driver()
            
            url = f"https://www.wildberries.ru/catalog/{article_id}/detail.aspx"
            self.driver.get(url)
            
            # Ждем загрузки страницы
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "product-page__main"))
            )
            
            # Получаем данные о товаре
            product = {
                'name': self.driver.find_element(By.CLASS_NAME, "product-page__header").text,
                'brand': self.driver.find_element(By.CLASS_NAME, "product-page__brand").text,
                'price': float(self.driver.find_element(By.CLASS_NAME, "price-block__final-price").text.replace('₽', '').strip()),
                'rating': float(self.driver.find_element(By.CLASS_NAME, "product-page__rating").text),
                'reviews': int(self.driver.find_element(By.CLASS_NAME, "product-page__reviews-count").text),
                'sales': int(self.driver.find_element(By.CLASS_NAME, "product-page__sales-count").text),
                'url': url
            }
            
            return {
                'success': True,
                'product': product
            }
            
        except Exception as e:
            logger.error(f"Ошибка при поиске товара: {e}")
            return {
                'success': False,
                'error': f"Не удалось найти товар с артикулом {article_id}"
            } 