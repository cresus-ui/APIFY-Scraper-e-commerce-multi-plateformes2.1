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

class AmazonScraper:
    """Scraper spécialisé pour Amazon"""
    
    def __init__(self):
        self.base_url = "https://www.amazon.com"
        self.search_url = "https://www.amazon.com/s"
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
                'Upgrade-Insecure-Requests': '1'
            }
            
            connector = aiohttp.TCPConnector(
                limit=10,
                limit_per_host=5,
                ttl_dns_cache=300,
                use_dns_cache=True
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
            # Délai aléatoire pour éviter la détection
            await asyncio.sleep(random.uniform(1, 3))
            
            async with session.get(url, params=params) as response:
                if response.status == 200:
                    return await response.text()
                elif response.status == 503:
                    logger.warning(f"Service indisponible (503) pour {url}")
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
    
    def _parse_product_card(self, product_element) -> Optional[Dict[str, Any]]:
        """Parse un élément produit de la page de résultats"""
        try:
            # Titre du produit
            title_elem = product_element.find('h2', class_='a-size-mini')
            if not title_elem:
                title_elem = product_element.find('span', class_='a-size-base-plus')
            if not title_elem:
                title_elem = product_element.find('span', class_='a-size-medium')
            
            title = title_elem.get_text(strip=True) if title_elem else "N/A"
            
            # Prix
            price = self._extract_price(product_element)
            
            # URL du produit
            link_elem = product_element.find('a', class_='a-link-normal')
            if not link_elem:
                link_elem = product_element.find('a')
            
            product_url = ""
            if link_elem and link_elem.get('href'):
                product_url = urljoin(self.base_url, link_elem['href'])
            
            # Image
            img_elem = product_element.find('img', class_='s-image')
            image_url = img_elem.get('src', '') if img_elem else ''
            
            # Rating
            rating = self._extract_rating(product_element)
            
            # Nombre d'avis
            reviews_count = self._extract_reviews_count(product_element)
            
            # Disponibilité
            availability = self._extract_availability(product_element)
            
            # ASIN (identifiant Amazon)
            asin = self._extract_asin(product_element, product_url)
            
            return {
                'title': title,
                'price': price,
                'original_price': price.get('original', 0) if isinstance(price, dict) else price,
                'discounted_price': price.get('discounted', 0) if isinstance(price, dict) else price,
                'currency': price.get('currency', 'USD') if isinstance(price, dict) else 'USD',
                'url': product_url,
                'image_url': image_url,
                'rating': rating,
                'reviews_count': reviews_count,
                'availability': availability,
                'asin': asin,
                'platform': 'amazon'
            }
            
        except Exception as e:
            logger.error(f"Erreur lors du parsing d'un produit: {str(e)}")
            return None
    
    def _extract_price(self, element) -> Dict[str, Any]:
        """Extrait le prix d'un élément produit"""
        price_info = {'original': 0, 'discounted': 0, 'currency': 'USD'}
        
        # Prix principal
        price_elem = element.find('span', class_='a-price-whole')
        if not price_elem:
            price_elem = element.find('span', class_='a-offscreen')
        
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            price_value = self._parse_price_text(price_text)
            price_info['original'] = price_value
            price_info['discounted'] = price_value
        
        # Prix barré (prix original)
        original_price_elem = element.find('span', class_='a-price a-text-price')
        if original_price_elem:
            original_text = original_price_elem.get_text(strip=True)
            original_value = self._parse_price_text(original_text)
            if original_value > price_info['discounted']:
                price_info['original'] = original_value
        
        return price_info
    
    def _parse_price_text(self, price_text: str) -> float:
        """Parse le texte du prix en valeur numérique"""
        try:
            # Supprime les caractères non numériques sauf le point et la virgule
            import re
            cleaned = re.sub(r'[^\d.,]', '', price_text)
            
            # Gère les différents formats de prix
            if ',' in cleaned and '.' in cleaned:
                # Format: 1,234.56
                cleaned = cleaned.replace(',', '')
            elif ',' in cleaned:
                # Format européen: 1234,56
                if len(cleaned.split(',')[1]) == 2:
                    cleaned = cleaned.replace(',', '.')
                else:
                    cleaned = cleaned.replace(',', '')
            
            return float(cleaned) if cleaned else 0.0
        except:
            return 0.0
    
    def _extract_rating(self, element) -> float:
        """Extrait la note du produit"""
        rating_elem = element.find('span', class_='a-icon-alt')
        if rating_elem:
            rating_text = rating_elem.get_text(strip=True)
            try:
                # Extrait le nombre de la chaîne "4.5 out of 5 stars"
                import re
                match = re.search(r'(\d+\.\d+)', rating_text)
                if match:
                    return float(match.group(1))
            except:
                pass
        return 0.0
    
    def _extract_reviews_count(self, element) -> int:
        """Extrait le nombre d'avis"""
        reviews_elem = element.find('a', class_='a-link-normal')
        if reviews_elem:
            reviews_text = reviews_elem.get_text(strip=True)
            try:
                import re
                # Cherche un nombre suivi de parenthèses ou dans le texte
                match = re.search(r'([\d,]+)', reviews_text)
                if match:
                    return int(match.group(1).replace(',', ''))
            except:
                pass
        return 0
    
    def _extract_availability(self, element) -> str:
        """Extrait l'information de disponibilité"""
        # Cherche différents indicateurs de stock
        stock_indicators = [
            'a-color-success',
            'a-color-price',
            'a-color-secondary'
        ]
        
        for indicator in stock_indicators:
            stock_elem = element.find('span', class_=indicator)
            if stock_elem:
                stock_text = stock_elem.get_text(strip=True).lower()
                if any(word in stock_text for word in ['in stock', 'available', 'ships']):
                    return 'in_stock'
                elif any(word in stock_text for word in ['out of stock', 'unavailable']):
                    return 'out_of_stock'
        
        return 'unknown'
    
    def _extract_asin(self, element, product_url: str) -> str:
        """Extrait l'ASIN du produit"""
        # Essaie d'extraire l'ASIN de l'URL
        import re
        if product_url:
            match = re.search(r'/dp/([A-Z0-9]{10})', product_url)
            if match:
                return match.group(1)
        
        # Essaie d'extraire l'ASIN des attributs data
        asin_attr = element.get('data-asin')
        if asin_attr:
            return asin_attr
        
        return ''
    
    async def search_products(self, search_term: str, max_pages: int = 5) -> List[Dict[str, Any]]:
        """Recherche des produits sur Amazon"""
        products = []
        
        for page in range(1, max_pages + 1):
            logger.info(f"Scraping Amazon page {page} pour '{search_term}'")
            
            params = {
                'k': search_term,
                'page': page,
                'ref': 'sr_pg_' + str(page)
            }
            
            html = await self._make_request(self.search_url, params)
            if not html:
                logger.warning(f"Impossible de récupérer la page {page}")
                continue
            
            soup = BeautifulSoup(html, 'html.parser')
            
            # Trouve les conteneurs de produits
            product_containers = soup.find_all('div', {'data-component-type': 's-search-result'})
            
            if not product_containers:
                logger.warning(f"Aucun produit trouvé sur la page {page}")
                break
            
            for container in product_containers:
                product = self._parse_product_card(container)
                if product and product['title'] != "N/A":
                    products.append(product)
            
            logger.info(f"Page {page}: {len(product_containers)} produits trouvés")
            
            # Délai entre les pages
            await asyncio.sleep(random.uniform(2, 4))
        
        return products
    
    async def scrape(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Point d'entrée principal pour le scraping Amazon"""
        search_terms = config.get('search_terms', ['laptop'])
        max_pages = config.get('max_pages', 5)
        
        all_products = []
        
        try:
            for term in search_terms:
                logger.info(f"Début de la recherche Amazon pour: {term}")
                products = await self.search_products(term, max_pages)
                
                # Ajoute le terme de recherche aux métadonnées
                for product in products:
                    product['search_term'] = term
                
                all_products.extend(products)
                
                # Délai entre les termes de recherche
                if len(search_terms) > 1:
                    await asyncio.sleep(random.uniform(3, 6))
            
            logger.info(f"Scraping Amazon terminé: {len(all_products)} produits")
            return all_products
            
        except Exception as e:
            logger.error(f"Erreur lors du scraping Amazon: {str(e)}")
            return all_products
        
        finally:
            if self.session:
                await self.session.close()
                self.session = None