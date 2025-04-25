import sqlite3
from datetime import datetime
from typing import List, Dict, Optional
import json

class NicheDatabase:
    """Database class for storing niche analysis data"""
    
    def __init__(self, db_path: str = "niche_analysis.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        # Products table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS products (
                article_id TEXT PRIMARY KEY,
                title TEXT,
                price REAL,
                sales_volume INTEGER,
                reviews_count INTEGER,
                rating REAL,
                category TEXT,
                brand TEXT,
                supplier TEXT,
                timestamp DATETIME
            )
        ''')
        
        # Category analysis table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS category_analysis (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_url TEXT,
                timestamp DATETIME,
                total_products INTEGER,
                avg_price REAL,
                price_min REAL,
                price_max REAL,
                avg_rating REAL,
                avg_reviews REAL,
                analysis_data TEXT
            )
        ''')
        
        # Opportunities table
        cur.execute('''
            CREATE TABLE IF NOT EXISTS opportunities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category_url TEXT,
                timestamp DATETIME,
                opportunity_type TEXT,
                description TEXT,
                confidence REAL
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_products(self, products: List[Dict]):
        """Save product metrics to database"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        for product in products:
            cur.execute('''
                INSERT OR REPLACE INTO products 
                (article_id, title, price, sales_volume, reviews_count, rating, 
                category, brand, supplier, timestamp)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product["article_id"],
                product["title"],
                product["price"],
                product["sales_volume"],
                product["reviews_count"],
                product["rating"],
                product["category"],
                product["brand"],
                product["supplier"],
                product["timestamp"]
            ))
        
        conn.commit()
        conn.close()
    
    def save_category_analysis(self, category_url: str, analysis: Dict):
        """Save category analysis to database"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute('''
            INSERT INTO category_analysis 
            (category_url, timestamp, total_products, avg_price, price_min, price_max,
            avg_rating, avg_reviews, analysis_data)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            category_url,
            datetime.now(),
            analysis["total_products"],
            analysis["avg_price"],
            analysis["price_range"]["min"],
            analysis["price_range"]["max"],
            analysis["avg_rating"],
            analysis["avg_reviews"],
            json.dumps(analysis)
        ))
        
        conn.commit()
        conn.close()
    
    def save_opportunities(self, category_url: str, opportunities: List[Dict]):
        """Save niche opportunities to database"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        for opp in opportunities:
            cur.execute('''
                INSERT INTO opportunities 
                (category_url, timestamp, opportunity_type, description, confidence)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                category_url,
                datetime.now(),
                opp["type"],
                opp["description"],
                opp["confidence"]
            ))
        
        conn.commit()
        conn.close()
    
    def get_latest_analysis(self, category_url: str) -> Optional[Dict]:
        """Get the latest analysis for a category"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute('''
            SELECT analysis_data FROM category_analysis 
            WHERE category_url = ? 
            ORDER BY timestamp DESC LIMIT 1
        ''', (category_url,))
        
        row = cur.fetchone()
        conn.close()
        
        if row:
            return json.loads(row[0])
        return None
    
    def get_historical_data(self, category_url: str, days: int = 30) -> List[Dict]:
        """Get historical analysis data for a category"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute('''
            SELECT analysis_data, timestamp 
            FROM category_analysis 
            WHERE category_url = ? 
            AND timestamp >= datetime('now', ?)
            ORDER BY timestamp DESC
        ''', (category_url, f'-{days} days'))
        
        rows = cur.fetchall()
        conn.close()
        
        return [{"data": json.loads(row[0]), "timestamp": row[1]} for row in rows]
    
    def get_top_opportunities(self, category_url: str, limit: int = 5) -> List[Dict]:
        """Get top opportunities for a category"""
        conn = sqlite3.connect(self.db_path)
        cur = conn.cursor()
        
        cur.execute('''
            SELECT opportunity_type, description, confidence, timestamp 
            FROM opportunities 
            WHERE category_url = ? 
            ORDER BY confidence DESC, timestamp DESC 
            LIMIT ?
        ''', (category_url, limit))
        
        rows = cur.fetchall()
        conn.close()
        
        return [{
            "type": row[0],
            "description": row[1],
            "confidence": row[2],
            "timestamp": row[3]
        } for row in rows] 