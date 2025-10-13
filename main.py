import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import random
import numpy as np
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import hashlib
import json
import os

# =============================================================================
# CONFIGURATION ET CLASSES D'AUTHENTIFICATION
# =============================================================================

# Configuration des identifiants
CREDENTIALS_FILE = "credentials.json"
DEFAULT_CREDENTIALS = {
    "username": "direction",
    "password": "admin2025"
}

# Palette de couleurs professionnelle
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

class LoginManager:
    """Gestionnaire d'authentification pour l'application"""
    
    def __init__(self):
        self.credentials_file = CREDENTIALS_FILE
        self.ensure_credentials_exist()
    
    def hash_password(self, password):
        """Hash le mot de passe avec SHA-256"""
        return hashlib.sha256(password.encode()).hexdigest()
    
    def ensure_credentials_exist(self):
        """Crée le fichier d'identifiants s'il n'existe pas"""
        if not os.path.exists(self.credentials_file):
            default_data = {
                "username": DEFAULT_CREDENTIALS["username"],
                "password": self.hash_password(DEFAULT_CREDENTIALS["password"]),
                "created_at": datetime.now().isoformat()
            }
            with open(self.credentials_file, 'w') as f:
                json.dump(default_data, f, indent=4)
    
    def load_credentials(self):
        """Charge les identifiants depuis le fichier"""
        try:
            with open(self.credentials_file, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"❌ Erreur lors du chargement des identifiants: {e}")
            return None
    
    def verify_credentials(self, username, password):
        """Vérifie les identifiants"""
        credentials = self.load_credentials()
        if not credentials:
            return False
        
        return (credentials.get("username") == username and 
                credentials.get("password") == self.hash_password(password))
    
    def change_password(self, old_password, new_password):
        """Change le mot de passe"""
        credentials = self.load_credentials()
        if not credentials:
            return False
        
        if credentials.get("password") != self.hash_password(old_password):
            return False
        
        credentials["password"] = self.hash_password(new_password)
        credentials["updated_at"] = datetime.now().isoformat()
        with open(self.credentials_file, 'w') as f:
            json.dump(credentials, f, indent=4)
        return True
    
    def get_current_username(self):
        """Retourne le nom d'utilisateur actuel"""
        credentials = self.load_credentials()
        return credentials.get("username") if credentials else None

class ModernLoginApp:
    """Application d'authentification moderne et professionnelle"""
    
    def __init__(self, on_login_success_callback):
        self.root = tk.Tk()
        self.on_login_success = on_login_success_callback
        self.setup_window()
        self.login_manager = LoginManager()
        
        # Variables
        self.current_view = "login"
        self.login_attempts = 0
        self.max_attempts = 5
        
        self.create_main_frame()
        self.show_login_view()
        
        # Animation de démarrage
        self.animate_welcome()
    
    def setup_window(self):
        """Configure la fenêtre principale"""
        self.root.title("SecureAuth Pro - Système d'Authentification Sécurisé")
        self.root.configure(bg=COLORS['bg_dark'])
        
        # Plein écran
        self.root.attributes('-fullscreen', True)
        self.root.attributes('-alpha', 0.95)
        
        # Bind Escape pour quitter le plein écran
        self.root.bind('<Escape>', lambda e: self.root.attributes('-fullscreen', False))
        
        # Centrer la fenêtre
        self.root.update_idletasks()
    
    def create_main_frame(self):
        """Crée le frame principal"""
        self.main_frame = tk.Frame(self.root, bg=COLORS['bg_dark'])
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=50, pady=50)
        
        # Header avec logo et titre
        self.create_header()
        
        # Container pour le contenu
        self.content_frame = tk.Frame(self.main_frame, bg=COLORS['bg_dark'])
        self.content_frame.pack(fill=tk.BOTH, expand=True, pady=20)
    
    def create_header(self):
        """Crée l'en-tête avec logo et titre"""
        header_frame = tk.Frame(self.main_frame, bg=COLORS['primary_dark'], height=100)
        header_frame.pack(fill=tk.X, pady=(0, 30))
        header_frame.pack_propagate(False)
        
        logo_frame = tk.Frame(header_frame, bg=COLORS['primary_dark'])
        logo_frame.pack(expand=True, fill=tk.BOTH, padx=50, pady=20)
        
        logo_label = tk.Label(logo_frame, text="🔐", font=('Arial', 24), 
                             bg=COLORS['primary_dark'], fg=COLORS['text_white'])
        logo_label.pack(side=tk.LEFT, padx=(0, 15))
        
        title_label = tk.Label(logo_frame, 
                              text="SecureAuth Pro", 
                              font=('Arial', 28, 'bold'),
                              bg=COLORS['primary_dark'], 
                              fg=COLORS['text_white'])
        title_label.pack(side=tk.LEFT)
        
        subtitle_label = tk.Label(logo_frame,
                                 text="Système d'Authentification Sécurisé",
                                 font=('Arial', 12),
                                 bg=COLORS['primary_dark'],
                                 fg=COLORS['text_light'])
        subtitle_label.pack(side=tk.LEFT, padx=(15, 0), pady=(5, 0))
        
        close_btn = tk.Button(header_frame, text="✕", font=('Arial', 16, 'bold'),
                             bg=COLORS['danger'], fg=COLORS['text_white'],
                             relief=tk.FLAT, cursor='hand2',
                             command=self.root.quit)
        close_btn.place(relx=0.98, rely=0.5, anchor='e')
    
    def show_login_view(self):
        """Affiche la vue de connexion"""
        self.clear_content()
        self.current_view = "login"
        
        login_container = tk.Frame(self.content_frame, bg=COLORS['bg_dark'])
        login_container.pack(expand=True, fill=tk.BOTH)
        
        # Côté gauche - Illustration
        left_frame = tk.Frame(login_container, bg=COLORS['bg_dark'], width=400)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 50))
        left_frame.pack_propagate(False)
        
        self.create_illustration(left_frame)
        
        # Côté droit - Formulaire
        right_frame = tk.Frame(login_container, bg=COLORS['card'], width=500)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        right_frame.pack_propagate(False)
        
        self.create_login_form(right_frame)
    
    def create_illustration(self, parent):
        """Crée l'illustration côté gauche"""
        title_label = tk.Label(parent, 
                              text="Bienvenue", 
                              font=('Arial', 32, 'bold'),
                              bg=COLORS['bg_dark'], 
                              fg=COLORS['text_white'])
        title_label.pack(pady=(100, 10))
        
        subtitle_label = tk.Label(parent,
                                text="Système de Gestion des Surveillances d'Examens",
                                font=('Arial', 16),
                                bg=COLORS['bg_dark'],
                                fg=COLORS['text_light'])
        subtitle_label.pack(pady=(0, 50))
        
        illustration_text = "🎓 📊 🕐 👥 🎯"
        illustration_label = tk.Label(parent, 
                                     text=illustration_text, 
                                     font=('Arial', 48),
                                     bg=COLORS['bg_dark'], 
                                     fg=COLORS['text_white'])
        illustration_label.pack(pady=50)
        
        features = [
            "✓ Authentification sécurisée",
            "✓ Gestion des permissions",
            "✓ Interface intuitive",
            "✓ Rapports détaillés",
            "✓ Support technique 24/7"
        ]
        
        for feature in features:
            feature_label = tk.Label(parent, 
                                   text=feature, 
                                   font=('Arial', 12),
                                   bg=COLORS['bg_dark'], 
                                   fg=COLORS['text_light'],
                                   anchor='w')
            feature_label.pack(fill=tk.X, pady=5)
    
    def create_login_form(self, parent):
        """Crée le formulaire de connexion"""
        form_frame = tk.Frame(parent, bg=COLORS['card'], padx=50, pady=60)
        form_frame.pack(expand=True, fill=tk.BOTH)
        
        title_label = tk.Label(form_frame, 
                              text="Connexion Sécurisée", 
                              font=('Arial', 24, 'bold'),
                              bg=COLORS['card'], 
                              fg=COLORS['primary'])
        title_label.pack(pady=(0, 40))
        
        # Champ utilisateur
        user_frame = tk.Frame(form_frame, bg=COLORS['card'])
        user_frame.pack(fill=tk.X, pady=15)
        
        tk.Label(user_frame, text="Nom d'utilisateur", 
                font=('Arial', 11, 'bold'),
                bg=COLORS['card'], fg=COLORS['text']).pack(anchor='w')
        
        self.username_entry = tk.Entry(user_frame, 
                                      font=('Arial', 14),
                                      relief=tk.FLAT,
                                      bg=COLORS['bg'],
                                      width=30)
        self.username_entry.pack(fill=tk.X, pady=(8, 0), ipady=12)
        self.username_entry.insert(0, DEFAULT_CREDENTIALS["username"])
        self.username_entry.bind('<Return>', lambda e: self.password_entry.focus())
        
        # Champ mot de passe
        pass_frame = tk.Frame(form_frame, bg=COLORS['card'])
        pass_frame.pack(fill=tk.X, pady=15)
        
        tk.Label(pass_frame, text="Mot de passe", 
                font=('Arial', 11, 'bold'),
                bg=COLORS['card'], fg=COLORS['text']).pack(anchor='w')
        
        self.password_entry = tk.Entry(pass_frame, 
                                      font=('Arial', 14),
                                      show='●',
                                      relief=tk.FLAT,
                                      bg=COLORS['bg'],
                                      width=30)
        self.password_entry.pack(fill=tk.X, pady=(8, 0), ipady=12)
        self.password_entry.bind('<Return>', lambda e: self.login())
        
        # Bouton de connexion
        login_btn_frame = tk.Frame(form_frame, bg=COLORS['card'])
        login_btn_frame.pack(fill=tk.X, pady=30)
        
        login_btn = tk.Button(login_btn_frame,
                             text="SE CONNECTER",
                             font=('Arial', 14, 'bold'),
                             bg=COLORS['success'],
                             fg=COLORS['text_white'],
                             relief=tk.FLAT,
                             cursor='hand2',
                             command=self.login,
                             width=20,
                             height=2)
        login_btn.pack(fill=tk.X, ipady=15)
        
        # Informations d'identification par défaut
        info_label = tk.Label(form_frame,
                             text=f"Identifiants par défaut: {DEFAULT_CREDENTIALS['username']} / {DEFAULT_CREDENTIALS['password']}",
                             font=('Arial', 9),
                             bg=COLORS['card'],
                             fg=COLORS['text_light'])
        info_label.pack(side=tk.BOTTOM, pady=(20, 0))
        
        self.password_entry.focus()
    
    def login(self):
        """Tente de se connecter"""
        username = self.username_entry.get().strip()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Erreur", "Veuillez remplir tous les champs!")
            return
        
        self.login_attempts += 1
        remaining_attempts = self.max_attempts - self.login_attempts
        
        if self.login_manager.verify_credentials(username, password):
            messagebox.showinfo("Succès", "Connexion réussie! Chargement de l'application...")
            self.root.destroy()
            # Appeler le callback pour lancer l'application principale
            self.on_login_success()
        else:
            if remaining_attempts > 0:
                messagebox.showerror("Erreur", f"Identifiants incorrects! {remaining_attempts} tentative(s) restante(s)")
                self.password_entry.delete(0, tk.END)
                self.password_entry.focus()
            else:
                messagebox.showerror("Erreur", "Nombre maximum de tentatives atteint! Fermeture...")
                self.root.after(3000, self.root.quit)
    
    def clear_content(self):
        """Efface le contenu actuel"""
        for widget in self.content_frame.winfo_children():
            widget.destroy()
    
    def animate_welcome(self):
        """Animation de bienvenue au démarrage"""
        welcome_label = tk.Label(self.content_frame, 
                               text="SecureAuth Pro", 
                               font=('Arial', 36, 'bold'),
                               bg=COLORS['bg_dark'], 
                               fg=COLORS['text_white'])
        welcome_label.place(relx=0.5, rely=0.5, anchor='center')
        
        def fade_out():
            for i in range(10, -1, -1):
                alpha = i / 10
                welcome_label.configure(fg=self.hex_to_rgba(COLORS['text_white'], alpha))
                self.root.update()
                self.root.after(50)
            welcome_label.destroy()
        
        self.root.after(1000, fade_out)
    
    def hex_to_rgba(self, hex_color, alpha):
        """Convertit une couleur hex en rgba"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def run(self):
        """Lance l'application de login"""
        self.root.mainloop()

