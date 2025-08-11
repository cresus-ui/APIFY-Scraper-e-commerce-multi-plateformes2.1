import asyncio
import json
import logging
import random
from typing import Dict, List, Any, Optional
from urllib.parse import urljoin, quote_plus

import aiohttp
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

logger = logging.getLogger(__name__)

class WalmartScraper:
    """Scraper spécialisé pour Walmart"""
    
    def __init__(self):
        self.base_url = "https://www.walmart.com"
        self.search_url = "https://www.walmart.com/search"
        self.ua = UserAgent()
        self.session = None
        
    async def _get_session(self) -> aiohttp.ClientSession:
        """Obtient une session HTTP configurée"""
        if not self.session:
            headers = {
                'User-Agent': self.ua.random,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Referer': 'https://www.walmart.com/'
            }
            
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
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
                    logger.warning("Rate limit atteint, attente...")
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
    
    def _parse_product_tile(self, tile_element) -> Optional[Dict[str, Any]]:
        """Parse un élément produit Walmart"""
        try:
            # Titre
            title_elem = tile_element.find('span', {'data-automation-id': 'product-title'})
            if not title_elem:
                title_elem = tile_element.find('a', class_='product-title-link')
            
            title = title_elem.get_text(strip=True) if title_elem else "N/A"
            
            # Prix
            price_info = self._extract_price(tile_element)
            
            # URL
            link_elem = tile_element.find('a', {'data-testid': 'product-title'})
            if not link_elem:
                link_elem = tile_element.find('a', class_='product-title-link')
            
            product_url = ""
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                if href.startswith('/'):
                    product_url = urljoin(self.base_url, href)
                else:
                    product_url = href
            
            # Image
            img_elem = tile_element.find('img', {'data-testid': 'productTileImage'})
            if not img_elem:
                img_elem = tile_element.find('img')
            
            image_url = img_elem.get('src', '') if img_elem else ''
            
            # Rating
            rating = self._extract_rating(tile_element)
            
            # Nombre d'avis
            reviews_count = self._extract_reviews_count(tile_element)
            
            # Disponibilité
            availability = self._extract_availability(tile_element)
            
            # Vendeur (Walmart ou tiers)
            seller = self._extract_seller(tile_element)
            
            # Livraison
            shipping_info = self._extract_shipping_info(tile_element)
            
            # ID produit
            product_id = self._extract_product_id(tile_element, product_url)
            
            return {
                'title': title,
                'price': price_info['current'],
                'original_price': price_info['original'],
                'currency': price_info['currency'],
                'url': product_url,
                'image_url': image_url,
                'rating': rating,
                'reviews_count': reviews_count,
                'availability': availability,
                'seller': seller,
                'shipping': shipping_info,
                'product_id': product_id,
                'platform': 'walmart'
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing d'un produit Walmart: {str(e)}")
            return None
    
    def _extract_price(self, element) -> Dict[str, Any]:
        """Extrait les informations de prix"""
        price_info = {'current': 0, 'original': 0, 'currency': 'USD'}
        
        # Prix actuel
        current_price_elem = element.find('span', {'itemprop': 'price'})
        if not current_price_elem:
            current_price_elem = element.find('span', class_='price-current')
        if not current_price_elem:
            current_price_elem = element.find('div', {'data-testid': 'price-current'})
        
        if current_price_elem:
            price_text = current_price_elem.get_text(strip=True)
            price_info['current'] = self._parse_price_text(price_text)
            price_info['original'] = price_info['current']
        
        # Prix original (barré)
        original_price_elem = element.find('span', class_='price-was')
        if not original_price_elem:
            original_price_elem = element.find('div', {'data-testid': 'price-was'})
        
        if original_price_elem:
            original_text = original_price_elem.get_text(strip=True)
            original_value = self._parse_price_text(original_text)
            if original_value > price_info['current']:
                price_info['original'] = original_value
        
        return price_info
    
    def _parse_price_text(self, price_text: str) -> float:
        """Parse le texte du prix en valeur numérique"""
        try:
            import re
            # Supprime tout sauf les chiffres, points et virgules
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
    
    def _extract_rating(self, element) -> float:
        """Extrait la note du produit"""
        rating_elem = element.find('span', class_='average-rating')
        if not rating_elem:
            rating_elem = element.find('div', {'data-testid': 'reviews-section'})
        
        if rating_elem:
            rating_text = rating_elem.get_text(strip=True)
            try:
                import re
                match = re.search(r'(\d+\.\d+)', rating_text)
                if match:
                    return float(match.group(1))
            except:
                pass
        return 0.0
    
    def _extract_reviews_count(self, element) -> int:
        """Extrait le nombre d'avis"""
        reviews_elem = element.find('span', class_='review-count')
        if not reviews_elem:
            reviews_elem = element.find('a', {'data-testid': 'reviews-link'})
        
        if reviews_elem:
            reviews_text = reviews_elem.get_text(strip=True)
            try:
                import re
                match = re.search(r'([\d,]+)', reviews_text)
                if match:
                    return int(match.group(1).replace(',', ''))
            except:
                pass
        return 0
    
    def _extract_availability(self, element) -> str:
        """Extrait l'information de disponibilité"""
        # Cherche les indicateurs de stock
        stock_indicators = [
            'in-stock',
            'out-of-stock',
            'limited-stock'
        ]
        
        for indicator in stock_indicators:
            stock_elem = element.find(class_=indicator)
            if stock_elem:
                if 'out-of-stock' in indicator:
                    return 'out_of_stock'
                elif 'limited' in indicator:
                    return 'limited_stock'
                else:
                    return 'in_stock'
        
        # Cherche dans le texte
        availability_elem = element.find('div', {'data-testid': 'fulfillment-speed'})
        if availability_elem:
            availability_text = availability_elem.get_text(strip=True).lower()
            if 'out of stock' in availability_text:
                return 'out_of_stock'
            elif 'in stock' in availability_text or 'available' in availability_text:
                return 'in_stock'
        
        return 'unknown'
    
    def _extract_seller(self, element) -> str:
        """Extrait l'information du vendeur"""
        seller_elem = element.find('span', {'data-testid': 'fulfillment-speed'})
        if not seller_elem:
            seller_elem = element.find('div', class_='seller-name')
        
        if seller_elem:
            seller_text = seller_elem.get_text(strip=True)
            if 'walmart' in seller_text.lower():
                return 'walmart'
            else:
                return 'third_party'
        
        return 'walmart'  # Par défaut
    
    def _extract_shipping_info(self, element) -> Dict[str, str]:
        """Extrait les informations de livraison"""
        shipping_info = {'speed': '', 'cost': ''}
        
        shipping_elem = element.find('div', {'data-testid': 'fulfillment-speed'})
        if shipping_elem:
            shipping_text = shipping_elem.get_text(strip=True)
            shipping_info['speed'] = shipping_text
            
            # Détecte la livraison gratuite
            if 'free' in shipping_text.lower():
                shipping_info['cost'] = 'free'
        
        return shipping_info
    
    def _extract_product_id(self, element, product_url: str) -> str:
        """Extrait l'ID du produit"""
        # Essaie d'extraire de l'URL
        import re
        if product_url:
            match = re.search(r'/ip/[^/]+/(\d+)', product_url)
            if match:
                return match.group(1)
        
        # Essaie d'extraire des attributs data
        product_id = element.get('data-item-id')
        if product_id:
            return product_id
        
        return ''
    
    async def search_products(self, search_term: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """Recherche des produits sur Walmart"""
        products = []
        
        for page in range(1, max_pages + 1):
            logger.info(f"Scraping Walmart page {page} pour '{search_term}'")
            
            params = {
                'q': search_term,
                'page': page,
                'sort': 'best_match'
            }
            
            html = await self._make_request(self.search_url, params)
            if not html:
                logger.warning(f"Impossible de récupérer la page {page}")
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Trouve les conteneurs de produits
            product_tiles = soup.find_all('div', {'data-testid': 'item-stack'})
            if not product_tiles:
                product_tiles = soup.find_all('div', class_='search-result-gridview-item')
            
            if not product_tiles:
                logger.warning(f"Aucun produit trouvé sur la page {page}")
                break
            
            page_products = 0
            for tile in product_tiles:
                product = self._parse_product_tile(tile)
                if product and product['title'] != "N/A":
                    products.append(product)
                    page_products += 1
            
            logger.info(f"Page {page}: {page_products} produits trouvés")
            
            # Délai entre les pages
            await asyncio.sleep(random.uniform(2, 4))
        
        return products
    
    async def scrape(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Point d'entrée principal pour le scraping Walmart"""
        search_terms = config.get('search_terms', ['laptop'])
        max_pages = config.get('max_pages', 5)
        
        all_products = []
        
        try:
            for term in search_terms:
                logger.info(f"Début de la recherche Walmart pour: {term}")
                products = await self.search_products(term, max_pages)
                
                # Ajoute le terme de recherche aux métadonnées
                for product in products:
                    product['search_term'] = term
                
                all_products.extend(products)
                
                # Délai entre les termes de recherche
                if len(search_terms) > 1:
                    await asyncio.sleep(random.uniform(3, 5))
            
            logger.info(f"Scraping Walmart terminé: {len(all_products)} produits")
            return all_products
            
        except Exception as e:
            logger.error(f"Erreur lors du scraping Walmart: {str(e)}")
            return all_products
        
        finally:
            if self.session:
                await self.session.close()
                self.session = None