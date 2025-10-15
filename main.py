"""
Application principale de gestion des surveillances d'examens
Version modulaire 2.0 - Architecture propre et maintenable
"""

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import pandas as pd
from datetime import datetime

# Import des modules personnalisés
from auth_module import ModernLoginApp, COLORS
from database_module import DatabaseManager
from algorithm_module import run_ga_improved, fitness
from ui_components import (
    SimpleButton, StatusBar, ModernTreeview, 
    ProgressWindow, setup_styles
)
from config import (
    GRADE_QUOTAS, SESSION_TIMES, SESSION_ORDER,
    APP_NAME, APP_VERSION
)


class SurveillanceApp:
    """Application principale de gestion des surveillances"""
    
    def __init__(self):
        print(f"🚀 Initialisation de {APP_NAME} v{APP_VERSION}")
        
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{APP_VERSION}")
        self.root.geometry("1300x800")
        self.root.configure(bg=COLORS['bg'])
        
        # Variables de l'application
        self.slots = []
        self.teachers = {}
        self.best = None
        self.best_fitness_history = []
        self.day_to_date = {}
        self.room_assignments = {}
        
        # Gestionnaire de base de données
        self.db_manager = DatabaseManager()
        
        # Configuration des styles
        setup_styles()
        
        # Création de l'interface
        self.create_ui()
        
        print("✅ Application initialisée avec succès")
    
    def create_ui(self):
        """Crée l'interface utilisateur complète"""
        
        # EN-TÊTE
        self.create_header()
        
        # ZONE PRINCIPALE
        main = tk.Frame(self.root, bg=COLORS['bg'])
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        # Barre d'outils
        self.create_toolbar(main)
        
        # Barre de recherche et export
        self.create_search_bar(main)
        
        # Tableau principal
        self.create_table(main)
        
        # BARRE DE STATUT
        self.status_bar = StatusBar(self.root)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)
        self.update_status("Prêt à commencer", "info")
        
        # Message de bienvenue
        self.show_welcome()
    
    def create_header(self):
        """Crée l'en-tête de l'application"""
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
                text=f"Portail Administratif - v{APP_VERSION}",
                font=('Arial', 10),
                bg=COLORS['primary'],
                fg='#BDC3C7').pack()
    
    def create_toolbar(self, parent):
        """Crée la barre d'outils avec tous les boutons"""
        toolbar_container = tk.Frame(parent, bg=COLORS['card'], relief=tk.FLAT, bd=1)
        toolbar_container.pack(fill=tk.X, pady=(0, 15))
        
        # Canvas avec scrollbar horizontale
        toolbar_canvas = tk.Canvas(toolbar_container, bg=COLORS['card'], height=100, highlightthickness=0)
        toolbar_scrollbar = ttk.Scrollbar(toolbar_container, orient=tk.HORIZONTAL, command=toolbar_canvas.xview)
        toolbar = tk.Frame(toolbar_canvas, bg=COLORS['card'])
        
        toolbar.bind("<Configure>", lambda e: toolbar_canvas.configure(scrollregion=toolbar_canvas.bbox("all")))
        toolbar_canvas.create_window((0, 0), window=toolbar, anchor="nw")
        toolbar_canvas.configure(xscrollcommand=toolbar_scrollbar.set)
        
        toolbar_canvas.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        toolbar_scrollbar.pack(side=tk.BOTTOM, fill=tk.X)
        
        toolbar_content = tk.Frame(toolbar, bg=COLORS['card'])
        toolbar_content.pack(fill=tk.X, padx=15, pady=12)
        
        # Section DONNÉES
        self.create_section(toolbar_content, "DONNÉES", [
            ("📄 Créneaux", self.load_slots, COLORS['primary']),
            ("👥 Enseignants", self.load_teachers, COLORS['primary']),
            ("⭐ Vœux", self.load_wishes, COLORS['primary'])
        ])
        
        self.add_separator(toolbar_content)
        
        # Section CONFIGURATION & GÉNÉRATION
        self.create_section(toolbar_content, "CONFIGURATION & GÉNÉRATION", [
            ("⚙ Quotas", self.configure_quotas, COLORS['secondary']),
            ("▶ GÉNÉRER", self.generate_planning, COLORS['success'])
        ])
        
        self.add_separator(toolbar_content)
        
        # Section VISUALISATION
        self.create_section(toolbar_content, "VISUALISATION", [
            ("👤 Enseignants", self.show_by_teacher, COLORS['text_light']),
            ("📅 Jours", self.show_by_day, COLORS['text_light']),
            ("🚪 Salles", self.show_by_room, COLORS['text_light']),
            ("📊 Qualité", self.show_planning_quality, COLORS['secondary'])
        ])
        
        self.add_separator(toolbar_content)
        
        # Section HISTORIQUE
        self.create_section(toolbar_content, "HISTORIQUE", [
            ("💾 Sauvegarder", self.save_current_planning, COLORS['accent']),
            ("📂 Historique", self.show_planning_history, COLORS['accent'])
        ])
    
    def create_section(self, parent, title, buttons):
        """Crée une section avec titre et boutons"""
        section = tk.Frame(parent, bg=COLORS['card'])
        section.pack(side=tk.LEFT, padx=(0, 30))
        
        tk.Label(section,
                text=title,
                font=('Arial', 9, 'bold'),
                bg=COLORS['card'],
                fg=COLORS['text_light']).pack(anchor='w', pady=(0, 8))
        
        btn_frame = tk.Frame(section, bg=COLORS['card'])
        btn_frame.pack()
        
        for text, command, color in buttons:
            SimpleButton(btn_frame,
                        text=text,
                        command=command,
                        bg_color=color).pack(side=tk.LEFT, padx=3)
    
    def add_separator(self, parent):
        """Ajoute un séparateur vertical"""
        tk.Frame(parent, bg=COLORS['border'], width=1).pack(side=tk.LEFT, fill=tk.Y, padx=15)
    
    def create_search_bar(self, parent):
        """Crée la barre de recherche et les boutons d'export"""
        search_frame = tk.Frame(parent, bg=COLORS['card'], relief=tk.FLAT)
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
        
        SimpleButton(search_frame,
                    text="📄 PDF",
                    command=self.export_pdf,
                    bg_color=COLORS['text_light']).pack(side=tk.RIGHT, padx=5, pady=10)
        
        SimpleButton(search_frame,
                    text="💾 CSV",
                    command=self.export_csv,
                    bg_color=COLORS['text_light']).pack(side=tk.RIGHT, padx=5, pady=10)
    
    def create_table(self, parent):
        """Crée le tableau principal avec scrollbars"""
        table_frame = tk.Frame(parent, bg=COLORS['card'])
        table_frame.pack(fill=tk.BOTH, expand=True)
        
        # Scrollbars
        y_scroll = ttk.Scrollbar(table_frame)
        y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        
        x_scroll = ttk.Scrollbar(table_frame, orient=tk.HORIZONTAL)
        x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Treeview
        self.tree = ModernTreeview(table_frame,
                                   yscrollcommand=y_scroll.set,
                                   xscrollcommand=x_scroll.set,
                                   selectmode='extended')
        self.tree.pack(fill=tk.BOTH, expand=True, padx=2, pady=2)
        
        y_scroll.config(command=self.tree.yview)
        x_scroll.config(command=self.tree.xview)
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

    
    def update_status(self, text, status_type="info"):
        """Met à jour la barre de statut"""
        self.status_bar.set_status(text, status_type)
        self.root.update_idletasks()
    
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
    
    # NOTE: Les méthodes suivantes doivent être copiées depuis votre code original:
    # - load_slots
    # - load_teachers
    # - load_wishes
    # - configure_quotas
    # - generate_planning
    # - display_planning_result
    # - show_by_teacher
    # - show_by_day
    # - show_by_room
    # - show_planning_quality
    # - save_current_planning
    # - show_planning_history
    # - export_csv
    # - export_pdf
    
    def run(self):
        """Lance l'application"""
        print("▶️ Lancement de l'interface graphique")
        self.root.mainloop()
    
    # Méthodes importées à copier depuis votre code original
    def load_slots(self):
        """Charge les créneaux depuis un fichier Excel"""
        # Copiez votre code original ici
        pass
    
    def load_teachers(self):
        """Charge les enseignants depuis un fichier Excel"""
        # Copiez votre code original ici
        pass
    
    def load_wishes(self):
        """Charge les vœux d'indisponibilité"""
        # Copiez votre code original ici
        pass
    
    def configure_quotas(self):
        """Configure les quotas par grade"""
        # Copiez votre code original ici
        pass
    
    def generate_planning(self):
        """Génère le planning avec l'algorithme génétique"""
        # Copiez votre code original ici
        pass
    
    def display_planning_result(self):
        """Affiche le planning généré"""
        # Copiez votre code original ici
        pass
    
    def show_by_teacher(self):
        """Vue par enseignant"""
        # Copiez votre code original ici
        pass
    
    def show_by_day(self):
        """Vue par jour"""
        # Copiez votre code original ici
        pass
    
    def show_by_room(self):
        """Vue par salle"""
        # Copiez votre code original ici
        pass
    
    def show_planning_quality(self):
        """Affiche la qualité du planning"""
        # Copiez votre code original ici
        pass
    
    def save_current_planning(self):
        """Sauvegarde le planning actuel"""
        # Copiez votre code original ici
        pass
    
    def show_planning_history(self):
        """Affiche l'historique des plannings"""
        # Copiez votre code original ici
        pass
    
    def export_csv(self):
        """Exporte en CSV"""
        # Copiez votre code original ici
        pass
    
    def export_pdf(self):
        """Exporte en PDF"""
        # Copiez votre code original ici
        pass


def main():
    """Point d'entrée principal de l'application"""
    
    def launch_surveillance_app():
        """Lance l'application après authentification réussie"""
        print("✅ Authentification réussie")
        print("🚀 Lancement de l'application de surveillance...")
        app = SurveillanceApp()
        app.run()
    
    # Affichage du banner
    print("=" * 60)
    print(f"  {APP_NAME}")
    print(f"  Version {APP_VERSION}")
    print("=" * 60)
    print()
    print("🔐 Lancement du module d'authentification...")
    print()
    
    # Lancer l'authentification
    login_app = ModernLoginApp(launch_surveillance_app)
    login_app.run()
    
    print()
    print("👋 Fermeture de l'application")
    print("=" * 60)


if __name__ == "__main__":
    main()