import asyncio
import logging
from typing import Dict, List, Any
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
import requests
import os
import matplotlib.pyplot as plt
import time

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ArticleAnalyzer:
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

    async def initialize_driver(self):
        """Инициализация WebDriver"""
        for attempt in range(self.max_retries):
            try:
                if self.driver:
                    await self.close_driver()
                
                chrome_options = Options()
                chrome_options.add_argument('--headless=new')
                chrome_options.add_argument('--no-sandbox')
                chrome_options.add_argument('--disable-dev-shm-usage')
                chrome_options.add_argument('--disable-gpu')
                chrome_options.add_argument('--window-size=1920,1080')
                chrome_options.add_argument('--disable-blink-features=AutomationControlled')
                chrome_options.add_experimental_option('excludeSwitches', ['enable-automation'])
                chrome_options.add_experimental_option('useAutomationExtension', False)
                
                # Добавляем User-Agent
                chrome_options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')
                
                # Добавляем дополнительные опции для стабильности
                chrome_options.add_argument('--disable-extensions')
                chrome_options.add_argument('--disable-infobars')
                chrome_options.add_argument('--disable-notifications')
                chrome_options.add_argument('--disable-popup-blocking')
                chrome_options.add_argument('--disable-web-security')
                chrome_options.add_argument('--ignore-certificate-errors')
                chrome_options.add_argument('--ignore-ssl-errors')
                chrome_options.add_argument('--disable-site-isolation-trials')
                chrome_options.add_argument('--disable-features=IsolateOrigins,site-per-process')
                
                # Увеличиваем таймауты и отключаем DNS prefetch
                chrome_options.add_argument('--dns-prefetch-disable')
                chrome_options.add_argument('--no-proxy-server')
                chrome_options.add_argument('--disable-background-networking')
                chrome_options.add_argument('--disable-background-timer-throttling')
                chrome_options.add_argument('--disable-backgrounding-occluded-windows')
                chrome_options.add_argument('--disable-breakpad')
                chrome_options.add_argument('--disable-component-extensions-with-background-pages')
                chrome_options.add_argument('--disable-features=TranslateUI,BlinkGenPropertyTrees')
                chrome_options.add_argument('--disable-ipc-flooding-protection')
                chrome_options.add_argument('--enable-features=NetworkService,NetworkServiceInProcess')
                
                service = Service(ChromeDriverManager().install())
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
                
                # Устанавливаем таймауты
                self.driver.set_page_load_timeout(self.page_load_timeout)
                self.wait = WebDriverWait(self.driver, self.element_timeout)
                
                # Проверяем работоспособность драйвера
                self.driver.get("https://www.wildberries.ru")
                await asyncio.sleep(5)  # Уменьшаем время ожидания
                
                # Проверяем, что страница полностью загрузилась
                try:
                    self.wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
                except TimeoutException:
                    logger.warning("Initial page load timeout, retrying...")
                    continue
                
                # Дополнительная проверка загрузки
                try:
                    self.wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
                except TimeoutException:
                    logger.warning("Body element not found, retrying...")
                    continue
                
                logger.info("WebDriver успешно инициализирован")
                return True
                
            except Exception as e:
                logger.error(f"Error initializing WebDriver (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise

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
                logger.info("WebDriver успешно закрыт")
            except Exception as e:
                logger.error(f"Error closing WebDriver: {e}")
                self.driver = None

    async def wait_for_element(self, by: By, value: str, timeout: int = None) -> Any:
        """Ожидание элемента с повторными попытками"""
        if timeout is None:
            timeout = self.element_timeout
            
        for attempt in range(self.max_retries):
            try:
                # Сначала проверяем, что страница загружена
                self.wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
                
                # Затем ищем элемент
                element = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_element_located((by, value))
                )
                return element
            except TimeoutException:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Timeout waiting for element {value}, attempt {attempt + 1}/{self.max_retries}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise
            except Exception as e:
                logger.error(f"Error waiting for element {value}: {e}")
                raise

    async def wait_for_elements(self, by: By, value: str, timeout: int = None) -> List[Any]:
        """Ожидание элементов с повторными попытками"""
        if timeout is None:
            timeout = self.element_timeout
            
        for attempt in range(self.max_retries):
            try:
                # Сначала проверяем, что страница загружена
                self.wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
                
                # Затем ищем элементы
                elements = WebDriverWait(self.driver, timeout).until(
                    EC.presence_of_all_elements_located((by, value))
                )
                return elements
            except TimeoutException:
                if attempt < self.max_retries - 1:
                    logger.warning(f"Timeout waiting for elements {value}, attempt {attempt + 1}/{self.max_retries}")
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                raise
            except Exception as e:
                logger.error(f"Error waiting for elements {value}: {e}")
                raise

    async def search_by_article(self, article_id: str) -> dict:
        """Поиск товара по артикулу"""
        for attempt in range(self.max_retries):
            try:
                if not self.driver:
                    await self.initialize_driver()
                
                # Формируем URL товара
                url = f"https://www.wildberries.ru/catalog/{article_id}/detail.aspx"
                
                # Открываем страницу товара
                self.driver.get(url)
                
                # Ждем загрузку страницы
                try:
                    self.wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
                except TimeoutException:
                    logger.warning("Initial page load timeout")
                    if attempt < self.max_retries - 1:
                        await self.close_driver()
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    return {
                        "success": False,
                        "error": "Превышено время ожидания загрузки страницы"
                    }
                
                # Проверяем наличие ошибки 404
                if "Страница не найдена" in self.driver.page_source:
                    return {
                        "success": False,
                        "error": "Товар не найден"
                    }
                
                # Ждем появления основных элементов
                try:
                    # Ждем появления цены
                    price_element = await self.wait_for_element(By.CSS_SELECTOR, "[data-widget='webPrice']")
                    price_text = price_element.text.replace("₽", "").replace(" ", "").strip()
                    price = float(price_text)
                    
                    # Ждем появления названия
                    name_element = await self.wait_for_element(By.CSS_SELECTOR, "h1")
                    name = name_element.text
                    
                    # Ждем появления рейтинга
                    rating_element = await self.wait_for_element(By.CSS_SELECTOR, "[data-widget='webRating']")
                    rating_text = rating_element.text.split()[0]
                    rating = float(rating_text)
                    
                    # Ждем появления отзывов
                    reviews_element = await self.wait_for_element(By.CSS_SELECTOR, "[data-widget='webReview']")
                    reviews_text = reviews_element.text.split()[0]
                    reviews = int(reviews_text)
                    
                    # Ждем появления продаж
                    sales_element = await self.wait_for_element(By.CSS_SELECTOR, "[data-widget='webProductSold']")
                    sales_text = sales_element.text.split()[0]
                    sales = int(sales_text)
                    
                    # Вычисляем дополнительные метрики
                    revenue = price * sales
                    profit = revenue * 0.3  # Примерная прибыль 30%
                    
                    # Определяем динамику продаж
                    sales_trend = "Стабильно"  # По умолчанию
                    if sales > 0:
                        sales_trend = "Рост" if sales > 10 else "Спад" if sales < 5 else "Стабильно"
                    
                    # Формируем результат
                    result = {
                        "success": True,
                        "data": {
                            "Название": name,
                            "Цена": f"{price:.2f}",
                            "Отзывы": reviews,
                            "Продажи за сутки": sales,
                            "Выручка за сутки": f"{revenue:.2f} ₽",
                            "Прибыль за сутки": f"{profit:.2f} ₽",
                            "Динамика продаж": sales_trend,
                            "Приблизительные продажи за неделю": sales * 7,
                            "Приблизительные продажи за месяц": sales * 30,
                            "Выручка за неделю (приблизительно)": f"{revenue * 7:.2f} ₽",
                            "Выручка за месяц (приблизительно)": f"{revenue * 30:.2f} ₽",
                            "Прибыль за неделю (приблизительно)": f"{profit * 7:.2f} ₽",
                            "Прибыль за месяц (приблизительно)": f"{profit * 30:.2f} ₽"
                        }
                    }
                    
                    return result
                    
                except TimeoutException:
                    logger.error("Timeout while waiting for elements")
                    if attempt < self.max_retries - 1:
                        await self.close_driver()
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    return {
                        "success": False,
                        "error": "Превышено время ожидания загрузки данных"
                    }
                except NoSuchElementException:
                    logger.error("Element not found")
                    if attempt < self.max_retries - 1:
                        await self.close_driver()
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    return {
                        "success": False,
                        "error": "Не удалось найти информацию о товаре"
                    }
                except Exception as e:
                    logger.error(f"Error extracting product data: {e}")
                    if attempt < self.max_retries - 1:
                        await self.close_driver()
                        await asyncio.sleep(self.retry_delay * (attempt + 1))
                        continue
                    return {
                        "success": False,
                        "error": "Не удалось получить информацию о товаре"
                    }
                
            except Exception as e:
                logger.error(f"Error searching by article (attempt {attempt + 1}/{self.max_retries}): {e}")
                if attempt < self.max_retries - 1:
                    await self.close_driver()
                    await asyncio.sleep(self.retry_delay * (attempt + 1))
                    continue
                return {
                    "success": False,
                    "error": "Произошла ошибка при поиске товара"
                }

    def get_article_info(self, article_id: str) -> Dict:
        """Получение информации о товаре по артикулу"""
        try:
            # Формируем URL для API
            api_url = f"https://card.wb.ru/cards/detail?curr=rub&dest=-1257786&regions=80,64,83,4,38,33,70,82,69,30,86,75,40,1,66,48,110,31,22,71,114&nm={article_id}"
            
            # Делаем запрос к API
            response = requests.get(api_url, headers=self.headers)
            
            if response.status_code == 200:
                data = response.json()
                products = data.get('data', {}).get('products', [])
                
                if not products:
                    logger.warning(f"Товар с артикулом {article_id} не найден")
                    return None
                
                product = products[0]
                
                # Извлекаем основную информацию с проверкой типов
                name = str(product.get('name', 'Unknown Product'))
                brand = str(product.get('brand', 'Unknown Brand'))
                price = float(product.get('priceU', 0)) / 100 if 'priceU' in product else float(product.get('price', 0))
                rating = float(product.get('rating', 0.0))
                reviews = int(product.get('reviewRating', 0))
                sales = int(product.get('soldQuantity', 0))
                likes = int(product.get('likes', 0))
                views = int(product.get('views', 0))
                
                # Извлекаем характеристики
                specs = {}
                if 'characteristics' in product and isinstance(product['characteristics'], list):
                    for char in product['characteristics']:
                        if isinstance(char, dict):
                            specs[str(char.get('name', ''))] = str(char.get('value', ''))
                
                # Извлекаем размеры
                sizes = []
                if 'sizes' in product and isinstance(product['sizes'], list):
                    for size in product['sizes']:
                        if isinstance(size, dict) and size.get('name'):
                            sizes.append(str(size['name']))
                
                # Извлекаем цвета
                colors = []
                if 'colors' in product and isinstance(product['colors'], list):
                    for color in product['colors']:
                        if isinstance(color, dict) and color.get('name'):
                            colors.append(str(color['name']))
                
                # Извлекаем отзывы
                feedback = []
                if 'feedbacks' in product and isinstance(product['feedbacks'], list):
                    for fb in product['feedbacks']:
                        if isinstance(fb, dict):
                            feedback.append({
                                'rating': float(fb.get('rating', 0)),
                                'text': str(fb.get('text', '')),
                                'date': str(fb.get('date', ''))
                            })
                
                return {
                    'article_id': str(article_id),
                    'name': name,
                    'brand': brand,
                    'price': price,
                    'rating': rating,
                    'reviews': reviews,
                    'sales': sales,
                    'likes': likes,
                    'views': views,
                    'specifications': specs,
                    'sizes': sizes,
                    'colors': colors,
                    'feedback': feedback
                }
            
            logger.warning(f"API вернул статус {response.status_code}")
            return None
            
        except Exception as e:
            logger.error(f"Ошибка при получении информации о товаре: {str(e)}")
            return None
    
    def analyze_article(self, article_id: str) -> Dict:
        """Полный анализ товара"""
        try:
            # Получаем информацию о товаре
            article_info = self.get_article_info(article_id)
            if not article_info:
                return {
                    "status": "error",
                    "error": "Не удалось получить информацию о товаре"
                }
            
            # Анализируем отзывы
            feedback_analysis = self._analyze_feedback(article_info['feedback'])
            
            # Анализируем продажи
            sales_analysis = self._analyze_sales(article_info)
            
            # Анализируем конкурентов
            competitors_analysis = self._analyze_competitors(article_info)
            
            # Формируем рекомендации
            recommendations = self._generate_recommendations(article_info, feedback_analysis, sales_analysis, competitors_analysis)
            
            return {
                "status": "success",
                "article_info": article_info,
                "feedback_analysis": feedback_analysis,
                "sales_analysis": sales_analysis,
                "competitors_analysis": competitors_analysis,
                "recommendations": recommendations
            }
            
        except Exception as e:
            return {
                "status": "error",
                "error": str(e)
            }
    
    def _analyze_feedback(self, feedback: List[Dict]) -> Dict:
        """Анализ отзывов"""
        if not feedback:
            return {
                "total_feedback": 0,
                "average_rating": 0,
                "positive_percentage": 0,
                "negative_percentage": 0,
                "common_complaints": [],
                "common_praises": []
            }
        
        # Подсчитываем статистику
        total = len(feedback)
        ratings = [f['rating'] for f in feedback]
        avg_rating = sum(ratings) / total
        positive = len([r for r in ratings if r >= 4])
        negative = len([r for r in ratings if r <= 2])
        
        # Анализируем тексты отзывов
        complaints = []
        praises = []
        for f in feedback:
            text = f['text'].lower()
            if f['rating'] <= 2:
                complaints.append(text)
            elif f['rating'] >= 4:
                praises.append(text)
        
        return {
            "total_feedback": total,
            "average_rating": round(avg_rating, 1),
            "positive_percentage": round(positive / total * 100, 1),
            "negative_percentage": round(negative / total * 100, 1),
            "common_complaints": self._extract_common_phrases(complaints),
            "common_praises": self._extract_common_phrases(praises)
        }
    
    def _analyze_sales(self, article_info: Dict) -> Dict:
        """Анализ продаж"""
        sales = article_info['sales']
        views = article_info['views']
        
        if views == 0:
            conversion = 0
        else:
            conversion = (sales / views) * 100
        
        return {
            "total_sales": sales,
            "views": views,
            "conversion_rate": round(conversion, 2),
            "sales_per_day": round(sales / 30, 1),  # Примерная оценка
            "performance": "high" if conversion > 5 else "medium" if conversion > 2 else "low"
        }
    
    def _analyze_competitors(self, article_info: Dict) -> Dict:
        """Анализ конкурентов"""
        # Здесь можно добавить логику анализа конкурентов
        # Например, поиск похожих товаров по названию или характеристикам
        return {
            "competition_level": "medium",  # Пример
            "price_position": "competitive",  # Пример
            "market_share": "small"  # Пример
        }
    
    def _generate_recommendations(self, article_info: Dict, feedback_analysis: Dict, 
                                sales_analysis: Dict, competitors_analysis: Dict) -> List[Dict]:
        """Генерация рекомендаций"""
        recommendations = []
        
        # Анализ цены
        if article_info['price'] > 10000:  # Пример порога
            recommendations.append({
                "type": "price",
                "description": "Рассмотрите возможность снижения цены для повышения конкурентоспособности",
                "confidence": 0.8
            })
        
        # Анализ отзывов
        if feedback_analysis['negative_percentage'] > 20:
            recommendations.append({
                "type": "quality",
                "description": "Улучшите качество товара на основе отзывов покупателей",
                "confidence": 0.9
            })
        
        # Анализ продаж
        if sales_analysis['performance'] == "low":
            recommendations.append({
                "type": "marketing",
                "description": "Усильте маркетинговые усилия для повышения продаж",
                "confidence": 0.7
            })
        
        return recommendations
    
    def _extract_common_phrases(self, texts: List[str]) -> List[str]:
        """Извлечение часто встречающихся фраз из текстов"""
        # Здесь можно добавить более сложную логику анализа текста
        # Например, использование NLP для выделения ключевых фраз
        return ["Часто встречающаяся фраза 1", "Часто встречающаяся фраза 2"]

    def visualize_article_data(self, analysis_result: dict):
        """Визуализация данных по товару"""
        try:
            # Создаем директорию для графиков, если её нет
            if not os.path.exists('plots'):
                os.makedirs('plots')

            article_info = analysis_result['article_info']
            feedback = analysis_result['feedback_analysis']
            sales = analysis_result['sales_analysis']
            
            # Создаем фигуру с несколькими графиками
            fig = plt.figure(figsize=(15, 10))
            
            # 1. График продаж и просмотров
            plt.subplot(2, 2, 1)
            data = {
                'Продажи': sales['total_sales'],
                'Просмотры': sales['views']
            }
            plt.bar(data.keys(), data.values())
            plt.title('Продажи и просмотры')
            plt.xticks(rotation=45)
            
            # 2. Круговая диаграмма отзывов
            plt.subplot(2, 2, 2)
            feedback_data = {
                'Положительные': feedback['positive_percentage'],
                'Отрицательные': feedback['negative_percentage'],
                'Нейтральные': 100 - feedback['positive_percentage'] - feedback['negative_percentage']
            }
            plt.pie(feedback_data.values(), labels=feedback_data.keys(), autopct='%1.1f%%')
            plt.title('Распределение отзывов')
            
            # 3. График эффективности продаж
            plt.subplot(2, 2, 3)
            performance_data = {
                'Конверсия': sales['conversion_rate'],
                'Продажи в день': sales['sales_per_day']
            }
            plt.bar(performance_data.keys(), performance_data.values())
            plt.title('Эффективность продаж')
            plt.xticks(rotation=45)
            
            # 4. График рейтинга
            plt.subplot(2, 2, 4)
            rating_data = {
                'Текущий рейтинг': article_info['rating'],
                'Средний рейтинг': feedback['average_rating']
            }
            plt.bar(rating_data.keys(), rating_data.values())
            plt.title('Рейтинг товара')
            plt.xticks(rotation=45)
            
            # Настраиваем общий заголовок
            plt.suptitle(f'Анализ товара: {article_info["name"]}', fontsize=16)
            
            # Сохраняем график
            plt.tight_layout()
            plt.savefig(f'plots/article_{article_info["article_id"]}_analysis.png')
            plt.close()
            
        except Exception as e:
            print(f"Error visualizing article data: {str(e)}")
            return None

    def _get_article_data(self, article: str) -> Dict[str, Any]:
        """Получение данных о товаре"""
        try:
            # Используем общий драйвер из класса
            self.driver.get(f"https://www.wildberries.ru/catalog/{article}/detail.aspx")
            time.sleep(2)  # Ждем загрузку страницы
            
            # Получаем данные с помощью WebDriverWait
            wait = WebDriverWait(self.driver, 10)
            
            # Получаем цену
            price_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-widget='webPrice']"))
            )
            price = float(price_element.text.replace('₽', '').replace(' ', '').strip())
            
            # Получаем рейтинг
            rating_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-widget='webRating']"))
            )
            rating = float(rating_element.text.split()[0])
            
            # Получаем количество отзывов
            reviews_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-widget='webReview']"))
            )
            reviews = int(reviews_element.text.split()[0])
            
            # Получаем продажи
            sales_element = wait.until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-widget='webProductSold']"))
            )
            sales = int(sales_element.text.split()[0])
            
            return {
                'price': price,
                'rating': rating,
                'reviews': reviews,
                'sales': sales
            }
            
        except Exception as e:
            logger.error(f"Error getting article data: {str(e)}")
            return {
                'price': 0,
                'rating': 0,
                'reviews': 0,
                'sales': 0
            } 