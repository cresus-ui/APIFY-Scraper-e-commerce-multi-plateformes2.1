import logging
import json
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import statistics
import re

logger = logging.getLogger(__name__)

class TrendAnalyzer:
    """Analyseur de tendances pour les données e-commerce"""
    
    def __init__(self):
        self.product_data = []  # Historique des données produits
        self.trend_cache = {}  # Cache des analyses de tendances
        
    def add_product_data(self, products: List[Dict[str, Any]], timestamp: datetime = None) -> None:
        """Ajoute des données produits pour l'analyse des tendances"""
        if timestamp is None:
            timestamp = datetime.now()
        
        data_entry = {
            'timestamp': timestamp.isoformat(),
            'datetime': timestamp,
            'products': products,
            'total_products': len(products)
        }
        
        self.product_data.append(data_entry)
        
        # Garde seulement les 30 derniers jours de données
        cutoff_date = datetime.now() - timedelta(days=30)
        self.product_data = [
            entry for entry in self.product_data 
            if entry['datetime'] >= cutoff_date
        ]
        
        # Vide le cache pour forcer le recalcul
        self.trend_cache.clear()
    
    def analyze_price_trends(self, platform: str = None, category: str = None, 
                           days: int = 7) -> Dict[str, Any]:
        """Analyse les tendances de prix générales"""
        cache_key = f"price_trends_{platform}_{category}_{days}"
        
        if cache_key in self.trend_cache:
            return self.trend_cache[cache_key]
        
        # Filtre les données par période
        cutoff_date = datetime.now() - timedelta(days=days)
        filtered_data = [
            entry for entry in self.product_data 
            if entry['datetime'] >= cutoff_date
        ]
        
        if not filtered_data:
            return {'trend': 'no_data', 'analysis': {}}
        
        # Filtre par plateforme et catégorie si spécifié
        relevant_products = []
        for entry in filtered_data:
            for product in entry['products']:
                if platform and product.get('platform') != platform:
                    continue
                if category and product.get('category') != category:
                    continue
                
                product_copy = product.copy()
                product_copy['analysis_timestamp'] = entry['datetime']
                relevant_products.append(product_copy)
        
        if not relevant_products:
            return {'trend': 'no_data', 'analysis': {}}
        
        analysis = self._analyze_price_patterns(relevant_products)
        
        self.trend_cache[cache_key] = analysis
        return analysis
    
    def _analyze_price_patterns(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Analyse les patterns de prix"""
        # Groupe par périodes (par jour)
        daily_data = defaultdict(list)
        
        for product in products:
            timestamp = product.get('analysis_timestamp')
            if timestamp:
                date_key = timestamp.date().isoformat()
                price = product.get('price', 0)
                if price > 0:
                    daily_data[date_key].append(price)
        
        if len(daily_data) < 2:
            return {'trend': 'insufficient_data', 'analysis': {}}
        
        # Calcule les moyennes quotidiennes
        daily_averages = {}
        for date, prices in daily_data.items():
            daily_averages[date] = statistics.mean(prices)
        
        # Analyse la tendance
        sorted_dates = sorted(daily_averages.keys())
        prices_timeline = [daily_averages[date] for date in sorted_dates]
        
        trend_analysis = self._calculate_price_trend(prices_timeline)
        
        # Statistiques additionnelles
        all_prices = [p for prices in daily_data.values() for p in prices]
        
        return {
            'trend': trend_analysis['direction'],
            'confidence': trend_analysis['confidence'],
            'analysis': {
                'daily_averages': daily_averages,
                'trend_strength': trend_analysis['strength'],
                'price_volatility': round(statistics.stdev(all_prices), 2) if len(all_prices) > 1 else 0,
                'min_price': min(all_prices),
                'max_price': max(all_prices),
                'avg_price': round(statistics.mean(all_prices), 2),
                'total_products_analyzed': len(products),
                'analysis_period_days': len(daily_data),
                'price_range': max(all_prices) - min(all_prices)
            }
        }
    
    def _calculate_price_trend(self, prices: List[float]) -> Dict[str, Any]:
        """Calcule la direction et la force d'une tendance de prix"""
        if len(prices) < 2:
            return {'direction': 'stable', 'strength': 0, 'confidence': 0}
        
        # Calcul de la tendance linéaire simple
        first_half = prices[:len(prices)//2]
        second_half = prices[len(prices)//2:]
        
        avg_first = statistics.mean(first_half)
        avg_second = statistics.mean(second_half)
        
        change = avg_second - avg_first
        percentage_change = (change / avg_first) * 100 if avg_first > 0 else 0
        
        # Détermine la direction
        if abs(percentage_change) < 1:
            direction = 'stable'
        elif percentage_change > 0:
            direction = 'increasing'
        else:
            direction = 'decreasing'
        
        # Calcule la force (0-100)
        strength = min(100, abs(percentage_change) * 10)
        
        # Calcule la confiance basée sur la cohérence
        confidence = self._calculate_trend_consistency(prices)
        
        return {
            'direction': direction,
            'strength': round(strength, 1),
            'confidence': confidence,
            'percentage_change': round(percentage_change, 2)
        }
    
    def _calculate_trend_consistency(self, prices: List[float]) -> float:
        """Calcule la cohérence d'une tendance (0-1)"""
        if len(prices) < 3:
            return 0.5
        
        # Calcule les changements directionnels
        changes = []
        for i in range(1, len(prices)):
            change = prices[i] - prices[i-1]
            if abs(change) > 0.01:  # Seuil minimal
                changes.append(1 if change > 0 else -1)
        
        if not changes:
            return 0.5
        
        # Calcule la cohérence directionnelle
        positive = sum(1 for c in changes if c > 0)
        negative = sum(1 for c in changes if c < 0)
        
        consistency = max(positive, negative) / len(changes)
        return round(consistency, 2)
    
    def analyze_availability_trends(self, platform: str = None, days: int = 7) -> Dict[str, Any]:
        """Analyse les tendances de disponibilité des produits"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        availability_data = defaultdict(list)
        
        for entry in self.product_data:
            if entry['datetime'] < cutoff_date:
                continue
            
            date_key = entry['datetime'].date().isoformat()
            
            for product in entry['products']:
                if platform and product.get('platform') != platform:
                    continue
                
                availability = product.get('availability', 'unknown')
                availability_data[date_key].append(availability)
        
        if not availability_data:
            return {'trend': 'no_data'}
        
        # Analyse les patterns de disponibilité
        daily_stats = {}
        for date, availabilities in availability_data.items():
            total = len(availabilities)
            in_stock = sum(1 for a in availabilities if a in ['in_stock', 'available', True])
            out_of_stock = sum(1 for a in availabilities if a in ['out_of_stock', 'unavailable', False])
            
            daily_stats[date] = {
                'total_products': total,
                'in_stock': in_stock,
                'out_of_stock': out_of_stock,
                'availability_rate': round((in_stock / total) * 100, 1) if total > 0 else 0
            }
        
        # Calcule la tendance de disponibilité
        sorted_dates = sorted(daily_stats.keys())
        availability_rates = [daily_stats[date]['availability_rate'] for date in sorted_dates]
        
        if len(availability_rates) >= 2:
            first_rate = statistics.mean(availability_rates[:len(availability_rates)//2])
            last_rate = statistics.mean(availability_rates[len(availability_rates)//2:])
            
            change = last_rate - first_rate
            
            if abs(change) < 2:
                trend = 'stable'
            elif change > 0:
                trend = 'improving'
            else:
                trend = 'declining'
        else:
            trend = 'stable'
        
        return {
            'trend': trend,
            'daily_statistics': daily_stats,
            'overall_availability_rate': round(statistics.mean(availability_rates), 1) if availability_rates else 0,
            'analysis_period_days': len(daily_stats)
        }
    
    def analyze_popular_products(self, platform: str = None, limit: int = 10) -> List[Dict[str, Any]]:
        """Analyse les produits populaires basés sur les ratings et reviews"""
        all_products = []
        
        for entry in self.product_data:
            for product in entry['products']:
                if platform and product.get('platform') != platform:
                    continue
                all_products.append(product)
        
        if not all_products:
            return []
        
        # Score de popularité basé sur rating et nombre de reviews
        scored_products = []
        
        for product in all_products:
            rating = product.get('rating', 0)
            reviews_count = product.get('reviews_count', 0)
            
            # Calcule un score de popularité
            if rating > 0 and reviews_count > 0:
                # Score = rating * log(reviews_count + 1)
                import math
                popularity_score = rating * math.log(reviews_count + 1)
                
                scored_products.append({
                    'product': product,
                    'popularity_score': popularity_score,
                    'rating': rating,
                    'reviews_count': reviews_count
                })
        
        # Trie par score de popularité
        scored_products.sort(key=lambda x: x['popularity_score'], reverse=True)
        
        return scored_products[:limit]
    
    def analyze_category_trends(self, days: int = 7) -> Dict[str, Any]:
        """Analyse les tendances par catégorie"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        category_data = defaultdict(lambda: {
            'products': [],
            'prices': [],
            'ratings': [],
            'availability': []
        })
        
        for entry in self.product_data:
            if entry['datetime'] < cutoff_date:
                continue
            
            for product in entry['products']:
                category = product.get('category', 'uncategorized')
                
                category_data[category]['products'].append(product)
                
                if product.get('price', 0) > 0:
                    category_data[category]['prices'].append(product['price'])
                
                if product.get('rating', 0) > 0:
                    category_data[category]['ratings'].append(product['rating'])
                
                availability = product.get('availability', 'unknown')
                category_data[category]['availability'].append(availability)
        
        # Analyse chaque catégorie
        category_analysis = {}
        
        for category, data in category_data.items():
            if not data['products']:
                continue
            
            analysis = {
                'total_products': len(data['products']),
                'avg_price': round(statistics.mean(data['prices']), 2) if data['prices'] else 0,
                'price_range': {
                    'min': min(data['prices']) if data['prices'] else 0,
                    'max': max(data['prices']) if data['prices'] else 0
                },
                'avg_rating': round(statistics.mean(data['ratings']), 2) if data['ratings'] else 0,
                'availability_rate': 0
            }
            
            # Calcule le taux de disponibilité
            if data['availability']:
                available_count = sum(
                    1 for a in data['availability'] 
                    if a in ['in_stock', 'available', True]
                )
                analysis['availability_rate'] = round(
                    (available_count / len(data['availability'])) * 100, 1
                )
            
            category_analysis[category] = analysis
        
        # Trie par nombre de produits
        try:
            sorted_categories = sorted(
                category_analysis.items(),
                key=lambda x: x[1].get('total_products', 0) if isinstance(x[1], dict) else 0,
                reverse=True
            )
        except Exception as e:
            logger.error(f"Erreur lors du tri des catégories: {e}")
            sorted_categories = list(category_analysis.items())
        
        return {
            'categories': dict(sorted_categories),
            'total_categories': len(category_analysis),
            'analysis_period_days': days
        }
    
    def analyze_platform_performance(self, days: int = 7) -> Dict[str, Any]:
        """Analyse les performances par plateforme"""
        cutoff_date = datetime.now() - timedelta(days=days)
        
        platform_data = defaultdict(lambda: {
            'products': [],
            'prices': [],
            'ratings': [],
            'availability': []
        })
        
        for entry in self.product_data:
            if entry['datetime'] < cutoff_date:
                continue
            
            for product in entry['products']:
                platform = product.get('platform', 'unknown')
                
                platform_data[platform]['products'].append(product)
                
                if product.get('price', 0) > 0:
                    platform_data[platform]['prices'].append(product['price'])
                
                if product.get('rating', 0) > 0:
                    platform_data[platform]['ratings'].append(product['rating'])
                
                availability = product.get('availability', 'unknown')
                platform_data[platform]['availability'].append(availability)
        
        # Analyse chaque plateforme
        platform_analysis = {}
        
        for platform, data in platform_data.items():
            if not data['products']:
                continue
            
            analysis = {
                'total_products': len(data['products']),
                'avg_price': round(statistics.mean(data['prices']), 2) if data['prices'] else 0,
                'price_competitiveness': 0,  # Sera calculé après
                'avg_rating': round(statistics.mean(data['ratings']), 2) if data['ratings'] else 0,
                'availability_rate': 0,
                'product_variety': len(set(p.get('title', '') for p in data['products']))
            }
            
            # Calcule le taux de disponibilité
            if data['availability']:
                available_count = sum(
                    1 for a in data['availability'] 
                    if a in ['in_stock', 'available', True]
                )
                analysis['availability_rate'] = round(
                    (available_count / len(data['availability'])) * 100, 1
                )
            
            platform_analysis[platform] = analysis
        
        # Calcule la compétitivité des prix
        all_avg_prices = [data['avg_price'] for data in platform_analysis.values() if data['avg_price'] > 0]
        
        if all_avg_prices:
            overall_avg = statistics.mean(all_avg_prices)
            
            for platform, analysis in platform_analysis.items():
                if analysis['avg_price'] > 0:
                    # Score de compétitivité: plus le prix est bas, plus le score est élevé
                    competitiveness = max(0, 100 - ((analysis['avg_price'] / overall_avg - 1) * 100))
                    analysis['price_competitiveness'] = round(competitiveness, 1)
        
        return {
            'platforms': platform_analysis,
            'total_platforms': len(platform_analysis),
            'analysis_period_days': days
        }
    
    def analyze(self, products: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Méthode principale d'analyse des tendances"""
        # Ajoute les données produits
        self.add_product_data(products)
        
        # Génère le rapport complet
        return self.generate_trend_report()
    
    def generate_trend_report(self, days: int = 7) -> Dict[str, Any]:
        """Génère un rapport complet des tendances"""
        report = {
            'report_generated_at': datetime.now().isoformat(),
            'analysis_period_days': days,
            'summary': {},
            'price_trends': {},
            'availability_trends': {},
            'popular_products': [],
            'category_analysis': {},
            'platform_performance': {}
        }
        
        try:
            # Analyse des tendances de prix globales
            report['price_trends'] = self.analyze_price_trends(days=days)
            
            # Analyse de disponibilité
            report['availability_trends'] = self.analyze_availability_trends(days=days)
            
            # Produits populaires
            report['popular_products'] = self.analyze_popular_products(limit=10)
            
            # Analyse par catégorie
            report['category_analysis'] = self.analyze_category_trends(days=days)
            
            # Performance des plateformes
            report['platform_performance'] = self.analyze_platform_performance(days=days)
            
            # Résumé exécutif
            total_products = sum(
                len(entry['products']) for entry in self.product_data
                if entry['datetime'] >= datetime.now() - timedelta(days=days)
            )
            
            report['summary'] = {
                'total_products_analyzed': total_products,
                'total_platforms': len(report['platform_performance'].get('platforms', {})),
                'total_categories': len(report['category_analysis'].get('categories', {})),
                'overall_price_trend': report['price_trends'].get('trend', 'unknown'),
                'overall_availability_trend': report['availability_trends'].get('trend', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"Erreur lors de la génération du rapport: {e}")
            report['error'] = str(e)
        
        return report
    
    def export_trends_data(self) -> Dict[str, Any]:
        """Exporte toutes les données de tendances"""
        return {
            'product_data_entries': len(self.product_data),
            'date_range': {
                'start': min(entry['timestamp'] for entry in self.product_data) if self.product_data else None,
                'end': max(entry['timestamp'] for entry in self.product_data) if self.product_data else None
            },
            'cache_entries': len(self.trend_cache),
            'total_products_tracked': sum(entry['total_products'] for entry in self.product_data)
        }