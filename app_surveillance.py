import random
import numpy as np
from datetime import datetime, timedelta
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas

# Fonctions utilitaires
def parse_datetime(slot_str):
    return datetime.strptime(slot_str, '%Y-%m-%d %H:%M')

def get_teacher_slots(assignment, teacher):
    return sorted([parse_datetime(slot) for slot in assignment if teacher in assignment[slot]])

def dispersion_penalty(teacher_slots):
    if len(teacher_slots) < 2:
        return 0
    deltas = [(teacher_slots[i+1] - teacher_slots[i]).total_seconds() / 3600 for i in range(len(teacher_slots)-1)]
    min_delta = min(deltas)
    return -max(0, 4 - min_delta) * 10  # Pénalité si écart <4h

# Génération population
def generate_population(pop_size, slots, teachers):
    population = []
    teacher_list = list(teachers.keys())
    for _ in range(pop_size):
        assignment = {}
        for slot, nb_needed in slots:
            available = [e for e in teacher_list if slot not in teachers[e]['indispo']]
            selected = random.sample(available, min(nb_needed, len(available))) if len(available) >= nb_needed else random.choices(available, k=nb_needed)
            assignment[slot] = selected
        population.append(assignment)
    return population

# Fitness
def fitness(assignment, teachers, slots_dict):
    score = 0.0
    # Couverture
    for slot in assignment:
        unique_assigned = set(assignment[slot])
        if len(unique_assigned) < slots_dict[slot]:
            score -= 1000 * (slots_dict[slot] - len(unique_assigned))
    # No duplicates in slot
    for slot in assignment:
        if len(assignment[slot]) != len(set(assignment[slot])):
            score -= 500
    # Counts and quota
    counts = {e: 0 for e in teachers}
    for slot in assignment:
        for e in assignment[slot]:
            counts[e] += 1
    for e in counts:
        if counts[e] > teachers[e]['quota']:
            score -= 1000 * (counts[e] - teachers[e]['quota'])
    # Équité (variance)
    if sum(counts.values()) > 0:
        variance = np.var(list(counts.values()))
        score -= variance * 10
    # Dispersion
    for e in teachers:
        t_slots = get_teacher_slots(assignment, e)
        score += dispersion_penalty(t_slots)
    return score

# Crossover et mutation
def crossover(parent1, parent2):
    child = {}
    keys = list(parent1.keys())
    midpoint = len(keys) // 2
    for i in range(midpoint):
        child[keys[i]] = parent1[keys[i]][:]
    for i in range(midpoint, len(keys)):
        child[keys[i]] = parent2[keys[i]][:]
    return child

def mutate(assignment, teachers, slots):
    slot_keys = list(assignment.keys())
    slot1, slot2 = random.sample(slot_keys, 2)
    if assignment[slot1] and assignment[slot2]:
        e1 = random.choice(assignment[slot1])
        e2 = random.choice(assignment[slot2])
        if slot2 not in teachers[e1]['indispo'] and slot1 not in teachers[e2]['indispo']:
            assignment[slot1].remove(e1)
            assignment[slot1].append(e2)
            assignment[slot2].remove(e2)
            assignment[slot2].append(e1)
    return assignment

# Boucle GA

import random
import time

