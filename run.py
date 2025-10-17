#!/usr/bin/env python3
"""
Script de lancement avec vérifications préalables
"""
import sys
import os

def check_dependencies():
    """Vérifie que toutes les dépendances sont installées"""
    print("🔍 Vérification des dépendances...")
    
    missing = []
    dependencies = {
        'pandas': 'pandas',
        'numpy': 'numpy',
        'openpyxl': 'openpyxl',
        'xlrd': 'xlrd',
        'reportlab': 'reportlab',
        'tkinter': 'tkinter (généralement inclus avec Python)'
    }
    
    for module, name in dependencies.items():
        try:
            if module == 'tkinter':
                import tkinter
            else:
                __import__(module)
            print(f"  ✅ {name}")
        except ImportError:
            print(f"  ❌ {name} - MANQUANT")
            missing.append(name)
    
    if missing:
        print("\n❌ Dépendances manquantes détectées!")
        print("\nPour installer les dépendances manquantes:")
        print("  pip install -r requirements.txt")
        print("\nOu individuellement:")
        for dep in missing:
            if 'tkinter' not in dep:
                print(f"  pip install {dep.split()[0]}")
        return False
    
    print("\n✅ Toutes les dépendances sont installées!")
    return True

def check_files():
    """Vérifie que tous les fichiers nécessaires sont présents"""
    print("\n🔍 Vérification des fichiers...")
    
    required_files = [
        'main.py',
        'genetic_algorithm.py',
        'view_methods.py',
        'pdf_export.py'
    ]
    
    missing = []
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file} - MANQUANT")
            missing.append(file)
    
    if missing:
        print("\n❌ Fichiers manquants!")
        print("Assurez-vous que tous les fichiers sont dans le même répertoire.")
        return False
    
    print("\n✅ Tous les fichiers sont présents!")
    return True

def run_tests():
    """Exécute les tests si le fichier existe"""
    if os.path.exists('test_corrections.py'):
        print("\n🧪 Exécution des tests...")
        try:
            import test_corrections
            success = test_corrections.run_all_tests()
            if success:
                print("\n✅ Tous les tests sont passés!")
                return True
            else:
                print("\n⚠️ Certains tests ont échoué, mais l'application peut fonctionner.")
                return True  # Continuer quand même
        except Exception as e:
            print(f"\n⚠️ Erreur lors des tests: {e}")
            print("L'application va continuer quand même...")
            return True
    return True

def main():
    """Fonction principale"""
    print("=" * 70)
    print("  SYSTÈME DE GESTION DES PLANNINGS DE SURVEILLANCE")
    print("  Version 2.0 - Optimisée et Corrigée")
    print("=" * 70)
    print()
    
    # Vérifications préalables
    if not check_dependencies():
        sys.exit(1)
    
    if not check_files():
        sys.exit(1)
    
    if not run_tests():
        print("\n❌ Arrêt de l'application.")
        sys.exit(1)
    
    # Lancement de l'application
    print("\n" + "=" * 70)
    print("🚀 Lancement de l'application...")
    print("=" * 70)
    print()
    
    try:
        from main import App
        app = App()
        app.mainloop()
    except KeyboardInterrupt:
        print("\n\n⚠️ Application interrompue par l'utilisateur.")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Erreur lors du lancement: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()