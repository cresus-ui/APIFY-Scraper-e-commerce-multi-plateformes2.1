import logging
import re
from typing import Dict, List, Any, Optional
from datetime import datetime
from urllib.parse import urlparse

logger = logging.getLogger(__name__)

class DataProcessor:
    """Processeur de données pour normaliser les données des différentes plateformes"""
    
    def __init__(self):
        self.currency_symbols = {
            '$': 'USD',
            '€': 'EUR',
            '£': 'GBP',
            '¥': 'JPY',
            '₹': 'INR'
        }
        
    def normalize_product_data(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalise les données produits de toutes les plateformes"""
        normalized_products = []
        
        for product in products:
            try:
                normalized = self._normalize_single_product(product)
                if normalized:
                    normalized_products.append(normalized)
            except Exception as e:
                logger.error(f"Erreur lors de la normalisation d'un produit: {str(e)}")
                continue
        
        logger.info(f"Normalisation terminée: {len(normalized_products)}/{len(products)} produits")
        return normalized_products
    
    def _normalize_single_product(self, product: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Normalise un seul produit"""
        try:
            normalized = {
                # Informations de base
                'id': self._generate_product_id(product),
                'title': self._clean_title(product.get('title', '')),
                'description': self._clean_description(product.get('description', '')),
                'url': self._validate_url(product.get('url', '')),
                'image_url': self._validate_url(product.get('image_url', '')),
                
                # Prix
                'price': self._normalize_price(product.get('price', 0)),
                'original_price': self._normalize_price(product.get('original_price', 0)),
                'currency': self._normalize_currency(product.get('currency', 'USD')),
                'discount_percentage': self._calculate_discount_percentage(
                    product.get('price', 0),
                    product.get('original_price', 0)
                ),
                
                # Évaluations
                'rating': self._normalize_rating(product.get('rating', 0)),
                'reviews_count': self._normalize_count(product.get('reviews_count', 0)),
                
                # Disponibilité
                'availability': self._normalize_availability(product.get('availability', 'unknown')),
                'in_stock': self._determine_stock_status(product),
                
                # Métadonnées de plateforme
                'platform': product.get('platform', 'unknown'),
                'platform_id': self._extract_platform_id(product),
                'search_term': product.get('search_term', ''),
                
                # Informations spécifiques par plateforme
                'platform_specific': self._extract_platform_specific_data(product),
                
                # Timestamps
                'scraped_at': datetime.now().isoformat(),
                'last_updated': datetime.now().isoformat()
            }
            
            # Validation finale
            if self._validate_normalized_product(normalized):
                return normalized
            else:
                return None
                
        except Exception as e:
            logger.error(f"Erreur lors de la normalisation: {str(e)}")
            return None
    
    def _generate_product_id(self, product: Dict[str, Any]) -> str:
        """Génère un ID unique pour le produit"""
        platform = product.get('platform', 'unknown')
        platform_id = self._extract_platform_id(product)
        
        if platform_id:
            return f"{platform}_{platform_id}"
        
        # Fallback: utilise l'URL ou le titre
        url = product.get('url', '')
        title = product.get('title', '')
        
        if url:
            # Extrait un identifiant de l'URL
            url_hash = str(hash(url))[-8:]
            return f"{platform}_{url_hash}"
        elif title:
            # Utilise le hash du titre
            title_hash = str(hash(title))[-8:]
            return f"{platform}_{title_hash}"
        
        # Dernier recours
        return f"{platform}_{datetime.now().timestamp()}"
    
    def _clean_title(self, title: str) -> str:
        """Nettoie le titre du produit"""
        if not title or title == "N/A":
            return ""
        
        # Supprime les caractères de contrôle et espaces multiples
        cleaned = re.sub(r'\s+', ' ', title.strip())
        
        # Supprime les préfixes communs
        prefixes_to_remove = [
            'New Listing',
            'SPONSORED',
            'Ad'
        ]
        
        for prefix in prefixes_to_remove:
            if cleaned.startswith(prefix):
                cleaned = cleaned[len(prefix):].strip()
        
        return cleaned[:500]  # Limite la longueur
    
    def _clean_description(self, description: str) -> str:
        """Nettoie la description du produit"""
        if not description:
            return ""
        
        # Supprime les balises HTML
        cleaned = re.sub(r'<[^>]+>', '', description)
        
        # Supprime les caractères de contrôle
        cleaned = re.sub(r'[\x00-\x1f\x7f-\x9f]', '', cleaned)
        
        # Normalise les espaces
        cleaned = re.sub(r'\s+', ' ', cleaned.strip())
        
        return cleaned[:1000]  # Limite la longueur
    
    def _validate_url(self, url: str) -> str:
        """Valide et normalise une URL"""
        if not url:
            return ""
        
        try:
            parsed = urlparse(url)
            if parsed.scheme and parsed.netloc:
                return url
        except:
            pass
        
        return ""
    
    def _normalize_price(self, price: Any) -> float:
        """Normalise un prix"""
        if isinstance(price, (int, float)):
            return max(0.0, float(price))
        
        if isinstance(price, str):
            try:
                # Supprime tout sauf les chiffres, points et virgules
                cleaned = re.sub(r'[^\d.,]', '', price)
                
                if ',' in cleaned and '.' in cleaned:
                    cleaned = cleaned.replace(',', '')
                elif ',' in cleaned:
                    if len(cleaned.split(',')[1]) == 2:
                        cleaned = cleaned.replace(',', '.')
                    else:
                        cleaned = cleaned.replace(',', '')
                
                return max(0.0, float(cleaned)) if cleaned else 0.0
            except:
                return 0.0
        
        return 0.0
    
    def _normalize_currency(self, currency: str) -> str:
        """Normalise le code de devise"""
        if not currency:
            return 'USD'
        
        # Si c'est un symbole, convertit en code
        if currency in self.currency_symbols:
            return self.currency_symbols[currency]
        
        # Normalise le code de devise
        currency_upper = currency.upper().strip()
        
        # Codes de devise valides
        valid_currencies = ['USD', 'EUR', 'GBP', 'JPY', 'CAD', 'AUD', 'INR']
        
        if currency_upper in valid_currencies:
            return currency_upper
        
        return 'USD'  # Par défaut
    
    def _calculate_discount_percentage(self, current_price: float, original_price: float) -> float:
        """Calcule le pourcentage de remise"""
        current = self._normalize_price(current_price)
        original = self._normalize_price(original_price)
        
        if original > current > 0:
            return round(((original - current) / original) * 100, 2)
        
        return 0.0
    
    def _normalize_rating(self, rating: Any) -> float:
        """Normalise une note (0-5)"""
        try:
            rating_float = float(rating)
            return max(0.0, min(5.0, rating_float))
        except:
            return 0.0
    
    def _normalize_count(self, count: Any) -> int:
        """Normalise un compteur"""
        try:
            if isinstance(count, str):
                # Supprime les virgules et autres caractères
                cleaned = re.sub(r'[^\d]', '', count)
                return int(cleaned) if cleaned else 0
            return max(0, int(count))
        except:
            return 0
    
    def _normalize_availability(self, availability: Any) -> str:
        """Normalise le statut de disponibilité"""
        if not availability:
            return 'unknown'
        
        availability_str = str(availability).lower()
        
        if any(term in availability_str for term in ['in_stock', 'available', 'in stock']):
            return 'in_stock'
        elif any(term in availability_str for term in ['out_of_stock', 'unavailable', 'out of stock']):
            return 'out_of_stock'
        elif any(term in availability_str for term in ['limited', 'low stock']):
            return 'limited_stock'
        
        return 'unknown'
    
    def _determine_stock_status(self, product: Dict[str, Any]) -> bool:
        """Détermine si le produit est en stock"""
        availability = self._normalize_availability(product.get('availability', 'unknown'))
        
        if availability == 'in_stock':
            return True
        elif availability == 'out_of_stock':
            return False
        
        # Vérifications spécifiques par plateforme
        platform = product.get('platform', '')
        
        if platform == 'shopify':
            return product.get('available', True)
        
        # Par défaut, considère comme en stock si pas d'info contraire
        return True
    
    def _extract_platform_id(self, product: Dict[str, Any]) -> str:
        """Extrait l'ID spécifique à la plateforme"""
        platform = product.get('platform', '')
        
        # Mapping des champs d'ID par plateforme
        id_fields = {
            'amazon': ['asin', 'product_id'],
            'ebay': ['item_id', 'product_id'],
            'walmart': ['product_id'],
            'etsy': ['listing_id', 'product_id'],
            'shopify': ['product_id', 'variant_id']
        }
        
        if platform in id_fields:
            for field in id_fields[platform]:
                if field in product and product[field]:
                    return str(product[field])
        
        return ""
    
    def _extract_platform_specific_data(self, product: Dict[str, Any]) -> Dict[str, Any]:
        """Extrait les données spécifiques à chaque plateforme"""
        platform = product.get('platform', '')
        specific_data = {}
        
        if platform == 'amazon':
            specific_data = {
                'asin': product.get('asin', ''),
                'prime_eligible': 'prime' in product.get('shipping', {}).get('speed', '').lower()
            }
        
        elif platform == 'ebay':
            specific_data = {
                'item_id': product.get('item_id', ''),
                'sale_type': product.get('sale_type', ''),
                'condition': product.get('condition', ''),
                'bid_count': product.get('bid_count', 0),
                'time_left': product.get('time_left', ''),
                'seller': product.get('seller', {})
            }
        
        elif platform == 'walmart':
            specific_data = {
                'product_id': product.get('product_id', ''),
                'seller': product.get('seller', ''),
                'shipping': product.get('shipping', {})
            }
        
        elif platform == 'etsy':
            specific_data = {
                'listing_id': product.get('listing_id', ''),
                'shop': product.get('shop', {}),
                'badges': product.get('badges', []),
                'favorites_count': product.get('favorites_count', 0)
            }
        
        elif platform == 'shopify':
            specific_data = {
                'product_id': product.get('product_id', ''),
                'vendor': product.get('vendor', ''),
                'product_type': product.get('product_type', ''),
                'tags': product.get('tags', []),
                'variants_count': product.get('variants_count', 0),
                'store_url': product.get('store_url', ''),
                'store_domain': product.get('store_domain', '')
            }
        
        return specific_data
    
    def _validate_normalized_product(self, product: Dict[str, Any]) -> bool:
        """Valide qu'un produit normalisé est valide"""
        required_fields = ['id', 'title', 'platform']
        
        for field in required_fields:
            if not product.get(field):
                logger.warning(f"Produit invalide: champ '{field}' manquant ou vide")
                return False
        
        # Vérifie que le prix est valide
        if product.get('price', 0) < 0:
            logger.warning("Produit invalide: prix négatif")
            return False
        
        return True
    
    def deduplicate_products(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Supprime les doublons basés sur le titre et la plateforme"""
        seen = set()
        unique_products = []
        
        for product in products:
            # Crée une clé unique basée sur le titre nettoyé et la plateforme
            title_clean = re.sub(r'[^\w\s]', '', product.get('title', '')).lower().strip()
            platform = product.get('platform', '')
            key = f"{platform}_{title_clean}"
            
            if key not in seen:
                seen.add(key)
                unique_products.append(product)
        
        logger.info(f"Déduplication: {len(unique_products)}/{len(products)} produits uniques")
        return unique_products
    
    def filter_products(self, products: List[Dict[str, Any]], filters: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Filtre les produits selon des critères"""
        filtered = products.copy()
        
        # Filtre par prix minimum
        if 'min_price' in filters:
            min_price = float(filters['min_price'])
            filtered = [p for p in filtered if p.get('price', 0) >= min_price]
        
        # Filtre par prix maximum
        if 'max_price' in filters:
            max_price = float(filters['max_price'])
            filtered = [p for p in filtered if p.get('price', 0) <= max_price]
        
        # Filtre par note minimum
        if 'min_rating' in filters:
            min_rating = float(filters['min_rating'])
            filtered = [p for p in filtered if p.get('rating', 0) >= min_rating]
        
        # Filtre par disponibilité
        if 'in_stock_only' in filters and filters['in_stock_only']:
            filtered = [p for p in filtered if p.get('in_stock', True)]
        
        # Filtre par plateforme
        if 'platforms' in filters:
            platforms = filters['platforms']
            if isinstance(platforms, str):
                platforms = [platforms]
            filtered = [p for p in filtered if p.get('platform') in platforms]
        
        logger.info(f"Filtrage: {len(filtered)}/{len(products)} produits après filtres")
        return filtered