def run_ga(slots, teachers):
    slots_dict = {slot: nb for slot, nb in slots}
    pop_size = 50
    generations = 200
    random.seed(time.time())  # Différente à chaque run
    pop = generate_population(pop_size, slots, teachers)
    
    best_global = None
    best_fitness = float('-inf')
    fitness_history = []
    
    for gen in range(generations):
        pop = sorted(pop, key=lambda x: fitness(x, teachers, slots_dict), reverse=True)
        new_pop = pop[:5]  # Élite
        while len(new_pop) < pop_size:
            p1, p2 = random.choices(pop[:pop_size//2], k=2)
            child = crossover(p1, p2)
            if random.random() < 0.2:
                child = mutate(child, teachers, slots)
            for slot in child:
                child[slot] = list(set(child[slot]))
                while len(child[slot]) < slots_dict[slot]:
                    available = [e for e in teachers if slot not in teachers[e]['indispo'] and e not in child[slot]]
                    if available:
                        child[slot].append(random.choice(available))
            new_pop.append(child)
        pop = new_pop
        
        current_best_fitness = fitness(pop[0], teachers, slots_dict)
        fitness_history.append(current_best_fitness)
        if current_best_fitness > best_fitness:
            best_fitness = current_best_fitness
            best_global = pop[0].copy()
        
        if gen % 50 == 0:
            print(f"Gen {gen}: Meilleure fitness = {current_best_fitness}")
    
    # Analyse finale
    print(f"Meilleure fitness globale = {best_fitness}")
    print("Dernières 5 fitness :", fitness_history[-5:])
    print("Vérification manuelle suggérée :")
    counts = {e: 0 for e in teachers}
    for slot in best_global:
        for e in best_global[slot]:
            counts[e] += 1
    print("Nombre de surveillances par enseignant :", counts)
    return best_global

# Interface Tkinter
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestion des Créneaux de Surveillance")
        self.geometry("800x600")
        
        # Boutons
        tk.Button(self, text="Charger Créneaux (CSV)", command=self.load_slots).pack(pady=5)
        tk.Button(self, text="Charger Enseignants (CSV)", command=self.load_teachers).pack(pady=5)
        tk.Button(self, text="Générer Planning", command=self.generate_planning).pack(pady=5)
        tk.Button(self, text="Exporter CSV", command=self.export_csv).pack(pady=5)
        tk.Button(self, text="Exporter PDF", command=self.export_pdf).pack(pady=5)
        
        # Table pour visualisation
        self.tree = ttk.Treeview(self, columns=("Slot", "Enseignants"), show="headings")
        self.tree.heading("Slot", text="Créneau")
        self.tree.heading("Enseignants", text="Enseignants Assignés")
        self.tree.pack(fill=tk.BOTH, expand=True)
        
        self.slots = None
        self.teachers = None
        self.best = None

    def load_slots(self):
        file = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if file:
            df = pd.read_csv(file)  # Attendu: colonnes 'slot' (str '%Y-%m-%d %H:%M'), 'nb_needed' (int)
            self.slots = list(zip(df['slot'], df['nb_needed']))
            messagebox.showinfo("Info", f"{len(self.slots)} créneaux chargés.")

    def load_teachers(self):
        file = filedialog.askopenfilename(filetypes=[("CSV", "*.csv")])
        if file:
            df = pd.read_csv(file)  # Attendu: colonnes 'id', 'grade', 'quota', 'indispo' (str séparés par ;)
            self.teachers = {}
            for _, row in df.iterrows():
                indispo = row['indispo'].split(';') if pd.notna(row['indispo']) else []
                self.teachers[row['id']] = {'grade': row['grade'], 'quota': row['quota'], 'indispo': indispo}
            messagebox.showinfo("Info", f"{len(self.teachers)} enseignants chargés.")

    def generate_planning(self):
        if not self.slots or not self.teachers:
            messagebox.showerror("Erreur", "Chargez les données d'abord !")
            return
        self.best = run_ga(self.slots, self.teachers)
        # Affichage dans table
        self.tree.delete(*self.tree.get_children())
        for slot in sorted(self.best):
            ens_str = ", ".join(self.best[slot])
            self.tree.insert("", "end", values=(slot, ens_str))
        messagebox.showinfo("Info", "Planning généré !")

    def export_csv(self):
        if not self.best:
            messagebox.showerror("Erreur", "Générez le planning d'abord !")
            return
        file = filedialog.asksaveasfilename(defaultextension=".csv")
        if file:
            df = pd.DataFrame({"Slot": list(self.best.keys()), "Enseignants": [", ".join(v) for v in self.best.values()]})
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
            for slot in sorted(self.best):
                ens_str = ", ".join(self.best[slot])
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
