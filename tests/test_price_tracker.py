import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.price_tracker import PriceTracker

class TestPriceTracker:
    """Tests pour le système de suivi des prix"""
    
    def setup_method(self):
        """Configuration avant chaque test"""
        self.tracker = PriceTracker()
    
    def test_tracker_initialization(self):
        """Test l'initialisation du tracker"""
        assert len(self.tracker.price_history) == 0
        assert len(self.tracker.price_alerts) == 0
    
    def test_add_price_record(self):
        """Test l'ajout d'un enregistrement de prix"""
        product_id = "test_product_123"
        price = 99.99
        currency = "USD"
        platform = "amazon"
        
        self.tracker.add_price_record(product_id, price, currency, platform)
        
        assert product_id in self.tracker.price_history
        assert len(self.tracker.price_history[product_id]) == 1
        
        record = self.tracker.price_history[product_id][0]
        assert record['price'] == price
        assert record['currency'] == currency
        assert record['platform'] == platform
        assert 'timestamp' in record
        assert 'datetime' in record
    
    def test_add_multiple_price_records(self):
        """Test l'ajout de plusieurs enregistrements"""
        product_id = "test_product_123"
        prices = [99.99, 89.99, 79.99]
        
        for price in prices:
            self.tracker.add_price_record(product_id, price)
        
        assert len(self.tracker.price_history[product_id]) == 3
        
        # Vérifier l'ordre chronologique
        records = self.tracker.price_history[product_id]
        for i, price in enumerate(prices):
            assert records[i]['price'] == price
    
    def test_price_history_limit(self):
        """Test la limitation de l'historique des prix"""
        product_id = "test_product_123"
        
        # Ajouter plus de 100 enregistrements
        for i in range(150):
            self.tracker.add_price_record(product_id, float(i))
        
        # Vérifier que seulement les 100 derniers sont conservés
        assert len(self.tracker.price_history[product_id]) == 100
        
        # Vérifier que ce sont les plus récents
        records = self.tracker.price_history[product_id]
        assert records[0]['price'] == 50.0  # 150 - 100
        assert records[-1]['price'] == 149.0
    
    def test_detect_price_changes_no_change(self):
        """Test la détection sans changement de prix"""
        products = [
            {
                'id': 'product_1',
                'title': 'Test Product',
                'price': 99.99,
                'currency': 'USD',
                'platform': 'amazon'
            }
        ]
        
        # Premier appel - pas de changement détecté
        changes = self.tracker.detect_price_changes(products)
        assert len(changes) == 0
        
        # Deuxième appel avec le même prix - pas de changement
        changes = self.tracker.detect_price_changes(products)
        assert len(changes) == 0
    
    def test_detect_price_changes_with_change(self):
        """Test la détection avec changement de prix"""
        product_id = 'product_1'
        
        # Premier produit à 100$
        products_v1 = [{
            'id': product_id,
            'title': 'Test Product',
            'price': 100.0,
            'currency': 'USD',
            'platform': 'amazon'
        }]
        
        # Deuxième produit à 80$ (baisse de 20%)
        products_v2 = [{
            'id': product_id,
            'title': 'Test Product',
            'price': 80.0,
            'currency': 'USD',
            'platform': 'amazon'
        }]
        
        # Premier scan
        self.tracker.detect_price_changes(products_v1)
        
        # Deuxième scan avec changement
        changes = self.tracker.detect_price_changes(products_v2)
        
        assert len(changes) == 1
        change = changes[0]
        
        assert change['product_id'] == product_id
        assert change['current_price'] == 80.0
        assert change['previous_price'] == 100.0
        assert change['price_change'] == -20.0
        assert change['percentage_change'] == -20.0
        assert change['change_type'] == 'decrease'
    
    def test_detect_price_changes_small_change_ignored(self):
        """Test que les petits changements sont ignorés"""
        product_id = 'product_1'
        
        # Premier produit à 100$
        products_v1 = [{
            'id': product_id,
            'title': 'Test Product',
            'price': 100.0,
            'currency': 'USD',
            'platform': 'amazon'
        }]
        
        # Deuxième produit à 100.50$ (changement de 0.5%)
        products_v2 = [{
            'id': product_id,
            'title': 'Test Product',
            'price': 100.50,
            'currency': 'USD',
            'platform': 'amazon'
        }]
        
        self.tracker.detect_price_changes(products_v1)
        changes = self.tracker.detect_price_changes(products_v2)
        
        # Changement trop petit, doit être ignoré
        assert len(changes) == 0
    
    def test_get_price_trends_no_data(self):
        """Test l'obtention de tendances sans données"""
        trends = self.tracker.get_price_trends('nonexistent_product')
        
        assert trends['trend'] == 'no_data'
        assert trends['confidence'] == 0
    
    def test_get_price_trends_insufficient_data(self):
        """Test l'obtention de tendances avec données insuffisantes"""
        product_id = 'product_1'
        
        # Ajouter un seul point de données
        self.tracker.add_price_record(product_id, 100.0)
        
        trends = self.tracker.get_price_trends(product_id)
        
        assert trends['trend'] == 'insufficient_data'
        assert trends['confidence'] == 0
    
    def test_get_price_trends_stable(self):
        """Test l'obtention de tendances stables"""
        product_id = 'product_1'
        
        # Ajouter des prix stables
        prices = [100.0, 101.0, 99.5, 100.5, 99.8]
        for price in prices:
            self.tracker.add_price_record(product_id, price)
        
        trends = self.tracker.get_price_trends(product_id)
        
        assert trends['trend'] == 'stable'
        assert trends['confidence'] > 0
        assert abs(trends['percentage_change']) < 2
    
    def test_get_price_trends_increasing(self):
        """Test l'obtention de tendances croissantes"""
        product_id = 'product_1'
        
        # Ajouter des prix croissants
        prices = [100.0, 105.0, 110.0, 115.0, 120.0]
        for price in prices:
            self.tracker.add_price_record(product_id, price)
        
        trends = self.tracker.get_price_trends(product_id)
        
        assert trends['trend'] == 'increasing'
        assert trends['percentage_change'] > 0
        assert trends['confidence'] > 0.5
    
    def test_get_price_trends_decreasing(self):
        """Test l'obtention de tendances décroissantes"""
        product_id = 'product_1'
        
        # Ajouter des prix décroissants
        prices = [120.0, 115.0, 110.0, 105.0, 100.0]
        for price in prices:
            self.tracker.add_price_record(product_id, price)
        
        trends = self.tracker.get_price_trends(product_id)
        
        assert trends['trend'] == 'decreasing'
        assert trends['percentage_change'] < 0
        assert trends['confidence'] > 0.5
    
    def test_calculate_trend_confidence(self):
        """Test le calcul de confiance des tendances"""
        # Tendance très cohérente (tous croissants)
        consistent_prices = [100, 105, 110, 115, 120]
        confidence_high = self.tracker._calculate_trend_confidence(consistent_prices)
        
        # Tendance incohérente (zigzag)
        inconsistent_prices = [100, 110, 105, 115, 108]
        confidence_low = self.tracker._calculate_trend_confidence(inconsistent_prices)
        
        assert confidence_high > confidence_low
        assert 0 <= confidence_high <= 1
        assert 0 <= confidence_low <= 1
    
    def test_create_price_alert(self):
        """Test la création d'alertes de prix"""
        product_id = 'product_1'
        target_price = 80.0
        alert_type = 'below'
        
        alert_id = self.tracker.create_price_alert(product_id, target_price, alert_type)
        
        assert alert_id is not None
        assert len(self.tracker.price_alerts) == 1
        
        alert = self.tracker.price_alerts[0]
        assert alert['id'] == alert_id
        assert alert['product_id'] == product_id
        assert alert['target_price'] == target_price
        assert alert['alert_type'] == alert_type
        assert alert['triggered'] is False
    
    def test_check_price_alerts_below(self):
        """Test la vérification d'alertes de prix (en dessous)"""
        product_id = 'product_1'
        
        # Créer une alerte pour prix en dessous de 90$
        self.tracker.create_price_alert(product_id, 90.0, 'below')
        
        # Produit à 95$ - ne doit pas déclencher
        products_high = [{
            'id': product_id,
            'price': 95.0,
            'title': 'Test Product'
        }]
        
        triggered = self.tracker.check_price_alerts(products_high)
        assert len(triggered) == 0
        
        # Produit à 85$ - doit déclencher
        products_low = [{
            'id': product_id,
            'price': 85.0,
            'title': 'Test Product'
        }]
        
        triggered = self.tracker.check_price_alerts(products_low)
        assert len(triggered) == 1
        assert triggered[0]['triggered_price'] == 85.0
    
    def test_check_price_alerts_above(self):
        """Test la vérification d'alertes de prix (au-dessus)"""
        product_id = 'product_1'
        
        # Créer une alerte pour prix au-dessus de 110$
        self.tracker.create_price_alert(product_id, 110.0, 'above')
        
        # Produit à 105$ - ne doit pas déclencher
        products_low = [{
            'id': product_id,
            'price': 105.0,
            'title': 'Test Product'
        }]
        
        triggered = self.tracker.check_price_alerts(products_low)
        assert len(triggered) == 0
        
        # Produit à 115$ - doit déclencher
        products_high = [{
            'id': product_id,
            'price': 115.0,
            'title': 'Test Product'
        }]
        
        triggered = self.tracker.check_price_alerts(products_high)
        assert len(triggered) == 1
        assert triggered[0]['triggered_price'] == 115.0
    
    def test_check_price_alerts_change(self):
        """Test la vérification d'alertes de changement de prix"""
        product_id = 'product_1'
        
        # Créer une alerte pour changement de 10%
        self.tracker.create_price_alert(product_id, 10.0, 'change')
        
        # Ajouter un prix initial
        self.tracker.add_price_record(product_id, 100.0)
        
        # Changement de 5% - ne doit pas déclencher
        products_small_change = [{
            'id': product_id,
            'price': 105.0,
            'title': 'Test Product'
        }]
        
        triggered = self.tracker.check_price_alerts(products_small_change)
        assert len(triggered) == 0
        
        # Changement de 15% - doit déclencher
        products_big_change = [{
            'id': product_id,
            'price': 115.0,
            'title': 'Test Product'
        }]
        
        triggered = self.tracker.check_price_alerts(products_big_change)
        assert len(triggered) == 1
    
    def test_get_platform_price_comparison(self):
        """Test la comparaison de prix entre plateformes"""
        products = [
            {
                'id': 'product_1_amazon',
                'title': 'iPhone 15 Pro',
                'price': 999.0,
                'platform': 'amazon',
                'url': 'https://amazon.com/iphone15'
            },
            {
                'id': 'product_1_ebay',
                'title': 'iPhone 15 Pro Max',
                'price': 1099.0,
                'platform': 'ebay',
                'url': 'https://ebay.com/iphone15'
            },
            {
                'id': 'product_2_amazon',
                'title': 'MacBook Pro 2023',
                'price': 1999.0,
                'platform': 'amazon',
                'url': 'https://amazon.com/macbook'
            }
        ]
        
        comparison = self.tracker.get_platform_price_comparison(products)
        
        assert 'product_comparisons' in comparison
        assert 'platform_statistics' in comparison
        assert 'total_comparisons' in comparison
        
        # Vérifier les statistiques par plateforme
        stats = comparison['platform_statistics']
        assert 'amazon' in stats
        assert 'ebay' in stats
        
        amazon_stats = stats['amazon']
        assert amazon_stats['count'] == 2
        assert amazon_stats['avg_price'] == 1499.0  # (999 + 1999) / 2
    
    def test_export_price_history(self):
        """Test l'export de l'historique des prix"""
        product_id = 'product_1'
        
        # Ajouter quelques enregistrements
        prices = [100.0, 95.0, 105.0]
        for price in prices:
            self.tracker.add_price_record(product_id, price, 'USD', 'amazon')
        
        # Export pour un produit spécifique
        export_single = self.tracker.export_price_history(product_id)
        
        assert product_id in export_single
        assert len(export_single[product_id]) == 3
        
        # Vérifier la structure des données exportées
        record = export_single[product_id][0]
        assert 'price' in record
        assert 'currency' in record
        assert 'platform' in record
        assert 'timestamp' in record
        assert 'datetime' not in record  # Ne doit pas être dans l'export
        
        # Export complet
        export_all = self.tracker.export_price_history()
        
        assert product_id in export_all
        assert len(export_all[product_id]) == 3
    
    def test_group_similar_products(self):
        """Test le groupement de produits similaires"""
        products = [
            {'title': 'iPhone 15 Pro Max 256GB'},
            {'title': 'iPhone 15 Pro 128GB'},
            {'title': 'Samsung Galaxy S24 Ultra'},
            {'title': 'Samsung Galaxy S24 Plus'},
            {'title': 'MacBook Pro 2023'}
        ]
        
        groups = self.tracker._group_similar_products(products)
        
        # Vérifier que les produits similaires sont groupés
        iphone_group = None
        samsung_group = None
        
        for group_key, group_products in groups.items():
            if 'iphone 15 pro' in group_key.lower():
                iphone_group = group_products
            elif 'samsung galaxy s24' in group_key.lower():
                samsung_group = group_products
        
        assert iphone_group is not None
        assert len(iphone_group) == 2
        
        assert samsung_group is not None
        assert len(samsung_group) == 2
    
    def test_compare_product_group(self):
        """Test la comparaison d'un groupe de produits"""
        products = [
            {
                'title': 'iPhone 15 Pro',
                'price': 999.0,
                'platform': 'amazon',
                'url': 'https://amazon.com/iphone'
            },
            {
                'title': 'iPhone 15 Pro',
                'price': 1099.0,
                'platform': 'ebay',
                'url': 'https://ebay.com/iphone'
            },
            {
                'title': 'iPhone 15 Pro',
                'price': 1049.0,
                'platform': 'walmart',
                'url': 'https://walmart.com/iphone'
            }
        ]
        
        comparison = self.tracker._compare_product_group(products)
        
        assert comparison is not None
        assert comparison['title'] == 'iPhone 15 Pro'
        assert comparison['cheapest']['platform'] == 'amazon'
        assert comparison['cheapest']['price'] == 999.0
        assert comparison['most_expensive']['platform'] == 'ebay'
        assert comparison['most_expensive']['price'] == 1099.0
        assert comparison['price_range'] == 100.0
        assert comparison['total_variants'] == 3


if __name__ == "__main__":
    pytest.main([__file__])