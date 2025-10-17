# Les méthodes de visualisation
def show_by_teacher(self):
    from view_methods import show_by_teacher
    show_by_teacher(self)

def show_by_day_calendar(self):
    from view_methods import show_by_day_calendar
    show_by_day_calendar(self)

def show_by_room(self):
    from view_methods import show_by_room
    show_by_room(self)

def show_planning_quality(self):
    from view_methods import show_planning_quality
    show_planning_quality(self)

def print_current_view(self):
    """Imprime la vue actuelle en PDF"""
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
        from pdf_export import (
            export_calendar_pdf, export_teacher_pdf, export_room_pdf,
            export_quality_pdf, export_generic_pdf
        )

        if self.current_view == "calendar":
            export_calendar_pdf(file, self)
        elif self.current_view == "teacher":
            export_teacher_pdf(file, self)
        elif self.current_view == "room":
            export_room_pdf(file, self)
        elif self.current_view == "quality":
            export_quality_pdf(file, self)
        else:
            export_generic_pdf(file, self)
        messagebox.showinfo("✅ Succès", f"PDF exporté:\n{file}")
    except Exception as e:
        messagebox.showerror("❌ Erreur", f"Erreur export PDF:\n{str(e)}")

if __name__ == "__main__":
    app = App()
    app.mainloop()

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
from datetime import datetime
import time

# Import du module algorithme génétique
from genetic_algorithm import (
    run_ga_optimized, fitness, is_valid_teacher, 
    check_gap_violations, check_responsable_presence,
    calculate_quota_violations, SESSION_ORDER, SESSION_TIMES
)

# Import du module PDF
from pdf_export import (
    export_calendar_pdf, export_teacher_pdf, export_room_pdf,
    export_quality_pdf, export_generic_pdf, export_selected_teacher_pdf
)

# Configuration initiale des quotas par grade
GRADE_QUOTAS = {
    "PR": 8, "MA": 7, "V": 6, "PTC": 5, "AC": 4,
    "VA": 4, "AS": 4, "EX": 4, "MC": 4, "PES": 4
}

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Gestion des Créneaux de Surveillance - Version Optimisée")
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
        
        # Frame de chargement
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
        
        # Frame de génération
        gen_frame = tk.LabelFrame(main_frame, text="🧬 Génération du Planning",
                                font=("Arial", 10, "bold"), padx=10, pady=5)
        gen_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(gen_frame, text="▶️ GÉNÉRER PLANNING", command=self.generate_planning,
                 bg="#4CAF50", fg="white", font=("Arial", 14, "bold"),
                 height=2).pack(pady=10)
        
        # Frame de visualisation
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
        
        # Frame d'export
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
        
        # Barre de recherche
        search_frame = tk.Frame(main_frame)
        search_frame.pack(fill=tk.X, pady=5)
        tk.Label(search_frame, text="🔍 Recherche:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
        self.search_entry = tk.Entry(search_frame, font=("Arial", 10))
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
        self.search_entry.bind("<KeyRelease>", self.on_search)
        
        # TreeView
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
                
                if 'ordre_arrivee' in df.columns or 'timestamp' in df.columns:
                    sort_col = 'ordre_arrivee' if 'ordre_arrivee' in df.columns else 'timestamp'
                    df = df.sort_values(sort_col)
                
                loaded_count = 0
                
                for idx, row in df.iterrows():
                    if pd.isna(row['code_smartex_ens']):
                        continue
                    ens = str(int(row['code_smartex_ens']))
                    if ens in self.teachers:
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
                                    priority = 2.0 - (idx / max(len(df), 1))
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
        
        progress_label = tk.Label(progress_window, text="Génération 0/2000",
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
        
        # Assigner aux salles
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

    def populate_flat_view(self):
        self.tree.delete(*self.tree.get_children())
        for row in self.view_data:
            text = " ".join(map(str, row[:-1] if len(row) > 1 and isinstance(row[-1], str) and row[-1] in ["over_quota", "unassigned", "voeux_violes", "voeux_ok", "optimal", "acceptable", "problem", "header", "ok", "warning", "error"] else row)).lower()
            if self.current_filter in text or not self.current_filter:
                tag = row[-1] if len(row) > 1 and isinstance(row[-1], str) and row[-1] in ["over_quota", "unassigned", "voeux_violes", "voeux_ok", "optimal", "acceptable", "problem", "header", "ok", "warning", "error"] else ""
                values = row[:-1] if tag else row
                self.tree.insert("", "end", values=values, tags=(tag,) if tag else ())

    def configure_action_buttons(self):
        for widget in self.action_frame.winfo_children():
            widget.destroy()
        
        if self.current_view == "teacher":
            tk.Button(self.action_frame, text="🖨️ PDF Enseignant Sélectionné",
                     command=self.export_selected_teacher_wrapper, 
                     bg="#FF5722", fg="white").pack(side=tk.LEFT, padx=5)

    def export_selected_teacher_wrapper(self):
        selected = self.tree.selection()
        if not selected:
            messagebox.showerror("❌ Erreur", "Sélectionnez un enseignant!")
            return
        
        iid = selected[0]
        values = self.tree.item(iid)['values']
        export_selected_teacher_pdf(values, self.teachers)

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

    # Les méthodes de visualisation seront ajoutées dans la partie 2
    def show_by_teacher(self):
        pass  # À implémenter dans partie 2
    
    def show_by_day_calendar(self):
        pass  # À implémenter dans partie 2
    
    def show_by_room(self):
        pass  # À implémenter dans partie 2
    
    def show_planning_quality(self):
        pass  # À implémenter dans partie 2
    
    def print_current_view(self):
        pass  # À implémenter dans partie 2

if __name__ == "__main__":
    app = App()
    app.mainloop()