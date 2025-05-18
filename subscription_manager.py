import json
import os
import logging
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

class SubscriptionManager:
    def __init__(self):
        self.db_file = "subscriptions.json"
        self._load_data()
    
    def _load_data(self):
        """Загружает данные из JSON файла."""
        if os.path.exists(self.db_file):
            try:
                with open(self.db_file, 'r', encoding='utf-8') as f:
                    self.data = json.load(f)
            except Exception as e:
                logger.error(f"Ошибка загрузки данных: {str(e)}")
                self.data = {"users": {}}
        else:
            self.data = {"users": {}}
    
    def _save_data(self):
        """Сохраняет данные в JSON файл."""
        try:
            with open(self.db_file, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Ошибка сохранения данных: {str(e)}")
    
    def add_user(self, user_id):
        """Добавляет нового пользователя."""
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            self.data["users"][user_id] = {
                "balance": 0,
                "subscription": None,
                "subscription_until": None,
                "tracked_items": [],
                "actions": {
                    "product_analysis": {"used": 0, "limit": 0},
                    "niche_analysis": {"used": 0, "limit": 0},
                    "tracking_items": {"used": 0, "limit": 0},
                    "global_search": {"used": 0, "limit": 0}
                }
            }
            self._save_data()
            logger.info(f"Добавлен новый пользователь: {user_id}")
    
    def get_user_balance(self, user_id):
        """Возвращает баланс пользователя."""
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            self.add_user(user_id)
        return self.data["users"][user_id].get("balance", 0)
    
    def update_balance(self, user_id, amount):
        """Обновляет баланс пользователя."""
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            self.add_user(user_id)
        
        current_balance = self.data["users"][user_id].get("balance", 0)
        self.data["users"][user_id]["balance"] = current_balance + amount
        self._save_data()
        logger.info(f"Обновлен баланс пользователя {user_id}: {current_balance} -> {current_balance + amount}")
        return self.data["users"][user_id]["balance"]
    
    def get_tracked_items(self, user_id):
        """Возвращает список отслеживаемых товаров."""
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            self.add_user(user_id)
        tracked_items = self.data["users"][user_id].get("tracked_items", [])
        
        # Преобразуем старый формат (просто список ID) в новый формат (список словарей)
        result = []
        for item in tracked_items:
            if isinstance(item, str):
                # Старый формат, преобразуем в новый
                result.append({
                    "id": item,
                    "name": "Неизвестный товар",
                    "price": 0,
                    "added_date": datetime.now().isoformat(),
                    "last_update": datetime.now().isoformat()
                })
            else:
                # Новый формат, используем как есть
                result.append(item)
        
        return result
    
    def add_tracked_item(self, user_id, item_id, item_name="", item_price=0):
        """Добавляет товар в список отслеживаемых."""
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            self.add_user(user_id)
        
        # Проверяем лимит отслеживаемых товаров
        subscription = self.get_subscription(user_id)
        if not subscription or not self.is_subscription_active(user_id):
            return False
        
        tracked_items = self.data["users"][user_id].get("tracked_items", [])
        
        # Проверяем, не превышен ли лимит отслеживаемых товаров
        action_stats = self.data["users"][user_id].get("actions", {}).get("tracking_items", {})
        limit = action_stats.get("limit", 0)
        
        if limit != float('inf') and len(tracked_items) >= limit:
            return False
        
        # Проверяем, не добавлен ли уже этот товар
        for item in tracked_items:
            if isinstance(item, dict) and item.get("id") == item_id:
                return True
            elif item == item_id:
                return True
        
        # Создаем новый элемент
        new_item = {
            "id": item_id,
            "name": item_name,
            "price": item_price,
            "stock": 0,
            "added_date": datetime.now().isoformat(),
            "last_update": datetime.now().isoformat()
        }
        
        # Добавляем товар в список отслеживаемых
        if "tracked_items" not in self.data["users"][user_id]:
            self.data["users"][user_id]["tracked_items"] = []
        
        self.data["users"][user_id]["tracked_items"].append(new_item)
        self._save_data()
        
        logger.info(f"Добавлен отслеживаемый товар {item_id} ({item_name}) для пользователя {user_id}")
        return True
    
    def remove_tracked_item(self, user_id, item_id):
        """Удаляет товар из списка отслеживаемых."""
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            return False
        
        tracked_items = self.data["users"][user_id].get("tracked_items", [])
        
        # Ищем товар в списке с учетом возможных разных форматов
        for i, item in enumerate(tracked_items):
            if isinstance(item, dict) and item.get("id") == item_id:
                # Новый формат (словарь)
                del tracked_items[i]
                self._save_data()
                logger.info(f"Удален отслеживаемый товар {item_id} для пользователя {user_id}")
                return True
            elif item == item_id:
                # Старый формат (просто ID)
                del tracked_items[i]
                self._save_data()
                logger.info(f"Удален отслеживаемый товар {item_id} для пользователя {user_id}")
                return True
        
        return False
    
    def get_subscription(self, user_id):
        """Возвращает тип подписки пользователя."""
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            self.add_user(user_id)
        return self.data["users"][user_id].get("subscription")
    
    def update_subscription(self, user_id, subscription_type):
        """Обновляет подписку пользователя."""
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            self.add_user(user_id)
        
        # Устанавливаем тип подписки
        self.data["users"][user_id]["subscription"] = subscription_type
        
        # Устанавливаем срок действия подписки (30 дней)
        expiry_date = (datetime.now() + timedelta(days=30)).isoformat()
        self.data["users"][user_id]["subscription_until"] = expiry_date
        
        # Обновляем лимиты действий
        from new_bot import SUBSCRIPTION_LIMITS
        limits = SUBSCRIPTION_LIMITS.get(subscription_type, {})
        for action, limit in limits.items():
            if action in self.data["users"][user_id]["actions"]:
                self.data["users"][user_id]["actions"][action]["limit"] = limit
                # Сбрасываем счетчик использованных действий
                self.data["users"][user_id]["actions"][action]["used"] = 0
        
        self._save_data()
        logger.info(f"Обновлена подписка пользователя {user_id} на {subscription_type} до {expiry_date}")
        return True
    
    def is_subscription_active(self, user_id):
        """Проверяет, активна ли подписка."""
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            return False
        
        subscription_until = self.data["users"][user_id].get("subscription_until")
        if not subscription_until:
            return False
        
        try:
            expiry_date = datetime.fromisoformat(subscription_until)
            return expiry_date > datetime.now()
        except (ValueError, TypeError):
            return False
    
    def get_subscription_stats(self, user_id):
        """Возвращает статистику подписки."""
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            return None
        
        subscription = self.data["users"][user_id].get("subscription")
        if not subscription:
            return None
        
        subscription_until = self.data["users"][user_id].get("subscription_until")
        if not subscription_until:
            return None
        
        actions = self.data["users"][user_id].get("actions", {})
        
        return {
            "type": subscription,
            "expiry_date": subscription_until,
            "actions": actions
        }
    
    def can_perform_action(self, user_id, action_type):
        """Проверяет, может ли пользователь выполнить действие."""
        user_id = str(user_id)
        
        # Проверяем, активна ли подписка
        if not self.is_subscription_active(user_id):
            return False
        
        # Проверяем лимиты действий
        actions = self.data["users"][user_id].get("actions", {})
        if action_type not in actions:
            return False
        
        action = actions[action_type]
        used = action.get("used", 0)
        limit = action.get("limit", 0)
        
        # Если лимит бесконечный (float('inf')), то всегда возвращаем True
        if limit == float('inf'):
            return True
        
        # Проверяем, не превышен ли лимит
        if used >= limit:
            return False
        
        # Увеличиваем счетчик использованных действий
        self.data["users"][user_id]["actions"][action_type]["used"] = used + 1
        self._save_data()
        
        return True
    
    def get_expiring_subscriptions(self):
        """Возвращает список подписок, которые скоро истекут."""
        expiring_subs = []
        
        for user_id, user_data in self.data["users"].items():
            subscription = user_data.get("subscription")
            subscription_until = user_data.get("subscription_until")
            
            if not subscription or not subscription_until:
                continue
            
            try:
                expiry_date = datetime.fromisoformat(subscription_until)
                days_left = (expiry_date - datetime.now()).days
                
                if 0 < days_left <= 3:  # Подписка истекает в течение 3 дней
                    expiring_subs.append({
                        "user_id": int(user_id),
                        "type": subscription,
                        "expiry_date": subscription_until
                    })
            except (ValueError, TypeError):
                continue
        
        return expiring_subs
    
    def update_tracked_item(self, user_id, item_id, new_data):
        """Обновляет информацию о товаре в списке отслеживаемых."""
        user_id = str(user_id)
        if user_id not in self.data["users"]:
            return False
        
        tracked_items = self.data["users"][user_id].get("tracked_items", [])
        
        # Ищем товар в списке
        for i, item in enumerate(tracked_items):
            if isinstance(item, dict) and item.get("id") == item_id:
                # Обновляем данные товара
                self.data["users"][user_id]["tracked_items"][i] = new_data
                self._save_data()
                logger.info(f"Обновлен отслеживаемый товар {item_id} для пользователя {user_id}")
                return True
            elif item == item_id:
                # Заменяем старый формат (просто ID) на новый формат (словарь)
                self.data["users"][user_id]["tracked_items"][i] = new_data
                self._save_data()
                logger.info(f"Обновлен отслеживаемый товар {item_id} для пользователя {user_id}")
                return True
        
        return False
    
    def get_all_users(self):
        """Возвращает словарь со всеми пользователями и их данными."""
        return self.data.get("users", {}) 