# =============================================================================
# APPLICATION PRINCIPALE DE GESTION DES SURVEILLANCES
# =============================================================================

# Configuration initiale des quotas par grade
GRADE_QUOTAS = {
    "PR": 8, "MA": 7, "V": 6, "PTC": 5, "AC": 4,
    "VA": 4, "AS": 4, "EX": 4, "MC": 4, "PES": 4
}

SESSION_TIMES = {"S1": "08:30", "S2": "10:30", "S3": "12:30", "S4": "14:30"}
SESSION_ORDER = {"S1": 1, "S2": 2, "S3": 3, "S4": 4}

# Fonctions de l'algorithme génétique (conservées de votre code original)
def parse_datetime(slot_str):
    date_part, session = slot_str.split()
    return datetime.strptime(date_part, '%Y-%m-%d'), SESSION_ORDER[session]

def get_teacher_slots(assignment, teacher):
    return sorted([
        (parse_datetime(slot)[0], parse_datetime(slot)[1]) 
        for slot in assignment if teacher in assignment[slot]
    ])

def check_consecutivity_violations(assignment, teachers, slots_dict):
    violations = 0
    for teacher in teachers:
        if not teachers[teacher]['participe_surveillance']:
            continue
        teacher_slots = get_teacher_slots(assignment, teacher)
        for i in range(len(teacher_slots) - 1):
            date1, order1 = teacher_slots[i]
            date2, order2 = teacher_slots[i + 1]
            if date1 == date2 and abs(order2 - order1) > 1:
                violations += 1
    return violations

def dispersion_penalty(teacher_slots):
    if len(teacher_slots) < 2:
        return 0
    penalty = 0
    for i in range(len(teacher_slots) - 1):
        date1, order1 = teacher_slots[i]
        date2, order2 = teacher_slots[i + 1]
        if date1 == date2:
            gap = abs(order2 - order1)
            penalty -= max(0, 2 - gap) * 10
    return penalty

def calculate_grade_equity(counts, teachers):
    grades = set(t['grade'] for t in teachers.values())
    total_variance = 0
    for grade in grades:
        grade_counts = [counts[e] for e in teachers if teachers[e]['grade'] == grade]
        if grade_counts and len(grade_counts) > 1:
            variance = np.var(grade_counts)
            total_variance += variance
    return total_variance

