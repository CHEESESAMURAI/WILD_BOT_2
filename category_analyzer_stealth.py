import asyncio
import logging
import random
import time
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from selenium.webdriver.common.action_chains import ActionChains
from webdriver_manager.chrome import ChromeDriverManager
from typing import Dict, List, Optional
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from article_analyzer import ArticleAnalyzer

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# List of user agents to rotate
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36 Edg/91.0.864.59'
]

class CategoryAnalyzer:
    def __init__(self, driver=None):
        """Initialize the analyzer with an optional existing WebDriver"""
        self.driver = driver
        self.products = []
        self.article_analyzer = None
        self.session = requests.Session()
        self._init_webdriver()

    def _init_webdriver(self):
        """Initialize WebDriver if not already initialized"""
        if self.driver is None:
            try:
                logger.info("Initializing WebDriver...")
                options = webdriver.ChromeOptions()
                options.add_argument('--headless')
                options.add_argument('--no-sandbox')
                options.add_argument('--disable-dev-shm-usage')
                options.add_argument('--disable-gpu')
                options.add_argument('--window-size=1920,1080')
                options.add_argument('--disable-blink-features=AutomationControlled')
                options.add_experimental_option("excludeSwitches", ["enable-automation"])
                options.add_experimental_option('useAutomationExtension', False)
                
                # Add random user agent
                user_agent = random.choice(USER_AGENTS)
                options.add_argument(f'user-agent={user_agent}')
                
                # Initialize WebDriver with retry logic
                max_retries = 3
                for attempt in range(max_retries):
                    try:
                        self.driver = webdriver.Chrome(options=options)
                        self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
                        self.wait = WebDriverWait(self.driver, 10)
                        logger.info("WebDriver successfully initialized")
                        break
                    except Exception as e:
                        logger.error(f"Failed to initialize WebDriver (attempt {attempt + 1}/{max_retries}): {str(e)}")
                        if attempt == max_retries - 1:
                            raise
                        time.sleep(2)
                
                # Initialize article analyzer with the same driver
                self.article_analyzer = ArticleAnalyzer(self.driver)
                
            except Exception as e:
                logger.error(f"Error initializing WebDriver: {str(e)}")
                raise

    async def close_driver(self):
        """Close WebDriver"""
        if self.driver:
            try:
                self.driver.quit()
            except Exception as e:
                logger.warning(f"Error closing driver: {e}")
            finally:
                self.driver = None
                self.wait = None
                logger.info("WebDriver closed")

    async def ensure_driver(self):
        """Ensure WebDriver is initialized"""
        if not self.driver or not self.wait:
            self.initialize_driver()

    async def _get_category_products(self, url: str) -> List[Dict]:
        """Get list of products from category"""
        try:
            # First try with requests to get the initial page content
            logger.info(f"Trying to fetch URL with requests: {url}")
            response = self.session.get(url, timeout=30)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch URL with requests: {response.status_code}")
                # Fall back to Selenium
                return await self._get_category_products_selenium(url)
            
            # Parse the HTML with BeautifulSoup
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Check if we got a valid page
            if "wildberries" not in response.text.lower():
                logger.warning("Response doesn't look like Wildberries page, falling back to Selenium")
                return await self._get_category_products_selenium(url)
            
            # Try to find product cards in the HTML
            product_cards = soup.select("div[class*='product-card']")
            if not product_cards:
                product_cards = soup.select("div[class*='card']")
            if not product_cards:
                product_cards = soup.select("div[class*='product']")
            if not product_cards:
                product_cards = soup.select("div[class*='item']")
            if not product_cards:
                product_cards = soup.select("div[class*='goods']")
            
            logger.info(f"Found {len(product_cards)} product cards with requests")
            
            if not product_cards:
                logger.warning("No product cards found with requests, falling back to Selenium")
                return await self._get_category_products_selenium(url)
            
            # Extract product data
            products = []
            for card in product_cards:
                try:
                    # Get article ID
                    article = None
                    
                    # Method 1: data-nm-id attribute
                    if card.has_attr('data-nm-id'):
                        article = card['data-nm-id']
                    
                    # Method 2: href from link
                    if not article:
                        link = card.select_one("a[href*='/catalog/']")
                        if link and link.has_attr('href'):
                            href = link['href']
                            if '/catalog/' in href:
                                article = href.split('/catalog/')[1].split('/')[0]
                    
                    # Method 3: data-article attribute
                    if not article and card.has_attr('data-article'):
                        article = card['data-article']
                    
                    if not article:
                        continue
                    
                    # Get price
                    price = None
                    price_element = card.select_one("span[class*='price']") or card.select_one("div[class*='price']") or card.select_one("span[class*='cost']") or card.select_one("div[class*='cost']")
                    
                    if price_element:
                        price_text = price_element.text.replace("₽", "").replace(" ", "").strip()
                        try:
                            price = float(''.join(c for c in price_text if c.isdigit() or c == '.'))
                        except ValueError:
                            pass
                    
                    if not price:
                        continue
                    
                    # Get rating
                    rating = 0
                    rating_element = card.select_one("span[class*='rating']")
                    if rating_element:
                        if rating_element.has_attr('style') and 'width:' in rating_element['style']:
                            width = float(rating_element['style'].split('width:')[1].split('%')[0])
                            rating = width / 20
                        else:
                            rating_text = rating_element.text.strip()
                            if rating_text and rating_text.replace('.', '').isdigit():
                                try:
                                    rating = float(rating_text)
                                except ValueError:
                                    pass
                    
                    # Get reviews count
                    reviews = 0
                    reviews_element = card.select_one("span[class*='count']") or card.select_one("div[class*='count']") or card.select_one("span[class*='reviews']") or card.select_one("div[class*='reviews']")
                    
                    if reviews_element:
                        reviews_text = reviews_element.text.strip()
                        if reviews_text:
                            try:
                                reviews = int(''.join(filter(str.isdigit, reviews_text)))
                            except ValueError:
                                pass
                    
                    # Get sales count
                    sales = 0
                    sales_element = card.select_one("span[class*='sold']") or card.select_one("div[class*='sold']") or card.select_one("span[class*='sales']") or card.select_one("div[class*='sales']")
                    
                    if sales_element:
                        sales_text = sales_element.text.strip()
                        if sales_text:
                            try:
                                sales = int(''.join(filter(str.isdigit, sales_text)))
                            except ValueError:
                                pass
                    
                    products.append({
                        "article": article,
                        "price": price,
                        "rating": rating,
                        "reviews": reviews,
                        "sales": sales
                    })
                    
                except Exception as e:
                    logger.warning(f"Error processing card: {e}")
                    continue
            
            logger.info(f"Successfully processed {len(products)} products with requests")
            
            if not products:
                logger.warning("No products extracted with requests, falling back to Selenium")
                return await self._get_category_products_selenium(url)
            
            return products
            
        except Exception as e:
            logger.error(f"Error getting category products with requests: {e}")
            # Fall back to Selenium
            return await self._get_category_products_selenium(url)

    def _find_product_cards_with_js(self) -> List:
        """Find product cards using JavaScript"""
        try:
            # JavaScript для поиска карточек товаров
            js_script = """
            function findProductCards() {
                // Массив для хранения найденных карточек
                let cards = [];
                
                // Функция для проверки, является ли элемент карточкой товара
                function isProductCard(element) {
                    // Проверяем наличие атрибутов, характерных для карточек товаров
                    if (element.hasAttribute('data-card-type') && 
                        element.getAttribute('data-card-type').includes('product')) {
                        return true;
                    }
                    
                    // Проверяем наличие атрибута data-nm-id
                    if (element.hasAttribute('data-nm-id')) {
                        return true;
                    }
                    
                    // Проверяем наличие атрибута data-article
                    if (element.hasAttribute('data-article')) {
                        return true;
                    }
                    
                    // Проверяем классы
                    const classList = element.className.split(' ');
                    const productKeywords = ['product', 'card', 'goods', 'item', 'catalog'];
                    for (let className of classList) {
                        if (productKeywords.some(keyword => 
                            className.toLowerCase().includes(keyword.toLowerCase()))) {
                            return true;
                        }
                    }
                    
                    // Проверяем наличие ссылки на товар
                    const links = element.getElementsByTagName('a');
                    for (let link of links) {
                        if (link.href && link.href.includes('/catalog/')) {
                            return true;
                        }
                    }
                    
                    // Проверяем наличие цены
                    const priceElements = element.querySelectorAll('[class*="price"], [class*="cost"]');
                    if (priceElements.length > 0) {
                        return true;
                    }
                    
                    // Проверяем наличие рейтинга
                    const ratingElements = element.querySelectorAll('[class*="rating"], [class*="stars"]');
                    if (ratingElements.length > 0) {
                        return true;
                    }
                    
                    return false;
                }
                
                // Рекурсивный поиск карточек
                function searchForCards(element) {
                    // Проверяем текущий элемент
                    if (isProductCard(element)) {
                        cards.push(element);
                    }
                    
                    // Проверяем дочерние элементы
                    for (let child of element.children) {
                        searchForCards(child);
                    }
                }
                
                // Начинаем поиск с body
                searchForCards(document.body);
                
                // Фильтруем дубликаты
                const uniqueCards = [];
                const seen = new Set();
                
                for (let card of cards) {
                    const cardId = card.getAttribute('data-nm-id') || 
                                 card.getAttribute('data-article') || 
                                 card.innerHTML;
                    
                    if (!seen.has(cardId)) {
                        seen.add(cardId);
                        uniqueCards.push(card);
                    }
                }
                
                return uniqueCards;
            }
            
            return findProductCards();
            """
            
            # Выполняем JavaScript
            cards = self.driver.execute_script(js_script)
            
            if cards:
                logger.info(f"Найдено {len(cards)} карточек товаров с помощью JavaScript")
                return cards
            
            return []
            
        except Exception as e:
            logger.error(f"Ошибка при поиске карточек с помощью JavaScript: {str(e)}")
            return []

    def _find_product_cards_with_xpath(self) -> List:
        """Find product cards using XPath"""
        try:
            # XPath expressions for product cards
            xpath_expressions = [
                "//div[contains(@class, 'product-card')]",
                "//div[contains(@class, 'ProductCard')]",
                "//div[contains(@class, 'card')]",
                "//div[contains(@class, 'item')]",
                "//div[contains(@class, 'goods')]",
                "//div[@data-card-type='product']",
                "//div[contains(@data-card-type, 'product')]",
                "//div[.//a[contains(@href, '/catalog/')]]",
                "//div[contains(@class, 'catalog-page__product')]",
                "//div[contains(@class, 'catalog-page__card')]",
                "//div[contains(@class, 'catalog-page__item')]",
                "//div[contains(@class, 'catalog-page__goods')]",
                "//div[contains(@class, 'product-card__content')]",
                "//div[contains(@class, 'product-card__inner')]",
                "//div[contains(@class, 'product-card__outer')]",
                "//div[contains(@class, 'product-card__main')]",
                "//div[contains(@class, 'product-card__side')]",
                "//div[contains(@class, 'product-card__top')]",
                "//div[contains(@class, 'product-card__bottom')]",
                "//div[contains(@class, 'product-card__left')]",
                "//div[contains(@class, 'product-card__right')]",
                "//div[contains(@class, 'product-card__center')]",
                "//div[contains(@class, 'product-card__middle')]"
            ]
            
            cards = []
            for xpath in xpath_expressions:
                try:
                    elements = self.driver.find_elements(By.XPATH, xpath)
                    if elements:
                        logger.info(f"Found {len(elements)} cards with XPath: {xpath}")
                        cards.extend(elements)
                except Exception as e:
                    logger.warning(f"Error with XPath {xpath}: {str(e)}")
                    continue
            
            return cards
            
        except Exception as e:
            logger.error(f"Error finding cards with XPath: {str(e)}")
            return []

    def _find_product_cards_with_css(self) -> List:
        """Find product cards using CSS selectors"""
        try:
            # CSS selectors for product cards
            css_selectors = [
                "div.product-card",
                "div.ProductCard",
                "div.card",
                "div.item",
                "div.goods",
                "div[data-card-type='product']",
                "div[data-card-type*='product']",
                "div.catalog-page__product",
                "div.catalog-page__card",
                "div.catalog-page__item",
                "div.catalog-page__goods",
                "div.product-card__content",
                "div.product-card__inner",
                "div.product-card__outer",
                "div.product-card__main",
                "div.product-card__side",
                "div.product-card__top",
                "div.product-card__bottom",
                "div.product-card__left",
                "div.product-card__right",
                "div.product-card__center",
                "div.product-card__middle"
            ]
            
            cards = []
            for selector in css_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        logger.info(f"Found {len(elements)} cards with CSS: {selector}")
                        cards.extend(elements)
                except Exception as e:
                    logger.warning(f"Error with CSS selector {selector}: {str(e)}")
                    continue
            
            return cards
            
        except Exception as e:
            logger.error(f"Error finding cards with CSS: {str(e)}")
            return []

    def _check_and_switch_to_frame(self) -> bool:
        """Проверяет наличие iframe и переключается на него при необходимости"""
        try:
            # Проверяем наличие iframe
            iframes = self.driver.find_elements(By.TAG_NAME, "iframe")
            if iframes:
                logger.info(f"Найдено {len(iframes)} iframe")
                for iframe in iframes:
                    try:
                        # Пробуем переключиться на iframe
                        self.driver.switch_to.frame(iframe)
                        logger.info("Успешно переключились на iframe")
                        return True
                    except Exception as e:
                        logger.warning(f"Не удалось переключиться на iframe: {str(e)}")
                        continue
            return False
        except Exception as e:
            logger.error(f"Ошибка при проверке iframe: {str(e)}")
            return False

    def _check_for_blocking(self) -> bool:
        """Check if the page is blocked or showing captcha"""
        try:
            # Get page source
            page_source = self.driver.page_source.lower()
            
            # Check for common blocking indicators
            blocking_indicators = [
                "captcha",
                "access denied",
                "доступ запрещен",
                "проверка безопасности",
                "security check",
                "please verify you are a human",
                "пожалуйста, подтвердите, что вы человек"
            ]
            
            # Check if any blocking indicator is present
            for indicator in blocking_indicators:
                if indicator in page_source:
                    logger.warning(f"Blocking indicator found: {indicator}")
                    return True
                
            # Check if we're still on a valid Wildberries URL
            current_url = self.driver.current_url
            if "wildberries.ru" not in current_url:
                logger.warning(f"Redirected to non-Wildberries URL: {current_url}")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking for blocking: {str(e)}")
            return True

    def _handle_captcha(self) -> bool:
        """Handle captcha by taking screenshot and getting user input"""
        try:
            # Take screenshot of the captcha
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            screenshot_path = f"captcha_{timestamp}.png"
            
            # Try to find captcha input field
            input_selectors = [
                "input[name*='captcha']",
                "input[id*='captcha']",
                "input[class*='captcha']",
                "input[type='text']",
                "input[class*='input']",
                "input[class*='verification']"
            ]
            
            captcha_input = None
            for selector in input_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        captcha_input = elements[0]
                        break
                except Exception:
                    continue
            
            if not captcha_input:
                logger.error("Could not find captcha input field")
                return False
            
            # Try to find submit button
            submit_selectors = [
                "button[type='submit']",
                "button[class*='submit']",
                "button[class*='confirm']",
                "button[class*='verify']",
                "input[type='submit']"
            ]
            
            submit_button = None
            for selector in submit_selectors:
                try:
                    elements = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    if elements:
                        submit_button = elements[0]
                        break
                except Exception:
                    continue
            
            if not submit_button:
                logger.error("Could not find submit button")
                return False
            
            # Take screenshot of the entire page
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Captcha screenshot saved to {screenshot_path}")
            
            # Here you would send the screenshot to the user through your bot
            # and wait for their response with the captcha solution
            # This part should be implemented in your bot's message handler
            
            # For now, we'll just prepare the method to receive the solution
            def solve_captcha(solution: str) -> bool:
                try:
                    # Input the solution
                    captcha_input.clear()
                    captcha_input.send_keys(solution)
                    time.sleep(random.uniform(0.5, 1.0))
                    
                    # Click submit with random delay
                    time.sleep(random.uniform(0.3, 0.7))
                    submit_button.click()
                    
                    # Wait for page to update
                    time.sleep(random.uniform(2, 3))
                    
                    # Check if captcha was solved successfully
                    if not any(indicator in self.driver.page_source.lower() 
                             for indicator in ["captcha", "введите код", "подтвердите"]):
                        logger.info("Captcha solved successfully")
                        return True
                    
                    logger.warning("Captcha solution was incorrect")
                    return False
                    
                except Exception as e:
                    logger.error(f"Error solving captcha: {str(e)}")
                    return False
            
            # Store the solve_captcha function so it can be called from your bot
            self.solve_captcha = solve_captcha
            
            # Return False for now since we need the bot to implement the user interaction
            return False
            
        except Exception as e:
            logger.error(f"Error handling captcha: {str(e)}")
            return False

    async def _get_category_products_selenium(self, url: str) -> List[Dict]:
        """Get category products using Selenium"""
        try:
            # Initialize driver if needed
            if not self.driver:
                if not self.initialize_driver():
                    return []
            
            # Load page with retry mechanism
            for attempt in range(3):
                try:
                    self.driver.get(url)
                    time.sleep(random.uniform(2, 4))
                    break
                except Exception as e:
                    if attempt == 2:
                        logger.error(f"Failed to load page after 3 attempts: {str(e)}")
                        return []
                    time.sleep(random.uniform(5, 10))
            
            # Check for blocking
            if self._check_for_blocking():
                logger.error("Page blocked or requires captcha")
                return []
            
            # Wait for page to load
            time.sleep(random.uniform(3, 5))
            
            # Scroll page to load all products
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 5
            
            while scroll_attempts < max_scroll_attempts:
                # Random scroll amount
                scroll_amount = random.randint(300, 700)
                self.driver.execute_script(f"window.scrollBy(0, {scroll_amount});")
                time.sleep(random.uniform(1, 2))
                
                # Check if new content was loaded
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                if new_height == last_height:
                    scroll_attempts += 1
                else:
                    scroll_attempts = 0
                    last_height = new_height
                
                # Random pause between scrolls
                if random.random() < 0.3:
                    time.sleep(random.uniform(2, 4))
            
            # Try to find product cards using different methods
            cards = []
            
            # 1. Try JavaScript method
            try:
                js_cards = self._find_product_cards_with_js()
                if js_cards:
                    logger.info(f"Found {len(js_cards)} cards with JavaScript")
                    cards.extend(js_cards)
            except Exception as e:
                logger.warning(f"JavaScript method failed: {str(e)}")
            
            # 2. Try XPath method
            try:
                xpath_cards = self._find_product_cards_with_xpath()
                if xpath_cards:
                    logger.info(f"Found {len(xpath_cards)} cards with XPath")
                    cards.extend(xpath_cards)
            except Exception as e:
                logger.warning(f"XPath method failed: {str(e)}")
            
            # 3. Try CSS method
            try:
                css_cards = self._find_product_cards_with_css()
                if css_cards:
                    logger.info(f"Found {len(css_cards)} cards with CSS")
                    cards.extend(css_cards)
            except Exception as e:
                logger.warning(f"CSS method failed: {str(e)}")
            
            if not cards:
                logger.error("No product cards found")
                return []
            
            # Process found cards
            products = []
            for card in cards:
                try:
                    # Get product data
                    product_data = self._extract_product_data(card)
                    if product_data:
                        products.append(product_data)
                except StaleElementReferenceException:
                    logger.warning("Element became stale, skipping")
                    continue
                except Exception as e:
                    logger.error(f"Error processing product card: {str(e)}")
                    continue
            
            return products
            
        except Exception as e:
            logger.error(f"Error getting category products: {str(e)}")
            return []

    async def analyze_category(self, url: str) -> dict:
        """Analyze category"""
        try:
            # Get category products
            products = await self._get_category_products(url)
            
            if not products:
                return {
                    'total_products': 0,
                    'price_stats': {'min': 0, 'max': 0, 'avg': 0, 'median': 0},
                    'sales_stats': {'total': 0, 'avg_per_day': 0},
                    'rating_stats': {'avg': 0, 'avg_reviews': 0},
                    'trends': {'price': 0, 'sales': 0, 'competition': 0},
                    'opportunities': "Нет данных для анализа"
                }
            
            # Calculate statistics
            prices = [p['price'] for p in products]
            ratings = [p['rating'] for p in products if p['rating'] > 0]
            reviews = [p['reviews'] for p in products if p['reviews'] > 0]
            sales = [p['sales'] for p in products if p['sales'] > 0]
            
            return {
                'total_products': len(products),
                'price_stats': {
                    'min': min(prices),
                    'max': max(prices),
                    'avg': sum(prices) / len(prices),
                    'median': sorted(prices)[len(prices) // 2]
                },
                'sales_stats': {
                    'total': sum(sales),
                    'avg_per_day': sum(sales) / 30 if sales else 0
                },
                'rating_stats': {
                    'avg': sum(ratings) / len(ratings) if ratings else 0,
                    'avg_reviews': sum(reviews) / len(reviews) if reviews else 0
                },
                'trends': {
                    'price': ((max(prices) - min(prices)) / min(prices) * 100) if min(prices) > 0 else 0,
                    'sales': ((max(sales) - min(sales)) / min(sales) * 100) if min(sales) > 0 else 0,
                    'competition': len(products) / 100 * 50  # Simple competition metric
                },
                'opportunities': self._find_opportunities(products)
            }
            
        except Exception as e:
            logger.error(f"Error analyzing category: {e}")
            return {
                'total_products': 0,
                'price_stats': {'min': 0, 'max': 0, 'avg': 0, 'median': 0},
                'sales_stats': {'total': 0, 'avg_per_day': 0},
                'rating_stats': {'avg': 0, 'avg_reviews': 0},
                'trends': {'price': 0, 'sales': 0, 'competition': 0},
                'opportunities': "Произошла ошибка при анализе категории"
            }

    def _find_opportunities(self, products: List[Dict]) -> str:
        """Find market opportunities"""
        if not products:
            return "Нет данных для анализа"
        
        opportunities = []
        
        # Analyze prices
        prices = [p['price'] for p in products]
        avg_price = sum(prices) / len(prices)
        
        if min(prices) < avg_price * 0.7:
            opportunities.append("Есть возможность выхода в нижний ценовой сегмент")
        
        if max(prices) > avg_price * 1.3:
            opportunities.append("Есть возможность выхода в премиальный сегмент")
        
        # Analyze ratings
        ratings = [p['rating'] for p in products if p['rating'] > 0]
        if ratings and sum(ratings) / len(ratings) < 4.5:
            opportunities.append("Есть возможность улучшения качества для повышения рейтинга")
        
        # Analyze sales
        sales = [p['sales'] for p in products if p['sales'] > 0]
        if sales and sum(sales) / len(sales) < max(sales) * 0.3:
            opportunities.append("Есть возможность увеличения продаж через маркетинг")
        
        return "\n".join(opportunities) if opportunities else "Нет явных возможностей для улучшения"

    def _extract_product_data(self, card) -> Optional[Dict]:
        """Extract product data from a card element"""
        try:
            # Get article ID
            article_id = self._extract_article_id(card)
            if not article_id:
                logger.warning("Could not extract article ID")
                return None
            
            # Get price
            price = self._extract_price(card)
            if not price:
                logger.warning(f"Could not extract price for article {article_id}")
                return None
            
            # Get rating
            rating = self._extract_rating(card)
            
            # Get reviews count
            reviews = self._extract_reviews(card)
            
            # Get sales count
            sales = self._extract_sales(card)
            
            return {
                "article_id": article_id,
                "price": price,
                "rating": rating,
                "reviews": reviews,
                "sales": sales
            }
            
        except Exception as e:
            logger.error(f"Error extracting product data: {str(e)}")
            return None
            
    def _extract_article_id(self, card) -> Optional[str]:
        """Extract article ID from a card element"""
        try:
            # Try multiple methods to get the article ID
            
            # Method 1: data-nm-id attribute
            article_id = card.get_attribute("data-nm-id")
            if article_id:
                logger.info(f"Found article ID from data-nm-id: {article_id}")
                return article_id
                
            # Method 2: data-article attribute
            article_id = card.get_attribute("data-article")
            if article_id:
                logger.info(f"Found article ID from data-article: {article_id}")
                return article_id
                
            # Method 3: href from link
            try:
                link = card.find_element(By.CSS_SELECTOR, "a[href*='/catalog/']")
                href = link.get_attribute("href")
                if href and "/catalog/" in href:
                    article_id = href.split("/catalog/")[1].split("/")[0]
                    logger.info(f"Found article ID from href: {article_id}")
                    return article_id
            except Exception:
                pass
                
            # Method 4: Look for any link with article ID pattern
            try:
                links = card.find_elements(By.TAG_NAME, "a")
                for link in links:
                    href = link.get_attribute("href")
                    if href and "/catalog/" in href:
                        article_id = href.split("/catalog/")[1].split("/")[0]
                        logger.info(f"Found article ID from link: {article_id}")
                        return article_id
            except Exception:
                pass
                
            # Method 5: Look for any element with article ID pattern
            try:
                elements = card.find_elements(By.CSS_SELECTOR, "[id*='article'], [id*='product']")
                for element in elements:
                    element_id = element.get_attribute("id")
                    if element_id and any(x in element_id.lower() for x in ["article", "product", "nm"]):
                        logger.info(f"Found potential article ID from element ID: {element_id}")
                        return element_id
            except Exception:
                pass
                
            logger.warning("Could not find article ID using any method")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting article ID: {str(e)}")
            return None
            
    def _extract_price(self, card) -> Optional[float]:
        """Extract price from a card element"""
        try:
            # Try multiple selectors for price
            price_selectors = [
                "span[class*='price']",
                "div[class*='price']",
                "span[class*='cost']",
                "div[class*='cost']",
                "span[class*='amount']",
                "div[class*='amount']",
                "span[class*='sum']",
                "div[class*='sum']",
                "span[class*='value']",
                "div[class*='value']"
            ]
            
            for selector in price_selectors:
                try:
                    price_element = card.find_element(By.CSS_SELECTOR, selector)
                    price_text = price_element.text.strip()
                    
                    # Clean price text
                    price_text = price_text.replace("₽", "").replace(" ", "").strip()
                    price_text = ''.join(c for c in price_text if c.isdigit() or c == '.')
                    
                    if price_text:
                        try:
                            price = float(price_text)
                            if price > 0:  # Validate price
                                logger.info(f"Found price: {price}")
                                return price
                        except ValueError:
                            continue
                except Exception:
                    continue
            
            # If no price found with selectors, try to find any text that looks like a price
            try:
                # Look for text with currency symbol
                elements = card.find_elements(By.XPATH, ".//*[contains(text(), '₽')]")
                for element in elements:
                    price_text = element.text.strip()
                    price_text = price_text.replace("₽", "").replace(" ", "").strip()
                    price_text = ''.join(c for c in price_text if c.isdigit() or c == '.')
                    
                    if price_text:
                        try:
                            price = float(price_text)
                            if price > 0:  # Validate price
                                logger.info(f"Found price from text: {price}")
                                return price
                        except ValueError:
                            continue
            except Exception:
                pass
            
            logger.warning("Could not find price using any method")
            return None
            
        except Exception as e:
            logger.error(f"Error extracting price: {str(e)}")
            return None
            
    def _extract_rating(self, card) -> float:
        """Extract rating from a card element"""
        try:
            # Try multiple selectors for rating
            rating_selectors = [
                "span[class*='rating']",
                "div[class*='rating']",
                "span[class*='stars']",
                "div[class*='stars']",
                "span[class*='score']",
                "div[class*='score']"
            ]
            
            for selector in rating_selectors:
                try:
                    rating_element = card.find_element(By.CSS_SELECTOR, selector)
                    
                    # Method 1: Check for style attribute with width percentage
                    style = rating_element.get_attribute("style")
                    if style and "width:" in style:
                        try:
                            width_percent = float(style.split("width:")[1].split("%")[0].strip())
                            rating = width_percent / 20  # Assuming 5-star rating
                            logger.info(f"Found rating from style: {rating}")
                            return rating
                        except (ValueError, IndexError):
                            pass
                    
                    # Method 2: Check for text content
                    rating_text = rating_element.text.strip()
                    if rating_text:
                        try:
                            # Try to extract number from text
                            rating_text = ''.join(c for c in rating_text if c.isdigit() or c == '.')
                            if rating_text:
                                rating = float(rating_text)
                                if 0 <= rating <= 5:  # Validate rating
                                    logger.info(f"Found rating from text: {rating}")
                                    return rating
                        except ValueError:
                            pass
                except Exception:
                    continue
            
            # Default rating if none found
            return 0.0
            
        except Exception as e:
            logger.error(f"Error extracting rating: {str(e)}")
            return 0.0
            
    def _extract_reviews(self, card) -> int:
        """Extract reviews count from a card element"""
        try:
            # Try multiple selectors for reviews
            review_selectors = [
                "span[class*='review']",
                "div[class*='review']",
                "span[class*='comment']",
                "div[class*='comment']",
                "span[class*='count']",
                "div[class*='count']"
            ]
            
            for selector in review_selectors:
                try:
                    review_element = card.find_element(By.CSS_SELECTOR, selector)
                    review_text = review_element.text.strip()
                    
                    # Clean review text
                    review_text = ''.join(c for c in review_text if c.isdigit())
                    
                    if review_text:
                        try:
                            reviews = int(review_text)
                            if reviews >= 0:  # Validate reviews count
                                logger.info(f"Found reviews count: {reviews}")
                                return reviews
                        except ValueError:
                            continue
                except Exception:
                    continue
            
            # Default reviews count if none found
            return 0
            
        except Exception as e:
            logger.error(f"Error extracting reviews count: {str(e)}")
            return 0
            
    def _extract_sales(self, card) -> int:
        """Extract sales count from a card element"""
        try:
            # Try multiple selectors for sales
            sales_selectors = [
                "span[class*='sold']",
                "div[class*='sold']",
                "span[class*='sales']",
                "div[class*='sales']",
                "span[class*='purchased']",
                "div[class*='purchased']",
                "span[class*='bought']",
                "div[class*='bought']"
            ]
            
            for selector in sales_selectors:
                try:
                    sales_element = card.find_element(By.CSS_SELECTOR, selector)
                    sales_text = sales_element.text.strip()
                    
                    # Clean sales text
                    sales_text = ''.join(c for c in sales_text if c.isdigit())
                    
                    if sales_text:
                        try:
                            sales = int(sales_text)
                            if sales >= 0:  # Validate sales count
                                logger.info(f"Found sales count: {sales}")
                                return sales
                        except ValueError:
                            continue
                except Exception:
                    continue
            
            # Default sales count if none found
            return 0
            
        except Exception as e:
            logger.error(f"Error extracting sales count: {str(e)}")
            return 0

    def _save_debug_info(self, error_type: str):
        """Save debug information for troubleshooting"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            
            # Save screenshot
            screenshot_path = f"debug_screenshot_{error_type}_{timestamp}.png"
            self.driver.save_screenshot(screenshot_path)
            logger.info(f"Debug screenshot saved to {screenshot_path}")
            
            # Save page source
            source_path = f"debug_source_{error_type}_{timestamp}.html"
            with open(source_path, "w", encoding="utf-8") as f:
                f.write(self.driver.page_source)
            logger.info(f"Page source saved to {source_path}")
            
            # Save cookies
            cookies_path = f"debug_cookies_{error_type}_{timestamp}.json"
            with open(cookies_path, "w", encoding="utf-8") as f:
                json.dump(self.driver.get_cookies(), f, indent=2)
            logger.info(f"Cookies saved to {cookies_path}")
            
        except Exception as e:
            logger.error(f"Error saving debug info: {str(e)}") 