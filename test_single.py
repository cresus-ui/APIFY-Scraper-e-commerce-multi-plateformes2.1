#!/usr/bin/env python3
"""
Script de test simple pour l'Actor Apify E-commerce Scraper
"""

import json
import os
import sys
from pathlib import Path

# Configuration de test
test_config = {
    "search_queries": ["gaming mouse"],
    "max_products_per_query": 8,
    "enable_price_tracking": True,
    "enable_trend_analysis": True,
    "platforms": {
        "amazon": {
            "enabled": True,
            "max_pages": 2
        },
        "ebay": {
            "enabled": True,
            "max_pages": 2
        },
        "walmart": {
            "enabled": False
        },
        "etsy": {
            "enabled": False
        }
    },
    "proxy_configuration": {
        "use_proxy": False
    }
}

print("🧪 Test de l'Actor E-commerce Scraper")
print("="*50)
print(f"Configuration de test:")
print(json.dumps(test_config, indent=2))
print("="*50)

# Sauvegarder la configuration
with open('test_config.json', 'w') as f:
    json.dump(test_config, f, indent=2)

print("✅ Configuration sauvegardée dans test_config.json")
print("\n🚀 Pour tester l'Actor, exécutez:")
print("$env:APIFY_INPUT_FILE='test_config.json'; python main.py")