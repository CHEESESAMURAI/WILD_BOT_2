import asyncio
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException, StaleElementReferenceException
from webdriver_manager.chrome import ChromeDriverManager
from typing import Dict, List, Optional
import time
import random

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CategoryAnalyzer:
    def __init__(self):
        self.driver = None
        self.wait = None
        self.page_load_timeout = 30
        self.element_timeout = 20
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

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
            
            # Add user agent
            chrome_options.add_argument(f'user-agent={self.headers["User-Agent"]}')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # Set timeouts
            self.driver.set_page_load_timeout(self.page_load_timeout)
            self.wait = WebDriverWait(self.driver, self.element_timeout)
            
            # Test the driver
            self.driver.get("https://www.wildberries.ru")
            await asyncio.sleep(3)  # Wait for initial load
            
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
            await self.initialize_driver()

    async def _get_category_products(self, url: str) -> List[Dict]:
        """Get list of products from category"""
        try:
            await self.ensure_driver()
            
            # Clean and encode URL properly
            url = url.replace('ё', 'e').strip()
            logger.info(f"Opening URL: {url}")
            
            # Add random delay to avoid detection
            await asyncio.sleep(random.uniform(1, 3))
            
            self.driver.get(url)
            
            # Wait for page load
            try:
                self.wait.until(lambda driver: driver.execute_script('return document.readyState') == 'complete')
                logger.info("Page load complete")
            except TimeoutException:
                logger.warning("Initial page load timeout, but continuing...")
            
            # Give extra time for dynamic content
            await asyncio.sleep(5)
            
            # Scroll page with random delays
            last_height = self.driver.execute_script("return document.body.scrollHeight")
            scroll_attempts = 0
            max_scroll_attempts = 3
            
            while scroll_attempts < max_scroll_attempts:
                # Scroll with random position
                scroll_position = random.randint(0, 100)
                self.driver.execute_script(f"window.scrollTo(0, document.body.scrollHeight * {scroll_position/100});")
                await asyncio.sleep(random.uniform(1, 2))
                
                # Scroll to bottom
                self.driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
                await asyncio.sleep(random.uniform(2, 3))
                
                new_height = self.driver.execute_script("return document.body.scrollHeight")
                logger.info(f"Scroll attempt {scroll_attempts + 1}: height changed from {last_height} to {new_height}")
                if new_height == last_height:
                    break
                last_height = new_height
                scroll_attempts += 1
            
            # Find product cards with multiple selectors and retries
            logger.info("Looking for product cards...")
            product_cards = []
            selectors = [
                "div[class*='product-card']",
                "div[class*='card']",
                "div[class*='product']",
                "div[class*='item']",
                "div[class*='goods']"
            ]
            
            for selector in selectors:
                try:
                    logger.info(f"Trying selector: {selector}")
                    # Wait for any product card to be present with shorter timeout
                    self.wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    
                    # Get all product cards
                    product_cards = self.driver.find_elements(By.CSS_SELECTOR, selector)
                    logger.info(f"Found {len(product_cards)} product cards with selector: {selector}")
                    
                    if product_cards:
                        break
                except Exception as e:
                    logger.warning(f"Selector {selector} failed: {e}")
                    continue
            
            if not product_cards:
                logger.error("No product cards found with any selector")
                # Take screenshot for debugging
                try:
                    self.driver.save_screenshot("debug_screenshot.png")
                    logger.info("Debug screenshot saved")
                except Exception as e:
                    logger.error(f"Failed to save debug screenshot: {e}")
                
                # Try to get page source for debugging
                try:
                    with open("debug_page.html", "w", encoding="utf-8") as f:
                        f.write(self.driver.page_source)
                    logger.info("Debug page source saved")
                except Exception as e:
                    logger.error(f"Failed to save debug page source: {e}")
                
                return []
            
            products = []
            for index, card in enumerate(product_cards):
                try:
                    logger.info(f"Processing card {index + 1}")
                    
                    # Add random delay between processing cards
                    await asyncio.sleep(random.uniform(0.1, 0.3))
                    
                    # Get article ID with multiple methods
                    article = None
                    try:
                        # Method 1: data-nm-id attribute
                        article = card.get_attribute('data-nm-id')
                        
                        # Method 2: href from link
                        if not article:
                            try:
                                link_element = card.find_element(By.CSS_SELECTOR, "a[href*='/catalog/']")
                                href = link_element.get_attribute('href')
                                if href and '/catalog/' in href:
                                    article = href.split('/catalog/')[1].split('/')[0]
                            except NoSuchElementException:
                                pass
                        
                        # Method 3: data-article attribute
                        if not article:
                            article = card.get_attribute('data-article')
                            
                    except Exception as e:
                        logger.warning(f"Error getting article ID for card {index + 1}: {e}")
                        continue
                    
                    if not article:
                        logger.warning(f"No article found for card {index + 1}")
                        continue
                    
                    logger.info(f"Found article ID: {article}")
                    
                    # Get price with multiple selectors
                    price = None
                    price_selectors = [
                        "span[class*='price']",
                        "div[class*='price']",
                        "span[class*='cost']",
                        "div[class*='cost']"
                    ]
                    
                    for selector in price_selectors:
                        try:
                            price_element = card.find_element(By.CSS_SELECTOR, selector)
                            price_text = price_element.text.replace("₽", "").replace(" ", "").strip()
                            price = float(''.join(c for c in price_text if c.isdigit() or c == '.'))
                            logger.info(f"Found price: {price}")
                            break
                        except Exception:
                            continue
                    
                    if not price:
                        logger.warning(f"No price found for card {index + 1}")
                        continue
                    
                    # Get rating with multiple methods
                    rating = 0
                    try:
                        # Method 1: rating element with style
                        rating_element = card.find_element(By.CSS_SELECTOR, "span[class*='rating']")
                        rating_style = rating_element.get_attribute('style')
                        if rating_style and 'width:' in rating_style:
                            width = float(rating_style.split('width:')[1].split('%')[0])
                            rating = width / 20
                            logger.info(f"Found rating: {rating}")
                        
                        # Method 2: rating text
                        if not rating:
                            rating_text = rating_element.text.strip()
                            if rating_text and rating_text.replace('.', '').isdigit():
                                rating = float(rating_text)
                                logger.info(f"Found rating from text: {rating}")
                    except Exception as e:
                        logger.warning(f"Error getting rating for card {index + 1}: {e}")
                    
                    # Get reviews count with multiple selectors
                    reviews = 0
                    review_selectors = [
                        "span[class*='count']",
                        "div[class*='count']",
                        "span[class*='reviews']",
                        "div[class*='reviews']"
                    ]
                    
                    for selector in review_selectors:
                        try:
                            reviews_element = card.find_element(By.CSS_SELECTOR, selector)
                            reviews_text = reviews_element.text.strip()
                            if reviews_text:
                                reviews = int(''.join(filter(str.isdigit, reviews_text)))
                                logger.info(f"Found reviews: {reviews}")
                                break
                        except Exception:
                            continue
                    
                    # Get sales count with multiple selectors
                    sales = 0
                    sales_selectors = [
                        "span[class*='sold']",
                        "div[class*='sold']",
                        "span[class*='sales']",
                        "div[class*='sales']"
                    ]
                    
                    for selector in sales_selectors:
                        try:
                            sales_element = card.find_element(By.CSS_SELECTOR, selector)
                            sales_text = sales_element.text.strip()
                            if sales_text:
                                sales = int(''.join(filter(str.isdigit, sales_text)))
                                logger.info(f"Found sales: {sales}")
                                break
                        except Exception:
                            continue
                    
                    products.append({
                        "article": article,
                        "price": price,
                        "rating": rating,
                        "reviews": reviews,
                        "sales": sales
                    })
                    
                except StaleElementReferenceException:
                    logger.warning(f"Stale element for card {index + 1}, skipping")
                    continue
                except Exception as e:
                    logger.error(f"Error processing card {index + 1}: {e}")
                    continue
            
            logger.info(f"Successfully processed {len(products)} products")
            return products
            
        except Exception as e:
            logger.error(f"Error getting category products: {e}")
            # Take screenshot for debugging
            try:
                self.driver.save_screenshot("error_screenshot.png")
                logger.info("Error screenshot saved")
            except Exception as e:
                logger.error(f"Failed to save error screenshot: {e}")
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