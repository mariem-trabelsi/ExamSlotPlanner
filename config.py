"""
Module de configuration centralisée pour l'application
"""

# =============================================================================
# CONFIGURATION DE L'APPLICATION
# =============================================================================

APP_NAME = "Système de Gestion des Surveillances d'Examens"
APP_VERSION = "2.0.0"
APP_AUTHOR = "Direction - Établissement"

# =============================================================================
# CONFIGURATION DES QUOTAS PAR GRADE
# =============================================================================

GRADE_QUOTAS = {
    "PR": 8,    # Professeur
    "MA": 7,    # Maître Assistant
    "V": 6,     # Vacant
    "PTC": 5,   # PTC
    "AC": 4,    # Assistant Contractuel
    "VA": 4,    # Vacataire
    "AS": 4,    # Assistant
    "EX": 4,    # Expert
    "MC": 4,    # Maître de Conférences
    "PES": 4    # PES
}

# =============================================================================
# CONFIGURATION DES SESSIONS
# =============================================================================

SESSION_TIMES = {
    "S1": "08:30",
    "S2": "10:30",
    "S3": "12:30",
    "S4": "14:30"
}

SESSION_ORDER = {
    "S1": 1,
    "S2": 2,
    "S3": 3,
    "S4": 4
}

SESSION_DURATION = 120  # Durée en minutes

# =============================================================================
# CONFIGURATION DE L'ALGORITHME GÉNÉTIQUE
# =============================================================================

GA_CONFIG = {
    'population_size': 100,
    'generations': 100,
    'elite_size': 10,
    'mutation_rate_low': 0.2,
    'mutation_rate_high': 0.5,
    'tournament_size': 5,
    'stagnation_threshold': 50
}

# =============================================================================
# CONFIGURATION DES CONTRAINTES
# =============================================================================

CONSTRAINTS = {
    'min_teachers_per_room': 2,
    'max_teachers_per_room': 4,
    'penalty_missing_teacher': -1000,
    'penalty_excess_teacher': -1000,
    'penalty_duplicate': -500,
    'penalty_quota_violation': -1000,
    'penalty_unavailability': -1000,
    'penalty_consecutivity': -1000,
    'bonus_optimal': 100,
    'penalty_dispersion': 10,
    'penalty_inequity': 10
}

# =============================================================================
# CONFIGURATION DE LA BASE DE DONNÉES
# =============================================================================

DATABASE_CONFIG = {
    'name': 'surveillance_planning.db',
    'backup_enabled': True,
    'backup_frequency': 'daily',  # daily, weekly, monthly
    'max_backups': 10
}

# =============================================================================
# CONFIGURATION DE L'INTERFACE
# =============================================================================

UI_CONFIG = {
    'default_window_size': '1300x800',
    'min_window_size': (1024, 768),
    'theme': 'modern',
    'font_family': 'Arial',
    'font_size_normal': 10,
    'font_size_large': 12,
    'font_size_title': 16,
    'animation_enabled': True,
    'notification_duration': 3000  # millisecondes
}

# =============================================================================
# CONFIGURATION DES EXPORTS
# =============================================================================

EXPORT_CONFIG = {
    'csv_encoding': 'utf-8-sig',
    'csv_delimiter': ',',
    'pdf_page_size': 'letter',
    'pdf_font': 'Helvetica',
    'pdf_title': 'Planning de Surveillance des Examens',
    'include_timestamp': True,
    'include_statistics': True
}

# =============================================================================
# CONFIGURATION DE LA SÉCURITÉ
# =============================================================================

SECURITY_CONFIG = {
    'max_login_attempts': 5,
    'session_timeout': 3600,  # secondes
    'password_min_length': 8,
    'require_password_change': False,
    'password_change_interval': 90  # jours
}

# =============================================================================
# CONFIGURATION DES LOGS
# =============================================================================

LOG_CONFIG = {
    'enabled': True,
    'level': 'INFO',  # DEBUG, INFO, WARNING, ERROR, CRITICAL
    'file': 'surveillance_app.log',
    'max_size': 10 * 1024 * 1024,  # 10 MB
    'backup_count': 5,
    'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
}

# =============================================================================
# MESSAGES DE L'APPLICATION
# =============================================================================

