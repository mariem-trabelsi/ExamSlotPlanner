import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
import random
import numpy as np
from datetime import datetime, timedelta
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Initial configurable quotas by grade (default values)
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

# Session mappings
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
    date_part, session = slot_str.split()
    return datetime.strptime(date_part, '%Y-%m-%d'), SESSION_ORDER[session]

def get_teacher_slots(assignment, teacher):
    return sorted([(parse_datetime(slot)[0], parse_datetime(slot)[1]) for slot in assignment if teacher in assignment[slot]])

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

def fitness(assignment, teachers, slots_dict):
    score = 0.0
    counts = {e: 0 for e in teachers}
    last_sessions = {e: None for e in teachers}
    
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
            session = slot_data['session']
            if last_sessions[e] is not None:
                if abs(SESSION_ORDER[session] - SESSION_ORDER[last_sessions[e]]) > 1:
                    score -= 1000
            last_sessions[e] = session
    
    for e in teachers:
        t_slots = get_teacher_slots(assignment, e)
        score += dispersion_penalty(t_slots)
    
    grades = set(t['grade'] for t in teachers.values())
    for g in grades:
        g_counts = [counts[e] for e in teachers if teachers[e]['grade'] == g]
        if g_counts:
            variance = np.var(g_counts)
            score -= 10 * variance
    
    return score

def generate_population(pop_size, slots, teachers):
    population = []
    teacher_list = [str(e) for e in teachers if teachers[e]['participe_surveillance']]
    for _ in range(pop_size):
        assignment = {}
        for slot, slot_data in slots:
            min_needed = 2 * slot_data['room_count']
            available = [e for e in teacher_list if slot not in teachers[e]['indispo']]
            selected = random.sample(available, min(min_needed, len(available))) if available else []
            while len(selected) < min_needed and available:
                selected.append(random.choice(available))
            assignment[slot] = selected[:4 * slot_data['room_count']]
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

def mutate(assignment, teachers, slots, slots_dict):
    slot_keys = list(assignment.keys())
    if len(slot_keys) < 2:
        return assignment
    slot1, slot2 = random.sample(slot_keys, 2)
    if assignment[slot1] and assignment[slot2]:
        s1_session = slots_dict[slot1]['session']
        s2_session = slots_dict[slot2]['session']
        if abs(SESSION_ORDER[s1_session] - SESSION_ORDER[s2_session]) == 1:
            e1 = random.choice(assignment[slot1])
            e2 = random.choice(assignment[slot2])
            if slot2 not in teachers[e1]['indispo'] and slot1 not in teachers[e2]['indispo']:
                assignment[slot1].remove(e1)
                assignment[slot1].append(e2)
                assignment[slot2].remove(e2)
                assignment[slot2].append(e1)
    return assignment

