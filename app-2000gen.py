import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import random
import numpy as np
from datetime import datetime
import time
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
import multiprocessing as mp  # Added for parallelism

# Configuration initiale des quotas par grade
GRADE_QUOTAS = {
    "PR": 8, "MA": 7, "V": 6, "PTC": 5, "AC": 4,
    "VA": 4, "AS": 4, "EX": 4, "MC": 4, "PES": 4
}
SESSION_TIMES = {"S1": "08:30", "S2": "10:30", "S3": "12:30", "S4": "14:30"}
SESSION_ORDER = {"S1": 1, "S2": 2, "S3": 3, "S4": 4}

def parse_datetime(slot_str):
    date_part, session = slot_str.split()
    return datetime.strptime(date_part, '%Y-%m-%d'), SESSION_ORDER[session]

def get_teacher_slots(assignment, teacher):
    return sorted([(parse_datetime(slot)[0], parse_datetime(slot)[1], slot)
                  for slot in assignment if teacher in assignment[slot]])

def check_gap_violations(assignment, teachers, slots_dict):
    """Vérifie les séances creuses dans la même journée"""
    violations = {'one_gap': 0, 'two_gaps': 0}
   
    for teacher in teachers:
        if not teachers[teacher]['participe_surveillance']:
            continue
        teacher_slots = get_teacher_slots(assignment, teacher)
       
        # Grouper par jour
        days = {}
        for date, order, slot in teacher_slots:
            date_key = date.strftime('%Y-%m-%d')
            if date_key not in days:
                days[date_key] = []
            days[date_key].append(order)
       
        # Vérifier les gaps pour chaque jour
        for date_key, sessions in days.items():
            if len(sessions) < 2:
                continue
            sessions = sorted(sessions)
           
            # Vérifier tous les gaps
            for i in range(len(sessions) - 1):
                gap = sessions[i + 1] - sessions[i]
                if gap == 2: # Une séance creuse (ex: S1→S3 ou S2→S4)
                    violations['one_gap'] += 1
                elif gap == 3: # Deux séances creuses (S1→S4)
                    violations['two_gaps'] += 1
   
    return violations

def dispersion_penalty(teacher_slots):
    """Pénalise les mauvaises répartitions de séances dans la journée"""
    if len(teacher_slots) < 2:
        return 0
    penalty = 0
   
    # Grouper par jour
    days = {}
    for date, order, slot in teacher_slots:
        date_key = date.strftime('%Y-%m-%d')
        if date_key not in days:
            days[date_key] = []
        days[date_key].append(order)
   
    # Pénaliser les gaps dans chaque jour
    for date_key, sessions in days.items():
        if len(sessions) < 2:
            continue
        sessions = sorted(sessions)
       
        for i in range(len(sessions) - 1):
            gap = sessions[i + 1] - sessions[i]
            if gap == 1: # Séances consécutives - BIEN
                penalty += 20
            elif gap == 2: # Une séance creuse (S1→S3 ou S2→S4) - MAUVAIS
                penalty -= 50
            elif gap == 3: # Deux séances creuses (S1→S4) - TRÈS MAUVAIS
                penalty -= 100
   
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

def is_valid_teacher(t):
    """Vérifie si un enseignant est valide (pas NaN)"""
    if t is None:
        return False
    # Convert to string first, then check
    t_str = str(t).strip()
    return t_str and t_str.lower() != 'nan'

def fitness(assignment, teachers, slots_dict):
    score = 0.0
    counts = {e: 0 for e in teachers}
    total_resp_present = 0
    total_resp = 0
    for slot in assignment:
        valid_teachers = [t for t in assignment[slot] if is_valid_teacher(t) and t in teachers]
        unique_assigned = set(valid_teachers)
        slot_data = slots_dict[slot]
        room_count = slot_data['room_count']
        min_needed = 2 * room_count
        max_needed = 4 * room_count
       
        if len(unique_assigned) < min_needed:
            score -= 500 * (min_needed - len(unique_assigned)) ** 2  # Scaled penalty
        if len(unique_assigned) > max_needed:
            score -= 500 * (len(unique_assigned) - max_needed) ** 2  # Scaled
        if len(unique_assigned) == min_needed:
            score += 100
           
        if len(valid_teachers) != len(unique_assigned):
            score -= 500
       
        # NOUVEAU: Bonus si le prof responsable est présent
        enseignant_responsable = str(slot_data.get('enseignant', '')).strip()
        if enseignant_responsable and is_valid_teacher(enseignant_responsable):
            total_resp += 1
            if enseignant_responsable in valid_teachers:
                score += 200  # BONUS IMPORTANT pour présence du prof responsable
                total_resp_present += 1
            else:
                score -= 100  # Pénalité si absent
           
        for e in valid_teachers:
            counts[e] += 1
            if counts[e] > teachers[e]['quota']:
                score -= 500 * (counts[e] - teachers[e]['quota']) ** 2  # Scaled
            if slot in teachers[e]['indispo']:
                # NOUVEAU: Pénalité pondérée par l'ordre d'arrivée du vœu
                wish_priority = teachers[e].get('wish_priority', {}).get(slot, 1.0)
                score -= 2000 * wish_priority  # Amplified
   
    # NOUVEAU: Pénaliser les séances creuses
    gap_violations = check_gap_violations(assignment, teachers, slots_dict)
    score -= 200 * gap_violations['one_gap']  # Pénalité pour 1 séance creuse
    score -= 500 * gap_violations['two_gaps']  # Pénalité DOUBLE pour 2 séances creuses
   
    # Bonus for zero gaps
    if gap_violations['one_gap'] == 0 and gap_violations['two_gaps'] == 0:
        score += 500

    # Bonus if all responsables present
    if total_resp > 0 and total_resp_present == total_resp:
        score += 500

    for e in teachers:
        if not teachers[e]['participe_surveillance']:
            continue
        t_slots = get_teacher_slots(assignment, e)
        score += dispersion_penalty(t_slots)
       
    total_variance = calculate_grade_equity(counts, teachers)
    score -= 50 * total_variance  # Higher weight
   
    return score

def generate_population(pop_size, slots, teachers):
    population = []
    teacher_list = [str(e) for e in teachers
                   if teachers[e]['participe_surveillance'] and is_valid_teacher(e)]
   
    # Precompute quotas remaining (initially full)
    for _ in range(pop_size):
        assignment = {}
        # Sort teachers by remaining quota descending for prioritization
        sorted_teachers = sorted(teacher_list, key=lambda t: teachers[t]['quota'], reverse=True)
        for slot, slot_data in slots:
            min_needed = 2 * slot_data['room_count']
            available = [e for e in sorted_teachers if slot not in teachers[e]['indispo']]
           
            # NOUVEAU: Prioriser le prof responsable
            enseignant_responsable = str(slot_data.get('enseignant', '')).strip()
            selected = []
            if enseignant_responsable and is_valid_teacher(enseignant_responsable) and enseignant_responsable in available:
                selected.append(enseignant_responsable)
                available.remove(enseignant_responsable)
           
            if available:
                needed = min(min_needed - len(selected), len(available))
                selected.extend(random.sample(available, needed))
                while len(selected) < min_needed and available:
                    selected.append(random.choice(available))
                assignment[slot] = selected[:4 * slot_data['room_count']]
            else:
                assignment[slot] = selected if selected else []
        population.append(assignment)
    return population

