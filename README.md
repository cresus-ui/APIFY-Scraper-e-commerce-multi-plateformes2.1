# Multi-Platform E-commerce Scraper for Apify

🛒 **Scraper e-commerce multi-plateformes automatique** - Amazon, eBay, Walmart, Etsy, Shopify

## 📋 Description

Cet acteur Apify permet de scraper automatiquement les données produits de plusieurs plateformes e-commerce majeures :

- **Amazon** - Produits, prix, avis, disponibilité
- **eBay** - Enchères, achats immédiats, conditions
- **Walmart** - Catalogue produits, prix, stock
- **Etsy** - Produits artisanaux, vendeurs, évaluations
- **Shopify** - Boutiques en ligne personnalisées

## ✨ Fonctionnalités

### 🔍 Scraping Multi-Plateformes
- Support de 5 plateformes e-commerce majeures
- Extraction automatique des données produits
- Gestion des différents formats de données
- Rotation automatique des User-Agents

### 💰 Suivi des Prix
- Détection automatique des changements de prix
- Historique des prix par produit
- Alertes de prix personnalisables
- Comparaison de prix entre plateformes

### 📊 Analyse des Tendances
- Tendances de prix par catégorie
- Analyse de la disponibilité des produits
- Identification des produits populaires
- Performance comparative des plateformes

### 🛡️ Fonctionnalités Avancées
- Gestion des erreurs et retry automatique
- Respect des limites de taux (rate limiting)
- Normalisation des données multi-plateformes
- Export en formats multiples (JSON, CSV)

## 🚀 Installation

### Prérequis
- Python 3.8+
- Compte Apify (pour le déploiement)

### Installation locale
```bash
# Cloner le projet
git clone <repository-url>
cd APIFY-Scraper-e-commerce-multi-plateformes2.0

# Installer les dépendances
pip install -r requirements.txt

# Configuration (optionnel)
cp .env.example .env
# Éditer .env avec vos paramètres
```

## 📖 Utilisation

### Configuration de base

```python
from apify import Actor

# Configuration d'entrée
input_data = {
    "search_queries": ["laptop gaming", "smartphone"],
    "platforms": ["amazon", "ebay", "walmart"],
    "max_products_per_query": 50,
    "enable_price_tracking": True,
    "enable_trend_analysis": True
}

# Lancement du scraper
async with Actor:
    await Actor.main()
```

### Paramètres d'entrée

| Paramètre | Type | Description | Défaut |
|-----------|------|-------------|--------|
| `search_queries` | Array | Liste des termes de recherche | `[]` |
| `platforms` | Array | Plateformes à scraper | `["amazon", "ebay"]` |
| `max_products_per_query` | Number | Nombre max de produits par recherche | `20` |
| `enable_price_tracking` | Boolean | Activer le suivi des prix | `true` |
| `enable_trend_analysis` | Boolean | Activer l'analyse des tendances | `true` |
| `output_format` | String | Format de sortie (json/csv) | `"json"` |
| `proxy_configuration` | Object | Configuration proxy | `{}` |

### Exemple de configuration avancée

```json
{
  "search_queries": [
    "MacBook Pro 2023",
    "iPhone 15",
    "Samsung Galaxy S24"
  ],
  "platforms": ["amazon", "ebay", "walmart", "etsy"],
  "max_products_per_query": 100,
  "filters": {
    "min_price": 100,
    "max_price": 2000,
    "min_rating": 4.0,
    "availability_only": true
  },
  "enable_price_tracking": true,
  "enable_trend_analysis": true,
  "price_alerts": [
    {
      "product_keywords": "MacBook Pro",
      "target_price": 1500,
      "alert_type": "below"
    }
  ],
  "output_format": "json",
  "proxy_configuration": {
    "useApifyProxy": true,
    "apifyProxyGroups": ["RESIDENTIAL"]
  }
}
```

## 📊 Format des données de sortie

### Données produit
```json
{
  "id": "unique_product_id",
  "title": "Nom du produit",
  "price": 299.99,
  "currency": "USD",
  "original_price": 399.99,
  "discount_percentage": 25,
  "url": "https://...",
  "image_url": "https://...",
  "rating": 4.5,
  "reviews_count": 1250,
  "availability": "in_stock",
  "platform": "amazon",
  "category": "Electronics",
  "seller": "Vendeur officiel",
  "shipping_info": "Livraison gratuite",
  "scraped_at": "2024-01-15T10:30:00Z"
}
```