def fitness(assignment, teachers, slots_dict):
    score = 0.0
    counts = {e: 0 for e in teachers}
    
    for slot in assignment:
        unique_assigned = set(assignment[slot])
        slot_data = slots_dict[slot]
        room_count = slot_data['room_count']
        min_needed = 2 * room_count
        max_needed = 4 * room_count
        
        if len(unique_assigned) < min_needed:
            score -= 1000 * (min_needed - len(unique_assigned))
        if len(unique_assigned) > max_needed:
            score -= 1000 * (len(unique_assigned) - max_needed)
        if len(unique_assigned) == min_needed:
            score += 100
        if len(assignment[slot]) != len(unique_assigned):
            score -= 500
        
        for e in assignment[slot]:
            counts[e] += 1
            if counts[e] > teachers[e]['quota']:
                score -= 1000 * (counts[e] - teachers[e]['quota'])
            if slot in teachers[e]['indispo']:
                score -= 1000
    
    violations = check_consecutivity_violations(assignment, teachers, slots_dict)
    score -= 1000 * violations
    
    for e in teachers:
        if not teachers[e]['participe_surveillance']:
            continue
        t_slots = get_teacher_slots(assignment, e)
        score += dispersion_penalty(t_slots)
    
    total_variance = calculate_grade_equity(counts, teachers)
    score -= 10 * total_variance
    
    return score

def generate_population(pop_size, slots, teachers):
    population = []
    teacher_list = [str(e) for e in teachers if teachers[e]['participe_surveillance']]
    
    for _ in range(pop_size):
        assignment = {}
        for slot, slot_data in slots:
            min_needed = 2 * slot_data['room_count']
            available = [e for e in teacher_list if slot not in teachers[e]['indispo']]
            
            if available:
                selected = random.sample(available, min(min_needed, len(available)))
                while len(selected) < min_needed and available:
                    selected.append(random.choice(available))
                assignment[slot] = selected[:4 * slot_data['room_count']]
            else:
                assignment[slot] = []
        
        population.append(assignment)
    return population

def crossover(parent1, parent2):
    child = {}
    keys = list(parent1.keys())
    midpoint = len(keys) // 2
    
    for i in range(midpoint):
        child[keys[i]] = parent1[keys[i]][:]
    for i in range(midpoint, len(keys)):
        child[keys[i]] = parent2[keys[i]][:]
    
    return child

def mutate_improved(assignment, teachers, slots, slots_dict):
    mutation_type = random.choice(['swap', 'reassign', 'redistribute'])
    
    if mutation_type == 'swap':
        slot_keys = list(assignment.keys())
        if len(slot_keys) >= 2:
            slot1, slot2 = random.sample(slot_keys, 2)
            if assignment[slot1] and assignment[slot2]:
                e1 = random.choice(assignment[slot1])
                e2 = random.choice(assignment[slot2])
                
                if (slot2 not in teachers[e1]['indispo'] and 
                    slot1 not in teachers[e2]['indispo']):
                    idx1 = assignment[slot1].index(e1)
                    idx2 = assignment[slot2].index(e2)
                    assignment[slot1][idx1] = e2
                    assignment[slot2][idx2] = e1
    
    elif mutation_type == 'reassign':
        counts = {}
        for e in teachers:
            if teachers[e]['participe_surveillance']:
                counts[e] = sum(1 for slot in assignment if e in assignment[slot])
        
        overloaded = [e for e in counts if counts[e] > teachers[e]['quota']]
        underloaded = [e for e in counts if counts[e] < teachers[e]['quota']]
        
        if overloaded and underloaded:
            e_over = random.choice(overloaded)
            e_under = random.choice(underloaded)
            slots_with_over = [s for s in assignment if e_over in assignment[s]]
            
            if slots_with_over:
                slot = random.choice(slots_with_over)
                if slot not in teachers[e_under]['indispo']:
                    idx = assignment[slot].index(e_over)
                    assignment[slot][idx] = e_under
    
    elif mutation_type == 'redistribute':
        grades = list(set(t['grade'] for t in teachers.values() if t['participe_surveillance']))
        if grades:
            grade = random.choice(grades)
            grade_teachers = [e for e in teachers 
                            if teachers[e]['grade'] == grade 
                            and teachers[e]['participe_surveillance']]
            
            if len(grade_teachers) >= 2:
                counts = {e: sum(1 for slot in assignment if e in assignment[slot]) 
                         for e in grade_teachers}
                
                most = max(counts, key=counts.get)
                least = min(counts, key=counts.get)
                
                if counts[most] - counts[least] >= 2:
                    slots_with_most = [s for s in assignment if most in assignment[s]]
                    if slots_with_most:
                        slot = random.choice(slots_with_most)
                        if slot not in teachers[least]['indispo']:
                            idx = assignment[slot].index(most)
                            assignment[slot][idx] = least
    
    return assignment

def repair_solution(child, teachers, slots_dict):
    for slot in child:
        slot_data = slots_dict[slot]
        min_needed = 2 * slot_data['room_count']
        max_needed = 4 * slot_data['room_count']
        
        child[slot] = list(set(child[slot]))
        
        attempts = 0
        while len(child[slot]) < min_needed and attempts < 100:
            available = [e for e in teachers 
                        if slot not in teachers[e]['indispo'] 
                        and e not in child[slot]
                        and teachers[e]['participe_surveillance']]
            if available:
                child[slot].append(random.choice(available))
            else:
                break
            attempts += 1
        
        if len(child[slot]) > max_needed:
            child[slot] = child[slot][:max_needed]
    
    return child