def crossover(parent1, parent2):
    # Improved: uniform crossover
    child = {}
    for key in parent1.keys():
        if random.random() < 0.5:
            child[key] = parent1[key][:]
        else:
            child[key] = parent2[key][:]
    return child

def mutate_improved(assignment, teachers, slots, slots_dict):
    mutation_type = random.choice(['swap', 'reassign', 'redistribute', 'remove_overload'])
    teacher_list = [t for t in teachers if teachers[t]['participe_surveillance'] and is_valid_teacher(t)]
   
    if mutation_type == 'swap':
        slot_keys = list(assignment.keys())
        if len(slot_keys) >= 2:
            slot1, slot2 = random.sample(slot_keys, 2)
            valid1 = [t for t in assignment[slot1] if t in teacher_list]
            valid2 = [t for t in assignment[slot2] if t in teacher_list]
            if valid1 and valid2:
                e1 = random.choice(valid1)
                e2 = random.choice(valid2)
                if (slot2 not in teachers[e1]['indispo'] and slot1 not in teachers[e2]['indispo']):
                    idx1 = assignment[slot1].index(e1)
                    idx2 = assignment[slot2].index(e2)
                    assignment[slot1][idx1] = e2
                    assignment[slot2][idx2] = e1
                   
    elif mutation_type == 'reassign':
        counts = {e: sum(1 for slot in assignment if e in assignment[slot]) for e in teacher_list}
        overloaded = [e for e in counts if e in teachers and counts[e] > teachers[e]['quota']]
        underloaded = [e for e in counts if e in teachers and counts[e] < teachers[e]['quota']]
       
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
            grade_teachers = [e for e in teacher_list if teachers[e]['grade'] == grade]
            if len(grade_teachers) >= 2:
                counts = {e: sum(1 for slot in assignment if e in assignment[slot]) for e in grade_teachers}
                most = max(counts, key=counts.get)
                least = min(counts, key=counts.get)
                if counts[most] - counts[least] >= 2:
                    slots_with_most = [s for s in assignment if most in assignment[s]]
                    if slots_with_most:
                        slot = random.choice(slots_with_most)
                        if slot not in teachers[least]['indispo']:
                            idx = assignment[slot].index(most)
                            assignment[slot][idx] = least

    elif mutation_type == 'remove_overload':
        counts = {e: sum(1 for slot in assignment if e in assignment[slot]) for e in teacher_list}
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
                   
    return assignment

def repair_solution(child, teachers, slots_dict):
    teacher_list = [t for t in teachers if teachers[t]['participe_surveillance'] and is_valid_teacher(t)]
   
    for slot in child:
        child[slot] = [t for t in child[slot] if is_valid_teacher(t) and t in teacher_list]
        slot_data = slots_dict[slot]
        min_needed = 2 * slot_data['room_count']
        max_needed = 4 * slot_data['room_count']
        child[slot] = list(set(child[slot]))
       
        # Compute current counts for prioritization
        current_counts = {e: sum(1 for s in child if e in child[s]) for e in teacher_list}
        attempts = 0
        while len(child[slot]) < min_needed and attempts < 100:
            available = sorted([e for e in teacher_list
                               if slot not in teachers[e]['indispo'] and e not in child[slot]],
                               key=lambda e: teachers[e]['quota'] - current_counts.get(e, 0), reverse=True)  # Prioritize under-quota
            if available:
                child[slot].append(available[0])  # Take the one with most quota left
            else:
                break
            attempts += 1
           
        if len(child[slot]) > max_needed:
            child[slot] = child[slot][:max_needed]
           
    return child

def evaluate_individual(ind, teachers, slots_dict):
    return ind, fitness(ind, teachers, slots_dict)

