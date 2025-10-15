import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import random
import numpy as np
import customtkinter as ctk
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Configuration initiale des quotas par grade
GRADE_QUOTAS = {
    "PR": 8,
    "MA": 7,
    "V": 6,
    "PTC": 5,
    "AC": 4,
    "VA": 4,
    "AS": 4,
    "EX": 4,
    "MC": 4,
    "PES": 4
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

def parse_datetime(slot_str):
    """Parse un créneau en date et ordre de session"""
    date_part, session = slot_str.split()
    return datetime.strptime(date_part, '%Y-%m-%d'), SESSION_ORDER[session]

def get_teacher_slots(assignment, teacher):
    """Récupère tous les créneaux assignés à un enseignant"""
    return sorted([
        (parse_datetime(slot)[0], parse_datetime(slot)[1]) 
        for slot in assignment if teacher in assignment[slot]
    ])

def check_consecutivity_violations(assignment, teachers, slots_dict):
    """
    Vérifie les violations de consécutivité
    Violation = même jour ET gap entre sessions > 1 (ex: S1 puis S4)
    """
    violations = 0
    for teacher in teachers:
        if not teachers[teacher]['participe_surveillance']:
            continue
        teacher_slots = get_teacher_slots(assignment, teacher)
        for i in range(len(teacher_slots) - 1):
            date1, order1 = teacher_slots[i]
            date2, order2 = teacher_slots[i + 1]
            
            # Violation SI même jour ET gap > 1
            if date1 == date2 and abs(order2 - order1) > 1:
                violations += 1
    return violations

def dispersion_penalty(teacher_slots):
    """
    Pénalité pour mauvaise dispersion temporelle
    Encourage les sessions consécutives le même jour
    """
    if len(teacher_slots) < 2:
        return 0
    penalty = 0
    for i in range(len(teacher_slots) - 1):
        date1, order1 = teacher_slots[i]
        date2, order2 = teacher_slots[i + 1]
        if date1 == date2:
            gap = abs(order2 - order1)
            # Bonus si consécutif (gap = 1)
            penalty -= max(0, 2 - gap) * 10
    return penalty

def calculate_grade_equity(counts, teachers):
    """Calcule l'équité par grade (variance)"""
    grades = set(t['grade'] for t in teachers.values())
    total_variance = 0
    for grade in grades:
        grade_counts = [counts[e] for e in teachers if teachers[e]['grade'] == grade]
        if grade_counts and len(grade_counts) > 1:
            variance = np.var(grade_counts)
            total_variance += variance
    return total_variance

def fitness(assignment, teachers, slots_dict):
    """
    Fonction de fitness améliorée
    Pénalités:
    - Contraintes rigides: -1000 par violation
    - Contraintes souples: ajustements graduels
    """
    score = 0.0
    counts = {e: 0 for e in teachers}
    
    # 1. Vérification des contraintes par créneau
    for slot in assignment:
        unique_assigned = set(assignment[slot])
        slot_data = slots_dict[slot]
        room_count = slot_data['room_count']
        min_needed = 2 * room_count
        max_needed = 4 * room_count
        
        # Contrainte: minimum profs par salle
        if len(unique_assigned) < min_needed:
            score -= 1000 * (min_needed - len(unique_assigned))
        
        # Contrainte: maximum profs par salle
        if len(unique_assigned) > max_needed:
            score -= 1000 * (len(unique_assigned) - max_needed)
        
        # Bonus si exactement 2 profs/salle (optimal)
        if len(unique_assigned) == min_needed:
            score += 100
        
        # Pénalité pour doublons (ne devrait pas arriver)
        if len(assignment[slot]) != len(unique_assigned):
            score -= 500
        
        # Compter les assignations et vérifier contraintes
        for e in assignment[slot]:
            counts[e] += 1
            
            # Contrainte: respect des quotas
            if counts[e] > teachers[e]['quota']:
                score -= 1000 * (counts[e] - teachers[e]['quota'])
            
            # Contrainte: respect des vœux d'indisponibilité
            if slot in teachers[e]['indispo']:
                score -= 1000
    
    # 2. Vérification de la consécutivité (CORRIGÉE)
    violations = check_consecutivity_violations(assignment, teachers, slots_dict)
    score -= 1000 * violations
    
    # 3. Bonus pour bonne dispersion temporelle
    for e in teachers:
        if not teachers[e]['participe_surveillance']:
            continue
        t_slots = get_teacher_slots(assignment, e)
        score += dispersion_penalty(t_slots)
    
    # 4. Équité par grade (variance minimale)
    total_variance = calculate_grade_equity(counts, teachers)
    score -= 10 * total_variance
    
    return score

def generate_population(pop_size, slots, teachers):
    """Génère la population initiale"""
    population = []
    teacher_list = [str(e) for e in teachers if teachers[e]['participe_surveillance']]
    
    for _ in range(pop_size):
        assignment = {}
        for slot, slot_data in slots:
            min_needed = 2 * slot_data['room_count']
            available = [e for e in teacher_list if slot not in teachers[e]['indispo']]
            
            if available:
                selected = random.sample(available, min(min_needed, len(available)))
                # Compléter si nécessaire
                while len(selected) < min_needed and available:
                    selected.append(random.choice(available))
                assignment[slot] = selected[:4 * slot_data['room_count']]
            else:
                assignment[slot] = []
        
        population.append(assignment)
    return population

def crossover(parent1, parent2):
    """Croisement uniforme entre deux parents"""
    child = {}
    keys = list(parent1.keys())
    midpoint = len(keys) // 2
    
    for i in range(midpoint):
        child[keys[i]] = parent1[keys[i]][:]
    for i in range(midpoint, len(keys)):
        child[keys[i]] = parent2[keys[i]][:]
    
    return child

def mutate_improved(assignment, teachers, slots, slots_dict):
    """
    Mutation améliorée avec 3 stratégies:
    1. Swap: Échange entre deux créneaux
    2. Reassign: Réassigner un prof surchargé vers un sous-chargé
    3. Redistribute: Équilibrer au sein d'un grade
    """
    mutation_type = random.choice(['swap', 'reassign', 'redistribute'])
    
    if mutation_type == 'swap':
        # Échange entre 2 créneaux
        slot_keys = list(assignment.keys())
        if len(slot_keys) >= 2:
            slot1, slot2 = random.sample(slot_keys, 2)
            if assignment[slot1] and assignment[slot2]:
                e1 = random.choice(assignment[slot1])
                e2 = random.choice(assignment[slot2])
                
                # Vérifier que l'échange est valide
                if (slot2 not in teachers[e1]['indispo'] and 
                    slot1 not in teachers[e2]['indispo']):
                    # Effectuer l'échange
                    idx1 = assignment[slot1].index(e1)
                    idx2 = assignment[slot2].index(e2)
                    assignment[slot1][idx1] = e2
                    assignment[slot2][idx2] = e1
    
    elif mutation_type == 'reassign':
        # Réassigner un prof surchargé vers un prof sous-chargé
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
        # Redistribuer pour équilibrer un grade
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
    """Répare une solution pour respecter les contraintes minimales"""
    for slot in child:
        slot_data = slots_dict[slot]
        min_needed = 2 * slot_data['room_count']
        max_needed = 4 * slot_data['room_count']
        
        # Supprimer les doublons
        child[slot] = list(set(child[slot]))
        
        # Compléter si insuffisant
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
        
        # Réduire si trop
        if len(child[slot]) > max_needed:
            child[slot] = child[slot][:max_needed]
    
    return child

def run_ga_improved(slots, teachers, progress_callback=None):
    """
    Algorithme génétique amélioré avec:
    - Population plus grande
    - Élitisme renforcé
    - Sélection par tournoi
    - Mutation adaptative
    - Détection de stagnation
    """
    slots_dict = {slot: data for slot, data in slots}
    pop_size = 100
    generations = 200
    elite_size = 10
    
    pop = generate_population(pop_size, slots, teachers)
    best_fitness_history = []
    stagnation_counter = 0
    
    for gen in range(generations):
        # Évaluation avec fitness
        pop_with_fitness = [(ind, fitness(ind, teachers, slots_dict)) for ind in pop]
        pop_with_fitness.sort(key=lambda x: x[1], reverse=True)
        
        best_fitness = pop_with_fitness[0][1]
        best_fitness_history.append(best_fitness)
        
        # Détection de stagnation
        if gen > 50:
            if best_fitness_history[-1] == best_fitness_history[-50]:
                stagnation_counter += 1
            else:
                stagnation_counter = 0
        
        # Mutation adaptative: augmenter si stagnation
        mutation_rate = 0.2 if stagnation_counter < 10 else 0.5
        
        # Callback pour mise à jour UI
        if progress_callback:
            progress_callback(gen, generations, best_fitness)
        
        # Élitisme: garder les meilleurs
        new_pop = [ind for ind, _ in pop_with_fitness[:elite_size]]
        
        # Génération de nouveaux individus
        while len(new_pop) < pop_size:
            # Sélection par tournoi
            tournament1 = random.sample(pop_with_fitness[:pop_size//2], 5)
            p1 = max(tournament1, key=lambda x: x[1])[0]
            
            tournament2 = random.sample(pop_with_fitness[:pop_size//2], 5)
            p2 = max(tournament2, key=lambda x: x[1])[0]
            
            # Croisement
            child = crossover(p1, p2)
            
            # Mutation
            if random.random() < mutation_rate:
                child = mutate_improved(child, teachers, slots, slots_dict)
            
            # Réparation
            child = repair_solution(child, teachers, slots_dict)
            
            new_pop.append(child)
        
        pop = new_pop
    
    return pop_with_fitness[0][0], best_fitness_history
system_font = "Segoe UI"
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestion des Créneaux de Surveillance - Version Améliorée")
        self.geometry("1200x900")
        
        # Frame principal avec scrollbar
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Section 1: Chargement des données
        load_frame = tk.LabelFrame(main_frame, text="📁 Chargement des Données", font=("Arial", 10, "bold"))
        load_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(load_frame, text="Charger Créneaux (Excel)", command=self.load_slots, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(load_frame, text="Charger Enseignants (Excel)", command=self.load_teachers, bg="#2196F3", fg="white").pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(load_frame, text="Charger Vœux (Excel)", command=self.load_wishes, bg="#FF9800", fg="white").pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(load_frame, text="⚙️ Configurer Quotas", command=self.configure_quotas, bg="#9C27B0", fg="white").pack(side=tk.LEFT, padx=5, pady=5)
        
        # Section 2: Génération
        gen_frame = tk.LabelFrame(main_frame, text="🧬 Génération du Planning", font=("Arial", 10, "bold"))
        gen_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(gen_frame, text="▶️ Générer Planning", command=self.generate_planning, bg="#4CAF50", fg="white", font=("Arial", 12, "bold")).pack(pady=10)
        
        # Section 3: Visualisation
        view_frame = tk.LabelFrame(main_frame, text="👁️ Visualisation", font=("Arial", 10, "bold"))
        view_frame.pack(fill=tk.X, pady=5)
        
        view_buttons_frame = tk.Frame(view_frame)
        view_buttons_frame.pack(pady=5)
        
        tk.Button(view_buttons_frame, text="👤 Par Enseignant", command=self.show_by_teacher).pack(side=tk.LEFT, padx=5)
        self.teacher_search = tk.Entry(view_buttons_frame, width=20)
        self.teacher_search.pack(side=tk.LEFT, padx=5)
        self.teacher_search.bind('<KeyRelease>', lambda e: self.filter_tree('teacher'))
        
        tk.Button(view_buttons_frame, text="📅 Par Jour", command=self.show_by_day).pack(side=tk.LEFT, padx=5)
        self.day_search = tk.Entry(view_buttons_frame, width=20)
        self.day_search.pack(side=tk.LEFT, padx=5)
        self.day_search.bind('<KeyRelease>', lambda e: self.filter_tree('day'))
        
        view_buttons_frame2 = tk.Frame(view_frame)
        view_buttons_frame2.pack(pady=5)
        
        tk.Button(view_buttons_frame2, text="🚪 Par Salle", command=self.show_by_room).pack(side=tk.LEFT, padx=5)
        self.room_search = tk.Entry(view_buttons_frame2, width=20)
        self.room_search.pack(side=tk.LEFT, padx=5)
        self.room_search.bind('<KeyRelease>', lambda e: self.filter_tree('room'))
        
        tk.Button(view_buttons_frame2, text="📊 Qualité du Planning", command=self.show_planning_quality, bg="#E91E63", fg="white", font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=5)
        tk.Button(view_buttons_frame2, text="ℹ️ Infos Générales", command=self.show_general_info).pack(side=tk.LEFT, padx=5)
        
        # Section 4: Export
        export_frame = tk.LabelFrame(main_frame, text="💾 Export", font=("Arial", 10, "bold"))
        export_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(export_frame, text="📄 Exporter CSV", command=self.export_csv).pack(side=tk.LEFT, padx=5, pady=5)
        tk.Button(export_frame, text="📑 Exporter PDF", command=self.export_pdf).pack(side=tk.LEFT, padx=5, pady=5)
        
        # Treeview avec scrollbars
        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        tree_scroll_y = tk.Scrollbar(tree_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        
        tree_scroll_x = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
        self.tree = ttk.Treeview(tree_frame, 
                                 columns=("Col1", "Col2"), 
                                 show="headings",
                                 yscrollcommand=tree_scroll_y.set,
                                 xscrollcommand=tree_scroll_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)
        
        # Variables
        self.slots = []
        self.teachers = {}
        self.best = None
        self.best_fitness_history = []
        self.day_to_date = {}
        self.room_assignments = {}
        self.quota_window = None
        self.quota_entries = {}

    def filter_tree(self, view):
        """Filtre les éléments du treeview selon la recherche"""
        search_text = ''
        if view == 'teacher':
            search_text = self.teacher_search.get().lower()
        elif view == 'day':
            search_text = self.day_search.get().lower()
        elif view == 'room':
            search_text = self.room_search.get().lower()

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
            if not match:
                self.tree.detach(item)
            else:
                self.tree.reattach(item, '', 'end')

    def load_slots(self):
        """Charge les créneaux depuis Excel"""
        file = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file:
            try:
                engine = 'openpyxl' if file.endswith('.xlsx') else 'xlrd'
                df = pd.read_excel(file, engine=engine)
                
                df['dateExam'] = pd.to_datetime(df['dateExam'], format='%d/%m/%Y', dayfirst=True)
                df['h_debut_time'] = df['h_debut'].str.extract(r'(\d{2}:\d{2}:\d{2})', expand=False)
                df['h_fin_time'] = df['h_fin'].str.extract(r'(\d{2}:\d{2}:\d{2})', expand=False)
                df['h_debut'] = pd.to_datetime(df['dateExam'].astype(str) + ' ' + df['h_debut_time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
                df['h_fin'] = pd.to_datetime(df['dateExam'].astype(str) + ' ' + df['h_fin_time'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
                
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
                
                messagebox.showinfo("✅ Succès", f"{len(self.slots)} créneaux chargés avec succès!")
            except Exception as e:
                messagebox.showerror("❌ Erreur", f"Erreur lors du chargement des créneaux:\n{str(e)}")

    def load_teachers(self):
        """Charge les enseignants depuis Excel"""
        file = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file:
            try:
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
                messagebox.showinfo("✅ Succès", f"{len(self.teachers)} enseignants chargés\n({participating} participent à la surveillance)")
            except Exception as e:
                messagebox.showerror("❌ Erreur", f"Erreur lors du chargement des enseignants:\n{str(e)}")

    def load_wishes(self):
        """Charge les vœux d'indisponibilité depuis Excel"""
        file = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file:
            if not self.day_to_date:
                messagebox.showerror("❌ Erreur", "Veuillez d'abord charger les créneaux!")
                return
            
            try:
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
                
                messagebox.showinfo("✅ Succès", f"Vœux chargés: {loaded_count} indisponibilités\npour {affected_teachers} enseignants")
            except Exception as e:
                messagebox.showerror("❌ Erreur", f"Erreur lors du chargement des vœux:\n{str(e)}")

    def configure_quotas(self):
        """Ouvre la fenêtre de configuration des quotas"""
        if self.quota_window and self.quota_window.winfo_exists():
            self.quota_window.lift()
            return
        
        self.quota_window = tk.Toplevel(self)
        self.quota_window.title("⚙️ Configuration des Quotas par Grade")
        self.quota_window.geometry("350x400")
        
        tk.Label(self.quota_window, text="Entrez les quotas par grade:", font=("Arial", 11, "bold")).pack(pady=10)
        
        scroll_frame = tk.Frame(self.quota_window)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=10)
        
        for grade in sorted(GRADE_QUOTAS.keys()):
            frame = tk.Frame(scroll_frame)
            tk.Label(frame, text=f"{grade}:", width=10, anchor='w').pack(side=tk.LEFT)
            entry = tk.Entry(frame, width=10)
            entry.insert(0, str(GRADE_QUOTAS[grade]))
            entry.pack(side=tk.LEFT, padx=5)
            self.quota_entries[grade] = entry
            frame.pack(pady=3)
        
        button_frame = tk.Frame(self.quota_window)
        button_frame.pack(pady=10)
        tk.Button(button_frame, text="💾 Sauvegarder", command=self.save_quotas, bg="#4CAF50", fg="white").pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="❌ Annuler", command=self.quota_window.destroy).pack(side=tk.LEFT, padx=5)

    def save_quotas(self):
        """Sauvegarde les quotas configurés"""
        try:
            for grade, entry in self.quota_entries.items():
                quota = int(entry.get())
                if quota < 0:
                    raise ValueError(f"Quota négatif pour {grade}")
                GRADE_QUOTAS[grade] = quota
            
            # Mettre à jour les quotas des enseignants
            for teacher in self.teachers:
                self.teachers[teacher]['quota'] = GRADE_QUOTAS.get(self.teachers[teacher]['grade'], 2)
            
            messagebox.showinfo("✅ Succès", "Quotas mis à jour avec succès!")
            if self.quota_window:
                self.quota_window.destroy()
        except ValueError as e:
            messagebox.showerror("❌ Erreur", f"Valeur invalide: {str(e)}\nLes quotas doivent être des nombres positifs.")

    def generate_planning(self):
        """Génère le planning avec barre de progression"""
        if not self.slots or not self.teachers:
            messagebox.showerror("❌ Erreur", "Veuillez charger les créneaux et les enseignants d'abord!")
            return
        
        # Fenêtre de progression
        progress_window = tk.Toplevel(self)
        progress_window.title("⏳ Génération en cours...")
        progress_window.geometry("500x200")
        progress_window.transient(self)
        progress_window.grab_set()
        
        tk.Label(progress_window, text="🧬 Optimisation génétique en cours...", font=("Arial", 12, "bold")).pack(pady=15)
        
        progress_bar = ttk.Progressbar(progress_window, length=400, mode='determinate')
        progress_bar.pack(pady=10)
        
        progress_label = tk.Label(progress_window, text="Génération 0/500", font=("Arial", 10))
        progress_label.pack(pady=5)
        
        fitness_label = tk.Label(progress_window, text="Fitness: N/A", font=("Arial", 10))
        fitness_label.pack(pady=5)
        
        status_label = tk.Label(progress_window, text="Initialisation...", font=("Arial", 9), fg="gray")
        status_label.pack(pady=5)
        
        def update_progress(gen, total_gen, best_fitness):
            progress = (gen + 1) / total_gen * 100
            progress_bar['value'] = progress
            progress_label.config(text=f"Génération {gen+1}/{total_gen}")
            fitness_label.config(text=f"Meilleur fitness: {best_fitness:.0f}")
            
            # Status contextuel
            if best_fitness > -100:
                status_label.config(text="🟢 Solution excellente trouvée!", fg="green")
            elif best_fitness > -500:
                status_label.config(text="🟡 Solution acceptable", fg="orange")
            elif best_fitness > -1000:
                status_label.config(text="🟠 Optimisation en cours...", fg="orange")
            else:
                status_label.config(text="🔴 Recherche de solution...", fg="red")
            
            progress_window.update()
        
        try:
            # Lancer l'algorithme génétique
            self.best, self.best_fitness_history = run_ga_improved(self.slots, self.teachers, update_progress)
            
            progress_window.destroy()
            
            # Afficher le résultat dans le treeview
            self.display_planning_result()
            
            final_fitness = self.best_fitness_history[-1]
            quality = "🟢 Excellent" if final_fitness > -100 else \
                     "🟡 Acceptable" if final_fitness > -1000 else "🔴 Problématique"
            
            messagebox.showinfo("✅ Planning généré!", 
                              f"Planning généré avec succès!\n\n"
                              f"Qualité: {quality}\n"
                              f"Score final: {final_fitness:.0f}\n\n"
                              f"Utilisez '📊 Qualité du Planning' pour voir les détails.")
        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("❌ Erreur", f"Erreur lors de la génération:\n{str(e)}")

    def display_planning_result(self):
        """Affiche le planning généré dans le treeview"""
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Créneau", "Enseignants")
        self.tree.heading("Créneau", text="Créneau")
        self.tree.heading("Enseignants", text="Enseignants Assignés")
        self.tree.column("Créneau", width=150)
        self.tree.column("Enseignants", width=600)
        for slot in sorted(self.best.keys()):
            teachers_assigned = [str(teacher) for teacher in self.best[slot]]
            self.tree.insert("", "end", values=(slot, ", ".join(teachers_assigned)))
            
            # Distribuer les enseignants dans les salles
            slot_data = next((data for s, data in self.slots if s == slot), None)
            if slot_data:
                room_count = slot_data['room_count']
                teachers_per_room = max(1, len(teachers_assigned) // room_count)
                rooms = list(self.room_assignments[slot].keys())
                
                # Réinitialiser les salles
                for room in rooms:
                    self.room_assignments[slot][room] = []
                
                # Distribuer
                for i, teacher in enumerate(teachers_assigned):
                    room_idx = min(i // teachers_per_room, len(rooms) - 1)
                    self.room_assignments[slot][rooms[room_idx]].append(teacher)

    def show_by_teacher(self):
        """Vue par enseignant avec statistiques complètes"""
        if not self.best:
            messagebox.showerror("❌ Erreur", "Veuillez générer le planning d'abord!")
            return
        
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Code", "Nom", "Prénom", "Grade", "Quota", "Assigné", "Créneaux", "Indispos")
        
        cols = {
            "Code": 80,
            "Nom": 120,
            "Prénom": 120,
            "Grade": 60,
            "Quota": 60,
            "Assigné": 80,
            "Créneaux": 300,
            "Indispos": 200
        }
        
        for col, width in cols.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width)
        
        # Compter les assignations
        teacher_slots = {teacher: [] for teacher in self.teachers}
        for slot in self.best:
            for teacher in self.best[slot]:
                teacher_slots[teacher].append(slot)
        
        # Enseignants assignés
        for teacher in sorted(teacher_slots.keys()):
            if teacher_slots[teacher]:  # A des assignations
                data = self.teachers[teacher]
                num_gardes = len(teacher_slots[teacher])
                tag = "over_quota" if num_gardes > data['quota'] else ""
                
                self.tree.insert("", "end", values=(
                    teacher,
                    data['nom'],
                    data['prenom'],
                    data['grade'],
                    data['quota'],
                    f"{num_gardes} {'⚠️' if num_gardes > data['quota'] else '✓'}",
                    ", ".join(sorted(teacher_slots[teacher])),
                    ", ".join(sorted(data['indispo'])) if data['indispo'] else "Aucune"
                ), tags=(tag,))
        
        # Enseignants non assignés (qui participent)
        assigned_teachers = set().union(*self.best.values())
        available_teachers = {t for t in self.teachers 
                            if self.teachers[t]['participe_surveillance'] 
                            and t not in assigned_teachers}
        
        for teacher in sorted(available_teachers):
            data = self.teachers[teacher]
            self.tree.insert("", "end", values=(
                teacher,
                data['nom'],
                data['prenom'],
                data['grade'],
                data['quota'],
                "0 ⚠️",
                "Non assigné",
                ", ".join(sorted(data['indispo'])) if data['indispo'] else "Aucune"
            ), tags=("unassigned",))
        
        # Style des tags
        self.tree.tag_configure("over_quota", background="#ffcccc")
        self.tree.tag_configure("unassigned", background="#ffffcc")

    def show_by_day(self):
        """Vue par jour"""
        if not self.best:
            messagebox.showerror("❌ Erreur", "Veuillez générer le planning d'abord!")
            return
        
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Jour", "Nombre de créneaux", "Créneaux")
        self.tree.heading("Jour", text="Jour")
        self.tree.heading("Nombre de créneaux", text="Nb Créneaux")
        self.tree.heading("Créneaux", text="Détails des Créneaux")
        
        self.tree.column("Jour", width=150)
        self.tree.column("Nombre de créneaux", width=120)
        self.tree.column("Créneaux", width=500)
        
        day_slots = {}
        for slot in self.best:
            day = slot.split()[0]
            if day not in day_slots:
                day_slots[day] = []
            day_slots[day].append(slot)
        
        for day in sorted(day_slots.keys()):
            slots_str = ", ".join(sorted(day_slots[day]))
            self.tree.insert("", "end", values=(day, len(day_slots[day]), slots_str))

    # def show_by_room(self):
    #     """Vue par salle avec les enseignants assignés"""
    #     if not self.best:
    #         messagebox.showerror("❌ Erreur", "Veuillez générer le planning d'abord!")
    #         return
        
    #     self.tree.delete(*self.tree.get_children())
    #     self.tree["columns"] = ("Créneau", "Salle", "Nb Profs", "Enseignants")
    #     self.tree.heading("Créneau", text="Créneau")
    #     self.tree.heading("Salle", text="Salle")
    #     self.tree.heading("Nb Profs", text="Nb Profs")
    #     self.tree.heading("Enseignants", text="Enseignants Assignés")
        
    #     self.tree.column("Créneau", width=150)
    #     self.tree.column("Salle", width=100)
    #     self.tree.column("Nb Profs", width=80)
    #     self.tree.column("Enseignants", width=500)
        
    #     for slot in sorted(self.best.keys()):
    #         for room, teachers in sorted(self.room_assignments[slot].items()):
    #             nb_profs = len(teachers)
    #             tag = "optimal" if nb_profs == 2 else "acceptable" if nb_profs <= 4 else "problem"
                
    #             self.tree.insert("", "end", values=(
    #                 slot, 
    #                 room, 
    #                 f"{nb_profs} {'✓' if nb_profs == 2 else '⚠️' if nb_profs > 4 else ''}", 
    #                 ", ".join(sorted(teachers))
    #             ), tags=(tag,))
        
    #     self.tree.tag_configure("optimal", background="#ccffcc")
    #     self.tree.tag_configure("acceptable", background="#ffffcc")
    #     self.tree.tag_configure("problem", background="#ffcccc")
    def show_by_room(self):
        if not self.best:
            messagebox.showerror("❌ Erreur", "Veuillez générer le planning d'abord!")
            return
    
        self.clear_content()
        self.page_title.configure(text="📍 Vue par Salle")
    
    # Control panel
        control_frame = ctk.CTkFrame(self.content_frame, fg_color="transparent")
        control_frame.pack(fill="x", pady=(0, 20))
    
    # Room filter dropdown
        filter_left = ctk.CTkFrame(control_frame, fg_color="transparent")
        filter_left.pack(side="left")
    
        ctk.CTkLabel(
        filter_left,
        text="Filtrer:",
        font=ctk.CTkFont(family=system_font, size=13),
        text_color="#37352f"
        ).pack(side="left", padx=(0, 10))
    
    # Get unique rooms from data
        all_rooms = set()
        for slot_rooms in self.room_assignments.values():
            all_rooms.update(slot_rooms.keys())
        room_list = ["Toutes les salles"] + sorted(all_rooms)
    
        self.room_filter = ctk.CTkComboBox(
        filter_left,
        values=room_list,
        width=200,
        height=36,
        font=ctk.CTkFont(family=system_font, size=13),
        border_width=1,
        border_color="#e3e2e0",
        button_color="#2383e2",
        button_hover_color="#1a6dc9",
        dropdown_fg_color="#ffffff",
        command=lambda _: self.refresh_room_calendar()
        )
        self.room_filter.pack(side="left")
        self.room_filter.set("Toutes les salles")
    
        # Legend
        legend_frame = ctk.CTkFrame(control_frame, fg_color="transparent")
        legend_frame.pack(side="right")
    
        self.create_legend_item(legend_frame, "● Optimal (2 profs)", "#d3f8d3", 0)
        self.create_legend_item(legend_frame, "● Acceptable (3-4)", "#fff4cc", 1)
        self.create_legend_item(legend_frame, "● Problème (>4)", "#ffd4d4", 2)
    
    # Scrollable calendar container
        self.calendar_container = ctk.CTkScrollableFrame(
            self.content_frame,
        fg_color="#ffffff",
        corner_radius=12,
        border_width=1,
        border_color="#e3e2e0"
    )
        self.calendar_container.pack(fill="both", expand=True)
    
    # Create calendar grid
        self.create_calendar_grid()

    def create_legend_item(self, parent, text, color, index):
        """Créer un élément de légende"""
        item_frame = ctk.CTkFrame(parent, fg_color="transparent")
        item_frame.pack(side="left", padx=10)
    
        color_box = ctk.CTkFrame(
        item_frame, 
        width=16, 
        height=16, 
        corner_radius=4, 
        fg_color=color, 
        border_width=1, 
        border_color="#e3e2e0"
    )
        color_box.pack(side="left", padx=(0, 6))
        color_box.pack_propagate(False)
    
        ctk.CTkLabel(
        item_frame,
        text=text,
        font=ctk.CTkFont(family=system_font, size=12),
        text_color="#37352f"
        ).pack(side="left")

    def create_calendar_grid(self):
        """Créer la grille du calendrier"""
        # Group slots by day
        days_schedule = {}
        for slot in sorted(self.best.keys()):
        # Extract day from slot (format: "Jour Session" or similar)
            parts = slot.split()
            day = parts[0] if parts else slot
            session = parts[1] if len(parts) > 1 else "S1"
        
            if day not in days_schedule:
                days_schedule[day] = {}
            days_schedule[day][session] = slot
    
    # Calendar grid header
        grid_frame = ctk.CTkFrame(self.calendar_container, fg_color="transparent")
        grid_frame.pack(fill="both", expand=True, padx=20, pady=20)
    
    # Configure grid weights
        grid_frame.grid_columnconfigure(0, weight=0, minsize=100)  # Time column
        for i in range(1, len(days_schedule) + 1):
            grid_frame.grid_columnconfigure(i, weight=1, minsize=250)
    
    # Header row - Days
        ctk.CTkLabel(
        grid_frame,
        text="",
        font=ctk.CTkFont(family=system_font, size=12, weight="bold"),
        text_color="#37352f"
    ).grid(row=0, column=0, sticky="nsew", padx=2, pady=2)
    
        col_idx = 1
        for day in sorted(days_schedule.keys()):
            day_header = ctk.CTkFrame(
            grid_frame,
            corner_radius=8,
            fg_color="#f7f6f3",
            border_width=1,
            border_color="#e3e2e0"
        )
            day_header.grid(row=0, column=col_idx, sticky="ew", padx=2, pady=2)
        
            ctk.CTkLabel(
            day_header,
            text=day,
            font=ctk.CTkFont(family=system_font, size=14, weight="bold"),
            text_color="#37352f"
        ).pack(pady=12)
        
            col_idx += 1
    
    # Time slots and events
        row_idx = 1
        for session, time in sorted(SESSION_TIMES.items(), key=lambda x: x[1]):
        # Time label
            time_label = ctk.CTkFrame(
            grid_frame,
            corner_radius=8,
            fg_color="#f7f6f3",
            border_width=1,
            border_color="#e3e2e0"
            )
            time_label.grid(row=row_idx, column=0, sticky="nsew", padx=2, pady=2)
        
            ctk.CTkLabel(
            time_label,
            text=f"{session}\n{time}",
            font=ctk.CTkFont(family=system_font, size=12, weight="bold"),
            text_color="#37352f"
            ).pack(pady=15)
        
        # Event cells for each day
            col_idx = 1
            for day in sorted(days_schedule.keys()):
                cell_frame = ctk.CTkFrame(
                grid_frame,
                corner_radius=8,
                fg_color="#ffffff",
                border_width=1,
                border_color="#e3e2e0"
            )
                cell_frame.grid(row=row_idx, column=col_idx, sticky="nsew", padx=2, pady=2)
            
            # Check if this day has this session
                if session in days_schedule[day]:
                    slot = days_schedule[day][session]
                    self.create_slot_events(cell_frame, slot)
            
                col_idx += 1
        
        # Set minimum row height
            grid_frame.grid_rowconfigure(row_idx, minsize=150)
            row_idx += 1

    def create_slot_events(self, parent, slot):
        """Créer les événements (salles) pour un créneau"""
        selected_room = self.room_filter.get()
        
        if slot not in self.room_assignments:
            return
        
        rooms_data = self.room_assignments[slot]
        
        # Filter by selected room if needed
        if selected_room != "Toutes les salles":
            if selected_room not in rooms_data:
                return
            rooms_data = {selected_room: rooms_data[selected_room]}
        
        event_container = ctk.CTkFrame(parent, fg_color="transparent")
        event_container.pack(fill="both", expand=True, padx=8, pady=8)
        
        for room, teachers in sorted(rooms_data.items()):
            nb_profs = len(teachers)
            
            # Determine color based on number of teachers
            if nb_profs == 2:
                bg_color = "#d3f8d3"
                status = "✓"
            elif nb_profs <= 4:
                bg_color = "#fff4cc"
                status = "⚠️"
            else:
                bg_color = "#ffd4d4"
                status = "⚠️"
            
            # Event card
            event_card = ctk.CTkFrame(
                event_container,
                corner_radius=6,
                fg_color=bg_color,
                border_width=1,
                border_color="#e3e2e0"
            )
            event_card.pack(fill="x", pady=4)
            
            # Card content
            card_content = ctk.CTkFrame(event_card, fg_color="transparent")
            card_content.pack(fill="both", padx=10, pady=8)
            
            # Room name and status
            header_frame = ctk.CTkFrame(card_content, fg_color="transparent")
            header_frame.pack(fill="x", anchor="w")
            
            ctk.CTkLabel(
                header_frame,
                text=f"🚪 {room}",
                font=ctk.CTkFont(family=system_font, size=13, weight="bold"),
                text_color="#37352f",
                anchor="w"
            ).pack(side="left")
            
            ctk.CTkLabel(
                header_frame,
                text=f"{status} {nb_profs} prof{'s' if nb_profs > 1 else ''}",
                font=ctk.CTkFont(family=system_font, size=11),
                text_color="#787774",
                anchor="e"
            ).pack(side="right")
            
            # Teachers list
            teachers_text = ", ".join(sorted(teachers))
            if len(teachers_text) > 50:
                teachers_text = teachers_text[:47] + "..."
            
            ctk.CTkLabel(
                card_content,
                text=teachers_text,
                font=ctk.CTkFont(family=system_font, size=11),
                text_color="#787774",
                anchor="w",
                wraplength=220
            ).pack(fill="x", anchor="w", pady=(4, 0))

    def refresh_room_calendar(self):
        """Rafraîchir le calendrier quand le filtre change"""
        for widget in self.calendar_container.winfo_children():
            widget.destroy()
        self.create_calendar_grid()
    def show_general_info(self):
        """Vue des informations générales"""
        if not self.best:
            messagebox.showerror("❌ Erreur", "Veuillez générer le planning d'abord!")
            return
        
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Information", "Valeur")
        self.tree.heading("Information", text="Information")
        self.tree.heading("Valeur", text="Valeur")
        
        self.tree.column("Information", width=400)
        self.tree.column("Valeur", width=200)
        
        total_teachers = len(self.teachers)
        participating = sum(1 for t in self.teachers.values() if t['participe_surveillance'])
        assigned_teachers = len(set().union(*self.best.values()))
        unassigned_teachers = sum(1 for t in self.teachers 
                                 if self.teachers[t]['participe_surveillance'] 
                                 and t not in set().union(*self.best.values()))
        total_slots = len(self.best)
        
        # Statistiques par grade
        grade_stats = {}
        counts = {}
        for teacher in self.teachers:
            counts[teacher] = sum(1 for slot in self.best if teacher in self.best[slot])
        
        for grade in set(t['grade'] for t in self.teachers.values()):
            grade_teachers = [t for t in self.teachers if self.teachers[t]['grade'] == grade]
            grade_counts = [counts[t] for t in grade_teachers]
            if grade_counts:
                grade_stats[grade] = {
                    'total': len(grade_teachers),
                    'min': min(grade_counts),
                    'max': max(grade_counts),
                    'avg': sum(grade_counts) / len(grade_counts)
                }
        
        # Affichage
        self.tree.insert("", "end", values=("=== ENSEIGNANTS ===", ""))
        self.tree.insert("", "end", values=("Nombre total d'enseignants", total_teachers))
        self.tree.insert("", "end", values=("Enseignants participant à la surveillance", participating))
        self.tree.insert("", "end", values=("Enseignants assignés", f"{assigned_teachers} ({100*assigned_teachers/participating:.1f}%)"))
        self.tree.insert("", "end", values=("Enseignants non assignés (participe=1)", unassigned_teachers))
        
        self.tree.insert("", "end", values=("", ""))
        self.tree.insert("", "end", values=("=== CRÉNEAUX ===", ""))
        self.tree.insert("", "end", values=("Nombre total de créneaux", total_slots))
        
        self.tree.insert("", "end", values=("", ""))
        self.tree.insert("", "end", values=("=== STATISTIQUES PAR GRADE ===", ""))
        
        for grade in sorted(grade_stats.keys()):
            stats = grade_stats[grade]
            self.tree.insert("", "end", values=(
                f"Grade {grade} ({stats['total']} profs)",
                f"Min: {stats['min']}, Max: {stats['max']}, Moy: {stats['avg']:.1f}"
            ))

    def show_planning_quality(self):
        """Affiche la qualité détaillée du planning"""
        if not self.best:
            messagebox.showerror("❌ Erreur", "Veuillez générer le planning d'abord!")
            return
        
        slots_dict = {slot: data for slot, data in self.slots}
        fitness_score = fitness(self.best, self.teachers, slots_dict)
        
        # Calculer les métriques
        counts = {}
        for teacher in self.teachers:
            counts[teacher] = sum(1 for slot in self.best if teacher in self.best[slot])
        
        # Violations des contraintes
        violations = {
            'min_profs': 0,
            'max_profs': 0,
            'quota_exceeded': 0,
            'voeux_violes': 0,
            'consecutivity': 0,
            'duplicates': 0
        }
        
        for slot in self.best:
            slot_data = slots_dict[slot]
            min_needed = 2 * slot_data['room_count']
            max_needed = 4 * slot_data['room_count']
            unique = len(set(self.best[slot]))
            
            if unique < min_needed:
                violations['min_profs'] += (min_needed - unique)
            if unique > max_needed:
                violations['max_profs'] += (unique - max_needed)
            if len(self.best[slot]) != unique:
                violations['duplicates'] += (len(self.best[slot]) - unique)
            
            for e in self.best[slot]:
                if counts[e] > self.teachers[e]['quota']:
                    violations['quota_exceeded'] += 1
                if slot in self.teachers[e]['indispo']:
                    violations['voeux_violes'] += 1
        
        violations['consecutivity'] = check_consecutivity_violations(self.best, self.teachers, slots_dict)
        
        # Équité par grade
        grade_stats = {}
        for grade in set(t['grade'] for t in self.teachers.values()):
            grade_counts = [counts[e] for e in self.teachers 
                          if self.teachers[e]['grade'] == grade]
            if grade_counts:
                grade_stats[grade] = {
                    'min': min(grade_counts),
                    'max': max(grade_counts),
                    'avg': np.mean(grade_counts),
                    'std': np.std(grade_counts),
                    'range': max(grade_counts) - min(grade_counts)
                }
        
        # Affichage
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Métrique", "Valeur", "Statut")
        self.tree.heading("Métrique", text="Métrique")
        self.tree.heading("Valeur", text="Valeur")
        self.tree.heading("Statut", text="Statut")
        
        self.tree.column("Métrique", width=350)
        self.tree.column("Valeur", width=150)
        self.tree.column("Statut", width=200)
        
        # Score global
        quality = "🟢 Excellent" if fitness_score > -100 else \
                 "🟡 Acceptable" if fitness_score > -500 else \
                 "🟠 Moyen" if fitness_score > -1000 else "🔴 Problématique"
        
        self.tree.insert("", "end", values=(
            "📊 SCORE GLOBAL DE FITNESS", 
            f"{fitness_score:.0f}", 
            quality
        ), tags=("header",))
        
        # Contraintes rigides
        self.tree.insert("", "end", values=("", "", ""))
        self.tree.insert("", "end", values=("=== ⚠️ CONTRAINTES RIGIDES ===", "", ""), tags=("header",))
        
        constraint_labels = {
            'min_profs': "Minimum 2 profs/salle",
            'max_profs': "Maximum 4 profs/salle",
            'quota_exceeded': "Dépassements de quota",
            'voeux_violes': "Vœux d'indisponibilité violés",
            'consecutivity': "Violations de consécutivité (S1→S4 même jour)",
            'duplicates': "Doublons d'enseignants"
        }
        
        for key, label in constraint_labels.items():
            count = violations[key]
            status = "✅ OK" if count == 0 else f"❌ {count} violation(s)"
            tag = "ok" if count == 0 else "error"
            self.tree.insert("", "end", values=(label, count, status), tags=(tag,))
        
        # Équité par grade
        self.tree.insert("", "end", values=("", "", ""))
        self.tree.insert("", "end", values=("=== ⚖️ ÉQUITÉ PAR GRADE ===", "", ""), tags=("header",))
        
        for grade in sorted(grade_stats.keys()):
            stats = grade_stats[grade]
            equity_status = "✅ Excellent" if stats['std'] < 1.0 else \
                          "🟡 Acceptable" if stats['std'] < 2.0 else "⚠️ À améliorer"
            
            self.tree.insert("", "end", values=(
                f"Grade {grade}",
                f"Min:{stats['min']} Max:{stats['max']} Moy:{stats['avg']:.1f}",
                f"σ={stats['std']:.2f} {equity_status}"
            ))
        
        # Utilisation des ressources
        self.tree.insert("", "end", values=("", "", ""))
        self.tree.insert("", "end", values=("=== 📈 UTILISATION DES RESSOURCES ===", "", ""), tags=("header",))
        
        assigned = len(set().union(*self.best.values()))
        available = sum(1 for t in self.teachers if self.teachers[t]['participe_surveillance'])
        usage_rate = 100 * assigned / available if available > 0 else 0
        usage_status = "✅ Optimal" if usage_rate > 80 else "⚠️ Sous-utilisé"
        
        self.tree.insert("", "end", values=(
            "Taux d'utilisation des enseignants",
            f"{assigned}/{available}",
            f"{usage_rate:.1f}% {usage_status}"
        ))
        
        # Évolution du fitness
        if self.best_fitness_history:
            improvement = self.best_fitness_history[-1] - self.best_fitness_history[0]
            self.tree.insert("", "end", values=(
                "Amélioration depuis le début",
                f"{improvement:+.0f}",
                "🚀" if improvement > 0 else "→"
            ))
        
        # Style
        self.tree.tag_configure("header", font=("Arial", 10, "bold"), background="#e0e0e0")
        self.tree.tag_configure("ok", background="#ccffcc")
        self.tree.tag_configure("error", background="#ffcccc")

    def export_csv(self):
        """Exporte le planning en CSV"""
        if not self.best:
            messagebox.showerror("❌ Erreur", "Veuillez générer le planning d'abord!")
            return
        
        file = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if file:
            try:
                data = []
                for slot in sorted(self.best.keys()):
                    teachers_str = ", ".join([str(t) for t in self.best[slot]])
                    data.append({"Créneau": slot, "Enseignants": teachers_str})
                
                df = pd.DataFrame(data)
                df.to_csv(file, index=False, encoding='utf-8-sig')
                messagebox.showinfo("✅ Succès", f"Planning exporté vers:\n{file}")
            except Exception as e:
                messagebox.showerror("❌ Erreur", f"Erreur lors de l'export CSV:\n{str(e)}")

    def export_pdf(self):
        """Exporte le planning en PDF"""
        if not self.best:
            messagebox.showerror("❌ Erreur", "Veuillez générer le planning d'abord!")
            return
        
        file = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        
        if file:
            try:
                c = canvas.Canvas(file, pagesize=letter)
                width, height = letter
                y = height - 50
                
                # Titre
                c.setFont("Helvetica-Bold", 16)
                c.drawString(50, y, "Planning de Surveillance des Examens")
                y -= 30
                
                # Date de génération
                c.setFont("Helvetica", 10)
                c.drawString(50, y, f"Généré le: {datetime.now().strftime('%d/%m/%Y %H:%M')}")
                y -= 20
                
                slots_dict = {slot: data for slot, data in self.slots}
                fitness_score = fitness(self.best, self.teachers, slots_dict)
                c.drawString(50, y, f"Score de qualité: {fitness_score:.0f}")
                y -= 40
                
                # Contenu
                c.setFont("Helvetica", 9)
                for slot in sorted(self.best.keys()):
                    if y < 50:
                        c.showPage()
                        y = height - 50
                        c.setFont("Helvetica", 9)
                    
                    teachers_str = ", ".join([str(t) for t in self.best[slot]])
                    
                    # Découper si trop long
                    if len(teachers_str) > 80:
                        c.drawString(50, y, f"{slot}:")
                        y -= 15
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
                        c.drawString(50, y, f"{slot}: {teachers_str}")
                        y -= 15
                
                c.save()
                messagebox.showinfo("✅ Succès", f"Planning exporté vers:\n{file}")
            except Exception as e:
                messagebox.showerror("❌ Erreur", f"Erreur lors de l'export PDF:\n{str(e)}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
