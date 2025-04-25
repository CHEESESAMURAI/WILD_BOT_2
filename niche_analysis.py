import asyncio
import json
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
import aiohttp
from bs4 import BeautifulSoup
import pandas as pd
from dataclasses import dataclass
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

@dataclass
class ProductMetrics:
    """Data class to store product performance metrics"""
    article_id: str
    title: str
    price: float
    sales_volume: int
    reviews_count: int
    rating: float
    category: str
    brand: str
    supplier: str
    timestamp: datetime

class WildberriesAPI:
    """Class for interacting with Wildberries API"""
    
    def __init__(self):
        self.base_url = "https://card.wb.ru/cards/v1"
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
        }
    
    async def get_product_details(self, article_id: str) -> Optional[Dict]:
        """Fetch product details from Wildberries API"""
        async with aiohttp.ClientSession(headers=self.headers) as session:
            url = f"{self.base_url}/detail?appType=1&curr=rub&dest=-1257786&spp=0&nm={article_id}"
            try:
                async with session.get(url) as response:
                    if response.status == 200:
                        return await response.json()
            except Exception as e:
                print(f"Error fetching product details: {e}")
        return None

class NicheAnalyzer:
    """Class for analyzing market niches and competitors"""
    
    def __init__(self):
        self.api = WildberriesAPI()
        self._setup_selenium()
    
    def _setup_selenium(self):
        """Setup Selenium WebDriver for scraping"""
        options = Options()
        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-gpu")
        service = Service(ChromeDriverManager().install())
        self.driver = webdriver.Chrome(service=service, options=options)
    
    async def analyze_category(self, category_url: str) -> List[ProductMetrics]:
        """Analyze all products in a category"""
        products = []
        try:
            self.driver.get(category_url)
            # Wait for product cards to load
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.CLASS_NAME, "product-card"))
            )
            
            # Extract product cards
            product_cards = self.driver.find_elements(By.CLASS_NAME, "product-card")
            
            for card in product_cards:
                try:
                    article_id = card.get_attribute("data-nm-id")
                    if article_id:
                        metrics = await self._extract_product_metrics(article_id)
                        if metrics:
                            products.append(metrics)
                except Exception as e:
                    print(f"Error processing product card: {e}")
                    continue
                    
        except Exception as e:
            print(f"Error analyzing category: {e}")
        finally:
            self.driver.quit()
        
        return products
    
    async def _extract_product_metrics(self, article_id: str) -> Optional[ProductMetrics]:
        """Extract metrics for a single product"""
        try:
            # Get API data
            api_data = await self.api.get_product_details(article_id)
            if not api_data or "data" not in api_data:
                return None
                
            product = api_data["data"]["products"][0]
            
            # Extract metrics
            return ProductMetrics(
                article_id=article_id,
                title=product.get("name", ""),
                price=float(product.get("priceU", 0)) / 100,  # Convert from kopecks
                sales_volume=product.get("sale", 0),
                reviews_count=product.get("reviewRating", 0),
                rating=float(product.get("rating", 0)),
                category=product.get("category", ""),
                brand=product.get("brand", ""),
                supplier=product.get("supplier", ""),
                timestamp=datetime.now()
            )
        except Exception as e:
            print(f"Error extracting metrics for product {article_id}: {e}")
            return None
    
    def analyze_competitors(self, products: List[ProductMetrics]) -> Dict:
        """Analyze competitors in the niche"""
        if not products:
            return {}
            
        df = pd.DataFrame([vars(p) for p in products])
        
        analysis = {
            "total_products": len(products),
            "avg_price": df["price"].mean(),
            "price_range": {
                "min": df["price"].min(),
                "max": df["price"].max()
            },
            "top_brands": df.groupby("brand")["sales_volume"].sum().nlargest(5).to_dict(),
            "top_suppliers": df.groupby("supplier")["sales_volume"].sum().nlargest(5).to_dict(),
            "avg_rating": df["rating"].mean(),
            "avg_reviews": df["reviews_count"].mean(),
            "sales_distribution": {
                "low": len(df[df["sales_volume"] < 10]),
                "medium": len(df[(df["sales_volume"] >= 10) & (df["sales_volume"] < 100)]),
                "high": len(df[df["sales_volume"] >= 100])
            }
        }
        
        return analysis
    
    def identify_niche_opportunities(self, analysis: Dict) -> List[Dict]:
        """Identify potential niche opportunities based on analysis"""
        opportunities = []
        
        # Example opportunity detection logic
        if analysis["avg_rating"] > 4.5 and analysis["avg_reviews"] < 100:
            opportunities.append({
                "type": "high_rating_low_reviews",
                "description": "High customer satisfaction but low review count - potential for growth",
                "confidence": 0.8
            })
            
        if analysis["sales_distribution"]["low"] > analysis["sales_distribution"]["high"] * 2:
            opportunities.append({
                "type": "low_competition",
                "description": "Low competition in the niche - potential for market entry",
                "confidence": 0.7
            })
            
        return opportunities

class RealTimeMonitor:
    """Class for real-time monitoring of niche metrics"""
    
    def __init__(self, niche_analyzer: NicheAnalyzer):
        self.niche_analyzer = niche_analyzer
        self.monitoring_interval = 3600  # 1 hour in seconds
    
    async def start_monitoring(self, category_url: str, callback):
        """Start real-time monitoring of a category"""
        while True:
            try:
                # Get current metrics
                products = await self.niche_analyzer.analyze_category(category_url)
                analysis = self.niche_analyzer.analyze_competitors(products)
                opportunities = self.niche_analyzer.identify_niche_opportunities(analysis)
                
                # Call callback with updated data
                await callback({
                    "timestamp": datetime.now(),
                    "products": products,
                    "analysis": analysis,
                    "opportunities": opportunities
                })
                
                # Wait for next update
                await asyncio.sleep(self.monitoring_interval)
                
            except Exception as e:
                print(f"Error in monitoring: {e}")
                await asyncio.sleep(60)  # Wait 1 minute before retrying 