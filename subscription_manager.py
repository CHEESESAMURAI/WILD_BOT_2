import sqlite3
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class SubscriptionManager:
    def __init__(self, db_path: str = "subscriptions.db"):
        self.db_path = db_path
        logger.info(f"Initializing SubscriptionManager with database: {db_path}")
        self._init_db()
        self.subscriptions = {}  # user_id -> subscription_type
        self.balances = {}  # user_id -> balance
        self.subscription_expiry = {}  # user_id -> expiry_date
        self.action_counts = {}  # user_id -> {action_type: count}
    
    def _init_db(self):
        """Инициализация базы данных"""
        logger.info("Initializing database tables")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица пользователей
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            balance REAL DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        ''')
        
        # Создаем таблицу подписок
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subscription_type TEXT,
            start_date TIMESTAMP,
            end_date TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Создаем таблицу транзакций
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            amount REAL,
            type TEXT,
            description TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Создаем таблицу лимитов
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS limits (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type TEXT,
            count INTEGER DEFAULT 0,
            last_reset TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Проверяем наличие колонки subscription_type
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'subscription_type' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_type TEXT DEFAULT 'free'")
        
        # Проверяем наличие колонки subscription_end
        cursor.execute("PRAGMA table_info(users)")
        columns = [column[1] for column in cursor.fetchall()]
        if 'subscription_end' not in columns:
            cursor.execute("ALTER TABLE users ADD COLUMN subscription_end DATE")
        
        # Таблица отслеживаемых товаров
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS tracked_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            article TEXT,
            last_price REAL,
            last_sales INTEGER,
            last_rating REAL,
            notify_price_change BOOLEAN DEFAULT 1,
            notify_sales_change BOOLEAN DEFAULT 1,
            notify_rating_change BOOLEAN DEFAULT 1,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        # Таблица действий пользователя
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_actions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            action_type TEXT,
            count INTEGER DEFAULT 0,
            reset_date DATE,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
        ''')
        
        conn.commit()
        conn.close()
        logger.info("Database tables initialized successfully")
    
    def add_user(self, user_id: int) -> None:
        """Добавление нового пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "INSERT OR IGNORE INTO users (user_id) VALUES (?)",
            (user_id,)
        )
        
        conn.commit()
        conn.close()
    
    def get_user_balance(self, user_id: int) -> float:
        logger.info(f"Getting balance for user {user_id}")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT balance FROM users WHERE user_id = ?",
            (user_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        balance = result[0] if result else 0.0
        logger.info(f"User {user_id} balance: {balance}₽")
        return balance
    
    def update_balance(self, user_id: int, amount: float):
        logger.info(f"Updating balance for user {user_id}: {amount}₽")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "UPDATE users SET balance = balance + ? WHERE user_id = ?",
            (amount, user_id)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"Balance updated successfully for user {user_id}")
    
    def add_tracked_item(self, user_id: int, article: str,
                        price: float, sales: int, rating: float) -> bool:
        """Добавление товара для отслеживания"""
        try:
            # Проверяем лимиты на отслеживание товаров
            can_track = self.can_perform_action(user_id, 'tracking_items')
            if not can_track:
                logger.info(f"User {user_id} cannot track more items (limit reached)")
                return False
            
            # Проверяем, не отслеживается ли уже этот товар
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute('''
            SELECT id FROM tracked_items 
            WHERE user_id = ? AND article = ?
            ''', (user_id, article))
            
            existing = cursor.fetchone()
            if existing:
                logger.info(f"Item {article} is already tracked by user {user_id}")
                conn.close()
                return True  # Товар уже отслеживается, считаем это успехом
            
            # Добавляем товар для отслеживания
            cursor.execute('''
            INSERT INTO tracked_items 
            (user_id, article, last_price, last_sales, last_rating)
            VALUES (?, ?, ?, ?, ?)
            ''', (user_id, article, price, sales, rating))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Successfully added tracked item {article} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error adding tracked item: {e}")
            return False
    
    def remove_tracked_item(self, user_id: int, article: str) -> bool:
        """Удаление отслеживаемого товара"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем существование товара
            cursor.execute('''
            SELECT id FROM tracked_items 
            WHERE user_id = ? AND article = ?
            ''', (user_id, article))
            
            existing = cursor.fetchone()
            if not existing:
                logger.info(f"Item {article} is not tracked by user {user_id}")
                conn.close()
                return False
            
            # Удаляем товар
            cursor.execute('''
            DELETE FROM tracked_items 
            WHERE user_id = ? AND article = ?
            ''', (user_id, article))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Successfully removed tracked item {article} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error removing tracked item: {e}")
            return False
    
    def get_tracked_items(self, user_id: int) -> List[Dict]:
        """Получение списка отслеживаемых товаров"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT article, last_price, last_sales, last_rating,
               notify_price_change, notify_sales_change, notify_rating_change
        FROM tracked_items 
        WHERE user_id = ?
        ''', (user_id,))
        
        items = []
        for row in cursor.fetchall():
            items.append({
                'article': row[0],
                'price': row[1],
                'sales': row[2],
                'rating': row[3],
                'notify_price': bool(row[4]),
                'notify_sales': bool(row[5]),
                'notify_rating': bool(row[6])
            })
        
        conn.close()
        return items
    
    def update_item_stats(self, article: str, 
                         new_price: float, 
                         new_sales: int, 
                         new_rating: float) -> List[Dict]:
        """
        Обновление статистики товара и получение уведомлений
        Возвращает список уведомлений для пользователей
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем текущие данные
        cursor.execute('''
        SELECT user_id, last_price, last_sales, last_rating,
               notify_price_change, notify_sales_change, notify_rating_change
        FROM tracked_items 
        WHERE article = ?
        ''', (article,))
        
        notifications = []
        for row in cursor.fetchall():
            user_id = row[0]
            old_price = row[1]
            old_sales = row[2]
            old_rating = row[3]
            notify_price = bool(row[4])
            notify_sales = bool(row[5])
            notify_rating = bool(row[6])
            
            # Проверяем изменения
            price_change = abs((new_price - old_price) / old_price) if old_price else 0
            sales_change = abs((new_sales - old_sales) / old_sales) if old_sales else 0
            rating_change = abs(new_rating - old_rating) if old_rating else 0
            
            notification = {
                'user_id': user_id,
                'article': article,
                'changes': []
            }
            
            # Добавляем уведомления при изменении более чем на 20%
            if notify_price and price_change > 0.2:
                notification['changes'].append({
                    'type': 'price',
                    'old': old_price,
                    'new': new_price,
                    'change': price_change
                })
            
            if notify_sales and sales_change > 0.2:
                notification['changes'].append({
                    'type': 'sales',
                    'old': old_sales,
                    'new': new_sales,
                    'change': sales_change
                })
            
            if notify_rating and rating_change > 0.5:
                notification['changes'].append({
                    'type': 'rating',
                    'old': old_rating,
                    'new': new_rating,
                    'change': rating_change
                })
            
            if notification['changes']:
                notifications.append(notification)
        
        # Обновляем данные
        cursor.execute('''
        UPDATE tracked_items 
        SET last_price = ?, last_sales = ?, last_rating = ?
        WHERE article = ?
        ''', (new_price, new_sales, new_rating, article))
        
        conn.commit()
        conn.close()
        
        return notifications 
    
    def get_subscription(self, user_id: int) -> str:
        """Получение типа подписки пользователя"""
        logger.info(f"Getting subscription for user {user_id}")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT subscription_type FROM users WHERE user_id = ?",
            (user_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        subscription = result[0] if result else 'free'
        logger.info(f"User {user_id} subscription: {subscription}")
        return subscription
    
    def update_subscription(self, user_id: int, subscription_type: str, duration_days: int = 30):
        """Обновление подписки пользователя"""
        logger.info(f"Updating subscription for user {user_id} to {subscription_type}")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        expiry_date = (datetime.now() + timedelta(days=duration_days)).strftime('%Y-%m-%d')
        
        cursor.execute(
            "UPDATE users SET subscription_type = ?, subscription_end = ? WHERE user_id = ?",
            (subscription_type, expiry_date, user_id)
        )
        
        conn.commit()
        conn.close()
        logger.info(f"Subscription updated successfully for user {user_id}")
    
    def is_subscription_active(self, user_id: int) -> bool:
        logger.info(f"Checking if subscription is active for user {user_id}")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT subscription_end FROM users WHERE user_id = ?",
            (user_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            logger.info(f"User {user_id} has no active subscription")
            return False
        
        is_active = datetime.now() < datetime.fromisoformat(result[0])
        logger.info(f"User {user_id} subscription active: {is_active}")
        return is_active
    
    def get_subscription_limits(self, user_id: int) -> dict:
        logger.info(f"Getting subscription limits for user {user_id}")
        subscription_type = self.get_subscription(user_id)
        if not self.is_subscription_active(user_id):
            logger.info(f"User {user_id} has no active subscription, returning zero limits")
            return {
                'product_analysis': 0,
                'niche_analysis': 0,
                'tracking_items': 0
            }
        
        limits = {
            'basic': {
                'product_analysis': 50,
                'niche_analysis': 20,
                'tracking_items': 10
            },
            'pro': {
                'product_analysis': float('inf'),
                'niche_analysis': float('inf'),
                'tracking_items': 50
            },
            'business': {
                'product_analysis': float('inf'),
                'niche_analysis': float('inf'),
                'tracking_items': 200
            }
        }
        user_limits = limits.get(subscription_type, limits['basic'])
        logger.info(f"User {user_id} limits: {user_limits}")
        return user_limits
    
    def can_perform_action(self, user_id: int, action_type: str) -> bool:
        logger.info(f"Checking if user {user_id} can perform action: {action_type}")
        limits = self.get_subscription_limits(user_id)
        if limits[action_type] == float('inf'):
            logger.info(f"User {user_id} has unlimited {action_type} actions")
            return True
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        SELECT count FROM user_actions 
        WHERE user_id = ? AND action_type = ?
        ''', (user_id, action_type))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            logger.info(f"User {user_id} has no {action_type} actions recorded")
            return True
        
        can_perform = result[0] < limits[action_type]
        logger.info(f"User {user_id} can perform {action_type}: {can_perform}")
        return can_perform
    
    def decrement_action_count(self, user_id: int, action_type: str):
        logger.info(f"Decrementing action count for user {user_id}, action: {action_type}")
        limits = self.get_subscription_limits(user_id)
        if limits[action_type] == float('inf'):
            logger.info(f"User {user_id} has unlimited {action_type} actions, skipping count")
            return
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем текущий счетчик
        cursor.execute('''
        SELECT count FROM user_actions 
        WHERE user_id = ? AND action_type = ?
        ''', (user_id, action_type))
        
        result = cursor.fetchone()
        
        if not result:
            # Создаем новую запись
            cursor.execute('''
            INSERT INTO user_actions (user_id, action_type, count)
            VALUES (?, ?, 1)
            ''', (user_id, action_type))
            logger.info(f"Created new action count record for user {user_id}, action: {action_type}")
        else:
            # Обновляем существующую запись
            cursor.execute('''
            UPDATE user_actions 
            SET count = count + 1
            WHERE user_id = ? AND action_type = ?
            ''', (user_id, action_type))
            logger.info(f"Updated action count for user {user_id}, action: {action_type}")
        
        conn.commit()
        conn.close()
    
    def get_subscription_end_date(self, user_id: int) -> str:
        """Получение даты окончания подписки пользователя"""
        logger.info(f"Getting subscription end date for user {user_id}")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute(
            "SELECT subscription_end FROM users WHERE user_id = ?",
            (user_id,)
        )
        
        result = cursor.fetchone()
        conn.close()
        
        if not result or not result[0]:
            logger.info(f"User {user_id} has no subscription end date")
            return "Не установлена"
        
        end_date = datetime.fromisoformat(result[0]).strftime("%d.%m.%Y")
        logger.info(f"User {user_id} subscription ends on: {end_date}")
        return end_date
    
    def get_subscription_stats(self, user_id: int) -> dict:
        """Получение статистики использования подписки"""
        logger.info(f"Getting subscription stats for user {user_id}")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем информацию о подписке
        cursor.execute('''
        SELECT subscription_type, subscription_end 
        FROM users WHERE user_id = ?
        ''', (user_id,))
        
        sub_info = cursor.fetchone()
        if not sub_info:
            logger.info(f"No subscription info found for user {user_id}")
            return {}
        
        # Получаем статистику действий
        cursor.execute('''
        SELECT action_type, count 
        FROM user_actions 
        WHERE user_id = ?
        ''', (user_id,))
        
        actions = cursor.fetchall()
        conn.close()
        
        limits = self.get_subscription_limits(user_id)
        stats = {
            'subscription_type': sub_info[0] if sub_info[0] else 'free',
            'expiry_date': sub_info[1].replace(' ', 'T') if sub_info[1] else None,
            'actions': {}
        }
        
        # Initialize all possible actions with zero usage
        for action_type in limits.keys():
            stats['actions'][action_type] = {
                'used': 0,
                'limit': limits[action_type]
            }
        
        # Update with actual usage
        for action_type, count in actions:
            if action_type in stats['actions']:
                stats['actions'][action_type]['used'] = count
        
        logger.info(f"Retrieved subscription stats for user {user_id}: {stats}")
        return stats
    
    def get_expiring_subscriptions(self) -> list:
        """Получение списка подписок, срок действия которых истекает в течение 3 дней"""
        logger.info("Getting expiring subscriptions")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        three_days_later = datetime.now() + timedelta(days=3)
        
        cursor.execute('''
        SELECT user_id, subscription_type, subscription_end 
        FROM users 
        WHERE subscription_end <= ? AND subscription_type != 'free'
        ''', (three_days_later,))
        
        expiring = cursor.fetchall()
        conn.close()
        
        result = [
            {
                'user_id': row[0],
                'type': row[1],
                'expiry_date': row[2]
            }
            for row in expiring
        ]
        
        logger.info(f"Found {len(result)} expiring subscriptions")
        return result
    
    def get_all_users(self) -> dict:
        """Получение всех пользователей и их данных"""
        logger.info("Getting all users")
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Получаем всех пользователей
        cursor.execute("SELECT user_id FROM users")
        users = cursor.fetchall()
        conn.close()
        
        # Формируем результат в виде словаря
        result = {}
        for user_row in users:
            user_id = str(user_row[0])
            
            # Получаем отслеживаемые товары для пользователя
            tracked_items = self.get_tracked_items(int(user_id))
            
            # Получаем тип подписки
            subscription = self.get_subscription(int(user_id))
            
            # Формируем данные пользователя в аналогичном JSON-версии формате
            result[user_id] = {
                "tracked_items": tracked_items,
                "subscription": subscription
            }
        
        return result 
    
    def update_tracked_item(self, user_id: int, article: str, new_data: dict) -> bool:
        """Обновление информации о товаре в списке отслеживаемых."""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Проверяем существование товара
            cursor.execute('''
            SELECT id FROM tracked_items 
            WHERE user_id = ? AND article = ?
            ''', (user_id, article))
            
            existing = cursor.fetchone()
            if not existing:
                logger.info(f"Item {article} is not tracked by user {user_id}")
                conn.close()
                return False
            
            # Извлекаем данные для обновления
            price = new_data.get('price', 0)
            sales = new_data.get('stock', 0)  # Используем stock как sales для совместимости
            rating = new_data.get('rating', 0.0)
            
            # Обновляем товар
            cursor.execute('''
            UPDATE tracked_items 
            SET last_price = ?, last_sales = ?, last_rating = ?
            WHERE user_id = ? AND article = ?
            ''', (price, sales, rating, user_id, article))
            
            conn.commit()
            conn.close()
            
            logger.info(f"Successfully updated tracked item {article} for user {user_id}")
            return True
        except Exception as e:
            logger.error(f"Error updating tracked item: {e}")
            return False 