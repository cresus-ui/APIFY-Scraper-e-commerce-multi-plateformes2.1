#!/usr/bin/env python3
"""
Scraper e-commerce multi-plateformes pour Apify
Supporte: Amazon, eBay, Walmart, Etsy, Shopify
Fonctionnalités: Suivi des prix, stocks, tendances
"""

import asyncio
import json
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime

from apify import Actor
from apify_client import ApifyClient
from scrapy import Spider
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings

from scrapers.amazon_scraper import AmazonScraper
from scrapers.ebay_scraper import EbayScraper
from scrapers.walmart_scraper import WalmartScraper
from scrapers.etsy_scraper import EtsyScraper
from scrapers.shopify_scraper import ShopifyScraper
from utils.data_processor import DataProcessor
from utils.price_tracker import PriceTracker
from utils.trend_analyzer import TrendAnalyzer

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class MultiPlatformEcommerceScraper:
    """Scraper principal pour toutes les plateformes e-commerce"""
    
    def __init__(self):
        self.scrapers = {
            'amazon': AmazonScraper(),
            'ebay': EbayScraper(),
            'walmart': WalmartScraper(),
            'etsy': EtsyScraper(),
            'shopify': ShopifyScraper()
        }
        self.data_processor = DataProcessor()
        self.price_tracker = PriceTracker()
        self.trend_analyzer = TrendAnalyzer()
        
    async def scrape_platform(self, platform: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Scrape une plateforme spécifique"""
        if platform not in self.scrapers:
            raise ValueError(f"Plateforme non supportée: {platform}")
            
        logger.info(f"Début du scraping pour {platform}")
        scraper = self.scrapers[platform]
        
        try:
            results = await scraper.scrape(config)
            logger.info(f"Scraping terminé pour {platform}: {len(results)} produits trouvés")
            return results
        except Exception as e:
            logger.error(f"Erreur lors du scraping de {platform}: {str(e)}")
            return []
    
    async def scrape_all_platforms(self, input_data: Dict[str, Any]) -> Dict[str, List[Dict[str, Any]]]:
        """Scrape toutes les plateformes configurées"""
        results = {}
        platforms = input_data.get('platforms', ['amazon', 'ebay', 'walmart', 'etsy'])
        
        tasks = []
        for platform in platforms:
            if platform in input_data.get('platform_configs', {}):
                config = input_data['platform_configs'][platform]
                task = self.scrape_platform(platform, config)
                tasks.append((platform, task))
        
        # Exécution parallèle des scrapers
        for platform, task in tasks:
            try:
                platform_results = await task
                results[platform] = platform_results
            except Exception as e:
                logger.error(f"Erreur pour {platform}: {str(e)}")
                results[platform] = []
        
        return results
    
    def analyze_trends(self, all_results: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Analyse les tendances à travers toutes les plateformes"""
        logger.info("Analyse des tendances en cours...")
        
        # Consolidation des données
        all_products = []
        for platform, products in all_results.items():
            for product in products:
                product['platform'] = platform
                all_products.append(product)
        
        # Analyse des tendances
        trends = self.trend_analyzer.analyze(all_products)
        
        return {
            'total_products': len(all_products),
            'platforms_scraped': list(all_results.keys()),
            'price_trends': trends.get('price_trends', {}),
            'stock_analysis': trends.get('stock_analysis', {}),
            'popular_categories': trends.get('popular_categories', []),
            'timestamp': datetime.now().isoformat()
        }

async def main():
    """Fonction principale de l'actor Apify"""
    async with Actor:
        # Récupération des inputs
        actor_input = await Actor.get_input() or {}
        logger.info(f"Input reçu: {json.dumps(actor_input, indent=2)}")
        
        # Configuration par défaut
        default_config = {
            'platforms': ['amazon', 'ebay', 'walmart', 'etsy'],
            'max_products_per_platform': 100,
            'track_prices': True,
            'analyze_trends': True,
            'platform_configs': {
                'amazon': {
                    'search_terms': actor_input.get('search_terms', ['laptop']),
                    'max_pages': actor_input.get('max_pages', 5),
                    'include_reviews': actor_input.get('include_reviews', False)
                },
                'ebay': {
                    'search_terms': actor_input.get('search_terms', ['laptop']),
                    'condition': actor_input.get('condition', 'all'),
                    'max_pages': actor_input.get('max_pages', 5)
                },
                'walmart': {
                    'search_terms': actor_input.get('search_terms', ['laptop']),
                    'max_pages': actor_input.get('max_pages', 5)
                },
                'etsy': {
                    'search_terms': actor_input.get('search_terms', ['handmade']),
                    'max_pages': actor_input.get('max_pages', 3)
                }
            }
        }
        
        # Fusion avec la configuration utilisateur
        config = {**default_config, **actor_input}
        
        # Initialisation du scraper
        scraper = MultiPlatformEcommerceScraper()
        
        try:
            # Scraping de toutes les plateformes
            results = await scraper.scrape_all_platforms(config)
            
            # Analyse des tendances si demandée
            analysis = None
            if config.get('analyze_trends', True):
                analysis = scraper.analyze_trends(results)
            
            # Préparation des résultats finaux
            final_results = {
                'scraping_results': results,
                'trend_analysis': analysis,
                'metadata': {
                    'scraping_timestamp': datetime.now().isoformat(),
                    'platforms_requested': config['platforms'],
                    'total_products_found': sum(len(products) for products in results.values())
                }
            }
            
            # Sauvegarde des résultats individuels par plateforme
            for platform, products in results.items():
                for product in products:
                    await Actor.push_data({
                        'platform': platform,
                        'product_data': product,
                        'scraped_at': datetime.now().isoformat()
                    })
            
            # Sauvegarde de l'analyse globale
            if analysis:
                await Actor.push_data({
                    'type': 'trend_analysis',
                    'analysis': analysis
                })
            
            logger.info(f"Scraping terminé avec succès. Total: {final_results['metadata']['total_products_found']} produits")
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution: {str(e)}")
            await Actor.fail()

if __name__ == '__main__':
    asyncio.run(main())