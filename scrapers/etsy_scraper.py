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

class EtsyScraper:
    """Scraper spécialisé pour Etsy"""
    
    def __init__(self):
        self.base_url = "https://www.etsy.com"
        self.search_url = "https://www.etsy.com/search"
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
                'Referer': 'https://www.etsy.com/'
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
            await asyncio.sleep(random.uniform(1, 3))
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 429:
                    logger.warning("Rate limit Etsy atteint, attente...")
                    await asyncio.sleep(random.uniform(10, 20))
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
    
    def _parse_listing_card(self, card_element) -> Optional[Dict[str, Any]]:
        """Parse un élément produit Etsy"""
        try:
            # Titre
            title_elem = card_element.find('h3', class_='v2-listing-card__title')
            if not title_elem:
                title_elem = card_element.find('a', {'data-test-id': 'listing-link'})
            
            title = title_elem.get_text(strip=True) if title_elem else "N/A"
            
            # Prix
            price_info = self._extract_price(card_element)
            
            # URL
            link_elem = card_element.find('a', {'data-test-id': 'listing-link'})
            if not link_elem:
                link_elem = card_element.find('a', class_='listing-link')
            
            listing_url = ""
            if link_elem and link_elem.get('href'):
                href = link_elem['href']
                if href.startswith('/'):
                    listing_url = urljoin(self.base_url, href)
                else:
                    listing_url = href
            
            # Image
            img_elem = card_element.find('img', class_='listing-page-image')
            if not img_elem:
                img_elem = card_element.find('img')
            
            image_url = img_elem.get('src', '') if img_elem else ''
            
            # Rating
            rating = self._extract_rating(card_element)
            
            # Nombre d'avis
            reviews_count = self._extract_reviews_count(card_element)
            
            # Vendeur/Shop
            shop_info = self._extract_shop_info(card_element)
            
            # Badges (bestseller, etc.)
            badges = self._extract_badges(card_element)
            
            # Livraison
            shipping_info = self._extract_shipping_info(card_element)
            
            # Favoris
            favorites_count = self._extract_favorites_count(card_element)
            
            # ID du listing
            listing_id = self._extract_listing_id(card_element, listing_url)
            
            return {
                'title': title,
                'price': price_info['current'],
                'original_price': price_info['original'],
                'currency': price_info['currency'],
                'url': listing_url,
                'image_url': image_url,
                'rating': rating,
                'reviews_count': reviews_count,
                'shop': shop_info,
                'badges': badges,
                'shipping': shipping_info,
                'favorites_count': favorites_count,
                'listing_id': listing_id,
                'platform': 'etsy'
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing d'un listing Etsy: {str(e)}")
            return None
    
    def _extract_price(self, element) -> Dict[str, Any]:
        """Extrait les informations de prix"""
        price_info = {'current': 0, 'original': 0, 'currency': 'USD'}
        
        # Prix actuel
        price_elem = element.find('span', class_='currency-value')
        if not price_elem:
            price_elem = element.find('p', class_='a-offscreen')
        if not price_elem:
            price_elem = element.find('span', class_='shop2-review-review')
        
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
        
        # Prix original (si en promotion)
        original_price_elem = element.find('span', class_='text-decoration-line-through')
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
        rating_elem = element.find('span', class_='shop2-review-rating')
        if not rating_elem:
            rating_elem = element.find('div', class_='stars')
        
        if rating_elem:
            # Cherche les étoiles pleines
            stars = rating_elem.find_all('span', class_='icon-b-2')
            if stars:
                return len(stars)
            
            # Essaie d'extraire du texte
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
        reviews_elem = element.find('span', class_='shop2-review-count')
        if not reviews_elem:
            reviews_elem = element.find('a', class_='listing-link')
        
        if reviews_elem:
            reviews_text = reviews_elem.get_text(strip=True)
            try:
                import re
                # Cherche un nombre entre parenthèses ou suivi de "reviews"
                match = re.search(r'\((\d+)\)|([\d,]+)\s*reviews?', reviews_text)
                if match:
                    number = match.group(1) or match.group(2)
                    return int(number.replace(',', ''))
            except:
                pass
        return 0
    
    def _extract_shop_info(self, element) -> Dict[str, str]:
        """Extrait les informations de la boutique"""
        shop_info = {'name': '', 'location': ''}
        
        shop_elem = element.find('p', class_='shop2-review-shop-name')
        if not shop_elem:
            shop_elem = element.find('span', class_='shop-name')
        
        if shop_elem:
            shop_info['name'] = shop_elem.get_text(strip=True)
        
        # Localisation de la boutique
        location_elem = element.find('span', class_='shop-location')
        if location_elem:
            shop_info['location'] = location_elem.get_text(strip=True)
        
        return shop_info
    
    def _extract_badges(self, element) -> List[str]:
        """Extrait les badges du produit"""
        badges = []
        
        # Bestseller badge
        bestseller_elem = element.find('span', class_='bestseller-badge')
        if bestseller_elem:
            badges.append('bestseller')
        
        # Free shipping badge
        free_shipping_elem = element.find('span', class_='free-shipping-badge')
        if free_shipping_elem:
            badges.append('free_shipping')
        
        # Sale badge
        sale_elem = element.find('span', class_='sale-badge')
        if sale_elem:
            badges.append('on_sale')
        
        return badges
    
    def _extract_shipping_info(self, element) -> Dict[str, str]:
        """Extrait les informations de livraison"""
        shipping_info = {'cost': '', 'estimated_delivery': ''}
        
        shipping_elem = element.find('p', class_='text-gray-lighter')
        if shipping_elem:
            shipping_text = shipping_elem.get_text(strip=True)
            
            if 'free shipping' in shipping_text.lower():
                shipping_info['cost'] = 'free'
            elif 'shipping' in shipping_text.lower():
                shipping_info['cost'] = shipping_text
        
        return shipping_info
    
    def _extract_favorites_count(self, element) -> int:
        """Extrait le nombre de favoris"""
        favorites_elem = element.find('span', class_='favorite-count')
        if favorites_elem:
            favorites_text = favorites_elem.get_text(strip=True)
            try:
                import re
                match = re.search(r'([\d,]+)', favorites_text)
                if match:
                    return int(match.group(1).replace(',', ''))
            except:
                pass
        return 0
    
    def _extract_listing_id(self, element, listing_url: str) -> str:
        """Extrait l'ID du listing"""
        # Essaie d'extraire de l'URL
        import re
        if listing_url:
            match = re.search(r'/listing/(\d+)', listing_url)
            if match:
                return match.group(1)
        
        # Essaie d'extraire des attributs data
        listing_id = element.get('data-listing-id')
        if listing_id:
            return listing_id
        
        return ''
    
    async def search_products(self, search_term: str, max_pages: int = 3) -> List[Dict[str, Any]]:
        """Recherche des produits sur Etsy"""
        products = []
        
        for page in range(1, max_pages + 1):
            logger.info(f"Scraping Etsy page {page} pour '{search_term}'")
            
            params = {
                'q': search_term,
                'page': page,
                'ref': 'pagination'
            }
            
            html = await self._make_request(self.search_url, params)
            if not html:
                logger.warning(f"Impossible de récupérer la page {page}")
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Trouve les cartes de listings
            listing_cards = soup.find_all('div', class_='v2-listing-card')
            if not listing_cards:
                listing_cards = soup.find_all('div', {'data-test-id': 'listing-card'})
            
            if not listing_cards:
                logger.warning(f"Aucun listing trouvé sur la page {page}")
                break
            
            page_products = 0
            for card in listing_cards:
                listing = self._parse_listing_card(card)
                if listing and listing['title'] != "N/A":
                    products.append(listing)
                    page_products += 1
            
            logger.info(f"Page {page}: {page_products} listings trouvés")
            
            # Délai plus long entre les pages pour Etsy
            await asyncio.sleep(random.uniform(3, 6))
        
        return products
    
    async def scrape(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Point d'entrée principal pour le scraping Etsy"""
        search_terms = config.get('search_terms', ['handmade'])
        max_pages = config.get('max_pages', 3)
        
        all_products = []
        
        try:
            for term in search_terms:
                logger.info(f"Début de la recherche Etsy pour: {term}")
                products = await self.search_products(term, max_pages)
                
                # Ajoute le terme de recherche aux métadonnées
                for product in products:
                    product['search_term'] = term
                
                all_products.extend(products)
                
                # Délai plus long entre les termes de recherche
                if len(search_terms) > 1:
                    await asyncio.sleep(random.uniform(5, 10))
            
            logger.info(f"Scraping Etsy terminé: {len(all_products)} listings")
            return all_products
            
        except Exception as e:
            logger.error(f"Erreur lors du scraping Etsy: {str(e)}")
            return all_products
        
        finally:
            if self.session:
                await self.session.close()
                self.session = None