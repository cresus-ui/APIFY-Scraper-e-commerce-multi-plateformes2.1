import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from bs4 import BeautifulSoup
import sys
import os

# Ajouter le répertoire parent au path pour les imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.amazon_scraper import AmazonScraper

class TestAmazonScraper:
    """Tests pour le scraper Amazon"""
    
    def setup_method(self):
        """Configuration avant chaque test"""
        self.scraper = AmazonScraper()
    
    def test_scraper_initialization(self):
        """Test l'initialisation du scraper"""
        assert self.scraper.base_url == "https://www.amazon.com"
        assert self.scraper.delay_range == (1, 3)
        assert self.scraper.max_retries == 3
    
    def test_build_search_url(self):
        """Test la construction d'URL de recherche"""
        query = "laptop gaming"
        url = self.scraper._build_search_url(query)
        
        assert "amazon.com/s" in url
        assert "laptop+gaming" in url or "laptop%20gaming" in url
    
    def test_build_search_url_with_page(self):
        """Test la construction d'URL avec pagination"""
        query = "smartphone"
        url = self.scraper._build_search_url(query, page=2)
        
        assert "amazon.com/s" in url
        assert "page=2" in url or "&page=2" in url
    
    def test_extract_price_valid(self):
        """Test l'extraction de prix valide"""
        # Test avec différents formats de prix
        test_cases = [
            ("$29.99", 29.99),
            ("$1,299.00", 1299.00),
            ("€45.50", 45.50),
            ("£199.99", 199.99),
            ("29.99", 29.99)
        ]
        
        for price_text, expected in test_cases:
            result = self.scraper._extract_price(price_text)
            assert result == expected
    
    def test_extract_price_invalid(self):
        """Test l'extraction de prix invalide"""
        invalid_prices = [
            "",
            "Price not available",
            "N/A",
            "Currently unavailable",
            None
        ]
        
        for price_text in invalid_prices:
            result = self.scraper._extract_price(price_text)
            assert result == 0
    
    def test_extract_rating_valid(self):
        """Test l'extraction de note valide"""
        test_cases = [
            ("4.5 out of 5 stars", 4.5),
            ("3.2 stars", 3.2),
            ("5.0", 5.0),
            ("2.7 étoiles", 2.7)
        ]
        
        for rating_text, expected in test_cases:
            result = self.scraper._extract_rating(rating_text)
            assert result == expected
    
    def test_extract_rating_invalid(self):
        """Test l'extraction de note invalide"""
        invalid_ratings = [
            "",
            "No rating",
            "N/A",
            None,
            "Be the first to review"
        ]
        
        for rating_text in invalid_ratings:
            result = self.scraper._extract_rating(rating_text)
            assert result == 0
    
    def test_extract_reviews_count_valid(self):
        """Test l'extraction du nombre d'avis valide"""
        test_cases = [
            ("1,234 reviews", 1234),
            ("567 customer reviews", 567),
            ("12,345 ratings", 12345),
            ("89 avis", 89)
        ]
        
        for reviews_text, expected in test_cases:
            result = self.scraper._extract_reviews_count(reviews_text)
            assert result == expected
    
    def test_extract_reviews_count_invalid(self):
        """Test l'extraction du nombre d'avis invalide"""
        invalid_reviews = [
            "",
            "No reviews yet",
            "N/A",
            None,
            "Be the first to review"
        ]
        
        for reviews_text in invalid_reviews:
            result = self.scraper._extract_reviews_count(reviews_text)
            assert result == 0
    
    def test_extract_availability_in_stock(self):
        """Test l'extraction de disponibilité - en stock"""
        in_stock_texts = [
            "In Stock",
            "Available",
            "En stock",
            "Disponible",
            "Ships from Amazon",
            "Usually ships within 1-2 days"
        ]
        
        for availability_text in in_stock_texts:
            result = self.scraper._extract_availability(availability_text)
            assert result == "in_stock"
    
    def test_extract_availability_out_of_stock(self):
        """Test l'extraction de disponibilité - rupture de stock"""
        out_of_stock_texts = [
            "Out of Stock",
            "Currently unavailable",
            "Rupture de stock",
            "Indisponible",
            "Temporarily out of stock"
        ]
        
        for availability_text in out_of_stock_texts:
            result = self.scraper._extract_availability(availability_text)
            assert result == "out_of_stock"
    
    def test_parse_product_card_complete(self):
        """Test l'analyse d'une carte produit complète"""
        # HTML simulé d'une carte produit Amazon
        html_content = """
        <div class="s-result-item">
            <h3 class="s-size-mini">
                <a href="/dp/B08N5WRWNW">
                    <span>Gaming Laptop ASUS ROG</span>
                </a>
            </h3>
            <span class="a-price-whole">$1,299</span>
            <span class="a-icon-alt">4.5 out of 5 stars</span>
            <span class="a-size-base">2,345 reviews</span>
            <img src="https://example.com/image.jpg" alt="product">
            <span class="a-color-success">In Stock</span>
        </div>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        card = soup.find('div', class_='s-result-item')
        
        result = self.scraper._parse_product_card(card)
        
        assert result is not None
        assert "Gaming Laptop ASUS ROG" in result['title']
        assert result['price'] == 1299.0
        assert result['rating'] == 4.5
        assert result['reviews_count'] == 2345
        assert result['availability'] == "in_stock"
        assert "amazon.com/dp/B08N5WRWNW" in result['url']
    
    def test_parse_product_card_minimal(self):
        """Test l'analyse d'une carte produit avec données minimales"""
        html_content = """
        <div class="s-result-item">
            <h3>
                <a href="/dp/B08N5WRWNW">
                    <span>Simple Product</span>
                </a>
            </h3>
        </div>
        """
        
        soup = BeautifulSoup(html_content, 'html.parser')
        card = soup.find('div', class_='s-result-item')
        
        result = self.scraper._parse_product_card(card)
        
        assert result is not None
        assert result['title'] == "Simple Product"
        assert result['price'] == 0
        assert result['rating'] == 0
        assert result['reviews_count'] == 0
        assert result['availability'] == "unknown"
    
    def test_parse_product_card_invalid(self):
        """Test l'analyse d'une carte produit invalide"""
        # Carte sans titre
        html_content = "<div class='s-result-item'><p>No title here</p></div>"
        
        soup = BeautifulSoup(html_content, 'html.parser')
        card = soup.find('div', class_='s-result-item')
        
        result = self.scraper._parse_product_card(card)
        
        assert result is None
    
    @patch('scrapers.amazon_scraper.AmazonScraper._make_request')
    def test_search_products_success(self, mock_request):
        """Test la recherche de produits avec succès"""
        # HTML de réponse simulé
        mock_html = """
        <html>
            <body>
                <div class="s-result-item">
                    <h3><a href="/dp/TEST123"><span>Test Product 1</span></a></h3>
                    <span class="a-price-whole">$99</span>
                </div>
                <div class="s-result-item">
                    <h3><a href="/dp/TEST456"><span>Test Product 2</span></a></h3>
                    <span class="a-price-whole">$149</span>
                </div>
            </body>
        </html>
        """
        
        mock_request.return_value = mock_html
        
        results = self.scraper.search_products("test query", max_products=10)
        
        assert len(results) == 2
        assert results[0]['title'] == "Test Product 1"
        assert results[0]['price'] == 99.0
        assert results[1]['title'] == "Test Product 2"
        assert results[1]['price'] == 149.0
    
    @patch('scrapers.amazon_scraper.AmazonScraper._make_request')
    def test_search_products_no_results(self, mock_request):
        """Test la recherche sans résultats"""
        mock_html = "<html><body><div>No results found</div></body></html>"
        mock_request.return_value = mock_html
        
        results = self.scraper.search_products("nonexistent product")
        
        assert len(results) == 0
    
    @patch('scrapers.amazon_scraper.AmazonScraper._make_request')
    def test_search_products_request_failure(self, mock_request):
        """Test la gestion d'échec de requête"""
        mock_request.return_value = None
        
        results = self.scraper.search_products("test query")
        
        assert len(results) == 0
    
    def test_generate_product_id(self):
        """Test la génération d'ID produit"""
        url1 = "https://www.amazon.com/dp/B08N5WRWNW"
        url2 = "https://www.amazon.com/product/B08N5WRWNW"
        url3 = "https://www.amazon.com/gp/product/B08N5WRWNW"
        
        id1 = self.scraper._generate_product_id(url1, "Test Product")
        id2 = self.scraper._generate_product_id(url2, "Test Product")
        id3 = self.scraper._generate_product_id(url3, "Test Product")
        
        # Tous devraient contenir l'ASIN
        assert "B08N5WRWNW" in id1
        assert "B08N5WRWNW" in id2
        assert "B08N5WRWNW" in id3
        
        # Les IDs devraient être cohérents
        assert id1 == id2 == id3
    
    def test_clean_title(self):
        """Test le nettoyage des titres"""
        test_cases = [
            ("  Gaming Laptop  ", "Gaming Laptop"),
            ("Product\nwith\nlinebreaks", "Product with linebreaks"),
            ("Product\twith\ttabs", "Product with tabs"),
            ("Product with   multiple   spaces", "Product with multiple spaces")
        ]
        
        for input_title, expected in test_cases:
            result = self.scraper._clean_title(input_title)
            assert result == expected
    
    @pytest.mark.integration
    @patch('scrapers.amazon_scraper.requests.get')
    def test_make_request_with_retry(self, mock_get):
        """Test les requêtes avec retry"""
        # Simuler un échec puis un succès
        mock_response_fail = Mock()
        mock_response_fail.raise_for_status.side_effect = Exception("Network error")
        
        mock_response_success = Mock()
        mock_response_success.raise_for_status.return_value = None
        mock_response_success.text = "<html>Success</html>"
        mock_response_success.status_code = 200
        
        mock_get.side_effect = [mock_response_fail, mock_response_success]
        
        result = self.scraper._make_request("https://example.com")
        
        assert result == "<html>Success</html>"
        assert mock_get.call_count == 2
    
    def test_validate_product_data(self):
        """Test la validation des données produit"""
        valid_product = {
            'title': 'Valid Product',
            'price': 99.99,
            'url': 'https://amazon.com/dp/TEST123'
        }
        
        invalid_products = [
            {},  # Vide
            {'title': ''},  # Titre vide
            {'title': 'Product', 'price': -10},  # Prix négatif
            {'title': 'Product', 'url': 'invalid-url'}  # URL invalide
        ]
        
        assert self.scraper._validate_product_data(valid_product) is True
        
        for invalid_product in invalid_products:
            assert self.scraper._validate_product_data(invalid_product) is False


if __name__ == "__main__":
    pytest.main([__file__])