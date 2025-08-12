#!/usr/bin/env python3
"""
Script de test pour l'Actor Apify E-commerce Scraper
"""

import asyncio
import json
import time
from datetime import datetime
from pathlib import Path
import os
import sys

# Ajouter le répertoire racine au path
sys.path.append(str(Path(__file__).parent))

from main import main as actor_main
from apify import Actor

class ActorTester:
    def __init__(self):
        self.test_results = []
        self.storage_path = Path("storage/datasets/default")
        
    def clear_storage(self):
        """Nettoie le stockage avant les tests"""
        if self.storage_path.exists():
            for file in self.storage_path.glob("*.json"):
                if file.name != "__metadata__.json":
                    file.unlink()
    
    async def run_test(self, test_name: str, input_data: dict):
        """Exécute un test avec des données d'entrée spécifiques"""
        print(f"\n🧪 Test: {test_name}")
        print(f"📝 Configuration: {json.dumps(input_data, indent=2)}")
        
        # Nettoyer le stockage
        self.clear_storage()
        
        # Configurer l'entrée
        os.environ['APIFY_INPUT'] = json.dumps(input_data)
        
        start_time = time.time()
        
        try:
            # Exécuter l'Actor
            await actor_main()
            
            execution_time = time.time() - start_time
            
            # Analyser les résultats
            results = self.analyze_results()
            
            test_result = {
                'test_name': test_name,
                'input_data': input_data,
                'execution_time': execution_time,
                'success': True,
                'results': results,
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"✅ Test réussi en {execution_time:.2f}s")
            print(f"📊 Résultats: {results['total_products']} produits trouvés")
            
        except Exception as e:
            execution_time = time.time() - start_time
            test_result = {
                'test_name': test_name,
                'input_data': input_data,
                'execution_time': execution_time,
                'success': False,
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            }
            
            print(f"❌ Test échoué: {str(e)}")
        
        self.test_results.append(test_result)
        return test_result
    
    def analyze_results(self):
        """Analyse les résultats stockés"""
        if not self.storage_path.exists():
            return {'total_products': 0, 'platforms': {}, 'trend_analysis': None}
        
        products_by_platform = {}
        total_products = 0
        trend_analysis = None
        
        for file in self.storage_path.glob("*.json"):
            if file.name == "__metadata__.json":
                continue
                
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                if data.get('type') == 'trend_analysis':
                    trend_analysis = data['analysis']
                elif 'platform' in data:
                    platform = data['platform']
                    if platform not in products_by_platform:
                        products_by_platform[platform] = 0
                    products_by_platform[platform] += 1
                    total_products += 1
            except Exception as e:
                print(f"⚠️ Erreur lors de l'analyse de {file}: {e}")
        
        return {
            'total_products': total_products,
            'platforms': products_by_platform,
            'trend_analysis': trend_analysis
        }
    
    def generate_report(self):
        """Génère un rapport de test complet"""
        report = {
            'test_summary': {
                'total_tests': len(self.test_results),
                'successful_tests': len([t for t in self.test_results if t['success']]),
                'failed_tests': len([t for t in self.test_results if not t['success']]),
                'total_execution_time': sum(t['execution_time'] for t in self.test_results),
                'generated_at': datetime.now().isoformat()
            },
            'test_results': self.test_results
        }
        
        # Sauvegarder le rapport
        with open('test_report.json', 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        return report

async def main():
    """Fonction principale de test"""
    tester = ActorTester()
    
    # Test 1: Configuration basique
    await tester.run_test("Test Basique", {
        "search_queries": ["laptop"],
        "max_products_per_query": 5,
        "platforms": {
            "amazon": {"enabled": True, "max_pages": 1},
            "ebay": {"enabled": True, "max_pages": 1},
            "walmart": {"enabled": False},
            "etsy": {"enabled": False}
        }
    })
    
    # Test 2: Recherche multiple
    await tester.run_test("Test Recherche Multiple", {
        "search_queries": ["smartphone", "tablet"],
        "max_products_per_query": 3,
        "platforms": {
            "amazon": {"enabled": True, "max_pages": 1},
            "ebay": {"enabled": True, "max_pages": 1},
            "walmart": {"enabled": False},
            "etsy": {"enabled": False}
        }
    })
    
    # Test 3: Toutes les plateformes
    await tester.run_test("Test Toutes Plateformes", {
        "search_queries": ["headphones"],
        "max_products_per_query": 2,
        "platforms": {
            "amazon": {"enabled": True, "max_pages": 1},
            "ebay": {"enabled": True, "max_pages": 1},
            "walmart": {"enabled": True, "max_pages": 1},
            "etsy": {"enabled": True, "max_pages": 1}
        }
    })
    
    # Générer le rapport
    report = tester.generate_report()
    
    print("\n" + "="*50)
    print("📋 RAPPORT DE TEST FINAL")
    print("="*50)
    print(f"Tests exécutés: {report['test_summary']['total_tests']}")
    print(f"Tests réussis: {report['test_summary']['successful_tests']}")
    print(f"Tests échoués: {report['test_summary']['failed_tests']}")
    print(f"Temps total: {report['test_summary']['total_execution_time']:.2f}s")
    
    for test in report['test_results']:
        status = "✅" if test['success'] else "❌"
        print(f"{status} {test['test_name']}: {test['execution_time']:.2f}s")
        if test['success'] and 'results' in test:
            print(f"   📊 {test['results']['total_products']} produits")
    
    print(f"\n📄 Rapport détaillé sauvegardé dans: test_report.json")

if __name__ == "__main__":
    asyncio.run(main())