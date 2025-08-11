import asyncio
import json
import logging
import random
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, quote_plus, urlparse

import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

class ShopifyScraper:
    """Scraper spécialisé pour les boutiques Shopify"""
    
    def __init__(self):
        self.ua = UserAgent()
        self.session = None
        self.shopify_stores = [
            'https://shop.tesla.com',
            'https://www.allbirds.com',
            'https://www.gymshark.com',
            'https://www.bombas.com',
            'https://www.away.com'
        ]
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtient une session HTTP configurée"""
        if not self.session:
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive'
            }
            
            connector = aiohttp.TCPConnector(
                limit=8,
                limit_per_host=4,
                ttl_dns_cache=300
            )
            
            timeout = aiohttp.ClientTimeout(total=30, connect=10)
            
            self.session = aiohttp.ClientSession(
                headers=headers,
                connector=connector,
                timeout=timeout
            )
        
        return self.session
    
    async def _make_request(self, url: str, params: Dict = None) -> Optional[str]:
        """Effectue une requête HTTP avec gestion d'erreurs"""
        session = await self._get_session()
        
        try:
            await asyncio.sleep(random.uniform(1, 2))
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 429:
                    logger.warning(f"Rate limit atteint pour {url}, attente...")
                    await asyncio.sleep(random.uniform(5, 10))
                    return None
                else:
                    logger.warning(f"Statut HTTP {response.status} pour {url}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout pour {url}")
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la requête {url}: {str(e)}")
            return None
    
    async def _get_shopify_products_api(self, store_url: str, search_term: str = None) -> List[Dict[str, Any]]:
        """Utilise l'API Shopify pour récupérer les produits"""
        products = []
        
        try:
            # URL de l'API produits Shopify
            api_url = f"{store_url.rstrip('/')}/products.json"
            
            params = {'limit': 250}
            if search_term:
                # Shopify ne supporte pas la recherche via l'API publique
                # On récupère tous les produits et on filtre
                pass
            
            html = await self._make_request(api_url, params)
            if not html:
                return products
            
            data = json.loads(html)
            
            for product_data in data.get('products', []):
                product = self._parse_shopify_api_product(product_data, store_url)
                if product:
                    # Filtre par terme de recherche si spécifié
                    if not search_term or search_term.lower() in product['title'].lower():
                        products.append(product)
            
            logger.info(f"API Shopify {store_url}: {len(products)} produits récupérés")
            
        except json.JSONDecodeError:
            logger.error(f"Réponse JSON invalide de {api_url}")
        except Exception as e:
            logger.error(f"Erreur API Shopify pour {store_url}: {str(e)}")
        
        return products
    
    def _parse_shopify_api_product(self, product_data: Dict, store_url: str) -> Optional[Dict[str, Any]]:
        """Parse un produit depuis l'API Shopify"""
        try:
            # Informations de base
            title = product_data.get('title', '')
            handle = product_data.get('handle', '')
            product_id = product_data.get('id', '')
            
            # URL du produit
            product_url = f"{store_url.rstrip('/')}/products/{handle}"
            
            # Variants (différentes options du produit)
            variants = product_data.get('variants', [])
            
            # Prix (prend le premier variant)
            price = 0
            compare_price = 0
            if variants:
                first_variant = variants[0]
                price = float(first_variant.get('price', 0))
                compare_price = float(first_variant.get('compare_at_price', 0) or 0)
            
            # Images
            images = product_data.get('images', [])
            image_url = images[0].get('src', '') if images else ''
            
            # Description
            description = product_data.get('body_html', '')
            
            # Tags
            tags = product_data.get('tags', [])
            if isinstance(tags, str):
                tags = [tag.strip() for tag in tags.split(',')]
            
            # Disponibilité
            available = product_data.get('available', False)
            
            # Vendor
            vendor = product_data.get('vendor', '')
            
            # Type de produit
            product_type = product_data.get('product_type', '')
            
            return {
                'title': title,
                'price': price,
                'original_price': compare_price if compare_price > price else price,
                'currency': 'USD',  # Par défaut, pourrait être détecté
                'url': product_url,
                'image_url': image_url,
                'description': description,
                'tags': tags,
                'available': available,
                'vendor': vendor,
                'product_type': product_type,
                'variants_count': len(variants),
                'product_id': str(product_id),
                'store_url': store_url,
                'platform': 'shopify'
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing d'un produit Shopify API: {str(e)}")
            return None
    
    async def _scrape_shopify_html(self, store_url: str, search_term: str = None) -> List[Dict[str, Any]]:
        """Scrape une boutique Shopify via HTML (fallback)"""
        products = []
        
        try:
            # Essaie différentes URLs de collection
            collection_urls = [
                f"{store_url.rstrip('/')}/collections/all",
                f"{store_url.rstrip('/')}/collections/featured",
                f"{store_url.rstrip('/')}/products"
            ]
            
            for collection_url in collection_urls:
                html = await self._make_request(collection_url)
                if not html:
                    continue
                
                soup = BeautifulSoup(html, 'html.parser')
                
                # Cherche les produits dans différents sélecteurs communs
                product_selectors = [
                    '.product-item',
                    '.product-card',
                    '.grid-product',
                    '.product',
                    '[data-product-id]'
                ]
                
                product_elements = []
                for selector in product_selectors:
                    elements = soup.select(selector)
                    if elements:
                        product_elements = elements
                        break
                
                if not product_elements:
                    continue
                
                for element in product_elements:
                    product = self._parse_shopify_html_product(element, store_url)
                    if product:
                        # Filtre par terme de recherche si spécifié
                        if not search_term or search_term.lower() in product['title'].lower():
                            products.append(product)
                
                # Si on a trouvé des produits, on s'arrête
                if products:
                    break
            
            logger.info(f"HTML Shopify {store_url}: {len(products)} produits récupérés")
            
        except Exception as e:
            logger.error(f"Erreur scraping HTML Shopify pour {store_url}: {str(e)}")
        
        return products
    
    def _parse_shopify_html_product(self, element, store_url: str) -> Optional[Dict[str, Any]]:
        """Parse un produit depuis le HTML Shopify"""
        try:
            # Titre
            title_selectors = ['.product-title', '.product-name', 'h3', 'h2', '.title']
            title = ""
            for selector in title_selectors:
                title_elem = element.select_one(selector)
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    break
            
            # Prix
            price_info = self._extract_shopify_price(element)
            
            # URL
            link_elem = element.find('a')
            product_url = ""
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                if href.startswith('/'):
                    product_url = urljoin(store_url, href)
                else:
                    product_url = href
            
            # Image
            img_elem = element.find('img')
            image_url = ""
            if img_elem:
                src = img_elem.get('src') or img_elem.get('data-src')
                if src:
                    if src.startswith('//'):
                        image_url = 'https:' + src
                    elif src.startswith('/'):
                        image_url = urljoin(store_url, src)
                    else:
                        image_url = src
            
            # Disponibilité
            availability = self._extract_shopify_availability(element)
            
            # Vendor/Brand
            vendor = self._extract_shopify_vendor(element)
            
            return {
                'title': title,
                'price': price_info['current'],
                'original_price': price_info['original'],
                'currency': price_info['currency'],
                'url': product_url,
                'image_url': image_url,
                'available': availability,
                'vendor': vendor,
                'store_url': store_url,
                'platform': 'shopify'
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing d'un produit Shopify HTML: {str(e)}")
            return None
    
    def _extract_shopify_price(self, element) -> Dict[str, Any]:
        """Extrait les informations de prix Shopify"""
        price_info = {'current': 0, 'original': 0, 'currency': 'USD'}
        
        # Sélecteurs de prix communs
        price_selectors = ['.price', '.product-price', '.money', '.price-current']
        
        for selector in price_selectors:
            price_elem = element.select_one(selector)
            if price_elem:
                price_text = price_elem.get_text(strip=True)
                price_info['current'] = self._parse_price_text(price_text)
                price_info['original'] = price_info['current']
                
                # Détecte la devise
                if '$' in price_text:
                    price_info['currency'] = 'USD'
                elif '€' in price_text:
                    price_info['currency'] = 'EUR'
                elif '£' in price_text:
                    price_info['currency'] = 'GBP'
                break
        
        # Prix original (barré)
        original_selectors = ['.price-compare', '.was-price', '.compare-at-price']
        for selector in original_selectors:
            original_elem = element.select_one(selector)
            if original_elem:
                original_text = original_elem.get_text(strip=True)
                original_value = self._parse_price_text(original_text)
                if original_value > price_info['current']:
                    price_info['original'] = original_value
                break
        
        return price_info
    
    def _parse_price_text(self, price_text: str) -> float:
        """Parse le texte du prix en valeur numérique"""
        try:
            import re
            cleaned = re.sub(r'[^\d.,]', '', price_text)
            
            if ',' in cleaned and '.' in cleaned:
                cleaned = cleaned.replace(',', '')
            elif ',' in cleaned:
                if len(cleaned.split(',')[1]) == 2:
                    cleaned = cleaned.replace(',', '.')
                else:
                    cleaned = cleaned.replace(',', '')
            
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0
    
    def _extract_shopify_availability(self, element) -> bool:
        """Extrait la disponibilité du produit"""
        # Cherche les indicateurs de stock
        availability_indicators = ['.sold-out', '.out-of-stock', '.unavailable']
        
        for indicator in availability_indicators:
            if element.select_one(indicator):
                return False
        
        # Cherche les indicateurs de disponibilité
        available_indicators = ['.in-stock', '.available', '.add-to-cart']
        
        for indicator in available_indicators:
            if element.select_one(indicator):
                return True
        
        return True  # Par défaut, considère comme disponible
    
    def _extract_shopify_vendor(self, element) -> str:
        """Extrait le vendor/brand du produit"""
        vendor_selectors = ['.vendor', '.brand', '.product-vendor']
        
        for selector in vendor_selectors:
            vendor_elem = element.select_one(selector)
            if vendor_elem:
                return vendor_elem.get_text(strip=True)
        
        return ''
    
    async def scrape_store(self, store_url: str, search_term: str = None) -> List[Dict[str, Any]]:
        """Scrape une boutique Shopify spécifique"""
        logger.info(f"Scraping boutique Shopify: {store_url}")
        
        # Essaie d'abord l'API
        products = await self._get_shopify_products_api(store_url, search_term)
        
        # Si l'API ne fonctionne pas, utilise le scraping HTML
        if not products:
            products = await self._scrape_shopify_html(store_url, search_term)
        
        return products
    
    async def scrape(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Point d'entrée principal pour le scraping Shopify"""
        search_terms = config.get('search_terms', [''])
        custom_stores = config.get('shopify_stores', [])
        max_stores = config.get('max_stores', 3)
        
        # Combine les boutiques par défaut et personnalisées
        stores_to_scrape = (custom_stores + self.shopify_stores)[:max_stores]
        
        all_products = []
        
        try:
            for store_url in stores_to_scrape:
                logger.info(f"Début du scraping pour la boutique: {store_url}")
                
                for search_term in search_terms:
                    products = await self.scrape_store(store_url, search_term)
                    
                    # Ajoute les métadonnées
                    for product in products:
                        product['search_term'] = search_term
                        product['store_domain'] = urlparse(store_url).netloc
                    
                    all_products.extend(products)
                    
                    # Délai entre les termes de recherche
                    if len(search_terms) > 1:
                        await asyncio.sleep(random.uniform(2, 4))
                
                # Délai entre les boutiques
                await asyncio.sleep(random.uniform(3, 6))
            
            logger.info(f"Scraping Shopify terminé: {len(all_products)} produits")
            return all_products
            
        except Exception as e:
            logger.error(f"Erreur lors du scraping Shopify: {str(e)}")
            return all_products
        
        finally:
            if self.session:
                await self.session.close()
                self.session = None