MESSAGES = {
    'welcome': {
        'title': "👋 Bienvenue dans le Système de Gestion des Surveillances",
        'subtitle': "Pour commencer, chargez vos fichiers Excel puis générez le planning.",
        'instructions': "Données nécessaires : Créneaux • Enseignants • Vœux (optionnel)"
    },
    'success': {
        'data_loaded': "✅ Données chargées avec succès!",
        'planning_generated': "✅ Planning généré avec succès!",
        'planning_saved': "✅ Planning sauvegardé avec succès!",
        'planning_exported': "✅ Planning exporté avec succès!",
        'planning_deleted': "✅ Planning supprimé avec succès!"
    },
    'error': {
        'no_data': "❌ Veuillez d'abord charger les données nécessaires",
        'no_planning': "❌ Aucun planning disponible",
        'load_failed': "❌ Erreur lors du chargement des données",
        'generation_failed': "❌ Erreur lors de la génération du planning",
        'save_failed': "❌ Erreur lors de la sauvegarde",
        'export_failed': "❌ Erreur lors de l'export"
    },
    'warning': {
        'no_selection': "⚠️ Veuillez sélectionner un élément",
        'incomplete_data': "⚠️ Données incomplètes",
        'low_quality': "⚠️ Qualité du planning à améliorer"
    },
    'info': {
        'loading': "⏳ Chargement en cours...",
        'generating': "⏳ Génération du planning en cours...",
        'processing': "⏳ Traitement en cours...",
        'saving': "⏳ Sauvegarde en cours..."
    }
}

# =============================================================================
# CONFIGURATION DES FORMATS DE FICHIERS
# =============================================================================

FILE_FORMATS = {
    'excel_extensions': ['.xlsx', '.xls'],
    'csv_extension': '.csv',
    'pdf_extension': '.pdf',
    'json_extension': '.json',
    'supported_imports': ['Excel files (*.xlsx *.xls)', 'CSV files (*.csv)'],
    'supported_exports': ['PDF files (*.pdf)', 'CSV files (*.csv)', 'Excel files (*.xlsx)']
}

# =============================================================================
# CONFIGURATION DES COULEURS (importée depuis ui_components)
# =============================================================================

COLORS = {
    'primary': '#2C3E50',
    'primary_light': '#34495E',
    'primary_dark': '#1A252F',
    'secondary': '#3498DB',
    'success': '#27AE60',
    'success_light': '#58D68D',
    'warning': '#E67E22',
    'danger': '#E74C3C',
    'bg': '#ECF0F1',
    'bg_dark': '#2C3E50',
    'card': '#FFFFFF',
    'card_dark': '#34495E',
    'text': '#2C3E50',
    'text_light': '#7F8C8D',
    'text_white': '#FFFFFF',
    'border': '#BDC3C7',
    'accent': '#9B59B6'
}

# =============================================================================
# FONCTIONS UTILITAIRES DE CONFIGURATION
# =============================================================================

def get_grade_quota(grade_code):
    """Retourne le quota pour un grade donné"""
    return GRADE_QUOTAS.get(grade_code, 4)  # 4 par défaut


def get_session_time(session_code):
    """Retourne l'heure pour une session donnée"""
    return SESSION_TIMES.get(session_code, "00:00")


def get_session_order(session_code):
    """Retourne l'ordre pour une session donnée"""
    return SESSION_ORDER.get(session_code, 0)


def update_grade_quota(grade_code, new_quota):
    """Met à jour le quota d'un grade"""
    if grade_code in GRADE_QUOTAS:
        GRADE_QUOTAS[grade_code] = new_quota
        return True
    return False


def get_all_grades():
    """Retourne la liste de tous les grades"""
    return list(GRADE_QUOTAS.keys())


def get_all_sessions():
    """Retourne la liste de toutes les sessions"""
    return list(SESSION_TIMES.keys())


def validate_config():
    """Valide la configuration"""
    errors = []
    
    # Vérifier les quotas
    for grade, quota in GRADE_QUOTAS.items():
        if quota < 0:
            errors.append(f"Quota négatif pour le grade {grade}")
    
    # Vérifier les sessions
    if len(SESSION_TIMES) != len(SESSION_ORDER):
        errors.append("Incohérence entre SESSION_TIMES et SESSION_ORDER")
    
    # Vérifier la configuration GA
    if GA_CONFIG['population_size'] < 10:
        errors.append("Taille de population trop petite")
    
    if GA_CONFIG['elite_size'] > GA_CONFIG['population_size']:
        errors.append("Elite size supérieur à la taille de population")
    
    return len(errors) == 0, errors


def print_config_summary():
    """Affiche un résumé de la configuration"""
    print("=" * 60)
    print(f"Configuration de {APP_NAME} v{APP_VERSION}")
    print("=" * 60)
    print(f"Grades configurés: {len(GRADE_QUOTAS)}")
    print(f"Sessions par jour: {len(SESSION_TIMES)}")
    print(f"Population GA: {GA_CONFIG['population_size']}")
    print(f"Générations GA: {GA_CONFIG['generations']}")
    print(f"Base de données: {DATABASE_CONFIG['name']}")
    print("=" * 60)
    
    # Validation
    is_valid, errors = validate_config()
    if is_valid:
        print("✅ Configuration valide")
    else:
        print("❌ Erreurs de configuration:")
        for error in errors:
            print(f"  - {error}")
    print("=" * 60)


# Validation au chargement du module
if __name__ == "__main__":
    print_config_summary()