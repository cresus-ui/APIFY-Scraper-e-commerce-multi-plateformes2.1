import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict
import statistics

logger = logging.getLogger(__name__)

class PriceTracker:
    """Système de suivi des prix pour détecter les changements et tendances"""
    
    def __init__(self):
        self.price_history = defaultdict(list)  # {product_id: [price_records]}
        self.price_alerts = []  # Liste des alertes de prix
        
    def add_price_record(self, product_id: str, price: float, currency: str = 'USD', 
                        platform: str = '', timestamp: datetime = None) -> None:
        """Ajoute un enregistrement de prix"""
        if timestamp is None:
            timestamp = datetime.now()
        
        price_record = {
            'price': price,
            'currency': currency,
            'platform': platform,
            'timestamp': timestamp.isoformat(),
            'datetime': timestamp
        }
        
        self.price_history[product_id].append(price_record)
        
        # Garde seulement les 100 derniers enregistrements par produit
        if len(self.price_history[product_id]) > 100:
            self.price_history[product_id] = self.price_history[product_id][-100:]
    
    def detect_price_changes(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Détecte les changements de prix pour une liste de produits"""
        price_changes = []
        
        for product in products:
            product_id = product.get('id', '')
            current_price = product.get('price', 0)
            currency = product.get('currency', 'USD')
            platform = product.get('platform', '')
            
            if not product_id or current_price <= 0:
                continue
            
            # Ajoute le prix actuel à l'historique
            self.add_price_record(product_id, current_price, currency, platform)
            
            # Analyse les changements
            change_info = self._analyze_price_change(product_id, current_price)
            
            if change_info:
                change_record = {
                    'product_id': product_id,
                    'product_title': product.get('title', ''),
                    'platform': platform,
                    'current_price': current_price,
                    'previous_price': change_info['previous_price'],
                    'price_change': change_info['price_change'],
                    'percentage_change': change_info['percentage_change'],
                    'change_type': change_info['change_type'],
                    'currency': currency,
                    'detected_at': datetime.now().isoformat()
                }
                price_changes.append(change_record)
        
        logger.info(f"Détection de changements de prix: {len(price_changes)} changements détectés")
        return price_changes
    
    def _analyze_price_change(self, product_id: str, current_price: float) -> Optional[Dict[str, Any]]:
        """Analyse les changements de prix pour un produit"""
        history = self.price_history.get(product_id, [])
        
        if len(history) < 2:
            return None
        
        # Compare avec le prix précédent
        previous_record = history[-2]
        previous_price = previous_record['price']
        
        if previous_price == current_price:
            return None
        
        price_change = current_price - previous_price
        percentage_change = (price_change / previous_price) * 100
        
        # Détermine le type de changement
        if price_change > 0:
            change_type = 'increase'
        else:
            change_type = 'decrease'
        
        # Seuil minimum pour considérer un changement significatif (1%)
        if abs(percentage_change) < 1.0:
            return None
        
        return {
            'previous_price': previous_price,
            'price_change': round(price_change, 2),
            'percentage_change': round(percentage_change, 2),
            'change_type': change_type
        }
    
    def get_price_trends(self, product_id: str, days: int = 30) -> Dict[str, Any]:
        """Obtient les tendances de prix pour un produit"""
        history = self.price_history.get(product_id, [])
        
        if not history:
            return {'trend': 'no_data', 'confidence': 0}
        
        # Filtre par période
        cutoff_date = datetime.now() - timedelta(days=days)
        recent_history = [
            record for record in history 
            if record['datetime'] >= cutoff_date
        ]
        
        if len(recent_history) < 2:
            return {'trend': 'insufficient_data', 'confidence': 0}
        
        return self._calculate_trend(recent_history)
    
    def _calculate_trend(self, price_records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcule la tendance des prix"""
        prices = [record['price'] for record in price_records]
        timestamps = [record['datetime'] for record in price_records]
        
        if len(prices) < 2:
            return {'trend': 'insufficient_data', 'confidence': 0}
        
        # Calcul de la tendance linéaire simple
        first_price = prices[0]
        last_price = prices[-1]
        
        price_change = last_price - first_price
        percentage_change = (price_change / first_price) * 100
        
        # Détermine la tendance
        if abs(percentage_change) < 2:
            trend = 'stable'
        elif percentage_change > 0:
            trend = 'increasing'
        else:
            trend = 'decreasing'
        
        # Calcule la confiance basée sur la cohérence
        confidence = self._calculate_trend_confidence(prices)
        
        # Statistiques additionnelles
        min_price = min(prices)
        max_price = max(prices)
        avg_price = statistics.mean(prices)
        volatility = statistics.stdev(prices) if len(prices) > 1 else 0
        
        return {
            'trend': trend,
            'confidence': confidence,
            'percentage_change': round(percentage_change, 2),
            'price_change': round(price_change, 2),
            'min_price': min_price,
            'max_price': max_price,
            'avg_price': round(avg_price, 2),
            'volatility': round(volatility, 2),
            'data_points': len(prices),
            'period_days': (timestamps[-1] - timestamps[0]).days if len(timestamps) > 1 else 0
        }
    
    def _calculate_trend_confidence(self, prices: List[float]) -> float:
        """Calcule la confiance dans la tendance (0-1)"""
        if len(prices) < 3:
            return 0.5
        
        # Calcule la cohérence de la direction
        changes = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if change != 0:
                changes.append(1 if change > 0 else -1)
        
        if not changes:
            return 0.5
        
        # Pourcentage de changements dans la même direction
        positive_changes = sum(1 for c in changes if c > 0)
        negative_changes = sum(1 for c in changes if c < 0)
        
        max_consistent = max(positive_changes, negative_changes)
        consistency = max_consistent / len(changes)
        
        # Ajuste la confiance basée sur le nombre de points de données
        data_factor = min(1.0, len(prices) / 10)
        
        return round(consistency * data_factor, 2)
    
    def get_platform_price_comparison(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Compare les prix entre plateformes pour des produits similaires"""
        # Groupe les produits par titre similaire
        product_groups = self._group_similar_products(products)
        
        comparisons = []
        
        for group_key, group_products in product_groups.items():
            if len(group_products) < 2:
                continue
            
            comparison = self._compare_product_group(group_products)
            if comparison:
                comparisons.append(comparison)
        
        # Statistiques globales
        platform_stats = self._calculate_platform_statistics(products)
        
        return {
            'product_comparisons': comparisons,
            'platform_statistics': platform_stats,
            'total_comparisons': len(comparisons)
        }
    
    def _group_similar_products(self, products: List[Dict[str, Any]]) -> Dict[str, List[Dict[str, Any]]]:
        """Groupe les produits similaires par titre"""
        groups = defaultdict(list)
        
        for product in products:
            title = product.get('title', '').lower()
            
            # Simplifie le titre pour le groupement
            import re
            simplified_title = re.sub(r'[^\w\s]', '', title)
            words = simplified_title.split()
            
            # Utilise les 3 premiers mots comme clé de groupe
            if len(words) >= 3:
                group_key = ' '.join(words[:3])
                groups[group_key].append(product)
        
        return groups
    
    def _compare_product_group(self, products: List[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """Compare les prix d'un groupe de produits similaires"""
        if len(products) < 2:
            return None
        
        # Trie par prix
        sorted_products = sorted(products, key=lambda p: p.get('price', 0))
        
        cheapest = sorted_products[0]
        most_expensive = sorted_products[-1]
        
        price_range = most_expensive['price'] - cheapest['price']
        avg_price = statistics.mean([p.get('price', 0) for p in products])
        
        # Analyse par plateforme
        platform_prices = {}
        for product in products:
            platform = product.get('platform', 'unknown')
            price = product.get('price', 0)
            
            if platform not in platform_prices or price < platform_prices[platform]['price']:
                platform_prices[platform] = {
                    'price': price,
                    'product': product
                }
        
        return {
            'title': cheapest.get('title', ''),
            'cheapest': {
                'platform': cheapest.get('platform'),
                'price': cheapest.get('price'),
                'url': cheapest.get('url')
            },
            'most_expensive': {
                'platform': most_expensive.get('platform'),
                'price': most_expensive.get('price'),
                'url': most_expensive.get('url')
            },
            'price_range': round(price_range, 2),
            'average_price': round(avg_price, 2),
            'platform_prices': platform_prices,
            'total_variants': len(products)
        }
    
    def _calculate_platform_statistics(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calcule les statistiques par plateforme"""
        platform_data = defaultdict(list)
        
        for product in products:
            platform = product.get('platform', 'unknown')
            price = product.get('price', 0)
            if price > 0:
                platform_data[platform].append(price)
        
        stats = {}
        for platform, prices in platform_data.items():
            if prices:
                stats[platform] = {
                    'count': len(prices),
                    'avg_price': round(statistics.mean(prices), 2),
                    'min_price': min(prices),
                    'max_price': max(prices),
                    'median_price': round(statistics.median(prices), 2)
                }
        
        return stats
    
    def create_price_alert(self, product_id: str, target_price: float, 
                          alert_type: str = 'below') -> str:
        """Crée une alerte de prix"""
        alert_id = f"alert_{len(self.price_alerts)}_{datetime.now().timestamp()}"
        
        alert = {
            'id': alert_id,
            'product_id': product_id,
            'target_price': target_price,
            'alert_type': alert_type,  # 'below', 'above', 'change'
            'created_at': datetime.now().isoformat(),
            'triggered': False
        }
        
        self.price_alerts.append(alert)
        return alert_id
    
    def check_price_alerts(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Vérifie les alertes de prix"""
        triggered_alerts = []
        
        # Crée un mapping produit_id -> prix actuel
        current_prices = {
            product.get('id', ''): product.get('price', 0)
            for product in products
            if product.get('id') and product.get('price', 0) > 0
        }
        
        for alert in self.price_alerts:
            if alert['triggered']:
                continue
            
            product_id = alert['product_id']
            if product_id not in current_prices:
                continue
            
            current_price = current_prices[product_id]
            target_price = alert['target_price']
            alert_type = alert['alert_type']
            
            triggered = False
            
            if alert_type == 'below' and current_price <= target_price:
                triggered = True
            elif alert_type == 'above' and current_price >= target_price:
                triggered = True
            elif alert_type == 'change':
                # Vérifie si le prix a changé de plus de target_price%
                history = self.price_history.get(product_id, [])
                if len(history) >= 2:
                    previous_price = history[-2]['price']
                    change_percentage = abs((current_price - previous_price) / previous_price * 100)
                    if change_percentage >= target_price:
                        triggered = True
            
            if triggered:
                alert['triggered'] = True
                alert['triggered_at'] = datetime.now().isoformat()
                alert['triggered_price'] = current_price
                triggered_alerts.append(alert.copy())
        
        return triggered_alerts
    
    def export_price_history(self, product_id: str = None) -> Dict[str, Any]:
        """Exporte l'historique des prix"""
        if product_id:
            return {
                product_id: [
                    {
                        'price': record['price'],
                        'currency': record['currency'],
                        'platform': record['platform'],
                        'timestamp': record['timestamp']
                    }
                    for record in self.price_history.get(product_id, [])
                ]
            }
        
        # Exporte tout l'historique
        export_data = {}
        for pid, history in self.price_history.items():
            export_data[pid] = [
                {
                    'price': record['price'],
                    'currency': record['currency'],
                    'platform': record['platform'],
                    'timestamp': record['timestamp']
                }
                for record in history
            ]
        
        return export_data