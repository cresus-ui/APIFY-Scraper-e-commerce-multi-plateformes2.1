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

class EbayScraper:
    """Scraper spécialisé pour eBay"""
    
    def __init__(self):
        self.base_url = "https://www.ebay.com"
        self.search_url = "https://www.ebay.com/sch/i.html"
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
                'Connection': 'keep-alive'
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
                else:
                    logger.warning(f"Statut HTTP {response.status} pour {url}")
                    return None
                    
        except asyncio.TimeoutError:
            logger.error(f"Timeout pour {url}")
            return None
        except Exception as e:
            logger.error(f"Erreur lors de la requête {url}: {str(e)}")
            return None
    
    def _parse_product_item(self, item_element) -> Optional[Dict[str, Any]]:
        """Parse un élément produit eBay"""
        try:
            # Titre
            title_elem = item_element.find('h3', class_='s-item__title')
            if not title_elem:
                title_elem = item_element.find('a', class_='s-item__link')
            
            title = title_elem.get_text(strip=True) if title_elem else "N/A"
            
            # Supprime les préfixes eBay
            if title.startswith('New Listing'):
                title = title.replace('New Listing', '').strip()
            
            # Prix
            price_info = self._extract_price(item_element)
            
            # URL
            link_elem = item_element.find('a', class_='s-item__link')
            item_url = link_elem.get('href', '') if link_elem else ''
            
            # Image
            img_elem = item_element.find('img', class_='s-item__image')
            image_url = img_elem.get('src', '') if img_elem else ''
            
            # Condition
            condition = self._extract_condition(item_element)
            
            # Type de vente (enchère ou achat immédiat)
            sale_type = self._extract_sale_type(item_element)
            
            # Temps restant pour les enchères
            time_left = self._extract_time_left(item_element)
            
            # Nombre d'enchères
            bid_count = self._extract_bid_count(item_element)
            
            # Vendeur
            seller_info = self._extract_seller_info(item_element)
            
            # Livraison
            shipping_info = self._extract_shipping_info(item_element)
            
            # ID de l'item
            item_id = self._extract_item_id(item_element, item_url)
            
            return {
                'title': title,
                'price': price_info['current'],
                'original_price': price_info['original'],
                'currency': price_info['currency'],
                'url': item_url,
                'image_url': image_url,
                'condition': condition,
                'sale_type': sale_type,
                'time_left': time_left,
                'bid_count': bid_count,
                'seller': seller_info,
                'shipping': shipping_info,
                'item_id': item_id,
                'platform': 'ebay'
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing d'un item eBay: {str(e)}")
            return None
    
    def _extract_price(self, element) -> Dict[str, Any]:
        """Extrait les informations de prix"""
        price_info = {'current': 0, 'original': 0, 'currency': 'USD'}
        
        # Prix principal
        price_elem = element.find('span', class_='s-item__price')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            
            # Gère les plages de prix (ex: "$10.00 to $20.00")
            if ' to ' in price_text:
                prices = price_text.split(' to ')
                if len(prices) == 2:
                    price_info['current'] = self._parse_price_text(prices[0])
                    price_info['original'] = self._parse_price_text(prices[1])
                else:
                    price_info['current'] = self._parse_price_text(price_text)
            else:
                price_info['current'] = self._parse_price_text(price_text)
                price_info['original'] = price_info['current']
            
            # Détecte la devise
            if '$' in price_text:
                price_info['currency'] = 'USD'
            elif '€' in price_text:
                price_info['currency'] = 'EUR'
            elif '£' in price_text:
                price_info['currency'] = 'GBP'
        
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
    
    def _extract_condition(self, element) -> str:
        """Extrait la condition de l'item"""
        condition_elem = element.find('span', class_='SECONDARY_INFO')
        if condition_elem:
            condition_text = condition_elem.get_text(strip=True).lower()
            if 'new' in condition_text:
                return 'new'
            elif 'used' in condition_text:
                return 'used'
            elif 'refurbished' in condition_text:
                return 'refurbished'
        return 'unknown'
    
    def _extract_sale_type(self, element) -> str:
        """Détermine le type de vente"""
        # Cherche les indicateurs d'enchère
        bid_elem = element.find('span', class_='s-item__bids')
        if bid_elem:
            return 'auction'
        
        # Cherche "Buy It Now"
        buy_now_elem = element.find('span', class_='s-item__purchase-options')
        if buy_now_elem and 'buy it now' in buy_now_elem.get_text().lower():
            return 'buy_it_now'
        
        return 'fixed_price'
    
    def _extract_time_left(self, element) -> str:
        """Extrait le temps restant pour les enchères"""
        time_elem = element.find('span', class_='s-item__time-left')
        if time_elem:
            return time_elem.get_text(strip=True)
        return ''
    
    def _extract_bid_count(self, element) -> int:
        """Extrait le nombre d'enchères"""
        bid_elem = element.find('span', class_='s-item__bids')
        if bid_elem:
            bid_text = bid_elem.get_text(strip=True)
            try:
                import re
                match = re.search(r'(\d+)', bid_text)
                if match:
                    return int(match.group(1))
            except:
                pass
        return 0
    
    def _extract_seller_info(self, element) -> Dict[str, str]:
        """Extrait les informations du vendeur"""
        seller_info = {'name': '', 'feedback': '', 'location': ''}
        
        seller_elem = element.find('span', class_='s-item__seller-info-text')
        if seller_elem:
            seller_info['name'] = seller_elem.get_text(strip=True)
        
        # Feedback du vendeur
        feedback_elem = element.find('span', class_='s-item__seller-info')
        if feedback_elem:
            feedback_text = feedback_elem.get_text(strip=True)
            seller_info['feedback'] = feedback_text
        
        return seller_info
    
    def _extract_shipping_info(self, element) -> Dict[str, str]:
        """Extrait les informations de livraison"""
        shipping_info = {'cost': '', 'location': ''}
        
        shipping_elem = element.find('span', class_='s-item__shipping')
        if shipping_elem:
            shipping_text = shipping_elem.get_text(strip=True)
            shipping_info['cost'] = shipping_text
        
        location_elem = element.find('span', class_='s-item__location')
        if location_elem:
            shipping_info['location'] = location_elem.get_text(strip=True)
        
        return shipping_info
    
    def _extract_item_id(self, element, item_url: str) -> str:
        """Extrait l'ID de l'item"""
        # Essaie d'extraire de l'URL
        import re
        if item_url:
            match = re.search(r'/itm/(\d+)', item_url)
            if match:
                return match.group(1)
        
        # Essaie d'extraire des attributs data
        item_id = element.get('data-itemid')
        if item_id:
            return item_id
        
        return ''
    
    async def search_products(self, search_term: str, max_pages: int = 5, condition: str = 'all') -> List[Dict[str, Any]]:
        """Recherche des produits sur eBay"""
        products = []
        
        for page in range(1, max_pages + 1):
            logger.info(f"Scraping eBay page {page} pour '{search_term}'")
            
            params = {
                '_nkw': search_term,
                '_pgn': page,
                '_skc': 0,
                'rt': 'nc'
            }
            
            # Filtre par condition si spécifié
            if condition != 'all':
                condition_map = {
                    'new': '1000',
                    'used': '3000',
                    'refurbished': '2500'
                }
                if condition in condition_map:
                    params['LH_ItemCondition'] = condition_map[condition]
            
            html = await self._make_request(self.search_url, params)
            if not html:
                logger.warning(f"Impossible de récupérer la page {page}")
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Trouve les items
            item_containers = soup.find_all('div', class_='s-item__wrapper')
            
            if not item_containers:
                logger.warning(f"Aucun item trouvé sur la page {page}")
                break
            
            page_products = 0
            for container in item_containers:
                item = self._parse_product_item(container)
                if item and item['title'] != "N/A":
                    products.append(item)
                    page_products += 1
            
            logger.info(f"Page {page}: {page_products} items trouvés")
            
            # Délai entre les pages
            await asyncio.sleep(random.uniform(1, 3))
        
        return products
    
    async def scrape(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Point d'entrée principal pour le scraping eBay"""
        search_terms = config.get('search_terms', ['laptop'])
        max_pages = config.get('max_pages', 5)
        condition = config.get('condition', 'all')
        
        all_products = []
        
        try:
            for term in search_terms:
                logger.info(f"Début de la recherche eBay pour: {term}")
                products = await self.search_products(term, max_pages, condition)
                
                # Ajoute le terme de recherche aux métadonnées
                for product in products:
                    product['search_term'] = term
                    product['condition_filter'] = condition
                
                all_products.extend(products)
                
                # Délai entre les termes de recherche
                if len(search_terms) > 1:
                    await asyncio.sleep(random.uniform(2, 4))
            
            logger.info(f"Scraping eBay terminé: {len(all_products)} items")
            return all_products
            
        except Exception as e:
            logger.error(f"Erreur lors du scraping eBay: {str(e)}")
            return all_products
        
        finally:
            if self.session:
                await self.session.close()
                self.session = None