def run_ga(slots, teachers):
    slots_dict = {slot: data for slot, data in slots}
    pop_size = 50
    generations = 200
    pop = generate_population(pop_size, slots, teachers)
    
    for gen in range(generations):
        pop = sorted(pop, key=lambda x: fitness(x, teachers, slots_dict), reverse=True)
        new_pop = pop[:5]
        while len(new_pop) < pop_size:
            p1, p2 = random.choices(pop[:pop_size//2], k=2)
            child = crossover(p1, p2)
            if random.random() < 0.2:
                child = mutate(child, teachers, slots, slots_dict)
            for slot in child:
                slot_data = slots_dict[slot]
                min_needed = 2 * slot_data['room_count']
                max_needed = 4 * slot_data['room_count']
                child[slot] = list(set(child[slot]))
                while len(child[slot]) < min_needed:
                    available = [e for e in teachers if slot not in teachers[e]['indispo'] and e not in child[slot]]
                    if available:
                        child[slot].append(random.choice(available))
                if len(child[slot]) > max_needed:
                    child[slot] = child[slot][:max_needed]
            new_pop.append(child)
        pop = new_pop
    
    return pop[0]

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestion des Créneaux de Surveillance")
        self.geometry("1000x800")
        
        # Buttons and Search Bars
        tk.Button(self, text="Charger Créneaux (Excel)", command=self.load_slots).pack(pady=5)
        tk.Button(self, text="Charger Enseignants (Excel)", command=self.load_teachers).pack(pady=5)
        tk.Button(self, text="Charger Vœux (Excel)", command=self.load_wishes).pack(pady=5)
        tk.Button(self, text="Configurer Quotas par Grade", command=self.configure_quotas).pack(pady=5)
        tk.Button(self, text="Générer Planning", command=self.generate_planning).pack(pady=5)
        
        self.teacher_frame = tk.Frame(self)
        tk.Button(self.teacher_frame, text="Voir par Enseignant", command=self.show_by_teacher).pack(side=tk.LEFT, pady=5)
        self.teacher_search = tk.Entry(self.teacher_frame)
        self.teacher_search.pack(side=tk.LEFT, pady=5, padx=5)
        self.teacher_frame.pack()
        
        self.day_frame = tk.Frame(self)
        tk.Button(self.day_frame, text="Voir par Jour", command=self.show_by_day).pack(side=tk.LEFT, pady=5)
        self.day_search = tk.Entry(self.day_frame)
        self.day_search.pack(side=tk.LEFT, pady=5, padx=5)
        self.day_frame.pack()
        
        self.room_frame = tk.Frame(self)
        tk.Button(self.room_frame, text="Voir par Salle", command=self.show_by_room).pack(side=tk.LEFT, pady=5)
        self.room_search = tk.Entry(self.room_frame)
        self.room_search.pack(side=tk.LEFT, pady=5, padx=5)
        self.room_frame.pack()
        
        self.info_frame = tk.Frame(self)
        tk.Button(self.info_frame, text="Voir Infos Générales", command=self.show_general_info).pack(side=tk.LEFT, pady=5)
        self.info_search = tk.Entry(self.info_frame)
        self.info_search.pack(side=tk.LEFT, pady=5, padx=5)
        self.info_frame.pack()
        
        tk.Button(self, text="Exporter CSV", command=self.export_csv).pack(pady=5)
        tk.Button(self, text="Exporter PDF", command=self.export_pdf).pack(pady=5)
        
        # Treeview
        self.tree = ttk.Treeview(self, columns=("Slot", "Enseignants"), show="headings")
        self.tree.heading("Slot", text="Créneau")
        self.tree.heading("Enseignants", text="Enseignants Assignés")
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.slots = []
        self.teachers = {}
        self.best = None
        self.day_to_date = {}
        self.room_assignments = {}
        
        # Bind search events
        self.teacher_search.bind('<KeyRelease>', lambda event: self.filter_tree('teacher'))
        self.day_search.bind('<KeyRelease>', lambda event: self.filter_tree('day'))
        self.room_search.bind('<KeyRelease>', lambda event: self.filter_tree('room'))
        self.info_search.bind('<KeyRelease>', lambda event: self.filter_tree('info'))
        
        # Quota configuration window
        self.quota_window = None
        self.quota_entries = {}

    def filter_tree(self, view):
        search_text = ''
        if view == 'teacher' and self.teacher_search.get():
            search_text = self.teacher_search.get().lower()
        elif view == 'day' and self.day_search.get():
            search_text = self.day_search.get().lower()
        elif view == 'room' and self.room_search.get():
            search_text = self.room_search.get().lower()
        elif view == 'info' and self.info_search.get():
            search_text = self.info_search.get().lower()

        for item in self.tree.get_children():
            match = False
            for col in self.tree['columns']:
                value = str(self.tree.set(item, col)).lower()
                if search_text in value:
                    match = True
                    break
            self.tree.detach(item) if not match else self.tree.reattach(item, '', 0)

    def load_slots(self):
        file = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file:
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
                enseignant = group['enseignant'].iloc[0]
                session = group['session'].iloc[0]
                self.slots.append((slot, {'room_count': room_count, 'enseignant': enseignant, 'session': session}))
                self.room_assignments[slot] = {room: [] for room in group['cod_salle'].unique()}
            
            unique_dates = sorted(df['dateExam'].unique())
            self.day_to_date = {str(i+1): d.strftime('%Y-%m-%d') for i, d in enumerate(unique_dates)}
            
            messagebox.showinfo("Info", f"{len(self.slots)} créneaux chargés.")

    def load_teachers(self):
        file = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file:
            engine = 'openpyxl' if file.endswith('.xlsx') else 'xlrd'
            df = pd.read_excel(file, engine=engine)
            for _, row in df.iterrows():
                participe = row['participe_surveillance'] in [1, '1', True, 'true']
                if participe:
                    code = str(row['code_smartex_ens'])
                    self.teachers[code] = {
                        'nom': row.get('nom_ens', ''),
                        'prenom': row.get('prenom_ens', ''),
                        'grade': row['grade_code_ens'],
                        'quota': GRADE_QUOTAS.get(row['grade_code_ens'], 2),
                        'indispo': [],
                        'participe_surveillance': True
                    }
            messagebox.showinfo("Info", f"{len(self.teachers)} enseignants chargés.")

    def load_wishes(self):
        file = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
        if file:
            engine = 'openpyxl' if file.endswith('.xlsx') else 'xlrd'
            df = pd.read_excel(file, engine=engine)
            df = df[(df['semestre'] == 'Semestre 2') & (df['type_ex'] == 'P')]
            for _, row in df.iterrows():
                ens = str(row['code_smartex_ens'])
                if ens in self.teachers:
                    date = self.day_to_date.get(str(row['jour']), None)
                    if date:
                        slot = f"{date} {row['seance']}"
                        if slot not in self.teachers[ens]['indispo']:
                            self.teachers[ens]['indispo'].append(slot)
            messagebox.showinfo("Info", "Vœux chargés.")

    def configure_quotas(self):
        if self.quota_window and self.quota_window.winfo_exists():
            self.quota_window.lift()
            return
        
        self.quota_window = tk.Toplevel(self)
        self.quota_window.title("Configurer Quotas par Grade")
        self.quota_window.geometry("300x300")
        
        tk.Label(self.quota_window, text="Entrez les quotas par grade :").pack(pady=5)
        
        for grade in GRADE_QUOTAS:
            frame = tk.Frame(self.quota_window)
            tk.Label(frame, text=f"{grade}: ").pack(side=tk.LEFT)
            entry = tk.Entry(frame)
            entry.insert(0, str(GRADE_QUOTAS[grade]))
            entry.pack(side=tk.LEFT, padx=5)
            self.quota_entries[grade] = entry
            frame.pack(pady=2)
        
        tk.Button(self.quota_window, text="Sauvegarder", command=self.save_quotas).pack(pady=10)
        tk.Button(self.quota_window, text="Annuler", command=self.quota_window.destroy).pack(pady=5)

    def save_quotas(self):
        for grade, entry in self.quota_entries.items():
            try:
                quota = int(entry.get())
                if quota < 0:
                    raise ValueError
                GRADE_QUOTAS[grade] = quota
            except ValueError:
                messagebox.showerror("Erreur", f"Le quota pour {grade} doit être un nombre positif.")
                return
        # Update teachers' quotas based on new GRADE_QUOTAS
        for teacher in self.teachers:
            self.teachers[teacher]['quota'] = GRADE_QUOTAS.get(self.teachers[teacher]['grade'], 2)
        messagebox.showinfo("Info", "Quotas mis à jour avec succès.")
        if self.quota_window:
            self.quota_window.destroy()

    def generate_planning(self):
        if not self.slots or not self.teachers:
            messagebox.showerror("Erreur", "Chargez les données d'abord !")
            return
        self.best = run_ga(self.slots, self.teachers)
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Slot", "Enseignants")
        self.tree.heading("Slot", text="Créneau")
        self.tree.heading("Enseignants", text="Enseignants Assignés")
        for slot in sorted(self.best.keys()):
            teachers_assigned = [str(teacher) for teacher in self.best[slot]]
            self.tree.insert("", "end", values=(slot, ", ".join(teachers_assigned)))
            room_count = next(data['room_count'] for s, data in self.slots if s == slot)
            teachers_per_room = len(teachers_assigned) // room_count
            rooms = list(self.room_assignments[slot].keys())
            for i, teacher in enumerate(teachers_assigned):
                room_idx = i // teachers_per_room
                if room_idx < len(rooms):
                    self.room_assignments[slot][rooms[room_idx]].append(teacher)
        messagebox.showinfo("Info", "Planning généré !")

    def show_by_teacher(self):
        if not self.best:
            messagebox.showerror("Erreur", "Générez le planning d'abord !")
            return
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Enseignant", "Nom", "Prenom", "Grade", "Quota", "Nombre de Gardes", "Créneaux Assignés", "Vœux Indispo")
        self.tree.heading("Enseignant", text="Enseignant")
        self.tree.heading("Nom", text="Nom")
        self.tree.heading("Prenom", text="Prénom")
        self.tree.heading("Grade", text="Grade")
        self.tree.heading("Quota", text="Quota")
        self.tree.heading("Nombre de Gardes", text="Nombre de Gardes")
        self.tree.heading("Créneaux Assignés", text="Créneaux Assignés")
        self.tree.heading("Vœux Indispo", text="Vœux Indispo")
        teacher_slots = {teacher: [] for teacher in self.teachers}
        for slot in self.best:
            for teacher in self.best[slot]:
                teacher_slots[teacher].append(slot)
        for teacher in sorted(teacher_slots.keys()):
            data = self.teachers[teacher]
            num_gardes = len(teacher_slots[teacher])
            self.tree.insert("", "end", values=(
                teacher,
                data['nom'],
                data['prenom'],
                data['grade'],
                data['quota'],
                num_gardes,
                ", ".join(sorted(teacher_slots[teacher])),
                ", ".join(sorted(data['indispo']))
            ))
        assigned_teachers = set().union(*self.best.values())
        available_teachers = {t for t in self.teachers if self.teachers[t]['participe_surveillance'] and t not in assigned_teachers}
        for teacher in sorted(available_teachers):
            data = self.teachers[teacher]
            self.tree.insert("", "end", values=(
                teacher,
                data['nom'],
                data['prenom'],
                data['grade'],
                data['quota'],
                0,
                "",
                ", ".join(sorted(data['indispo']))
            ))

    def show_by_day(self):
        if not self.best:
            messagebox.showerror("Erreur", "Générez le planning d'abord !")
            return
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Jour", "Créneaux")
        self.tree.heading("Jour", text="Jour")
        self.tree.heading("Créneaux", text="Créneaux")
        day_slots = {}
        for slot in self.best:
            day = slot.split()[0]
            if day not in day_slots:
                day_slots[day] = []
            day_slots[day].append(slot)
        for day in sorted(day_slots.keys()):
            self.tree.insert("", "end", values=(day, ", ".join(sorted(day_slots[day]))))

    def show_by_room(self):
        if not self.best:
            messagebox.showerror("Erreur", "Générez le planning d'abord !")
            return
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Slot", "Salle", "Enseignants")
        self.tree.heading("Slot", text="Créneau")
        self.tree.heading("Salle", text="Salle")
        self.tree.heading("Enseignants", text="Enseignants Assignés")
        for slot in sorted(self.best.keys()):
            for room, teachers in self.room_assignments[slot].items():
                self.tree.insert("", "end", values=(slot, room, ", ".join(sorted(teachers))))

    def show_general_info(self):
        if not self.best:
            messagebox.showerror("Erreur", "Générez le planning d'abord !")
            return
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Info", "Valeur")
        self.tree.heading("Info", text="Information")
        self.tree.heading("Valeur", text="Valeur")
        total_teachers = len(self.teachers)
        assigned_teachers = len(set().union(*self.best.values()))
        unassigned_teachers = sum(1 for t in self.teachers if self.teachers[t]['participe_surveillance'] and t not in set().union(*self.best.values()))
        total_slots = len(self.best)
        self.tree.insert("", "end", values=("Nombre total d'enseignants", total_teachers))
        self.tree.insert("", "end", values=("Nombre d'enseignants assignés", assigned_teachers))
        self.tree.insert("", "end", values=("Nombre d'enseignants non assignés (participe = 1)", unassigned_teachers))
        self.tree.insert("", "end", values=("Nombre total de créneaux", total_slots))

    def export_csv(self):
        if not self.best:
            messagebox.showerror("Erreur", "Générez le planning d'abord !")
            return
        file = filedialog.asksaveasfilename(defaultextension=".csv")
        if file:
            df = pd.DataFrame({"Slot": list(self.best.keys()), "Enseignants": [", ".join([str(t) for t in v]) for v in self.best.values()]})
            df.to_csv(file, index=False)
            messagebox.showinfo("Info", "Export CSV OK.")

    def export_pdf(self):
        if not self.best:
            messagebox.showerror("Erreur", "Générez le planning d'abord !")
            return
        file = filedialog.asksaveasfilename(defaultextension=".pdf")
        if file:
            c = canvas.Canvas(file, pagesize=letter)
            y = 750
            c.drawString(100, y, "Planning de Surveillance")
            y -= 30
            for slot in sorted(self.best.keys()):
                ens_str = ", ".join([str(t) for t in self.best[slot]])
                c.drawString(100, y, f"{slot}: {ens_str}")
                y -= 20
                if y < 50:
                    c.showPage()
                    y = 750
            c.save()
            messagebox.showinfo("Info", "Export PDF OK.")

if __name__ == "__main__":
    app = App()
    app.mainloop()
