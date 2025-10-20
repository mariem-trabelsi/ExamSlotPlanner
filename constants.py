# constants.py
"""
Constantes et configurations de l'application
"""

# Configuration des quotas par grade
GRADE_QUOTAS = {
    "PR": 4, "MA": 7, "V": 4, "PTC": 9, "AC": 9,
    "VA": 4, "AS": 8, "EX": 3, "MC": 4, "PES": 9
}

# Mappings des sessions
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

SESSION_COLORS = {
    's1': ('#E3F2FD', '#1976D2'),  # Blue
    's2': ('#E8F5E9', '#388E3C'),  # Green
    's3': ('#FFF3E0', '#F57C00'),  # Orange
    's4': ('#F3E5F5', '#7B1FA2')   # Purple
}

# Noms des jours en français
DAY_NAMES_FR = {
    'Monday': 'Lundi',
    'Tuesday': 'Mardi',
    'Wednesday': 'Mercredi',
    'Thursday': 'Jeudi',
    'Friday': 'Vendredi',
    'Saturday': 'Samedi',
    'Sunday': 'Dimanche'
}

# Police système
SYSTEM_FONT = "Segoe UI"

# Palette de couleurs moderne
COLORS = {
    'primary': '#2563EB',
    'primary_hover': '#1D4ED8',
    'success': '#10B981',
    'success_light': "#5AE6B7",
    'warning': '#F59E0B',
    'error': '#EF4444',
    'bg': '#E4E4E4',
    'card': '#FFFFFF',
    'sidebar': '#F8FAFC',
    'text': '#1F2937',
    'text_secondary': '#6B7280',
    'text_secondary_light': "#ACACAC",
    'border': '#E5E7EB',
    'hover': '#F3F4F6',
    'test': "#E2E2E2",
}