def run_ga_optimized(slots, teachers, progress_callback=None):
    EARLY_STOP_THRESHOLD = -50
    STAGNATION_LIMIT = 100
    MIN_IMPROVEMENT = 1.0
   
    slots_dict = {slot: data for slot, data in slots}
    pop_size = 300  # Increased
    max_generations = 2000  # Increased
    elite_size = int(pop_size * 0.2)  # 20%
   
    pop = generate_population(pop_size, slots, teachers)
    best_fitness_history = []
    stagnation_counter = 0
    last_significant_improvement_gen = 0
    start_time = time.time()
    mutation_rate = 0.25  # Initial
   
    # For parallelism
    pool = mp.Pool(mp.cpu_count())
   
    for gen in range(max_generations):
        # Parallel fitness evaluation
        pop_with_fitness = pool.starmap(evaluate_individual, [(ind, teachers, slots_dict) for ind in pop])
        pop_with_fitness.sort(key=lambda x: x[1], reverse=True)
        best_fitness = pop_with_fitness[0][1]
        best_fitness_history.append(best_fitness)
       
        if best_fitness > EARLY_STOP_THRESHOLD:
            if progress_callback:
                progress_callback(gen, max_generations, best_fitness,
                                "🎯 Solution optimale trouvée!", "optimal")
            pool.close()
            return pop_with_fitness[0][0], best_fitness_history, "optimal"
           
        if gen > 0:
            improvement = best_fitness - best_fitness_history[-2]
            if improvement >= MIN_IMPROVEMENT:
                last_significant_improvement_gen = gen
                stagnation_counter = 0
                mutation_rate *= 0.8  # Decrease on improvement
                mutation_rate = max(mutation_rate, 0.1)
            else:
                stagnation_counter += 1
               
        if gen - last_significant_improvement_gen > STAGNATION_LIMIT:
            if progress_callback:
                progress_callback(gen, max_generations, best_fitness,
                                "✅ Convergence atteinte", "stagnated")
            pool.close()
            return pop_with_fitness[0][0], best_fitness_history, "stagnated"
           
        fitness_values = [f for _, f in pop_with_fitness]
        diversity = np.std(fitness_values)
        if diversity < 1.0 and gen > 100:
            if progress_callback:
                progress_callback(gen, max_generations, best_fitness,
                                "✅ Population convergée", "converged")
            pool.close()
            return pop_with_fitness[0][0], best_fitness_history, "converged"
           
        if stagnation_counter < 20:
            mutation_rate = 0.25
        elif stagnation_counter < 50:
            mutation_rate = 0.5
        else:
            mutation_rate = 0.8
           
        if progress_callback:
            elapsed = time.time() - start_time
            eta = (elapsed / (gen + 1)) * (max_generations - gen - 1)
            status = f"Stag: {stagnation_counter} | Div: {diversity:.1f} | ETA: {eta:.0f}s | Mut: {mutation_rate:.2f}"
            progress_callback(gen, max_generations, best_fitness, status, "running")
           
        new_pop = [ind for ind, _ in pop_with_fitness[:elite_size]]
        while len(new_pop) < pop_size:
            tournament_size = 10  # Increased
            tournament1 = random.sample(pop_with_fitness[:pop_size//2], tournament_size)
            p1 = max(tournament1, key=lambda x: x[1])[0]
            tournament2 = random.sample(pop_with_fitness[:pop_size//2], tournament_size)
            p2 = max(tournament2, key=lambda x: x[1])[0]
            child = crossover(p1, p2)
            if random.random() < mutation_rate:
                child = mutate_improved(child, teachers, slots, slots_dict)
            child = repair_solution(child, teachers, slots_dict)
            new_pop.append(child)
        pop = new_pop
       
    pool.close()
    return pop_with_fitness[0][0], best_fitness_history, "max_gen"

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestion des Créneaux de Surveillance - Version Optimisée Complète")
        self.geometry("1400x900")
        self.slots = []
        self.teachers = {}
        self.best = None
        self.best_fitness_history = []
        self.day_to_date = {}
        self.room_assignments = {}
        self.quota_window = None
        self.quota_entries = {}
        self.current_view = "default"
        self.view_data = []
        self.action_frame = None
        self.search_entry = None
        self.current_filter = ""
        self.create_ui()

    def create_ui(self):
        main_frame = tk.Frame(self)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
       
        load_frame = tk.LabelFrame(main_frame, text="📁 Chargement des Données",
                                 font=("Arial", 10, "bold"), padx=10, pady=5)
        load_frame.pack(fill=tk.X, pady=5)
       
        btn_frame1 = tk.Frame(load_frame)
        btn_frame1.pack(fill=tk.X, pady=2)
       
        tk.Button(btn_frame1, text="📅 Charger Créneaux", command=self.load_slots,
                 bg="#4CAF50", fg="white", width=20).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame1, text="👥 Charger Enseignants", command=self.load_teachers,
                 bg="#2196F3", fg="white", width=20).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame1, text="💭 Charger Vœux", command=self.load_wishes,
                 bg="#FF9800", fg="white", width=20).pack(side=tk.LEFT, padx=3)
        tk.Button(btn_frame1, text="⚙️ Configurer Quotas", command=self.configure_quotas,
                 bg="#9C27B0", fg="white", width=20).pack(side=tk.LEFT, padx=3)
       
        gen_frame = tk.LabelFrame(main_frame, text="🧬 Génération du Planning",
                                font=("Arial", 10, "bold"), padx=10, pady=5)
        gen_frame.pack(fill=tk.X, pady=5)
       
        tk.Button(gen_frame, text="▶️ GÉNÉRER PLANNING", command=self.generate_planning,
                 bg="#4CAF50", fg="white", font=("Arial", 14, "bold"),
                 height=2).pack(pady=10)
       
        view_frame = tk.LabelFrame(main_frame, text="👁️ Visualisation & Impression",
                                 font=("Arial", 10, "bold"), padx=10, pady=5)
        view_frame.pack(fill=tk.X, pady=5)
       
        btn_frame2 = tk.Frame(view_frame)
        btn_frame2.pack(fill=tk.X, pady=3)
       
        tk.Button(btn_frame2, text="👤 Par Enseignant", command=self.show_by_teacher,
                 bg="#3F51B5", fg="white", width=18).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame2, text="📅 Par Jour (Calendrier)", command=self.show_by_day_calendar,
                 bg="#009688", fg="white", width=18).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame2, text="🚪 Par Salle", command=self.show_by_room,
                 bg="#795548", fg="white", width=18).pack(side=tk.LEFT, padx=2)
        tk.Button(btn_frame2, text="📊 Qualité Planning", command=self.show_planning_quality,
                 bg="#E91E63", fg="white", width=18).pack(side=tk.LEFT, padx=2)
       
        btn_frame3 = tk.Frame(view_frame)
        btn_frame3.pack(fill=tk.X, pady=3)
       
        tk.Button(btn_frame3, text="🖨️ Imprimer Vue Actuelle", command=self.print_current_view,
                 bg="#FF5722", fg="white", font=("Arial", 11, "bold"), width=25).pack(side=tk.LEFT, padx=2)
       
        self.hide_rooms_var = tk.BooleanVar(value=False)
        tk.Checkbutton(btn_frame3, text="🔒 Masquer les salles (pour enseignants)",
                      variable=self.hide_rooms_var, font=("Arial", 10),
                      command=self.refresh_view).pack(side=tk.LEFT, padx=10)
       
        export_frame = tk.LabelFrame(main_frame, text="💾 Export Données",
                                   font=("Arial", 10, "bold"), padx=10, pady=5)
        export_frame.pack(fill=tk.X, pady=5)
       
        tk.Button(export_frame, text="📄 Exporter CSV", command=self.export_csv,
                 width=20).pack(side=tk.LEFT, padx=5)
       
        self.view_type_label = tk.Label(main_frame, text="Vue actuelle: Aucune",
                                      font=("Arial", 11, "bold"), fg="#1976D2")
        self.view_type_label.pack(pady=5)
       
        self.action_frame = tk.Frame(main_frame)
        self.action_frame.pack(fill=tk.X, pady=5)
       
        search_frame = tk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="🔍 Recherche:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.search_entry = tk.Entry(search_frame, font=("Arial", 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind("<KeyRelease>", self.on_search)
       
        tree_frame = tk.Frame(main_frame)
        tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
       
        tree_scroll_y = tk.Scrollbar(tree_frame)
        tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
        tree_scroll_x = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
        tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
       
        self.tree = ttk.Treeview(tree_frame, columns=("Col1",), show="headings",
                               yscrollcommand=tree_scroll_y.set,
                               xscrollcommand=tree_scroll_x.set)
        self.tree.pack(fill=tk.BOTH, expand=True)
        tree_scroll_y.config(command=self.tree.yview)
        tree_scroll_x.config(command=self.tree.xview)

    def on_search(self, event=None):
        self.current_filter = self.search_entry.get().lower()
        self.refresh_view()

    def load_slots(self):
        file = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file:
            try:
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
                    # NOUVEAU: Extraire le code de l'enseignant responsable (smart_ens_code)
                    enseignant = ''
                    if 'smart_ens_code' in group.columns:
                        ens_code = group['smart_ens_code'].iloc[0]
                        if pd.notna(ens_code):
                            enseignant = str(int(ens_code))
                    elif 'enseignant' in group.columns:
                        enseignant = group['enseignant'].iloc[0] if pd.notna(group['enseignant'].iloc[0]) else ''
                   
                    session = group['session'].iloc[0]
                    self.slots.append((slot, {
                        'room_count': room_count,
                        'enseignant': enseignant,
                        'session': session
                    }))
                    self.room_assignments[slot] = {room: [] for room in group['cod_salle'].unique()}
               
                unique_dates = sorted(df['dateExam'].unique())
                self.day_to_date = {str(i+1): d.strftime('%Y-%m-%d') for i, d in enumerate(unique_dates)}
               
                # Compter les profs responsables identifiés
                profs_responsables = sum(1 for _, data in self.slots if data['enseignant'])
               
                messagebox.showinfo("✅ Succès", f"{len(self.slots)} créneaux chargés\n"
                                   f"{profs_responsables} profs responsables identifiés")
            except Exception as e:
                messagebox.showerror("❌ Erreur", f"Erreur:\n{str(e)}")

    def load_teachers(self):
        file = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file:
            try:
                engine = 'openpyxl' if file.endswith('.xlsx') else 'xlrd'
                df = pd.read_excel(file, engine=engine)
               
                for _, row in df.iterrows():
                    if pd.isna(row['code_smartex_ens']):
                        continue
                    code = str(int(row['code_smartex_ens']))
                    participe = row['participe_surveillance'] in [1, '1', True, 'true', 'True']
                    self.teachers[code] = {
                        'nom': row.get('nom_ens', ''),
                        'prenom': row.get('prenom_ens', ''),
                        'grade': row['grade_code_ens'],
                        'quota': GRADE_QUOTAS.get(row['grade_code_ens'], 2),
                        'indispo': [],
                        'wish_priority': {},
                        'participe_surveillance': participe
                    }
               
                participating = sum(1 for t in self.teachers.values() if t['participe_surveillance'])
                messagebox.showinfo("✅ Succès",
                                  f"{len(self.teachers)} enseignants chargés\n"
                                  f"{participating} participent à la surveillance")
            except Exception as e:
                messagebox.showerror("❌ Erreur", f"Erreur:\n{str(e)}")

    def load_wishes(self):
        file = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file:
            if not self.day_to_date:
                messagebox.showerror("❌ Erreur", "Chargez d'abord les créneaux!")
                return
            try:
                engine = 'openpyxl' if file.endswith('.xlsx') else 'xlrd'
                df = pd.read_excel(file, engine=engine)
               
                # NOUVEAU: Trier par ordre d'arrivée si une colonne existe, sinon par index
                if 'ordre_arrivee' in df.columns or 'timestamp' in df.columns:
                    sort_col = 'ordre_arrivee' if 'ordre_arrivee' in df.columns else 'timestamp'
                    df = df.sort_values(sort_col)
               
                loaded_count = 0
                wish_order = {} # Pour tracker l'ordre d'arrivée global
               
                for idx, row in df.iterrows():
                    if pd.isna(row['code_smartex_ens']):
                        continue
                    ens = str(int(row['code_smartex_ens']))
                    if ens in self.teachers:
                        # Initialiser wish_priority si pas encore fait
                        if 'wish_priority' not in self.teachers[ens]:
                            self.teachers[ens]['wish_priority'] = {}
                       
                        jour_str = str(int(row['jour'])) if pd.notna(row['jour']) else None
                        seance = str(row['seance']).strip() if pd.notna(row['seance']) else None
                        if jour_str and seance:
                            date = self.day_to_date.get(jour_str)
                            if date:
                                slot = f"{date} {seance}"
                                if slot not in self.teachers[ens]['indispo']:
                                    self.teachers[ens]['indispo'].append(slot)
                                    # NOUVEAU: Assigner une priorité basée sur l'ordre d'arrivée
                                    # Plus le vœu est ancien (petit idx), plus la priorité est forte (valeur haute)
                                    priority = 2.0 - (idx / max(len(df), 1)) # Entre 1.0 et 2.0
                                    self.teachers[ens]['wish_priority'][slot] = priority
                                    loaded_count += 1
               
                affected = len(set(str(int(row['code_smartex_ens'])) for _, row in df.iterrows()
                                if pd.notna(row['code_smartex_ens']) and str(int(row['code_smartex_ens'])) in self.teachers))
                messagebox.showinfo("✅ Succès",
                                  f"{loaded_count} vœux chargés pour {affected} enseignants\n"
                                  f"📊 Priorités appliquées (premiers arrivés mieux protégés)")
            except Exception as e:
                messagebox.showerror("❌ Erreur", f"Erreur:\n{str(e)}")

    def configure_quotas(self):
        if self.quota_window and self.quota_window.winfo_exists():
            self.quota_window.lift()
            return
           
        self.quota_window = tk.Toplevel(self)
        self.quota_window.title("⚙️ Configuration des Quotas")
        self.quota_window.geometry("400x450")
       
        tk.Label(self.quota_window, text="Quotas par grade:",
                font=("Arial", 12, "bold")).pack(pady=10)
       
        scroll_frame = tk.Frame(self.quota_window)
        scroll_frame.pack(fill=tk.BOTH, expand=True, padx=20)
       
        for grade in sorted(GRADE_QUOTAS.keys()):
            frame = tk.Frame(scroll_frame)
            tk.Label(frame, text=f"{grade}:", width=10, anchor='w',
                    font=("Arial", 10)).pack(side=tk.LEFT)
            entry = tk.Entry(frame, width=10, font=("Arial", 10))
            entry.insert(0, str(GRADE_QUOTAS[grade]))
            entry.pack(side=tk.LEFT, padx=5)
            self.quota_entries[grade] = entry
            frame.pack(pady=3)
       
        button_frame = tk.Frame(self.quota_window)
        button_frame.pack(pady=15)
       
        tk.Button(button_frame, text="💾 Sauvegarder", command=self.save_quotas,
                 bg="#4CAF50", fg="white", width=15).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="❌ Annuler", command=self.quota_window.destroy,
                 width=15).pack(side=tk.LEFT, padx=5)

    def save_quotas(self):
        try:
            for grade, entry in self.quota_entries.items():
                quota = int(entry.get())
                if quota < 0:
                    raise ValueError(f"Quota négatif pour {grade}")
                GRADE_QUOTAS[grade] = quota
               
            for teacher in self.teachers:
                self.teachers[teacher]['quota'] = GRADE_QUOTAS.get(
                    self.teachers[teacher]['grade'], 2)
                   
            messagebox.showinfo("✅ Succès", "Quotas mis à jour!")
            if self.quota_window:
                self.quota_window.destroy()
        except ValueError as e:
            messagebox.showerror("❌ Erreur", f"Valeur invalide: {str(e)}")

    def generate_planning(self):
        if not self.slots or not self.teachers:
            messagebox.showerror("❌ Erreur", "Chargez les données d'abord!")
            return
           
        progress_window = tk.Toplevel(self)
        progress_window.title("⏳ Génération en cours...")
        progress_window.geometry("600x250")
        progress_window.transient(self)
        progress_window.grab_set()
       
        tk.Label(progress_window, text="🧬 Optimisation génétique en cours...",
                font=("Arial", 14, "bold")).pack(pady=15)
       
        progress_bar = ttk.Progressbar(progress_window, length=500, mode='determinate')
        progress_bar.pack(pady=10)
       
        progress_label = tk.Label(progress_window, text="Génération 0/2000",  # Updated
                                font=("Arial", 11))
        progress_label.pack(pady=5)
       
        fitness_label = tk.Label(progress_window, text="Fitness: N/A",
                               font=("Arial", 11, "bold"), fg="#1976D2")
        fitness_label.pack(pady=5)
       
        status_label = tk.Label(progress_window, text="Initialisation...",
                              font=("Arial", 10), fg="gray")
        status_label.pack(pady=5)
       
        def update_progress(gen, total_gen, best_fitness, extra_info, state):
            progress = (gen + 1) / total_gen * 100
            progress_bar['value'] = progress
            progress_label.config(text=f"Génération {gen+1}/{total_gen}")
            fitness_label.config(text=f"Meilleur fitness: {best_fitness:.0f}")
            status_label.config(text=extra_info)
           
            if best_fitness > -100:
                fitness_label.config(fg="green")
            elif best_fitness > -500:
                fitness_label.config(fg="orange")
            else:
                fitness_label.config(fg="red")
            progress_window.update()
       
        try:
            self.best, self.best_fitness_history, stop_reason = run_ga_optimized(
                self.slots, self.teachers, update_progress)
            progress_window.destroy()
            self.display_planning_result()
           
            stop_messages = {
                "optimal": "🎯 Solution optimale trouvée!",
                "stagnated": "✅ Convergence atteinte",
                "converged": "✅ Population convergée",
                "max_gen": "⏱️ Nombre max de générations"
            }
           
            final_fitness = self.best_fitness_history[-1]
            quality = "🟢 Excellent" if final_fitness > -100 else \
                     "🟡 Acceptable" if final_fitness > -500 else "🔴 À améliorer"
                    
            messagebox.showinfo("✅ Planning généré!",
                              f"{stop_messages.get(stop_reason, 'Terminé')}\n\n"
                              f"Qualité: {quality}\n"
                              f"Score: {final_fitness:.0f}\n"
                              f"Générations: {len(self.best_fitness_history)}")
        except Exception as e:
            progress_window.destroy()
            messagebox.showerror("❌ Erreur", f"Erreur:\n{str(e)}")

    def display_planning_result(self):
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Créneau", "Enseignants")
        self.tree.heading("Créneau", text="Créneau")
        self.tree.heading("Enseignants", text="Enseignants Assignés")
        self.tree.column("Créneau", width=200)
        self.tree.column("Enseignants", width=800)
       
        data = []
        for slot in sorted(self.best.keys()):
            valid_teachers = [str(t) for t in self.best[slot] if is_valid_teacher(t)]
            data.append((slot, ", ".join(valid_teachers)))
           
        self.view_data = data
        self.populate_flat_view()
       
        # Assigner les enseignants aux salles
        for slot in self.best:
            valid_teachers = [str(t) for t in self.best[slot] if is_valid_teacher(t)]
            slot_data = next((data for s, data in self.slots if s == slot), None)
            if slot_data:
                room_count = slot_data['room_count']
                rooms = list(self.room_assignments[slot].keys())
               
                for room in rooms:
                    self.room_assignments[slot][room] = []
               
                teachers_per_room = max(1, len(valid_teachers) // room_count)
                for i, teacher in enumerate(valid_teachers):
                    room_idx = min(i // teachers_per_room, len(rooms) - 1)
                    self.room_assignments[slot][rooms[room_idx]].append(teacher)
       
        self.current_view = "default"
        self.view_type_label.config(text="Vue actuelle: Planning Général")
        self.configure_action_buttons()

    def show_by_teacher(self):
        if not self.best:
            messagebox.showerror("❌ Erreur", "Générez le planning d'abord!")
            return
           
        teacher_slots = {teacher: [] for teacher in self.teachers}
        for slot in self.best:
            valid_teachers = [t for t in self.best[slot] if is_valid_teacher(t)]
            for teacher in valid_teachers:
                if teacher in teacher_slots:
                    teacher_slots[teacher].append(slot)
       
        data = []
        for teacher in sorted(self.teachers.keys()):
            t_data = self.teachers[teacher]
            num_gardes = len(teacher_slots[teacher])
            violated_wishes = [slot for slot in teacher_slots[teacher]
                             if slot in t_data['indispo']]
           
            if violated_wishes:
                voeux_status = f"❌ {len(violated_wishes)} violé(s)"
                tag = "voeux_violes"
            elif t_data['indispo']:
                voeux_status = "✅ Respectés"
                tag = "voeux_ok"
            else:
                voeux_status = "Aucun vœu"
                tag = ""
               
            if num_gardes > t_data['quota']:
                tag = "over_quota"
            elif num_gardes == 0 and t_data['participe_surveillance']:
                tag = "unassigned"
               
            data.append((
                teacher, t_data['nom'], t_data['prenom'], t_data['grade'], t_data['quota'],
                f"{num_gardes} {'⚠️' if num_gardes > t_data['quota'] else '✓'}",
                ", ".join(sorted(teacher_slots[teacher])) if teacher_slots[teacher] else "Non assigné",
                ", ".join(sorted(t_data['indispo'])) if t_data['indispo'] else "Aucun",
                voeux_status, tag
            ))
       
        self.view_data = data
        self.tree["columns"] = ("Code", "Nom", "Prénom", "Grade", "Quota",
                              "Assigné", "Créneaux", "Vœux", "Statut Vœux")
        cols = {
            "Code": 80, "Nom": 120, "Prénom": 120, "Grade": 60, "Quota": 60,
            "Assigné": 80, "Créneaux": 300, "Vœux": 200, "Statut Vœux": 120
        }
        for col, width in cols.items():
            self.tree.heading(col, text=col)
            self.tree.column(col, width=width)
           
        self.populate_flat_view()
       
        self.tree.tag_configure("over_quota", background="#ffcccc")
        self.tree.tag_configure("unassigned", background="#ffffcc")
        self.tree.tag_configure("voeux_violes", background="#ff9999")
        self.tree.tag_configure("voeux_ok", background="#ccffcc")
       
        self.current_view = "teacher"
        self.view_type_label.config(text="Vue actuelle: Par Enseignant")
        self.configure_action_buttons()

    def populate_flat_view(self):
        self.tree.delete(*self.tree.get_children())
        for row in self.view_data:
            text = " ".join(map(str, row[:-1] if self.current_view in ["teacher", "room", "quality"] else row)).lower()
            if self.current_filter in text or not self.current_filter:
                tag = row[-1] if len(row) > 1 and self.current_view in ["teacher", "room", "quality"] else ""
                self.tree.insert("", "end", values=row[:-1] if tag else row, tags=(tag,))

    def show_by_day_calendar(self):
        if not self.best:
            messagebox.showerror("❌ Erreur", "Générez le planning d'abord!")
            return
           
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Session/Salle", "Enseignants")
        self.tree.heading("Session/Salle", text="Session / Salle")
        self.tree.heading("Enseignants", text="Enseignants")
        self.tree.column("Session/Salle", width=250)
        self.tree.column("Enseignants", width=800)
       
        days_data = {}
        for slot in sorted(self.best.keys()):
            date_str, session = slot.split()
            if date_str not in days_data:
                days_data[date_str] = {s: {} for s in ["S1", "S2", "S3", "S4"]}
            for room, teachers in self.room_assignments[slot].items():
                valid_teachers = [t for t in teachers if is_valid_teacher(t)]
                days_data[date_str][session][room] = valid_teachers
       
        hide_rooms = self.hide_rooms_var.get()
       
        for date_str in sorted(days_data.keys()):
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            date_display = date_obj.strftime('%d/%m/%Y (%A)')
            day_has_match = False
            day_iid = None
           
            for session in ["S1", "S2", "S3", "S4"]:
                session_display = f"{session} ({SESSION_TIMES[session]})"
                session_has_match = False
                session_iid = None
               
                if hide_rooms:
                    all_teachers = []
                    for room_teachers in days_data[date_str][session].values():
                        all_teachers.extend(room_teachers)
                    teachers_str = ", ".join(all_teachers) if all_teachers else "-"
                   
                    if self.current_filter in teachers_str.lower() or not self.current_filter:
                        session_has_match = True
                        day_has_match = True
                        if not day_iid:
                            day_iid = self.tree.insert("", "end", values=(date_display, ""), open=True, tags=("day_header",))
                        session_iid = self.tree.insert(day_iid, "end", values=(session_display, ""), open=True, tags=("session_header",))
                        self.tree.insert(session_iid, "end", values=("", teachers_str))
                else:
                    for room in sorted(days_data[date_str][session].keys()):
                        teachers = days_data[date_str][session][room]
                        teachers_str = ", ".join(teachers) if teachers else "-"
                        room_display = f"Salle {room}"
                        search_text = (room_display + " " + teachers_str).lower()
                       
                        if self.current_filter in search_text or not self.current_filter:
                            session_has_match = True
                            day_has_match = True
                            if not day_iid:
                                day_iid = self.tree.insert("", "end", values=(date_display, ""), open=True, tags=("day_header",))
                            if not session_iid:
                                session_iid = self.tree.insert(day_iid, "end", values=(session_display, ""), open=True, tags=("session_header",))
                            self.tree.insert(session_iid, "end", values=(room_display, teachers_str), tags=("room_item",))
       
        self.tree.tag_configure("day_header", font=("Arial", 14, "bold"), background="#e3f2fd")
        self.tree.tag_configure("session_header", font=("Arial", 12, "bold"), background="#f0f8ff")
        self.tree.tag_configure("room_item", font=("Arial", 10))
       
        self.current_view = "calendar"
        self.view_type_label.config(text="Vue actuelle: Calendrier par Jour")
        self.configure_action_buttons()

    def show_by_room(self):
        if not self.best:
            messagebox.showerror("❌ Erreur", "Générez le planning d'abord!")
            return
           
        self.tree["columns"] = ("Créneau", "Salle", "Nb Profs", "Enseignants")
        self.tree.heading("Créneau", text="Créneau")
        self.tree.heading("Salle", text="Salle")
        self.tree.heading("Nb Profs", text="Nb Profs")
        self.tree.heading("Enseignants", text="Enseignants")
        self.tree.column("Créneau", width=200)
        self.tree.column("Salle", width=100)
        self.tree.column("Nb Profs", width=100)
        self.tree.column("Enseignants", width=600)
       
        data = []
        for slot in sorted(self.best.keys()):
            for room in sorted(self.room_assignments[slot].keys()):
                teachers = self.room_assignments[slot][room]
                valid_teachers = [t for t in teachers if is_valid_teacher(t)]
                nb = len(valid_teachers)
                tag = "optimal" if nb == 2 else "acceptable" if nb <= 4 else "problem"
                data.append((slot, room, f"{nb} {'✓' if nb == 2 else '⚠️' if nb > 4 else ''}", ", ".join(valid_teachers), tag))
       
        self.view_data = data
        self.populate_flat_view()
       
        self.tree.tag_configure("optimal", background="#ccffcc")
        self.tree.tag_configure("acceptable", background="#ffffcc")
        self.tree.tag_configure("problem", background="#ffcccc")
       
        self.current_view = "room"
        self.view_type_label.config(text="Vue actuelle: Par Salle")
        self.configure_action_buttons()

    def show_planning_quality(self):
        if not self.best:
            messagebox.showerror("❌ Erreur", "Générez le planning d'abord!")
            return
           
        slots_dict = {slot: data for slot, data in self.slots}
        fitness_score = fitness(self.best, self.teachers, slots_dict)
       
        counts = {}
        for teacher in self.teachers:
            counts[teacher] = sum(1 for slot in self.best if teacher in self.best[slot])
       
        violations = {
            'min_profs': 0, 'max_profs': 0, 'quota_exceeded': 0,
            'voeux_violes': 0, 'voeux_prioritaires_violes': 0,
            'duplicates': 0, 'one_gap': 0, 'two_gaps': 0,
            'prof_responsable_absent': 0, 'prof_responsable_present': 0
        }
       
        for slot in self.best:
            valid_teachers = [t for t in self.best[slot] if is_valid_teacher(t)]
            unique = len(set(valid_teachers))
            slot_data = slots_dict[slot]
            min_needed = 2 * slot_data['room_count']
            max_needed = 4 * slot_data['room_count']
           
            if unique < min_needed:
                violations['min_profs'] += (min_needed - unique)
            if unique > max_needed:
                violations['max_profs'] += (unique - max_needed)
            if len(valid_teachers) != unique:
                violations['duplicates'] += (len(valid_teachers) - unique)
           
            # NOUVEAU: Vérifier présence du prof responsable
           
            prof_resp = str(slot_data.get('enseignant', '')).strip()
            if prof_resp and is_valid_teacher(prof_resp):
                if prof_resp in valid_teachers:
                    violations['prof_responsable_present'] += 1
                else:
                    violations['prof_responsable_absent'] += 1
               
            for e in valid_teachers:
                if e in self.teachers:
                    if counts[e] > self.teachers[e]['quota']:
                        violations['quota_exceeded'] += 1
                    if slot in self.teachers[e]['indispo']:
                        violations['voeux_violes'] += 1
                        # NOUVEAU: Compter les vœux prioritaires violés
                        priority = self.teachers[e].get('wish_priority', {}).get(slot, 1.0)
                        if priority > 1.5: # Vœux des premiers arrivés
                            violations['voeux_prioritaires_violes'] += 1
       
        # NOUVEAU: Calculer les violations de séances creuses
        gap_violations = check_gap_violations(self.best, self.teachers, slots_dict)
        violations['one_gap'] = gap_violations['one_gap']
        violations['two_gaps'] = gap_violations['two_gaps']
       
        grade_stats = {}
        for grade in set(t['grade'] for t in self.teachers.values()):
            grade_counts = [counts[e] for e in self.teachers
                          if self.teachers[e]['grade'] == grade]
            if grade_counts:
                grade_stats[grade] = {
                    'min': min(grade_counts), 'max': max(grade_counts),
                    'avg': np.mean(grade_counts), 'std': np.std(grade_counts)
                }
       
        self.tree["columns"] = ("Métrique", "Valeur", "Statut")
        for col in ["Métrique", "Valeur", "Statut"]:
            self.tree.heading(col, text=col)
        self.tree.column("Métrique", width=400)
        self.tree.column("Valeur", width=150)
        self.tree.column("Statut", width=200)
       
        data = []
        quality = "🟢 Excellent" if fitness_score > -100 else \
                 "🟡 Acceptable" if fitness_score > -500 else "🔴 À améliorer"
        data.append(("📊 SCORE GLOBAL", f"{fitness_score:.0f}", quality, "header"))
        data.append(("", "", "", ""))
        data.append(("=== ⚠️ CONTRAINTES RIGIDES ===", "", "", "header"))
       
        constraints = {
            'min_profs': "Minimum 2 profs/salle",
            'max_profs': "Maximum 4 profs/salle",
            'quota_exceeded': "Dépassements de quota",
            'voeux_violes': "Vœux violés (total)",
            'duplicates': "Doublons"
        }
       
        for key, label in constraints.items():
            count = violations[key]
            status = "✅ OK" if count == 0 else f"❌ {count} violation(s)"
            tag = "ok" if count == 0 else "error"
            data.append((label, count, status, tag))
       
        # NOUVEAU: Contraintes de priorité des vœux
        data.append(("", "", "", ""))
        data.append(("=== 🎯 PRIORITÉ DES VŒUX ===", "", "", "header"))
        voeux_prioritaires = violations['voeux_prioritaires_violes']
        voeux_normaux = violations['voeux_violes'] - voeux_prioritaires
        status_prio = "✅ Bien respectés" if voeux_prioritaires == 0 else f"⚠️ {voeux_prioritaires} violé(s)"
        tag_prio = "ok" if voeux_prioritaires == 0 else "warning"
        data.append(("Vœux prioritaires violés (premiers arrivés)", voeux_prioritaires, status_prio, tag_prio))
        data.append(("Vœux normaux violés (arrivés tard)", voeux_normaux,
                    f"{voeux_normaux} violé(s)" if voeux_normaux > 0 else "✅ OK", ""))
       
        # NOUVEAU: Contraintes de séances creuses
        data.append(("", "", "", ""))
        data.append(("=== 📅 CONTINUITÉ DES SÉANCES ===", "", "", "header"))
        one_gap = violations['one_gap']
        two_gaps = violations['two_gaps']
        status_1gap = "✅ Aucune" if one_gap == 0 else f"⚠️ {one_gap} occurrence(s)"
        status_2gaps = "✅ Aucune" if two_gaps == 0 else f"❌ {two_gaps} occurrence(s)"
        tag_1gap = "ok" if one_gap == 0 else "warning"
        tag_2gaps = "ok" if two_gaps == 0 else "error"
        data.append(("Séances avec 1 creux (S1→S3 ou S2→S4)", one_gap, status_1gap, tag_1gap))
        data.append(("Séances avec 2 creux (S1→S4)", two_gaps, status_2gaps, tag_2gaps))
       
        # NOUVEAU: Contraintes prof responsable
        data.append(("", "", "", ""))
        data.append(("=== 👨‍🏫 PROFS RESPONSABLES ===", "", "", "header"))
        total_resp = violations['prof_responsable_present'] + violations['prof_responsable_absent']
        if total_resp > 0:
            taux_presence = (violations['prof_responsable_present'] / total_resp) * 100
            status_resp = f"🟢 Excellent" if taux_presence >= 90 else \
                         f"🟡 Acceptable" if taux_presence >= 70 else "🔴 Insuffisant"
            data.append(("Profs responsables présents",
                        f"{violations['prof_responsable_present']}/{total_resp}",
                        f"{taux_presence:.1f}% {status_resp}", ""))
            data.append(("Profs responsables absents", violations['prof_responsable_absent'],
                        "❌" if violations['prof_responsable_absent'] > 0 else "✅", ""))
        else:
            data.append(("Profs responsables identifiés", 0, "⚠️ Aucun", "warning"))
       
        data.append(("", "", "", ""))
        data.append(("=== ⚖️ ÉQUITÉ PAR GRADE ===", "", "", "header"))
       
        for grade in sorted(grade_stats.keys()):
            stats = grade_stats[grade]
            equity = "✅ Excellent" if stats['std'] < 1.0 else \
                    "🟡 Acceptable" if stats['std'] < 2.0 else "⚠️ À améliorer"
            data.append((
                f"Grade {grade}",
                f"Min:{stats['min']} Max:{stats['max']} Moy:{stats['avg']:.1f}",
                f"σ={stats['std']:.2f} {equity}",
                ""
            ))
       
        if self.best_fitness_history:
            data.append(("", "", "", ""))
            data.append(("=== 📈 CONVERGENCE ===", "", "", "header"))
            total_gen = len(self.best_fitness_history)
            improvement = self.best_fitness_history[-1] - self.best_fitness_history[0]
            data.append((
                "Générations utilisées", total_gen,
                "✅" if total_gen < 1000 else "→",
                ""
            ))
            data.append((
                "Amélioration totale", f"{improvement:+.0f}",
                "🚀" if improvement > 0 else "→",
                ""
            ))
       
        self.view_data = data
        self.populate_flat_view()
       
        self.tree.tag_configure("header", font=("Arial", 11, "bold"),
                              background="#e0e0e0")
        self.tree.tag_configure("ok", background="#ccffcc")
        self.tree.tag_configure("warning", background="#fff3cd")
        self.tree.tag_configure("error", background="#ffcccc")
       
        self.current_view = "quality"
        self.view_type_label.config(text="Vue actuelle: Qualité du Planning")
        self.configure_action_buttons()

    def configure_action_buttons(self):
        for widget in self.action_frame.winfo_children():
            widget.destroy()
           
        if self.current_view == "teacher":
            tk.Button(self.action_frame, text="🖨️ Générer PDF pour l'enseignant sélectionné",
                     command=self.export_selected_teacher_pdf, bg="#FF5722", fg="white").pack(side=tk.LEFT, padx=5)

    def export_selected_teacher_pdf(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("❌ Erreur", "Sélectionnez un enseignant!")
            return
           
        iid = selected[0]
        values = self.tree.item(iid)['values']
        code, nom, prenom, grade, quota, assigne, creaneaux_str, voeux, statut_voeux = values
        creaneaux = creaneaux_str.split(", ") if creaneaux_str != "Non assigné" else []
       
        file = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"planning_{nom}_{prenom}_{datetime.now().strftime('%Y%m%d')}.pdf"
        )
        if not file:
            return
           
        try:
            doc = SimpleDocTemplate(file, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()
            title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], fontSize=16, alignment=1)
           
            elements.append(Paragraph(f"Planning de Surveillance pour {nom} {prenom} ({code})", title_style))
            elements.append(Spacer(1, 0.2*inch))
           
            info_data = [
                ["Grade", grade],
                ["Quota", quota],
                ["Assigné", assigne],
                ["Vœux", voeux],
                ["Statut Vœux", statut_voeux]
            ]
            info_table = Table(info_data)
            info_table.setStyle(TableStyle([
                ('GRID', (0,0), (-1,-1), 1, colors.black),
                ('BACKGROUND', (0,0), (0,-1), colors.lightgrey)
            ]))
            elements.append(info_table)
            elements.append(Spacer(1, 0.3*inch))
           
            elements.append(Paragraph("Créneaux Assignés:", styles['Heading2']))
            if creaneaux:
                creaneaux_data = [["Créneau"]] + [[c] for c in sorted(creaneaux)]
                creaneaux_table = Table(creaneaux_data)
                creaneaux_table.setStyle(TableStyle([
                    ('BACKGROUND', (0,0), (-1,0), colors.grey),
                    ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                    ('GRID', (0,0), (-1,-1), 1, colors.black)
                ]))
                elements.append(creaneaux_table)
            else:
                elements.append(Paragraph("Aucun créneau assigné.", styles['Normal']))
               
            doc.build(elements)
            messagebox.showinfo("✅ Succès", f"PDF généré: {file}")
        except Exception as e:
            messagebox.showerror("❌ Erreur", f"Erreur: {str(e)}")

    def refresh_view(self):
        if self.current_view == "default":
            self.display_planning_result()
        elif self.current_view == "teacher":
            self.show_by_teacher()
        elif self.current_view == "calendar":
            self.show_by_day_calendar()
        elif self.current_view == "room":
            self.show_by_room()
        elif self.current_view == "quality":
            self.show_planning_quality()

    def print_current_view(self):
        if not self.best:
            messagebox.showerror("❌ Erreur", "Générez le planning d'abord!")
            return
           
        file = filedialog.asksaveasfilename(
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf")],
            initialfile=f"planning_{self.current_view}_{datetime.now().strftime('%Y%m%d_%H%M')}.pdf"
        )
        if not file:
            return
           
        try:
            if self.current_view == "calendar":
                self.export_calendar_pdf(file)
            elif self.current_view == "teacher":
                self.export_teacher_pdf(file)
            elif self.current_view == "room":
                self.export_room_pdf(file)
            elif self.current_view == "quality":
                self.export_quality_pdf(file)
            else:
                self.export_generic_pdf(file)
            messagebox.showinfo("✅ Succès", f"PDF exporté:\n{file}")
        except Exception as e:
            messagebox.showerror("❌ Erreur", f"Erreur export PDF:\n{str(e)}")

    def export_calendar_pdf(self, filename):
        doc = SimpleDocTemplate(filename, pagesize=landscape(A4))
        elements = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle(
            'CustomTitle', parent=styles['Heading1'], fontSize=18,
            textColor=colors.HexColor('#1976D2'), spaceAfter=20, alignment=1
        )
       
        hide_rooms = self.hide_rooms_var.get()
        title_text = "Planning des Surveillances - Vue Calendrier"
        if hide_rooms:
            title_text += " (Salles masquees)"
        elements.append(Paragraph(title_text, title_style))
        elements.append(Spacer(1, 0.3*inch))
       
        days_data = {}
        for slot in sorted(self.best.keys()):
            date_str, session = slot.split()
            if date_str not in days_data:
                days_data[date_str] = {s: {} for s in ["S1", "S2", "S3", "S4"]}
            for room, teachers in self.room_assignments[slot].items():
                valid_teachers = [t for t in teachers if is_valid_teacher(t)]
                days_data[date_str][session][room] = valid_teachers
       
        for date_str in sorted(days_data.keys()):
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            date_display = date_obj.strftime('%d/%m/%Y - %A')
            elements.append(Paragraph(f"<b>{date_display}</b>", styles['Heading2']))
           
            if hide_rooms:
                data = [["S1\n08:30", "S2\n10:30", "S3\n12:30", "S4\n14:30"]]
                row = []
                for session in ["S1", "S2", "S3", "S4"]:
                    all_teachers = []
                    for room, teachers in days_data[date_str][session].items():
                        all_teachers.extend(teachers)
                    row.append("\n".join(all_teachers) if all_teachers else "-")
                data.append(row)
            else:
                all_rooms = set()
                for session in ["S1", "S2", "S3", "S4"]:
                    all_rooms.update(days_data[date_str][session].keys())
                data = [["Salle", "S1\n08:30", "S2\n10:30", "S3\n12:30", "S4\n14:30"]]
                for room in sorted(all_rooms):
                    row = [f"Salle {room}"]
                    for session in ["S1", "S2", "S3", "S4"]:
                        teachers = days_data[date_str][session].get(room, [])
                        row.append("\n".join(teachers) if teachers else "-")
                    data.append(row)
           
            table = Table(data)
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ]))
            elements.append(table)
            elements.append(Spacer(1, 0.3*inch))
           
        doc.build(elements)

    def export_teacher_pdf(self, filename):
        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
       
        elements.append(Paragraph("Planning par Enseignant", styles['Title']))
        elements.append(Spacer(1, 0.2*inch))
       
        teacher_slots = {teacher: [] for teacher in self.teachers}
        for slot in self.best:
            valid = [t for t in self.best[slot] if is_valid_teacher(t)]
            for teacher in valid:
                if teacher in teacher_slots:
                    teacher_slots[teacher].append(slot)
       
        data = [["Code", "Nom", "Grade", "Quota", "Assigne", "Voeux"]]
        for teacher in sorted(self.teachers.keys()):
            t_data = self.teachers[teacher]
            num = len(teacher_slots[teacher])
            violated = [s for s in teacher_slots[teacher] if s in t_data['indispo']]
            voeux_status = f"Viole {len(violated)}" if violated else \
                          "OK" if t_data['indispo'] else "Aucun"
            data.append([
                teacher,
                f"{t_data['nom']} {t_data['prenom']}",
                t_data['grade'],
                str(t_data['quota']),
                str(num),
                voeux_status
            ])
       
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
        doc.build(elements)

    def export_room_pdf(self, filename):
        doc = SimpleDocTemplate(filename, pagesize=landscape(A4))
        elements = []
        styles = getSampleStyleSheet()
       
        elements.append(Paragraph("Planning par Salle", styles['Title']))
        elements.append(Spacer(1, 0.2*inch))
       
        data = [["Creneau", "Salle", "Nb Profs", "Enseignants"]]
        for slot in sorted(self.best.keys()):
            for room in sorted(self.room_assignments[slot].keys()):
                teachers = self.room_assignments[slot][room]
                valid = [t for t in teachers if is_valid_teacher(t)]
                data.append([slot, room, str(len(valid)), ", ".join(valid)])
       
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 7),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
        doc.build(elements)

    def export_quality_pdf(self, filename):
        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
       
        elements.append(Paragraph("Rapport de Qualite du Planning", styles['Title']))
        elements.append(Spacer(1, 0.2*inch))
       
        slots_dict = {slot: data for slot, data in self.slots}
        fitness_score = fitness(self.best, self.teachers, slots_dict)
        quality = "Excellent" if fitness_score > -100 else \
                 "Acceptable" if fitness_score > -500 else "A ameliorer"
        elements.append(Paragraph(f"<b>Score global:</b> {fitness_score:.0f} ({quality})",
                                styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
       
        violations = {'min_profs': 0, 'max_profs': 0, 'one_gap': 0, 'two_gaps': 0,
                     'prof_responsable_absent': 0, 'prof_responsable_present': 0}
       
        for slot in self.best:
            valid = [t for t in self.best[slot] if is_valid_teacher(t)]
            unique = len(set(valid))
            slot_data = slots_dict[slot]
            min_needed = 2 * slot_data['room_count']
            max_needed = 4 * slot_data['room_count']
           
            if unique < min_needed:
                violations['min_profs'] += (min_needed - unique)
            if unique > max_needed:
                violations['max_profs'] += (unique - max_needed)
           
            # Vérifier prof responsable
           
            prof_resp = str(slot_data.get('enseignant', '')).strip()
            if prof_resp and is_valid_teacher(prof_resp):
                if prof_resp in valid:
                    violations['prof_responsable_present'] += 1
                else:
                    violations['prof_responsable_absent'] += 1
       
        gap_violations = check_gap_violations(self.best, self.teachers, slots_dict)
        violations['one_gap'] = gap_violations['one_gap']
        violations['two_gaps'] = gap_violations['two_gaps']
       
        data = [["Contrainte", "Violations"]]
        data.append(["Minimum 2 profs/salle", str(violations['min_profs'])])
        data.append(["Maximum 4 profs/salle", str(violations['max_profs'])])
        data.append(["Seances avec 1 creux (S1->S3, S2->S4)", str(violations['one_gap'])])
        data.append(["Seances avec 2 creux (S1->S4)", str(violations['two_gaps'])])
       
        total_resp = violations['prof_responsable_present'] + violations['prof_responsable_absent']
        if total_resp > 0:
            taux = (violations['prof_responsable_present'] / total_resp) * 100
            data.append(["Profs responsables presents", f"{violations['prof_responsable_present']}/{total_resp} ({taux:.1f}%)"])
       
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ]))
        elements.append(table)
        doc.build(elements)

    def export_generic_pdf(self, filename):
        doc = SimpleDocTemplate(filename, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
       
        elements.append(Paragraph("Planning de Surveillance", styles['Title']))
        elements.append(Spacer(1, 0.2*inch))
       
        for slot in sorted(self.best.keys()):
            valid = [str(t) for t in self.best[slot] if is_valid_teacher(t)]
            elements.append(Paragraph(f"<b>{slot}</b>: {', '.join(valid)}",
                                   styles['Normal']))
        doc.build(elements)

    def export_csv(self):
        if not self.best:
            messagebox.showerror("❌ Erreur", "Générez le planning d'abord!")
            return
           
        file = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv")]
        )
        if file:
            try:
                data = []
                for slot in sorted(self.best.keys()):
                    valid = [str(t) for t in self.best[slot] if is_valid_teacher(t)]
                    data.append({"Creneau": slot, "Enseignants": ", ".join(valid)})
                df = pd.DataFrame(data)
                df.to_csv(file, index=False, encoding='utf-8-sig')
                messagebox.showinfo("✅ Succès", f"CSV exporté:\n{file}")
            except Exception as e:
                messagebox.showerror("❌ Erreur", f"Erreur export CSV:\n{str(e)}")

if __name__ == "__main__":
    app = App()
    app.mainloop()