### Données de suivi des prix
```json
{
  "product_id": "unique_product_id",
  "price_changes": [
    {
      "previous_price": 399.99,
      "current_price": 299.99,
      "change_amount": -100.00,
      "change_percentage": -25.0,
      "detected_at": "2024-01-15T10:30:00Z"
    }
  ],
  "price_trend": {
    "direction": "decreasing",
    "confidence": 0.85,
    "volatility": 12.5
  }
}
```

### Rapport d'analyse des tendances
```json
{
  "summary": {
    "total_products_analyzed": 500,
    "total_platforms": 4,
    "analysis_period_days": 7
  },
  "price_trends": {
    "overall_trend": "stable",
    "platform_comparison": {
      "amazon": { "avg_price": 245.50, "competitiveness": 92 },
      "ebay": { "avg_price": 220.30, "competitiveness": 98 }
    }
  },
  "popular_products": [
    {
      "title": "iPhone 15 Pro",
      "popularity_score": 8.7,
      "platforms_available": 3
    }
  ]
}
```

## 🏗️ Architecture

```
├── main.py                 # Point d'entrée principal
├── actor.json             # Configuration Apify
├── requirements.txt       # Dépendances Python
├── scrapers/             # Modules de scraping
│   ├── __init__.py
│   ├── amazon_scraper.py
│   ├── ebay_scraper.py
│   ├── walmart_scraper.py
│   ├── etsy_scraper.py
│   └── shopify_scraper.py
└── utils/                # Utilitaires
    ├── __init__.py
    ├── data_processor.py  # Traitement des données
    ├── price_tracker.py   # Suivi des prix
    └── trend_analyzer.py  # Analyse des tendances
```

## 🔧 Configuration avancée

### Variables d'environnement

Créez un fichier `.env` :

```env
# Configuration Apify
APIFY_TOKEN=your_apify_token
APIFY_DEFAULT_DATASET_ID=your_dataset_id

# Configuration des scrapers
DEFAULT_REQUEST_DELAY=1
MAX_RETRIES=3
TIMEOUT_SECONDS=30

# Configuration des proxies
USE_PROXY=true
PROXY_GROUPS=RESIDENTIAL,DATACENTER

# Logging
LOG_LEVEL=INFO
```

### Personnalisation des scrapers

Chaque scraper peut être personnalisé :

```python
from scrapers.amazon_scraper import AmazonScraper

# Configuration personnalisée
scraper = AmazonScraper(
    delay_range=(1, 3),
    max_retries=5,
    custom_headers={
        'Accept-Language': 'fr-FR,fr;q=0.9'
    }
)
```

## 📈 Monitoring et logs

### Logs disponibles
- Progression du scraping
- Erreurs et retry
- Changements de prix détectés
- Statistiques de performance

### Métriques Apify
- Nombre de produits scrapés
- Taux de succès par plateforme
- Temps d'exécution
- Utilisation des proxies

## 🚨 Limitations et bonnes pratiques

### Limitations
- Respect des robots.txt
- Limites de taux par plateforme
- Certaines données peuvent nécessiter une authentification

### Bonnes pratiques
- Utilisez des proxies pour éviter les blocages
- Configurez des délais appropriés entre les requêtes
- Surveillez les changements de structure des sites
- Respectez les conditions d'utilisation des plateformes

## 🔄 Mise à jour et maintenance

### Mise à jour des sélecteurs
Les sélecteurs CSS/XPath peuvent changer. Vérifiez régulièrement :

```python
# Exemple de mise à jour d'un sélecteur
AMAZON_SELECTORS = {
    'title': 'h1#productTitle',  # Ancien
    'title': 'h1[data-automation-id="product-title"]'  # Nouveau
}
```

### Tests automatisés
```bash
# Lancer les tests
pytest tests/

# Tests spécifiques à une plateforme
pytest tests/test_amazon_scraper.py
```

## 📞 Support

- **Issues GitHub** : Pour les bugs et demandes de fonctionnalités
- **Documentation Apify** : [docs.apify.com](https://docs.apify.com)
- **Community Forum** : [community.apify.com](https://community.apify.com)

## 📄 Licence

Ce projet est sous licence MIT. Voir le fichier `LICENSE` pour plus de détails.

## 🤝 Contribution

Les contributions sont les bienvenues ! Veuillez :

1. Fork le projet
2. Créer une branche pour votre fonctionnalité
3. Commiter vos changements
4. Pousser vers la branche
5. Ouvrir une Pull Request

## 🏷️ Versions

- **v2.0.0** - Version actuelle avec support multi-plateformes
- **v1.0.0** - Version initiale Amazon uniquement

---

**Développé avec ❤️ pour la communauté Apify**