def run_ga_improved(slots, teachers, progress_callback=None):
    slots_dict = {slot: data for slot, data in slots}
    pop_size = 100
    generations = 500
    elite_size = 10
    
    pop = generate_population(pop_size, slots, teachers)
    best_fitness_history = []
    stagnation_counter = 0
    
    for gen in range(generations):
        pop_with_fitness = [(ind, fitness(ind, teachers, slots_dict)) for ind in pop]
        pop_with_fitness.sort(key=lambda x: x[1], reverse=True)
        
        best_fitness = pop_with_fitness[0][1]
        best_fitness_history.append(best_fitness)
        
        if gen > 50:
            if best_fitness_history[-1] == best_fitness_history[-50]:
                stagnation_counter += 1
            else:
                stagnation_counter = 0
        
        mutation_rate = 0.2 if stagnation_counter < 10 else 0.5
        
        if progress_callback:
            progress_callback(gen, generations, best_fitness)
        
        new_pop = [ind for ind, _ in pop_with_fitness[:elite_size]]
        
        while len(new_pop) < pop_size:
            tournament1 = random.sample(pop_with_fitness[:pop_size//2], 5)
            p1 = max(tournament1, key=lambda x: x[1])[0]
            
            tournament2 = random.sample(pop_with_fitness[:pop_size//2], 5)
            p2 = max(tournament2, key=lambda x: x[1])[0]
            
            child = crossover(p1, p2)
            
            if random.random() < mutation_rate:
                child = mutate_improved(child, teachers, slots, slots_dict)
            
            child = repair_solution(child, teachers, slots_dict)
            
            new_pop.append(child)
        
        pop = new_pop
    
    return pop_with_fitness[0][0], best_fitness_history

class SimpleButton(tk.Button):
    """Bouton simple et clair"""
    def __init__(self, parent, **kwargs):
        bg_color = kwargs.pop('bg_color', COLORS['primary'])
        
        super().__init__(
            parent,
            bg=bg_color,
            fg='white',
            font=('Arial', 10, 'bold'),
            relief=tk.FLAT,
            cursor='hand2',
            padx=20,
            pady=10,
            activebackground=self.darken(bg_color),
            activeforeground='white',
            **kwargs
        )
    
    def darken(self, color):
        """Assombrit une couleur"""
        color = color.lstrip('#')
        r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        r, g, b = max(0, r-20), max(0, g-20), max(0, b-20)
        return f'#{r:02x}{g:02x}{b:02x}'

class SurveillanceApp:
    """Application principale de gestion des surveillances"""
    
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gestion des Surveillances d'Examens")
        self.root.geometry("1300x800")
        self.root.configure(bg=COLORS['bg'])
        
        # Variables
        self.slots = []
        self.teachers = {}
        self.best = None
        self.best_fitness_history = []
        self.day_to_date = {}
        self.room_assignments = {}
        
        self.setup_styles()
        self.create_ui()
    
    def setup_styles(self):
        """Configure les styles"""
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("Custom.Treeview",
                       background=COLORS['card'],
                       foreground=COLORS['text'],
                       rowheight=30,
                       fieldbackground=COLORS['card'],
                       font=('Arial', 10))
        style.map('Custom.Treeview',
                 background=[('selected', COLORS['primary'])],
                 foreground=[('selected', 'white')])
        
        style.configure("Custom.Treeview.Heading",
                       background=COLORS['primary'],
                       foreground='white',
                       font=('Arial', 11, 'bold'),
                       relief=tk.FLAT)
        
        style.configure("Custom.Horizontal.TProgressbar",
                       background=COLORS['success'],
                       troughcolor=COLORS['border'],
                       borderwidth=0)
    
    def create_ui(self):
        """Crée l'interface principale"""
        
        # === EN-TÊTE ===
        header = tk.Frame(self.root, bg=COLORS['primary'], height=90)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        header_content = tk.Frame(header, bg=COLORS['primary'])
        header_content.pack(fill=tk.BOTH, expand=True)
        
        tk.Label(header_content, 
                text="📋 SYSTÈME DE GESTION DES SURVEILLANCES",
                font=('Arial', 18, 'bold'),
                bg=COLORS['primary'],
                fg='white').pack(pady=(15, 5))
        
        tk.Label(header_content,
                text="Portail Administratif - Planification des Examens",
                font=('Arial', 10),
                bg=COLORS['primary'],
                fg='#BDC3C7').pack()
        
        # === ZONE PRINCIPALE ===
        main = tk.Frame(self.root, bg=COLORS['bg'])
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # SECTION 1: Barre d'outils principale
        toolbar = tk.Frame(main, bg=COLORS['card'], relief=tk.FLAT, bd=1)
        toolbar.pack(fill=tk.X, pady=(0, 15))
        
        toolbar_content = tk.Frame(toolbar, bg=COLORS['card'])
        toolbar_content.pack(fill=tk.X, padx=15, pady=12)
        
        # Section Données
        data_section = tk.Frame(toolbar_content, bg=COLORS['card'])
        data_section.pack(side=tk.LEFT, padx=(0, 30))
        
        tk.Label(data_section,
                text="DONNÉES",
                font=('Arial', 9, 'bold'),
                bg=COLORS['card'],
                fg=COLORS['text_light']).pack(anchor='w', pady=(0, 8))
        
        data_buttons = tk.Frame(data_section, bg=COLORS['card'])
        data_buttons.pack()
        
        SimpleButton(data_buttons, 
                    text="📄 Créneaux",
                    command=self.load_slots,
                    bg_color=COLORS['primary']).pack(side=tk.LEFT, padx=3)
        
        SimpleButton(data_buttons,
                    text="👥 Enseignants",
                    command=self.load_teachers,
                    bg_color=COLORS['primary']).pack(side=tk.LEFT, padx=3)
        
        SimpleButton(data_buttons,
                    text="⭐ Vœux",
                    command=self.load_wishes,
                    bg_color=COLORS['primary']).pack(side=tk.LEFT, padx=3)
        
        # Séparateur vertical
        tk.Frame(toolbar_content, bg=COLORS['border'], width=1).pack(side=tk.LEFT, fill=tk.Y, padx=15)
        
        # Section Configuration & Génération
        gen_section = tk.Frame(toolbar_content, bg=COLORS['card'])
        gen_section.pack(side=tk.LEFT, padx=(0, 30))
        
        tk.Label(gen_section,
                text="CONFIGURATION & GÉNÉRATION",
                font=('Arial', 9, 'bold'),
                bg=COLORS['card'],
                fg=COLORS['text_light']).pack(anchor='w', pady=(0, 8))
        
        gen_buttons = tk.Frame(gen_section, bg=COLORS['card'])
        gen_buttons.pack()
        
        SimpleButton(gen_buttons,
                    text="⚙ Quotas",
                    command=self.configure_quotas,
                    bg_color=COLORS['secondary']).pack(side=tk.LEFT, padx=3)
        
        SimpleButton(gen_buttons,
                    text="▶ GÉNÉRER",
                    command=self.generate_planning,
                    bg_color=COLORS['success']).pack(side=tk.LEFT, padx=3)
        
        # Séparateur vertical
        tk.Frame(toolbar_content, bg=COLORS['border'], width=1).pack(side=tk.LEFT, fill=tk.Y, padx=15)
        
        # Section Visualisation
        view_section = tk.Frame(toolbar_content, bg=COLORS['card'])
        view_section.pack(side=tk.LEFT)
        
        tk.Label(view_section,
                text="VISUALISATION",
                font=('Arial', 9, 'bold'),
                bg=COLORS['card'],
                fg=COLORS['text_light']).pack(anchor='w', pady=(0, 8))
        
        view_buttons = tk.Frame(view_section, bg=COLORS['card'])
        view_buttons.pack()
        
        SimpleButton(view_buttons,
                    text="👤 Enseignants",
                    command=self.show_by_teacher,
                    bg_color=COLORS['text_light']).pack(side=tk.LEFT, padx=3)
        
        SimpleButton(view_buttons,
                    text="📅 Jours",
                    command=self.show_by_day,
                    bg_color=COLORS['text_light']).pack(side=tk.LEFT, padx=3)
        
        SimpleButton(view_buttons,
                    text="🚪 Salles",
                    command=self.show_by_room,
                    bg_color=COLORS['text_light']).pack(side=tk.LEFT, padx=3)
        
        SimpleButton(view_buttons,
                    text="📊 Qualité",
                    command=self.show_planning_quality,
                    bg_color=COLORS['secondary']).pack(side=tk.LEFT, padx=3)
        
        # SECTION 2: Barre de recherche et Export
        search_frame = tk.Frame(main, bg=COLORS['card'], relief=tk.FLAT)
        search_frame.pack(fill=tk.X, pady=(0, 10))
        
        tk.Label(search_frame,
                text="🔍 Rechercher:",
                font=('Arial', 10),
                bg=COLORS['card'],
                fg=COLORS['text']).pack(side=tk.LEFT, padx=15, pady=10)
        
        self.search_var = tk.StringVar()
        self.search_var.trace('w', lambda *args: self.on_search())
        
        search_entry = tk.Entry(search_frame,
                               textvariable=self.search_var,
                               font=('Arial', 11),
                               relief=tk.FLAT,
                               bg=COLORS['bg'])
        search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 15), pady=10, ipady=5)
        
        # Boutons d'export à droite
        SimpleButton(search_frame,
                    text="📄 PDF",
                    command=self.export_pdf,
                    bg_color=COLORS['text_light']).pack(side=tk.RIGHT, padx=5, pady=10)
        
        SimpleButton(search_frame,
                    text="💾 CSV",
                    command=self.export_csv,
                    bg_color=COLORS['text_light']).pack(side=tk.RIGHT, padx=5, pady=10)
        
        # SECTION 3: Tableau de résultats
        table_frame = tk.Frame(main, bg=COLORS['card'])
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        y_scroll = ttk.Scrollbar(table_frame)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        x_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview
        self.tree = ttk.Treeview(table_frame,
                                style="Custom.Treeview",
                                yscrollcommand=y_scroll.set,
                                xscrollcommand=x_scroll.set,
                                selectmode='extended')
        self.tree.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        y_scroll.config(command=self.tree.yview)
        x_scroll.config(command=self.tree.xview)
        
        # Message de bienvenue
        self.show_welcome()
        
        # === BARRE DE STATUT ===
        status_bar = tk.Frame(self.root, bg=COLORS['primary_dark'], height=35)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        status_bar.pack_propagate(False)
        
        self.status_label = tk.Label(status_bar,
                                     text="Prêt à commencer",
                                     font=('Arial', 10),
                                     bg=COLORS['primary_dark'],
                                     fg='white',
                                     anchor='w')
        self.status_label.pack(side=tk.LEFT, padx=15, fill=tk.X, expand=True)
    
    def show_welcome(self):
        """Affiche le message de bienvenue"""
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("info",)
        self.tree.heading("#0", text="")
        self.tree.heading("info", text="")
        self.tree.column("#0", width=0, stretch=False)
        self.tree.column("info", width=1000, anchor='center')
        
        messages = [
            "",
            "👋 Bienvenue dans le Système de Gestion des Surveillances",
            "",
            "Pour commencer, chargez vos fichiers Excel puis générez le planning.",
            "",
            "Données nécessaires : Créneaux • Enseignants • Vœux (optionnel)",
            ""
        ]
        
        for msg in messages:
            self.tree.insert("", "end", values=(msg,))
    
    def update_status(self, text):
        """Met à jour la barre de statut"""
        self.status_label.config(text=text)
        self.update_idletasks()
    
    def on_search(self):
        """Filtre les résultats en temps réel"""
        search_text = self.search_var.get().lower()
        
        if not search_text:
            for item in self.tree.get_children():
                self.tree.reattach(item, '', 'end')
            return
        
        for item in self.tree.get_children():
            match = False
            for col in self.tree['columns']:
                value = str(self.tree.set(item, col)).lower()
                if search_text in value:
                    match = True
                    break
            
            if match:
                self.tree.reattach(item, '', 'end')
            else:
                self.tree.detach(item)

    # Les autres méthodes (load_slots, load_teachers, load_wishes, configure_quotas, 
    # generate_planning, display_planning_result, show_by_teacher, show_by_day, 
    # show_by_room, show_planning_quality, export_csv, export_pdf) 
    # restent exactement les mêmes que dans votre code original
    
    def load_slots(self):
        """Charge les créneaux"""
        file = filedialog.askopenfilename(
            title="Sélectionner le fichier des créneaux",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if file:
            try:
                self.update_status("Chargement des créneaux...")
                engine = 'openpyxl' if file.endswith('.xlsx') else 'xlrd'
                df = pd.read_excel(file, engine=engine)
                
                df['dateExam'] = pd.to_datetime(df['dateExam'], format='%d/%m/%Y', dayfirst=True)
                df['h_debut_time'] = df['h_debut'].str.extract(r'(\d{2}:\d{2}:\d{2})', expand=False)
                df['h_fin_time'] = df['h_fin'].str.extract(r'(\d{2}:\d{2}:\d{2})', expand=False)
                df['h_debut'] = pd.to_datetime(df['dateExam'].astype(str) + ' ' + df['h_debut_time'], 
                                              format='%Y-%m-%d %H:%M:%S', errors='coerce')
                df['h_fin'] = pd.to_datetime(df['dateExam'].astype(str) + ' ' + df['h_fin_time'], 
                                            format='%Y-%m-%d %H:%M:%S', errors='coerce')
                
                df['slot'] = df.apply(lambda row: f"{row['dateExam'].strftime('%Y-%m-%d')} {next(k for k, v in SESSION_TIMES.items() if v == row['h_debut'].strftime('%H:%M'))}", axis=1)
                df['session'] = df['h_debut'].dt.strftime('%H:%M').map(lambda x: next((k for k, v in SESSION_TIMES.items() if v == x), None))
                
                grouped = df.groupby('slot')
                self.slots = []
                for slot, group in grouped:
                    room_count = len(group['cod_salle'].unique())
                    enseignant = group['enseignant'].iloc[0] if 'enseignant' in group.columns else ''
                    session = group['session'].iloc[0]
                    self.slots.append((slot, {'room_count': room_count, 'enseignant': enseignant, 'session': session}))
                    self.room_assignments[slot] = {room: [] for room in group['cod_salle'].unique()}
                
                unique_dates = sorted(df['dateExam'].unique())
                self.day_to_date = {str(i+1): d.strftime('%Y-%m-%d') for i, d in enumerate(unique_dates)}
                
                self.update_status(f"✅ {len(self.slots)} créneaux chargés avec succès")
                messagebox.showinfo("Succès", 
                                  f"✅ Créneaux chargés avec succès!\n\n"
                                  f"Nombre de créneaux: {len(self.slots)}\n"
                                  f"Nombre de jours: {len(unique_dates)}")
            except Exception as e:
                self.update_status("❌ Erreur lors du chargement")
                messagebox.showerror("Erreur", f"Impossible de charger les créneaux:\n\n{str(e)}")
    
    def load_teachers(self):
        """Charge les enseignants"""
        file = filedialog.askopenfilename(
            title="Sélectionner le fichier des enseignants",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if file:
            try:
                self.update_status("Chargement des enseignants...")
                engine = 'openpyxl' if file.endswith('.xlsx') else 'xlrd'
                df = pd.read_excel(file, engine=engine)
                
                for _, row in df.iterrows():
                    participe = row['participe_surveillance'] in [1, '1', True, 'true', 'True']
                    code = str(int(row['code_smartex_ens'])) if pd.notna(row['code_smartex_ens']) else str(row['code_smartex_ens'])
                    
                    self.teachers[code] = {
                        'nom': row.get('nom_ens', ''),
                        'prenom': row.get('prenom_ens', ''),
                        'grade': row['grade_code_ens'],
                        'quota': GRADE_QUOTAS.get(row['grade_code_ens'], 2),
                        'indispo': [],
                        'participe_surveillance': participe
                    }
                
                participating = sum(1 for t in self.teachers.values() if t['participe_surveillance'])
                self.update_status(f"✅ {len(self.teachers)} enseignants chargés ({participating} participants)")
                messagebox.showinfo("Succès",
                                  f"✅ Enseignants chargés avec succès!\n\n"
                                  f"Total: {len(self.teachers)}\n"
                                  f"Participants à la surveillance: {participating}")
            except Exception as e:
                self.update_status("❌ Erreur lors du chargement")
                messagebox.showerror("Erreur", f"Impossible de charger les enseignants:\n\n{str(e)}")
    
    def load_wishes(self):
        """Charge les vœux d'indisponibilité"""
        if not self.day_to_date:
            messagebox.showerror("Attention", "Veuillez d'abord charger les créneaux!")
            return
        
        file = filedialog.askopenfilename(
            title="Sélectionner le fichier des vœux",
            filetypes=[("Excel files", "*.xlsx *.xls")]
        )
        if file:
            try:
                self.update_status("Chargement des vœux...")
                engine = 'openpyxl' if file.endswith('.xlsx') else 'xlrd'
                df = pd.read_excel(file, engine=engine)
                
                loaded_count = 0
                for _, row in df.iterrows():
                    ens = str(int(row['code_smartex_ens'])) if pd.notna(row['code_smartex_ens']) else None
                    if ens and ens in self.teachers:
                        jour_str = str(int(row['jour'])) if pd.notna(row['jour']) else None
                        seance = str(row['seance']).strip() if pd.notna(row['seance']) else None
                        
                        if jour_str and seance:
                            date = self.day_to_date.get(jour_str, None)
                            if date:
                                slot = f"{date} {seance}"
                                if slot not in self.teachers[ens]['indispo']:
                                    self.teachers[ens]['indispo'].append(slot)
                                    loaded_count += 1
                
                affected_teachers = len(set(str(int(row['code_smartex_ens'])) for _, row in df.iterrows() 
                                           if pd.notna(row['code_smartex_ens']) and str(int(row['code_smartex_ens'])) in self.teachers))
                
                self.update_status(f"✅ {loaded_count} vœux chargés pour {affected_teachers} enseignants")
                messagebox.showinfo("Succès",
                                  f"✅ Vœux chargés avec succès!\n\n"
                                  f"Indisponibilités: {loaded_count}\n"
                                  f"Enseignants concernés: {affected_teachers}")
            except Exception as e:
                self.update_status("❌ Erreur lors du chargement")
                messagebox.showerror("Erreur", f"Impossible de charger les vœux:\n\n{str(e)}")
    
    def configure_quotas(self):
        """Configure les quotas par grade"""
        quota_win = tk.Toplevel(self.root)
        quota_win.title("Configuration des Quotas")
        quota_win.geometry("500x600")
        quota_win.configure(bg=COLORS['bg'])
        quota_win.transient(self.root)
        quota_win.grab_set()
        
        # Header
        header = tk.Frame(quota_win, bg=COLORS['primary'], height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header,
                text="⚙️ Configuration des Quotas",
                font=('Arial', 16, 'bold'),
                bg=COLORS['primary'],
                fg='white').pack(pady=20)
        
        # Content
        content = tk.Frame(quota_win, bg=COLORS['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        tk.Label(content,
                text="Définissez le nombre de surveillances par grade:",
                font=('Arial', 11),
                bg=COLORS['bg'],
                fg=COLORS['text']).pack(pady=(0, 15))
        
        # Scrollable frame
        canvas = tk.Canvas(content, bg=COLORS['bg'], highlightthickness=0)
        scrollbar = ttk.Scrollbar(content, orient="vertical", command=canvas.yview)
        scroll_frame = tk.Frame(canvas, bg=COLORS['bg'])
        
        scroll_frame.bind("<Configure>", lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.create_window((0, 0), window=scroll_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        quota_entries = {}
        
        for grade in sorted(GRADE_QUOTAS.keys()):
            row = tk.Frame(scroll_frame, bg=COLORS['card'], relief=tk.FLAT, borderwidth=1)
            row.pack(fill=tk.X, pady=5, padx=2)
            
            tk.Label(row,
                    text=f"Grade {grade}:",
                    font=('Arial', 11, 'bold'),
                    bg=COLORS['card'],
                    fg=COLORS['text'],
                    width=15,
                    anchor='w').pack(side=tk.LEFT, padx=15, pady=15)
            
            entry = tk.Entry(row,
                           font=('Arial', 12),
                           width=8,
                           relief=tk.FLAT,
                           bg=COLORS['bg'],
                           justify='center')
            entry.insert(0, str(GRADE_QUOTAS[grade]))
            entry.pack(side=tk.LEFT, padx=10)
            quota_entries[grade] = entry
            
            tk.Label(row,
                    text="surveillance(s)",
                    font=('Arial', 10),
                    bg=COLORS['card'],
                    fg=COLORS['text_light']).pack(side=tk.LEFT, padx=10)
        
        canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        btn_frame = tk.Frame(quota_win, bg=COLORS['bg'])
        btn_frame.pack(pady=20)
        
        def save_quotas():
            try:
                for grade, entry in quota_entries.items():
                    quota = int(entry.get())
                    if quota < 0:
                        raise ValueError(f"Quota négatif pour {grade}")
                    GRADE_QUOTAS[grade] = quota
                
                for teacher in self.teachers:
                    self.teachers[teacher]['quota'] = GRADE_QUOTAS.get(self.teachers[teacher]['grade'], 2)
                
                self.update_status("✅ Quotas mis à jour")
                messagebox.showinfo("Succès", "✅ Quotas mis à jour avec succès!")
                quota_win.destroy()
            except ValueError as e:
                messagebox.showerror("Erreur", f"Valeur invalide:\n\n{str(e)}\n\nLes quotas doivent être des nombres positifs.")
        
        SimpleButton(btn_frame,
                    text="💾 Sauvegarder",
                    command=save_quotas,
                    bg_color=COLORS['success']).pack(side=tk.LEFT, padx=5)
        
        SimpleButton(btn_frame,
                    text="Annuler",
                    command=quota_win.destroy,
                    bg_color=COLORS['text_light']).pack(side=tk.LEFT, padx=5)
    
    def generate_planning(self):
        """Génère le planning"""
        if not self.slots or not self.teachers:
            messagebox.showerror("Attention",
                               "Veuillez d'abord charger:\n\n"
                               "• Les créneaux\n"
                               "• Les enseignants")
            return
        
        # Fenêtre de progression
        progress_win = tk.Toplevel(self.root)
        progress_win.title("Génération en cours")
        progress_win.geometry("600x250")
        progress_win.configure(bg=COLORS['bg'])
        progress_win.transient(self.root)
        progress_win.grab_set()
        
        # Header
        header = tk.Frame(progress_win, bg=COLORS['success'], height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(header,
                text="⏳ Génération du Planning",
                font=('Arial', 16, 'bold'),
                bg=COLORS['success'],
                fg='white').pack(pady=20)
        
        # Content
        content = tk.Frame(progress_win, bg=COLORS['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=40, pady=20)
        
        progress_bar = ttk.Progressbar(content,
                                      length=500,
                                      mode='determinate',
                                      style="Custom.Horizontal.TProgressbar")
        progress_bar.pack(pady=15)
        
        progress_label = tk.Label(content,
                                 text="Initialisation...",
                                 font=('Arial', 12),
                                 bg=COLORS['bg'],
                                 fg=COLORS['text'])
        progress_label.pack(pady=10)
        
        status_label = tk.Label(content,
                              text="Préparation de l'algorithme génétique",
                              font=('Arial', 10),
                              bg=COLORS['bg'],
                              fg=COLORS['text_light'])
        status_label.pack(pady=5)
        
        def update_progress(gen, total_gen, best_fitness):
            progress = (gen + 1) / total_gen * 100
            progress_bar['value'] = progress
            progress_label.config(text=f"Génération {gen+1} / {total_gen}")
            
            if best_fitness > -100:
                status_label.config(text="✅ Excellente solution trouvée!", fg=COLORS['success'])
            elif best_fitness > -500:
                status_label.config(text="✓ Solution acceptable", fg=COLORS['warning'])
            else:
                status_label.config(text="🔄 Optimisation en cours...", fg=COLORS['text_light'])
            
            progress_win.update()
        
        try:
            self.update_status("Génération du planning en cours...")
            self.best, self.best_fitness_history = run_ga_improved(self.slots, self.teachers, update_progress)
            
            progress_win.destroy()
            
            final_fitness = self.best_fitness_history[-1]
            quality = "Excellent" if final_fitness > -100 else "Acceptable" if final_fitness > -1000 else "À améliorer"
            
            self.display_planning_result()
            self.update_status(f"✅ Planning généré - Qualité: {quality} (Score: {final_fitness:.0f})")
            
            messagebox.showinfo("Succès",
                              f"✅ Planning généré avec succès!\n\n"
                              f"Qualité: {quality}\n"
                              f"Score: {final_fitness:.0f}\n\n"
                              f"Consultez la vue '📊 Qualité' pour plus de détails.")
        except Exception as e:
            progress_win.destroy()
            self.update_status("❌ Erreur lors de la génération")
            messagebox.showerror("Erreur", f"Erreur lors de la génération:\n\n{str(e)}")
    
    def display_planning_result(self):
        """Affiche le planning généré"""
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("date", "session", "heure", "profs", "enseignants")
        
        headers = {
            "date": ("📅 Date", 100),
            "session": ("Session", 80),
            "heure": ("Heure", 80),
            "profs": ("Nb Profs", 80),
            "enseignants": ("Enseignants Assignés", 700)
        }
        
        for col, (text, width) in headers.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width)
        
        for slot in sorted(self.best.keys()):
            date_part, session = slot.split()
            teachers_list = [str(t) for t in self.best[slot]]
            nb_profs = len(teachers_list)
            
            tag = "ok" if nb_profs >= 2 else "warning"
            
            self.tree.insert("", "end", values=(
                datetime.strptime(date_part, '%Y-%m-%d').strftime('%d/%m/%Y'),
                session,
                SESSION_TIMES.get(session, ""),
                f"{nb_profs} {'✓' if nb_profs >= 2 else '⚠️'}",
                ", ".join(teachers_list)
            ), tags=(tag,))
            
            # Distribution dans les salles
            slot_data = next((data for s, data in self.slots if s == slot), None)
            if slot_data:
                room_count = slot_data['room_count']
                teachers_per_room = max(1, len(teachers_list) // room_count)
                rooms = list(self.room_assignments[slot].keys())
                
                for room in rooms:
                    self.room_assignments[slot][room] = []
                
                for i, teacher in enumerate(teachers_list):
                    room_idx = min(i // teachers_per_room, len(rooms) - 1)
                    self.room_assignments[slot][rooms[room_idx]].append(teacher)
        
        self.tree.tag_configure("ok", background="#E8F5E9")
        self.tree.tag_configure("warning", background="#FFF3E0")
    
    def show_by_teacher(self):
        """Vue par enseignant"""
        if not self.best:
            messagebox.showwarning("Attention", "Veuillez d'abord générer le planning!")
            return
        
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("code", "nom", "grade", "quota", "assigne", "taux", "creneaux")
        
        headers = {
            "code": ("Code", 80),
            "nom": ("Nom Complet", 200),
            "grade": ("Grade", 70),
            "quota": ("Quota", 70),
            "assigne": ("Assigné", 70),
            "taux": ("Taux", 70),
            "creneaux": ("Créneaux", 500)
        }
        
        for col, (text, width) in headers.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width)
        
        teacher_slots = {t: [] for t in self.teachers}
        for slot in self.best:
            for teacher in self.best[slot]:
                teacher_slots[teacher].append(slot)
        
        for teacher in sorted(teacher_slots.keys()):
            if teacher_slots[teacher]:
                data = self.teachers[teacher]
                num_gardes = len(teacher_slots[teacher])
                taux = (num_gardes / data['quota'] * 100) if data['quota'] > 0 else 0
                
                if num_gardes > data['quota']:
                    tag = "over"
                elif num_gardes == data['quota']:
                    tag = "ok"
                else:
                    tag = "under"
                
                full_name = f"{data['nom']} {data['prenom']}"
                creneaux_str = ", ".join(sorted(teacher_slots[teacher])[:3])
                if len(teacher_slots[teacher]) > 3:
                    creneaux_str += f" ... (+{len(teacher_slots[teacher])-3})"
                
                self.tree.insert("", "end", values=(
                    teacher,
                    full_name,
                    data['grade'],
                    data['quota'],
                    num_gardes,
                    f"{taux:.0f}%",
                    creneaux_str
                ), tags=(tag,))
        
        self.tree.tag_configure("ok", background="#E8F5E9")
        self.tree.tag_configure("over", background="#FFEBEE")
        self.tree.tag_configure("under", background="#FFF9C4")
        
        self.update_status(f"Vue par enseignant - {len([t for t in teacher_slots if teacher_slots[t]])} enseignants assignés")
    
    def show_by_day(self):
        """Vue par jour"""
        if not self.best:
            messagebox.showwarning("Attention", "Veuillez d'abord générer le planning!")
            return
        
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("date", "jour", "sessions", "total", "details")
        
        headers = {
            "date": ("Date", 120),
            "jour": ("Jour", 100),
            "sessions": ("Sessions", 80),
            "total": ("Total Profs", 100),
            "details": ("Détails", 600)
        }
        
        for col, (text, width) in headers.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width)
        
        day_slots = {}
        for slot in self.best:
            day = slot.split()[0]
            if day not in day_slots:
                day_slots[day] = []
            day_slots[day].append(slot)
        
        jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
        
        for day in sorted(day_slots.keys()):
            date_obj = datetime.strptime(day, '%Y-%m-%d')
            jour_nom = jours[date_obj.weekday()]
            nb_sessions = len(day_slots[day])
            total_profs = sum(len(self.best[slot]) for slot in day_slots[day])
            
            details = ", ".join([f"{s.split()[1]} ({len(self.best[s])} profs)" for s in sorted(day_slots[day])])
            
            self.tree.insert("", "end", values=(
                date_obj.strftime('%d/%m/%Y'),
                jour_nom,
                nb_sessions,
                total_profs,
                details
            ))
        
        self.update_status(f"Vue par jour - {len(day_slots)} jours d'examen")
    
    def show_by_room(self):
        """Vue par salle"""
        if not self.best:
            messagebox.showwarning("Attention", "Veuillez d'abord générer le planning!")
            return
        
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("creneau", "salle", "nb", "statut", "enseignants")
        
        headers = {
            "creneau": ("Créneau", 150),
            "salle": ("Salle", 100),
            "nb": ("Nb Profs", 80),
            "statut": ("Statut", 100),
            "enseignants": ("Enseignants", 500)
        }
        
        for col, (text, width) in headers.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width)
        
        for slot in sorted(self.best.keys()):
            for room, teachers in sorted(self.room_assignments[slot].items()):
                nb = len(teachers)
                
                if nb == 2:
                    statut, tag = "✓ Optimal", "ok"
                elif nb < 2:
                    statut, tag = "⚠️ Insuffisant", "warning"
                elif nb <= 4:
                    statut, tag = "Acceptable", "acceptable"
                else:
                    statut, tag = "⚠️ Trop", "warning"
                
                self.tree.insert("", "end", values=(
                    slot,
                    room,
                    nb,
                    statut,
                    ", ".join(sorted(teachers))
                ), tags=(tag,))
        
        self.tree.tag_configure("ok", background="#E8F5E9")
        self.tree.tag_configure("acceptable", background="#FFF9C4")
        self.tree.tag_configure("warning", background="#FFEBEE")
        
        total_rooms = sum(len(self.room_assignments[s]) for s in self.room_assignments)
        self.update_status(f"Vue par salle - {total_rooms} salles au total")
    
    def show_planning_quality(self):
        """Affiche la qualité du planning"""
        if not self.best:
            messagebox.showwarning("Attention", "Veuillez d'abord générer le planning!")
            return
        
        slots_dict = {slot: data for slot, data in self.slots}
        fitness_score = fitness(self.best, self.teachers, slots_dict)
        
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("critere", "valeur", "statut")
        
        headers = {
            "critere": ("Critère", 400),
            "valeur": ("Valeur", 150),
            "statut": ("Statut", 200)
        }
        
        for col, (text, width) in headers.items():
            self.tree.heading(col, text=text)
            self.tree.column(col, width=width)
        
        # Score global
        quality = "Excellent" if fitness_score > -100 else \
                 "Acceptable" if fitness_score > -500 else \
                 "Moyen" if fitness_score > -1000 else "À améliorer"
        
        color = COLORS['success'] if fitness_score > -100 else \
               COLORS['warning'] if fitness_score > -500 else COLORS['danger']
        
        self.tree.insert("", "end", values=(
            "SCORE GLOBAL",
            f"{fitness_score:.0f}",
            quality
        ), tags=("header",))
        
        # Calcul des violations
        counts = {t: sum(1 for s in self.best if t in self.best[s]) for t in self.teachers}
        
        violations = {
            'min_profs': 0,
            'quota': 0,
            'voeux': 0,
            'consecutivity': check_consecutivity_violations(self.best, self.teachers, slots_dict)
        }
        
        for slot in self.best:
            slot_data = slots_dict[slot]
            min_needed = 2 * slot_data['room_count']
            unique = len(set(self.best[slot]))
            
            if unique < min_needed:
                violations['min_profs'] += 1
            
            for e in self.best[slot]:
                if counts[e] > self.teachers[e]['quota']:
                    violations['quota'] += 1
                if slot in self.teachers[e]['indispo']:
                    violations['voeux'] += 1
        
        self.tree.insert("", "end", values=("", "", ""))
        self.tree.insert("", "end", values=("CONTRAINTES", "", ""), tags=("header",))
        
        constraint_items = [
            ("Minimum 2 profs par salle", violations['min_profs']),
            ("Respect des quotas", violations['quota']),
            ("Respect des vœux", violations['voeux']),
            ("Consécutivité (pas de S1→S4)", violations['consecutivity'])
        ]
        
        for label, count in constraint_items:
            statut = "✅ OK" if count == 0 else f"❌ {count} violation(s)"
            tag = "ok" if count == 0 else "error"
            self.tree.insert("", "end", values=(label, count, statut), tags=(tag,))
        
        self.tree.tag_configure("header", font=('Arial', 11, 'bold'), background=COLORS['border'])
        self.tree.tag_configure("ok", background="#E8F5E9")
        self.tree.tag_configure("error", background="#FFEBEE")
        
        self.update_status(f"Qualité du planning: {quality} (Score: {fitness_score:.0f})")
    
    def export_csv(self):
        """Exporte en CSV"""
        if not self.best:
            messagebox.showwarning("Attention", "Veuillez d'abord générer le planning!")
            return
        
        file = filedialog.asksaveasfilename(
            title="Enregistrer le planning",
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        
        if file:
            try:
                data = []
                for slot in sorted(self.best.keys()):
                    date_part, session = slot.split()
                    data.append({
                        "Date": datetime.strptime(date_part, '%Y-%m-%d').strftime('%d/%m/%Y'),
                        "Session": session,
                        "Heure": SESSION_TIMES.get(session, ""),
                        "Nb_Enseignants": len(self.best[slot]),
                        "Enseignants": ", ".join([str(t) for t in self.best[slot]])
                    })
                
                df = pd.DataFrame(data)
                df.to_csv(file, index=False, encoding='utf-8-sig')
                self.update_status(f"✅ Exporté vers {file}")
                messagebox.showinfo("Succès", f"✅ Planning exporté avec succès!\n\n{file}")
            except Exception as e:
                self.update_status("❌ Erreur d'export")
                messagebox.showerror("Erreur", f"Erreur lors de l'export:\n\n{str(e)}")
    
    def export_pdf(self):
        """Exporte en PDF"""
        if not self.best:
            messagebox.showwarning("Attention", "Veuillez d'abord générer le planning!")
            return
        
        file = filedialog.asksaveasfilename(
            title="Enregistrer le planning",
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")]
        )
        
        if file:
            try:
                c = canvas.Canvas(file, pagesize=letter)
                width, height = letter
                y = height - 50
                
                c.setFont("Helvetica-Bold", 18)
                c.drawString(50, y, "Planning de Surveillance des Examens")
                y -= 30
                
                c.setFont("Helvetica", 10)
                c.drawString(50, y, f"Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}")
                y -= 40
                
                c.setFont("Helvetica", 9)
                for slot in sorted(self.best.keys()):
                    if y < 50:
                        c.showPage()
                        y = height - 50
                        c.setFont("Helvetica", 9)
                    
                    date_part, session = slot.split()
                    teachers_str = ", ".join([str(t) for t in self.best[slot]])
                    
                    c.setFont("Helvetica-Bold", 10)
                    c.drawString(50, y, f"{datetime.strptime(date_part, '%Y-%m-%d').strftime('%d/%m/%Y')} - {session} ({SESSION_TIMES.get(session, '')})")
                    y -= 15
                    
                    c.setFont("Helvetica", 9)
                    if len(teachers_str) > 80:
                        words = teachers_str.split(", ")
                        line = ""
                        for word in words:
                            if len(line + word) < 80:
                                line += word + ", "
                            else:
                                c.drawString(70, y, line)
                                y -= 12
                                line = word + ", "
                        if line:
                            c.drawString(70, y, line.rstrip(", "))
                            y -= 15
                    else:
                        c.drawString(70, y, teachers_str)
                        y -= 15
                    
                    y -= 5
                
                c.save()
                self.update_status(f"✅ Exporté vers {file}")
                messagebox.showinfo("Succès", f"✅ Planning exporté avec succès!\n\n{file}")
            except Exception as e:
                self.update_status("❌ Erreur d'export")
                messagebox.showerror("Erreur", f"Erreur lors de l'export:\n\n{str(e)}")
    
    def run(self):
        """Lance l'application de surveillance"""
        self.root.mainloop()

# =============================================================================
# POINT D'ENTRÉE PRINCIPAL
# =============================================================================

def main():
    """Fonction principale qui gère le flux d'authentification"""
    
    def launch_surveillance_app():
        """Callback appelé après une authentification réussie"""
        print("🚀 Lancement de l'application de surveillance...")
        app = SurveillanceApp()
        app.run()
    
    # D'abord lancer l'authentification
    print("=" * 60)
    print("SYSTÈME DE GESTION DES SURVEILLANCES - AUTHENTIFICATION")
    print("=" * 60)
    
    login_app = ModernLoginApp(launch_surveillance_app)
    login_app.run()

if __name__ == "__main__":
    main()