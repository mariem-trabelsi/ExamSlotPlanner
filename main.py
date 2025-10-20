
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import customtkinter as ctk
import pandas as pd
from datetime import datetime, timedelta
from collections import defaultdict
from PIL import Image, ImageTk
import sqlite3
import json
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
import os
from login import LoginApp
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import glob

from genetic_algorithm import (
    run_ga_optimized, fitness, is_valid_teacher, 
    SESSION_TIMES
)
from view_methods import (
    show_by_teacher, show_by_day_calendar, show_by_room,
    show_planning_quality_with_prof_resp, show_prof_responsable_details, assign_teachers_to_rooms
)

from pdf_export import (
    export_teachers_to_pdf,
)

# Configuration initiale des quotas par grade
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


system_font = "Segoe UI"
class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Gestion des Creneaux de Surveillance - Version Optimisee")
        self.geometry("1500x950")
        self.configure(fg_color="#FAFAFA")
        # Initialiser la base de données
        self.setup_database()


        # Thème moderne
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        # Modern color palette
        self.colors = {
            'primary': '#2563EB',
            'primary_hover': '#1D4ED8',
            'success': '#10B981',
            'success_light':"#5AE6B7",
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

        self.drag_data = {"item": None, "teacher": None, "source_slot": None}
        self.selected_teacher = None
        self.context_menu = None
        self.selected_teacher_for_transfer = None



        self.slots = []
        self.prof_resp_list = []  # Liste des repartitions profs responsables par ligne du fichier
        self.teachers = {}
        self.best = None
        self.best_fitness_history = []
        self.day_to_date = {}
        self.room_assignments = {}
        self.room_names = {}  # Noms des salles (ex: "A112")
        self.quota_window = None
        self.quota_entries = {}
        self.current_view = "default"
        self.data_loaded = {
        'slots': False,
        'teachers': False,
        'wishes': False
        }
        self.view_data = []
        self.action_frame = None
        self.search_entry = None
        self.current_filter = ""
        self.data_buttons = {}
        self.create_modern_ui()
    
    def setup_database(self):
        """Initialise la base de données SQLite"""
        self.conn = sqlite3.connect('planning_history.db')
        self.cursor = self.conn.cursor()
        
        # Créer la table si elle n'existe pas
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS planning_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                planning_data TEXT NOT NULL,
                
                
                teacher_count INTEGER,
                slot_count INTEGER,
                
                notes TEXT
            )
        ''')
        self.conn.commit()
    
    def save_planning_to_history(self, notes=""):
        """Sauvegarde le planning actuel dans l'historique"""
        if not self.best:
            self.show_error_message("❌ Erreur", "Aucun planning à sauvegarder!")
            return False
        
        try:
            # Préparer les données pour la sauvegarde
            planning_data = {
                'best': self.best,
                'teachers': self.teachers,
                'slots': self.slots,
                'room_assignments': self.room_assignments,
                'prof_resp_list': self.prof_resp_list
            }
            
            # Calculer les statistiques
            #fitness_score = self.best_fitness_history[-1] if self.best_fitness_history else 0
            #generation_count = len(self.best_fitness_history)
            teacher_count = len(set().union(*self.best.values()))
            slot_count = len(self.best)
            
            # Compter les violations de contraintes (exemple simplifié)
            #constraints_violated = self.count_constraint_violations()
            
            # Insérer dans la base de données
            self.cursor.execute('''
                INSERT INTO planning_history 
                (timestamp, planning_data, teacher_count, slot_count, notes)
                VALUES (?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                json.dumps(planning_data),
                #fitness_score,
                #generation_count,
                teacher_count,
                slot_count,
                #constraints_violated,
                notes
            ))
            
            self.conn.commit()
            
            history_id = self.cursor.lastrowid
            self.show_success_message("✅ Sauvegarde réussie", 
                f"Planning sauvegardé dans l'historique (ID: {history_id})")
            return True
            
        except Exception as e:
            self.show_error_message("❌ Erreur", f"Erreur lors de la sauvegarde:\n{str(e)}")
            return False
    def count_constraint_violations(self):
        """Compte le nombre de violations de contraintes"""
        violations = 0
        
        if not self.best:
            return violations
        
        # Vérifier les quotas
        teacher_assignments = {}
        for slot in self.best:
            for teacher in self.best[slot]:
                if teacher not in teacher_assignments:
                    teacher_assignments[teacher] = 0
                teacher_assignments[teacher] += 1
        
        for teacher, count in teacher_assignments.items():
            if teacher in self.teachers and count > self.teachers[teacher]['quota']:
                violations += 1
        
        # Vérifier les salles surchargées
        for slot in self.room_assignments:
            for room, teachers in self.room_assignments[slot].items():
                if len(teachers) > 4:  # Maximum 4 profs par salle
                    violations += 1
                if len(teachers) < 2:  # Minimum 2 profs par salle
                    violations += 1
        
        return violations
    

    def show_history(self):
        """Affiche l'historique des plannings"""
        try:
            self.cursor.execute('''
                SELECT id, timestamp, teacher_count, 
                    slot_count, notes
                FROM planning_history 
                ORDER BY timestamp DESC
            ''')
            
            history_records = self.cursor.fetchall()
            
            if not history_records:
                self.show_error_message("📊 Historique vide", 
                    "Aucun planning sauvegardé dans l'historique.\nGénérez et sauvegardez d'abord un planning.")
                return
            
            # Créer une fenêtre pour afficher l'historique
            history_window = ctk.CTkToplevel(self)
            history_window.title("📊 Historique des Plannings")
            history_window.geometry("1000x700")
            history_window.configure(fg_color=self.colors['bg'])
            
            # Header
            header = ctk.CTkFrame(history_window, fg_color=self.colors['card'],
                                corner_radius=16, height=80)
            header.pack(fill='x', padx=20, pady=20)
            header.pack_propagate(False)
            
            ctk.CTkLabel(header, 
                        text="📊 Historique des Plannings Générés",
                        font=("Segoe UI", 20, "bold"),
                        text_color=self.colors['text']).pack(pady=25)
            
            # Treeview pour l'historique
            tree_frame = ctk.CTkFrame(history_window, fg_color='transparent')
            tree_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
            
            # Scrollbars
            tree_scroll_y = ctk.CTkScrollbar(tree_frame)
            tree_scroll_y.pack(side='right', fill='y')
            
            tree_scroll_x = ctk.CTkScrollbar(tree_frame, orientation='horizontal')
            tree_scroll_x.pack(side='bottom', fill='x')
            
            # Configuration du treeview
            history_tree = ttk.Treeview(
                tree_frame,
                columns=("ID", "Date", "Enseignants", "Créneaux", "Notes"),
                show="headings",
                yscrollcommand=tree_scroll_y.set,
                xscrollcommand=tree_scroll_x.set,
                height=15
            )
            
            history_tree.pack(fill='both', expand=True)
            
            tree_scroll_y.configure(command=history_tree.yview)
            tree_scroll_x.configure(command=history_tree.xview)
            
            # Configurer les colonnes
            columns_config = [
                ("ID", 60, "center"),
                ("Date", 150, "center"),
                ("Enseignants", 100, "center"),
                ("Créneaux", 100, "center"),
                ("Notes", 300, "w")
            ]
            
            for col, width, anchor in columns_config:
                history_tree.heading(col, text=col)
                history_tree.column(col, width=width, anchor=anchor)
            
            # Remplir avec les données - SUPPRIMER TOUTE RÉFÉRENCE AUX VIOLATIONS
            for record in history_records:
                (id, timestamp, teacher_count, slot_count, notes) = record
                
                # Formater la date
                date_obj = datetime.fromisoformat(timestamp)
                formatted_date = date_obj.strftime("%d/%m/%Y %H:%M")
                
                # INSÉRER SIMPLEMENT LES DONNÉES SANS CALCUL DE VIOLATIONS
                history_tree.insert("", "end", values=(
                    id, formatted_date, teacher_count, slot_count, notes or ""
                ))
            
            # SUPPRIMER LES TAGS DE COULEUR PUISQU'ON N'A PLUS LES VIOLATIONS
            # history_tree.tag_configure("optimal", background="#D1FAE5")
            # history_tree.tag_configure("acceptable", background="#FEF3C7")
            # history_tree.tag_configure("problem", background="#FEE2E2")
            
            # Frame pour les boutons d'action
            button_frame = ctk.CTkFrame(history_window, fg_color='transparent')
            button_frame.pack(fill='x', padx=20, pady=(0, 20))
            
            ctk.CTkButton(button_frame, text="📋 Charger ce planning",
                        font=("Segoe UI", 13, "bold"),
                        fg_color=self.colors['primary'],
                        hover_color=self.colors['primary_hover'],
                        height=45,
                        command=lambda: self.load_selected_planning(history_tree),
                        width=200).pack(side='left', padx=(0, 10))
            
            ctk.CTkButton(button_frame, text="🗑️ Supprimer",
                        font=("Segoe UI", 13),
                        fg_color=self.colors['error'],
                        hover_color=self.adjust_color(self.colors['error'], -20),
                        height=45,
                        command=lambda: self.delete_selected_history(history_tree),
                        width=120).pack(side='left', padx=(0, 10))
            
            # ctk.CTkButton(button_frame, text="💾 Sauvegarder le planning actuel",
            #             font=("Segoe UI", 13),
            #             fg_color=self.colors['success'],
            #             hover_color=self.adjust_color(self.colors['success'], -20),
            #             height=45,
            #             command=self.prompt_save_current_planning,
            #             width=250).pack(side='left')
            
            ctk.CTkButton(button_frame, text="❌ Fermer",
                        font=("Segoe UI", 13),
                        fg_color=self.colors['hover'],
                        hover_color=self.colors['border'],
                        text_color=self.colors['text'],
                        height=45,
                        command=history_window.destroy,
                        width=120).pack(side='right')
            
        except Exception as e:
            self.show_error_message("❌ Erreur", f"Erreur lors du chargement de l'historique:\n{str(e)}")
    
    def prompt_save_current_planning(self):
        """Demande à l'utilisateur de sauvegarder le planning actuel"""
        if not self.best:
            self.show_error_message("❌ Erreur", "Aucun planning à sauvegarder!")
            return
        
        # Créer une fenêtre de dialogue pour les notes
        save_window = ctk.CTkToplevel(self)
        save_window.title("💾 Sauvegarder le planning")
        save_window.geometry("500x300")
        save_window.transient(self)
        save_window.grab_set()
        
        ctk.CTkLabel(save_window,
                    text="Ajouter une note pour ce planning:",
                    font=("Segoe UI", 16, "bold")).pack(pady=20)
        
        notes_entry = ctk.CTkTextbox(save_window, width=400, height=100)
        notes_entry.pack(pady=10)
        notes_entry.insert("1.0", f"Planning généré le {datetime.now().strftime('%d/%m/%Y')}")
        
        def save_with_notes():
            notes = notes_entry.get("1.0", "end-1c").strip()
            self.save_planning_to_history(notes)
            save_window.destroy()
        
        ctk.CTkButton(save_window, text="💾 Sauvegarder",
                    font=("Segoe UI", 14, "bold"),
                    fg_color=self.colors['success'],
                    hover_color=self.adjust_color(self.colors['success'], -20),
                    height=45,
                    command=save_with_notes,
                    width=200).pack(pady=20)
        
    def load_selected_planning(self, history_tree):
        """Charge le planning sélectionné depuis l'historique"""
        selected = history_tree.selection()
        if not selected:
            self.show_error_message("❌ Erreur", "Veuillez sélectionner un planning dans l'historique")
            return
        
        item = selected[0]
        planning_id = history_tree.item(item, "values")[0]
        
        try:
            self.cursor.execute('SELECT planning_data FROM planning_history WHERE id = ?', (planning_id,))
            result = self.cursor.fetchone()
            
            if not result:
                self.show_error_message("❌ Erreur", "Planning non trouvé dans la base de données")
                return
            
            # Charger les données
            planning_data = json.loads(result[0])
            
            # Restaurer l'état de l'application
            self.best = planning_data['best']
            self.teachers = planning_data['teachers']
            self.slots = planning_data['slots']
            self.room_assignments = planning_data['room_assignments']
            self.prof_resp_list = planning_data['prof_resp_list']
            
            # Afficher le planning chargé
            self.display_planning_result()
            
            self.show_success_message("✅ Chargement réussi", 
                f"Planning chargé depuis l'historique (ID: {planning_id})")
            
        except Exception as e:
            self.show_error_message("❌ Erreur", f"Erreur lors du chargement:\n{str(e)}")

    def delete_selected_history(self, history_tree):
        """Supprime l'entrée sélectionnée de l'historique"""
        selected = history_tree.selection()
        if not selected:
            self.show_error_message("❌ Erreur", "Veuillez sélectionner un planning à supprimer")
            return
        
        item = selected[0]
        planning_id = history_tree.item(item, "values")[0]
        
        if messagebox.askyesno("Confirmation", f"Voulez-vous vraiment supprimer le planning #{planning_id} ?"):
            try:
                self.cursor.execute('DELETE FROM planning_history WHERE id = ?', (planning_id,))
                self.conn.commit()
                history_tree.delete(item)
                self.show_success_message("✅ Suppression réussie", f"Planning #{planning_id} supprimé")
            except Exception as e:
                self.show_error_message("❌ Erreur", f"Erreur lors de la suppression:\n{str(e)}")
    def create_modern_ui(self):
        # Main container with subtle shadow effect
        main_container = ctk.CTkFrame(self, fg_color='transparent')
        main_container.pack(fill='both', expand=True, padx=20, pady=20)
        
        # Header with gradient-like effect
        self.create_header(main_container)
        
        # Content area with cards
        content = ctk.CTkFrame(main_container, fg_color='transparent')
        content.pack(fill='both', expand=True, pady=(20, 0))
        
        # Left sidebar for actions
        self.create_sidebar(content)
        
        # Main content area
        self.main_content = ctk.CTkFrame(content, fg_color='transparent')
        self.main_content.pack(side='left', fill='both', expand=True, padx=(20, 0))
        
        # Action cards
        # self.create_action_cards()
        
        # Data view area
        self.create_data_view()
    def create_header(self, parent):
        header = ctk.CTkFrame(parent, fg_color=self.colors['test'], 
                             corner_radius=16, height=100)
        header.pack(fill='x', pady=(0, 0))
        header.pack_propagate(False)
        
        # Logo and title
        logo_container = ctk.CTkFrame(header, fg_color='transparent')
        logo_container.pack(side='left', padx=30, pady=20)
        
        logo = ctk.CTkFrame(logo_container, fg_color='transparent',
                           width=56, height=56, corner_radius=14)
        logo.pack(side='left')
        logo.pack_propagate(False)
        logo_image = ctk.CTkImage(
            light_image=Image.open("logoisi.png"), 
            dark_image=Image.open("logoisi.png"),  
            size=(60, 60)                      
            )
        logo_text = ctk.CTkLabel(logo, image=logo_image, text="")
        logo_text.place(relx=0.5, rely=0.5, anchor='center')
        
        title_container = ctk.CTkFrame(logo_container, fg_color='transparent')
        title_container.pack(side='left', padx=(16, 0))
        
        ctk.CTkLabel(title_container, 
                    text="Gestion des Créneaux de Surveillance",
                    font=("Segoe UI", 24, "bold"),
                    text_color=self.colors['text']).pack(anchor='w')
        
        ctk.CTkLabel(title_container,
                    text="Système de planification des examens",
                    font=("Segoe UI", 13),
                    text_color=self.colors['text_secondary']).pack(anchor='w')
            # Action buttons (RIGHT)
        buttons_container = ctk.CTkFrame(header, fg_color='transparent')
        buttons_container.pack(side='right', padx=30, pady=20)
        
        # Export individual PDF button
        export_btn = ctk.CTkButton(
            buttons_container,
            text="📄 Export Individuel",
            width=150,
            height=40,
            corner_radius=10,
            fg_color=self.colors['text_secondary'],
            hover_color=self.colors['text_secondary_light'],
            command=lambda: self.export_teachers_to_pdf()
        )
        export_btn.pack(side='left', padx=5)
        
        # Export general PDF button
        export_general_btn = ctk.CTkButton(
            buttons_container,
            text="📄 Export Général",
            width=150,
            height=40,
            corner_radius=10,
            fg_color=self.colors['text_secondary'],  
            hover_color=self.colors['text_secondary_light'],
            command=lambda: self.export_general_pdf()
        )
        export_general_btn.pack(side='left', padx=5)
        self.quality_btn = ctk.CTkButton(
            buttons_container,
            text="Qualité Planning",
            width=150,
            height=40,
            corner_radius=10,
            text_color="black",
            fg_color=self.colors['success'] if self.current_view == 'quality' else 'transparent',
            hover_color=self.colors['hover'],
            border_width=2,
            border_color=self.colors['success'],
            command=lambda: self.switch_view('quality')
        )
        self.quality_btn.pack(side='left', padx=5)
    def create_sidebar(self, parent):
        sidebar = ctk.CTkFrame(parent, fg_color=self.colors['card'],
                              corner_radius=16, width=320)
        sidebar.pack(side='left', fill='y')
        sidebar.pack_propagate(False)
        
        # Section: Chargement des données
        self.create_section(sidebar, "📁 Chargement des fichiers", 30)
        
        self.create_modern_button(
            sidebar, "Charger Créneaux", "📊", 
            self.load_slots, self.colors['error'], data_key='slots'
        )
        self.create_modern_button(
            sidebar, "Charger Enseignants", "👥",
            self.load_teachers, self.colors['error'], data_key='teachers'
        )
        self.create_modern_button(
            sidebar, "Charger Vœux", "💭",
            self.load_wishes, self.colors['error'], data_key='wishes'
        )
        self.create_modern_button(
            sidebar, "Configurer Quotas", "⚙️",
            self.configure_quotas, self.colors['text_secondary']
        )
        
        # Divider
        ctk.CTkFrame(sidebar, height=1, fg_color=self.colors['border']).pack(
            fill='x', padx=20, pady=20
        )
        
        # Section: Génération
        self.create_section(sidebar, "🧬 Génération du Planning", 0)
        
        self.create_modern_button(
            sidebar, "Générer Planning", "▶️",
            self.generate_planning, self.colors['success'], large=True
        )
        # Section: Génération
        #self.create_section(sidebar, "🧬 Historique du Planning", 0)

        #self.create_modern_button(
           # sidebar, "Voir Historique", "▶️",
           # self.generate_planning, self.colors['success'], large=True
        #)
        # Section: Historique
        self.create_section(sidebar, "🧬 Historique du Planning", 0)

        self.create_modern_button(
            sidebar, "Voir Historique", "▶️",
            self.show_history, self.colors['text_secondary'], large=True
        )
        self.create_modern_button(
        sidebar, "Sauvegarder Historique", "💾", 
        self.prompt_save_current_planning, self.colors['success'], large=False
        )
        # Divider
        ctk.CTkFrame(sidebar, height=1, fg_color=self.colors['border']).pack(
            fill='x', padx=20, pady=20
        )
        
        # Section: Export
        # self.create_section(sidebar, "💾 Export", 0)
        
        # export_frame = ctk.CTkFrame(sidebar, fg_color='transparent')
        # export_frame.pack(fill='x', padx=20, pady=(0, 10))
        
        # ctk.CTkButton(
        #     export_frame,
        #     text="CSV",
        #     font=("Segoe UI", 13, "bold"),
        #     fg_color=self.colors['hover'],
        #     hover_color=self.colors['border'],
        #     text_color=self.colors['text'],
        #     width=135,
        #     height=40,
        #     corner_radius=10,
        #     command=self.export_csv
        # ).pack(side='left', padx=(0, 10))
        
        # ctk.CTkButton(
        #     export_frame,
        #     text="PDF",
        #     font=("Segoe UI", 13, "bold"),
        #     fg_color=self.colors['hover'],
        #     hover_color=self.colors['border'],
        #     text_color=self.colors['text'],
        #     width=135,
        #     height=40,
        #     corner_radius=10,
        #     command=self.export_pdf
        # ).pack(side='left')
    def create_section(self, parent, title, top_padding):
        ctk.CTkLabel(
            parent,
            text=title,
            font=("Segoe UI", 12, "bold"),
            text_color=self.colors['text_secondary'],
            anchor='w'
        ).pack(fill='x', padx=20, pady=(top_padding, 15))
        
    def create_modern_button(self, parent, text, icon, command, color, large=False, data_key=None):
        height = 52 if large else 44
        font_size = 15 if large else 13
        
        # Add status indicator if this is a data loading button
        status_icon = ""
        btn_color = color
        if data_key:
            status_icon = " ✅" if self.data_loaded.get(data_key, False) else " ⚠️"
        
        btn = ctk.CTkButton(
            parent,
            text=f"{icon}  {text}{status_icon}",  # Changed: status at the end
            font=("Segoe UI", font_size, "bold" if large else "normal"),
            fg_color=color,
            hover_color=self.adjust_color(color, -20),
            text_color='white',
            height=height,
            corner_radius=10,
            command=command,
            anchor='w'  # ADD THIS LINE - aligns text to left
        )
        btn.pack(fill='x', padx=20, pady=(0, 10))
        # Store button reference if it's a data button
        if data_key:
            self.data_buttons[data_key] = btn
        
        return btn

    def update_button_status(self, data_key, text, icon):
        """Update button appearance when data is loaded"""
        if data_key in self.data_buttons:
            btn = self.data_buttons[data_key]
            status_icon = " ✅" if self.data_loaded[data_key] else " ⚠️"  # Changed: space before icon
            btn.configure(text=f"{icon}  {text}{status_icon}")  # Changed: status at the end
            btn.configure(fg_color=self.colors['success'])
            btn.configure(hover_color=self.adjust_color(self.colors['success'], -20))
    def adjust_color(self, hex_color, adjustment):
        """Darken or lighten a color"""
        hex_color = hex_color.lstrip('#')
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        r = max(0, min(255, r + adjustment))
        g = max(0, min(255, g + adjustment))
        b = max(0, min(255, b + adjustment))
        return f'#{r:02x}{g:02x}{b:02x}'
    def create_data_view(self):
        view_frame = ctk.CTkFrame(self.main_content, fg_color=self.colors['card'],
                                corner_radius=16)
        view_frame.pack(fill='both', expand=True)
        
        # Header with view switcher buttons
        header_container = ctk.CTkFrame(view_frame, fg_color='transparent', height=70)
        header_container.pack(fill='x', padx=25, pady=(20, 10))
        header_container.pack_propagate(False)
        
        # Title
        ctk.CTkLabel(header_container, 
                    text="📋 Données",
                    font=("Segoe UI", 18, "bold"),
                    text_color=self.colors['text']).pack(side='left')
        
        # View switcher buttons (center)
        view_buttons_frame = ctk.CTkFrame(header_container, fg_color='transparent')
        view_buttons_frame.pack(side='left', padx=50)
        
        # Track current view for button styling
        if not hasattr(self, 'current_view'):
            self.current_view = 'planning'
        
        # Planning view button
        self.planning_view_btn = ctk.CTkButton(
            view_buttons_frame,
            text="📅 Planning",
            width=80,
            height=40,
            corner_radius=10,
            text_color="black",
            fg_color=self.colors['primary'] if self.current_view == 'planning' else 'transparent',
            hover_color=self.colors['hover'],
            border_width=2,
            border_color=self.colors['primary'],
            command=lambda: self.switch_view('planning')
        )
        self.planning_view_btn.pack(side='left', padx=5)
        
        # Teacher view button
        self.teacher_view_btn = ctk.CTkButton(
            view_buttons_frame,
            text="👥 Par Enseignant",
            width=100,
            height=40,
            corner_radius=10,
            text_color="black",
            fg_color=self.colors['primary'] if self.current_view == 'teacher' else 'transparent',
            hover_color=self.colors['hover'],
            border_width=2,
            border_color=self.colors['primary'],
            command=lambda: self.switch_view('teacher')
        )
        self.teacher_view_btn.pack(side='left', padx=5)
        
        # Room view button
        self.room_view_btn = ctk.CTkButton(
            view_buttons_frame,
            text="🏫 Par Salle",
            width=100,
            height=40,
            corner_radius=10,
            text_color="black",
            fg_color=self.colors['primary'] if self.current_view == 'room' else 'transparent',
            hover_color=self.colors['hover'],
            border_width=2,
            border_color=self.colors['primary'],
            command=lambda: self.switch_view('room')
        )
        self.room_view_btn.pack(side='left', padx=5)
        self.subject_manager_view_btn = ctk.CTkButton(
            view_buttons_frame,
            text="👤 Par Responsable Matière",
            width=120,
            height=40,
            corner_radius=10,
            text_color="black",
            fg_color=self.colors['primary'] if self.current_view == 'subject_manager' else 'transparent',
            hover_color=self.colors['hover'],
            border_width=2,
            border_color=self.colors['primary'],
            command=lambda: self.switch_view('subject_manager')
        )
        self.subject_manager_view_btn.pack(side='left', padx=5)
       

            #     tk.Button(btn_frame2, text="Qualite Planning", command=self.show_planning_quality_wrapper,
    #              bg="#E91E63", fg="white", width=18).pack(side=tk.LEFT, padx=2)
        # Search inputs (right side) - only visible in certain views
        self.search_frame = ctk.CTkFrame(header_container, fg_color='transparent')
        self.search_frame.pack(side='right')
        
        # Teacher search (for all views)
        self.teacher_search = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="🔍 Rechercher enseignant...",
            width=150,
            height=40,
            corner_radius=10,
            border_width=1,
            border_color=self.colors['border']
        )
        self.teacher_search.pack(side='left', padx=5)
        self.teacher_search.bind('<KeyRelease>', lambda e: self.filter_by_teacher())
        
        # Day search (only for planning view)
        self.day_search = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="🔍 Rechercher jour...",
            width=150,
            height=40,
            corner_radius=10,
            border_width=1,
            border_color=self.colors['border']
        )
        self.day_search.pack(side='left', padx=5)
        self.day_search.bind('<KeyRelease>', lambda e: self.filter_by_date())
        
        # Room search (only for room view)
        self.room_search = ctk.CTkEntry(
            self.search_frame,
            placeholder_text="🔍 Rechercher salle...",
            width=150,
            height=40,
            corner_radius=10,
            border_width=1,
            border_color=self.colors['border']
        )
        # Start hidden, will be shown in room view
        
        # Treeview with modern styling
        tree_container = ctk.CTkFrame(view_frame, fg_color='transparent')
        tree_container.pack(fill='both', expand=True, padx=25, pady=(0, 25))
        
        # Scrollbars
        tree_scroll_y = ctk.CTkScrollbar(tree_container)
        tree_scroll_y.pack(side='right', fill='y', padx=(5, 0))
        
        tree_scroll_x = ctk.CTkScrollbar(tree_container, orientation='horizontal')
        tree_scroll_x.pack(side='bottom', fill='x', pady=(5, 0))
        
        # Style configuration for treeview
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure("Modern.Treeview",
                    background=self.colors['card'],
                    foreground=self.colors['text'],
                    fieldbackground=self.colors['card'],
                    borderwidth=0,
                    relief='flat',
                    rowheight=35)
        
        style.configure("Modern.Treeview.Heading",
                    background=self.colors['hover'],
                    foreground=self.colors['text'],
                    borderwidth=0,
                    relief='flat',
                    font=("Segoe UI", 11, "bold"))
        
        style.map('Modern.Treeview',
                background=[('selected', self.colors['primary'])],
                foreground=[('selected', 'white')])
        
        style.map('Modern.Treeview.Heading',
                background=[('active', self.colors['border'])])
        
        self.tree = ttk.Treeview(
            tree_container,
            columns=("Col1", "Col2"),
            show="headings",
            yscrollcommand=tree_scroll_y.set,
            xscrollcommand=tree_scroll_x.set,
            style="Modern.Treeview"
        )
        self.tree.pack(fill='both', expand=True)
        
        tree_scroll_y.configure(command=self.tree.yview)
        tree_scroll_x.configure(command=self.tree.xview)
        
        # Configure tags for colors
        self.tree.tag_configure("over_quota", background="#FEE2E2")
        self.tree.tag_configure("unassigned", background="#FEF3C7")
        self.tree.tag_configure("optimal", background="#D1FAE5")
        self.tree.tag_configure("acceptable", background="#FEF3C7")
        self.tree.tag_configure("problem", background="#FEE2E2")
        self.tree.tag_configure("optimal_light", background=self.adjust_color("#D1FAE5", 30))
        self.tree.tag_configure("acceptable_light", background=self.adjust_color("#FEF3C7", 30))
        self.tree.tag_configure("problem_light", background=self.adjust_color("#FEE2E2", 30))
        self.tree.tag_configure("header", background=self.colors['hover'], 
                            font=("Segoe UI", 11, "bold"))
        self.tree.tag_configure("ok", background="#D1FAE5")
        self.tree.tag_configure("error", background="#FEE2E2")
        
        # Session colors for planning view
        self.tree.tag_configure('session_s1', background='#E3F2FD')
        self.tree.tag_configure('session_s2', background='#E8F5E9')
        self.tree.tag_configure('session_s3', background='#FFF3E0')
        self.tree.tag_configure('session_s4', background='#F3E5F5')
        self.tree.tag_configure('date_group', background='#D1D5DB', font=('TkDefaultFont', 10, 'bold'))
        self.tree.tag_configure('separator', background='#BDBDBD')
        
        # Update search visibility based on current view
        self.update_search_visibility()
    def switch_view(self, view_type):
        """Switch between different view types"""
        self.current_view = view_type
        
        # Update button styles
        self.planning_view_btn.configure(
            fg_color=self.colors['primary'] if view_type == 'planning' else 'transparent'
        )
        self.teacher_view_btn.configure(
            fg_color=self.colors['primary'] if view_type == 'teacher' else 'transparent'
        )
        self.room_view_btn.configure(
            fg_color=self.colors['primary'] if view_type == 'room' else 'transparent'
        )
        self.subject_manager_view_btn.configure(
            fg_color=self.colors['primary'] if view_type == 'subject_manager' else 'transparent'
        )
        self.quality_btn.configure(
            fg_color=self.colors['success'] if view_type == 'quality' else 'transparent'
        )

        # Update search field visibility
        self.update_search_visibility()
        
        # Clear search fields
        self.teacher_search.delete(0, 'end')
        self.day_search.delete(0, 'end')
        if hasattr(self, 'room_search'):
            self.room_search.delete(0, 'end')
        
        # Display the appropriate view
        if view_type == 'planning':
            self.display_planning_result()
        elif view_type == 'teacher':
            self.show_by_teacher()
        elif view_type == 'room':
            self.show_by_room()
        elif view_type == 'quality':
            show_planning_quality_with_prof_resp(self)
        elif view_type == 'subject_manager':
            show_prof_responsable_details(self)
    

    def update_search_visibility(self):
        """Show/hide search fields based on current view"""
        # Remove room search if it exists
        if hasattr(self, 'room_search'):
            self.room_search.pack_forget()
        
        if self.current_view == 'planning':
            # Show teacher and day search
            self.teacher_search.pack(side='left', padx=5)
            self.day_search.pack(side='left', padx=5)
        elif self.current_view == 'teacher':
            # Show only teacher search
            self.teacher_search.pack(side='left', padx=5)
            self.day_search.pack_forget()
        elif self.current_view == 'room':
            # Show teacher and room search
            self.teacher_search.pack(side='left', padx=5)
            self.day_search.pack_forget()
            self.room_search.pack(side='left', padx=5)
        elif self.current_view == "quality":
            self.day_search.pack_forget()
            self.room_search.pack_forget()
            self.teacher_search.pack_forget()
        elif self.current_view == "subject_manager":
            self.room_search.pack_forget()
            self.teacher_search.pack_forget()
    def filter_by_teacher(self):
        """Filter the current view by teacher name/code"""
        search_term = self.teacher_search.get().lower().strip()
        
        if not search_term:
            # If search is empty, restore the current view
            self.switch_view(self.current_view)
            return
        
        # Get all items in the tree
        all_items = self.tree.get_children()
        
        for item in all_items:
            values = self.tree.item(item, 'values')
            
            # Check if any value contains the search term
            match = False
            for value in values:
                if search_term in str(value).lower():
                    match = True
                    break
            
            # Show or hide the item
            if match:
                self.tree.reattach(item, '', self.tree.index(item))
            else:
                self.tree.detach(item)
            
            # Also check children (for planning view with grouped dates)
            children = self.tree.get_children(item)
            for child in children:
                child_values = self.tree.item(child, 'values')
                child_match = False
                for value in child_values:
                    if search_term in str(value).lower():
                        child_match = True
                        break
                
                if child_match:
                    # Show parent if child matches
                    self.tree.reattach(item, '', self.tree.index(item))
                    self.tree.item(item, open=True)

    def filter_by_date(self):
        """Filter planning view by date"""
        if self.current_view != 'planning':
            return
        
        search_term = self.day_search.get().lower().strip()
        
        if not search_term:
            # If search is empty, restore planning view
            self.display_planning_result()
            return
        
        # Get all parent items (dates)
        all_items = self.tree.get_children()
        
        for item in all_items:
            values = self.tree.item(item, 'values')
            
            # Check if date matches
            if values and search_term in str(values[0]).lower():
                self.tree.reattach(item, '', self.tree.index(item))
                self.tree.item(item, open=True)
            else:
                self.tree.detach(item)
    # def create_sidebar_button(self, text, row, command):
    #     """Créer un bouton de sidebar avec indicateur de statut"""
    #     btn_frame = ctk.CTkFrame(self.sidebar, fg_color="transparent")
    #     btn_frame.grid(row=row, column=0, padx=20, pady=5, sticky="ew")
    #     btn_frame.grid_columnconfigure(0, weight=1)
        
    #     btn = ctk.CTkButton(
    #         btn_frame,
    #         text=text,
    #         command=command,
    #         height=36,
    #         anchor="w",
    #         font=ctk.CTkFont(family=system_font, size=13),
    #         fg_color="transparent",
    #         text_color="#37352f",
    #         hover_color="#ededec",
    #         corner_radius=6
    #     )
    #     btn.grid(row=0, column=0, sticky="ew")
        
    #     # Indicateur de statut (petit cercle)
    #     status_indicator = ctk.CTkLabel(
    #         btn_frame,
    #         text="○",
    #         font=ctk.CTkFont(family=system_font, size=16),
    #         text_color="#d3d3d3",
    #         width=20
    #     )
    #     status_indicator.grid(row=0, column=1, padx=(5, 0))
        
    #     # Stocker la référence pour pouvoir la modifier plus tard
    #     if "Créneaux" in text:
    #         self.slots_indicator = status_indicator
    #     elif "Enseignants" in text:
    #         self.teachers_indicator = status_indicator
    #     elif "Vœux" in text:
    #         self.wishes_indicator = status_indicator
        
    #     return btn
    # def create_main_content(self):
    #     """Zone principale de contenu"""
    #     self.main_frame = ctk.CTkFrame(self, corner_radius=0, fg_color="#ffffff")
    #     self.main_frame.grid(row=0, column=1, sticky="nsew", padx=0, pady=0)
    #     self.main_frame.grid_columnconfigure(0, weight=1)
    #     self.main_frame.grid_rowconfigure(1, weight=1)
        
    #     # Header avec actions
    #     self.create_header()
        
    #     # Content area
    #     self.content_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
    #     self.content_frame.grid(row=1, column=0, sticky="nsew", padx=30, pady=20)
    #     self.content_frame.grid_columnconfigure(0, weight=1)
    #     self.content_frame.grid_rowconfigure(0, weight=1)
        
    #     # Afficher l'écran de bienvenue
    #     self.show_welcome_screen()        
    # def create_ui(self):
    #     main_frame = tk.Frame(self)
    #     main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
    #     # Frame de chargement
    #     load_frame = tk.LabelFrame(main_frame, text="Chargement des Donnees",
    #                              font=("Arial", 10, "bold"), padx=10, pady=5)
    #     load_frame.pack(fill=tk.X, pady=5)
        
    #     btn_frame1 = tk.Frame(load_frame)
    #     btn_frame1.pack(fill=tk.X, pady=2)
        
    #     tk.Button(btn_frame1, text="Charger Creneaux", command=self.load_slots,
    #              bg="#4CAF50", fg="white", width=20).pack(side=tk.LEFT, padx=3)
    #     tk.Button(btn_frame1, text="Charger Enseignants", command=self.load_teachers,
    #              bg="#2196F3", fg="white", width=20).pack(side=tk.LEFT, padx=3)
    #     tk.Button(btn_frame1, text="Charger Voeux", command=self.load_wishes,
    #              bg="#FF9800", fg="white", width=20).pack(side=tk.LEFT, padx=3)
    #     tk.Button(btn_frame1, text="Configurer Quotas", command=self.configure_quotas,
    #              bg="#9C27B0", fg="white", width=20).pack(side=tk.LEFT, padx=3)
        
    #     # Frame de generation
    #     gen_frame = tk.LabelFrame(main_frame, text="Generation du Planning",
    #                             font=("Arial", 10, "bold"), padx=10, pady=5)
    #     gen_frame.pack(fill=tk.X, pady=5)
        
    #     tk.Button(gen_frame, text="GENERER PLANNING", command=self.generate_planning,
    #              bg="#4CAF50", fg="white", font=("Arial", 14, "bold"),
    #              height=2).pack(pady=10)
        
    #     # Frame de visualisation
    #     view_frame = tk.LabelFrame(main_frame, text="Visualisation & Impression",
    #                              font=("Arial", 10, "bold"), padx=10, pady=5)
    #     view_frame.pack(fill=tk.X, pady=5)
        
    #     btn_frame2 = tk.Frame(view_frame)
    #     btn_frame2.pack(fill=tk.X, pady=3)
        
    #     tk.Button(btn_frame2, text="Par Enseignant", command=self.show_by_teacher_wrapper,
    #              bg="#3F51B5", fg="white", width=18).pack(side=tk.LEFT, padx=2)
    #     tk.Button(btn_frame2, text="Par Jour (Calendrier)", command=self.show_by_day_calendar_wrapper,
    #              bg="#009688", fg="white", width=18).pack(side=tk.LEFT, padx=2)
    #     tk.Button(btn_frame2, text="Par Salle", command=self.show_by_room_wrapper,
    #              bg="#795548", fg="white", width=18).pack(side=tk.LEFT, padx=2)
    #     tk.Button(btn_frame2, text="Qualite Planning", command=self.show_planning_quality_wrapper,
    #              bg="#E91E63", fg="white", width=18).pack(side=tk.LEFT, padx=2)
        
    #     btn_frame3 = tk.Frame(view_frame)
    #     btn_frame3.pack(fill=tk.X, pady=3)
        
    #     tk.Button(btn_frame3, text="Profs Responsables", command=self.show_prof_responsable_wrapper,
    #              bg="#FF6F00", fg="white", width=20).pack(side=tk.LEFT, padx=2)
        
    #     self.hide_rooms_var = tk.BooleanVar(value=False)
    #     tk.Checkbutton(btn_frame3, text="Masquer les salles (pour enseignants)",
    #                   variable=self.hide_rooms_var, font=("Arial", 10),
    #                   command=self.refresh_view).pack(side=tk.LEFT, padx=10)
        
    #     # Frame d'export
    #     export_frame = tk.LabelFrame(main_frame, text="Export Donnees",
    #                                font=("Arial", 10, "bold"), padx=10, pady=5)
    #     export_frame.pack(fill=tk.X, pady=5)
        
    #     tk.Button(export_frame, text="Exporter CSV", command=self.export_csv,
    #              width=20).pack(side=tk.LEFT, padx=5)
        
    #     self.view_type_label = tk.Label(main_frame, text="Vue actuelle: Aucune",
    #                                   font=("Arial", 11, "bold"), fg="#1976D2")
    #     self.view_type_label.pack(pady=5)
        
    #     self.action_frame = tk.Frame(main_frame)
    #     self.action_frame.pack(fill=tk.X, pady=5)
        
    #     # Barre de recherche
    #     search_frame = tk.Frame(main_frame)
    #     search_frame.pack(fill=tk.X, pady=5)
    #     tk.Label(search_frame, text="Recherche:", font=("Arial", 10)).pack(side=tk.LEFT, padx=5)
    #     self.search_entry = tk.Entry(search_frame, font=("Arial", 10))
    #     self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5)
    #     self.search_entry.bind("<KeyRelease>", self.on_search)
        
    #     # TreeView
    #     tree_frame = tk.Frame(main_frame)
    #     tree_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
    #     tree_scroll_y = tk.Scrollbar(tree_frame)
    #     tree_scroll_y.pack(side=tk.RIGHT, fill=tk.Y)
    #     tree_scroll_x = tk.Scrollbar(tree_frame, orient=tk.HORIZONTAL)
    #     tree_scroll_x.pack(side=tk.BOTTOM, fill=tk.X)
        
    #     self.tree = ttk.Treeview(tree_frame, columns=("Col1",), show="headings",
    #                            yscrollcommand=tree_scroll_y.set,
    #                            xscrollcommand=tree_scroll_x.set)
    #     self.tree.pack(fill=tk.BOTH, expand=True)
    #     tree_scroll_y.config(command=self.tree.yview)
    #     tree_scroll_x.config(command=self.tree.xview)

    # def on_search(self, event=None):
    #     self.current_filter = self.search_entry.get().lower()
    #     self.refresh_view()
    
    # ========== DATA LOADING METHODS ==========
    
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
      file = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
      if file:
        try:
            engine = 'openpyxl' if file.endswith('.xlsx') else 'xlrd'
            df = pd.read_excel(file, engine=engine)
           
            print(f"Colonnes disponibles: {df.columns.tolist()}")
           
            df['dateExam'] = pd.to_datetime(df['dateExam'], format='%d/%m/%Y', dayfirst=True)
            df['h_debut_time'] = df['h_debut'].str.extract(r'(\d{2}:\d{2}:\d{2})', expand=False)
            df['h_fin_time'] = df['h_fin'].str.extract(r'(\d{2}:\d{2}:\d{2})', expand=False)
           
            df['h_debut'] = pd.to_datetime(df['dateExam'].astype(str) + ' ' + df['h_debut_time'],
                                         format='%Y-%m-%d %H:%M:%S', errors='coerce')
            df['h_fin'] = pd.to_datetime(df['dateExam'].astype(str) + ' ' + df['h_fin_time'],
                                       format='%Y-%m-%d %H:%M:%S', errors='coerce')
           
            SESSION_TIMES_REV = {v: k for k, v in SESSION_TIMES.items()}
            df['session'] = df['h_debut'].dt.strftime('%H:%M').map(lambda x: SESSION_TIMES_REV.get(x, 'S1'))
            df['slot'] = df.apply(lambda row: f"{row['dateExam'].strftime('%Y-%m-%d')} {row['session']}", axis=1)
           
            # Remove duplicates based on slot and cod_salle, keeping the first occurrence
            df = df.drop_duplicates(subset=['slot', 'cod_salle'], keep='first')
           
            # Trouver la colonne prof responsable
            prof_col = None
            if 'smart_ens_code' in df.columns:
                prof_col = 'smart_ens_code'
            elif 'enseignant' in df.columns:
                prof_col = 'enseignant'
            else:
                for col in df.columns:
                    if 'ens' in col.lower() or 'prof' in col.lower():
                        prof_col = col
                        break
           
            # Compter les repartitions APRES deduplication
            total_repartitions = len(df)
           
            # Collecter TOUTES les repartitions profs responsables (par ligne du fichier)
            self.prof_resp_list = []
            profs_responsables_count = 0
            if prof_col:
                for _, row in df.iterrows():
                    if pd.notna(row[prof_col]):
                        prof_val = row[prof_col]
                        if isinstance(prof_val, float):
                            prof_code = str(int(prof_val))
                        else:
                            prof_code = str(prof_val).strip()
                        if is_valid_teacher(prof_code):
                            profs_responsables_count += 1
                            self.prof_resp_list.append({
                                'prof_code': prof_code,
                                'slot': row['slot'],
                                'date_exam': row['dateExam'].strftime('%d/%m/%Y'),
                                'h_debut': row['h_debut_time'],
                                'h_fin': row['h_fin_time'],
                                'type_ex': row.get('type ex', ''),
                                'semestre': row.get('semestre', ''),
                                'cod_salle': row['cod_salle'],
                                'session': row['session'],
                                'jour': row['dateExam'].strftime('%a %d/%m/%Y')
                            })
           
            # CORRECT: Grouper par slot et conserver TOUTES les salles par slot
            self.slots = []
            self.room_names = {}
           
            grouped = df.groupby('slot')
           
            for slot, group in grouped:
                # Recuperer le prof responsable (premier de la liste pour ce slot)
                enseignant = ''
                if prof_col:
                    prof_values = group[prof_col].dropna()
                    if len(prof_values) > 0:
                        prof_val = prof_values.iloc[0]
                        if isinstance(prof_val, float):
                            enseignant = str(int(prof_val))
                        else:
                            enseignant = str(prof_val)
               
                # IMPORTANT: Recuperer TOUTES les salles UNIQUES de ce slot
                rooms = sorted(group['cod_salle'].unique().tolist())
                room_count = len(rooms)
               
                self.slots.append((slot, {
                    'room_count': room_count,
                    'enseignant': enseignant,
                    'session': group['session'].iloc[0],
                    'room_names': rooms  # TOUTES les salles
                }))
               
                # Stocker les noms de salles par slot
                if slot not in self.room_names:
                    self.room_names[slot] = {}
                for room in rooms:
                    self.room_names[slot][room] = room
               
                # Initialiser room_assignments avec TOUTES les salles
                self.room_assignments[slot] = {room: [] for room in rooms}
           
            unique_dates = sorted(df['dateExam'].unique())
            self.day_to_date = {str(i+1): d.strftime('%Y-%m-%d') for i, d in enumerate(unique_dates)}
            self.data_loaded['slots'] = True
            self.update_button_status('slots', "Charger Créneaux", "📊")
            self.show_success_message("✅ Succès",f"Fichier charge avec succès!\n\n"
                f"Total lignes : {total_repartitions}\n"
                f"Créneaux : {len(self.slots)}","400x250")

        except Exception as e:
            self.show_error_message("❌ Erreur", f"Erreur lors du chargement des créneaux:\n{str(e)}")



    def load_teachers(self):
      file = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
      if file:
        try:
            #ken email mech mawjoud -> exception
            engine = 'openpyxl' if file.endswith('.xlsx') else 'xlrd'
            df = pd.read_excel(file, engine=engine)
           
            required_columns = ['email_ens']
            missing_columns = [col for col in required_columns if col not in df.columns]
            if missing_columns:
                self.show_error_message(
                    "❌ Erreur",
                    f"Le fichier Excel ne contient pas la colonne requise : {', '.join(missing_columns)}"
                )
                return
            self.teachers = {}  # Réinitialiser le dictionnaire
            counter = 0  # Compteur pour gérer les emails manquants ou dupliqués
           
            for index, row in df.iterrows():
                # Vérifier la participation à la surveillance
                participe = row.get('participe_surveillance', False) in [1, '1', True, 'true', 'True']
               
                # Utiliser l'email comme clé, avec un mécanisme de secours
                email = row.get('email_ens', '')
                if not email or email in self.teachers:
                    # Si email manquant ou déjà utilisé, générer une clé unique
                    code = f"TEACHER_{index}_{counter}"
                    counter += 1
                else:
                    code = email
               
                # Ajouter l'enseignant au dictionnaire
                self.teachers[code] = {
                    'nom': row.get('nom_ens', ''),
                    'prenom': row.get('prenom_ens', ''),
                    'abrv': row.get('abrv_ens', ''),
                    'email': email,
                    'grade': row.get('grade_code_ens', ''),
                    'quota': GRADE_QUOTAS.get(row.get('grade_code_ens', ''), 2),
                    'indispo': [],
                    'wish_priority': {},
                    'participe_surveillance': participe,
                    'code_smartex_ens': str(int(row['code_smartex_ens'])) if 'code_smartex_ens' in row and not pd.isna(row['code_smartex_ens']) else ''
                }
           
            # Compter les enseignants participant à la surveillance
            participating = sum(1 for t in self.teachers.values() if t['participe_surveillance'])
            self.data_loaded['teachers'] = True
            self.update_button_status('teachers', "Charger Enseignants", "👥")
            self.show_success_message("✅ Succès", 
                f"{len(self.teachers)} enseignants chargés\n({participating} participent à la surveillance)")
        except Exception as e:
            self.show_error_message("❌ Erreur", f"Erreur lors du chargement des enseignants:\n{str(e)}")

    def load_wishes(self):
      file = filedialog.askopenfilename(filetypes=[("Excel files", "*.xlsx *.xls")])
      if file:
        if not self.day_to_date:
            self.show_error_message("❌ Erreur", "Chargez d'abord les créneaux!")
            return
        try:
            engine = 'openpyxl' if file.endswith('.xlsx') else 'xlrd'
            df = pd.read_excel(file, engine=engine)
            df = df.drop_duplicates(subset=['Enseignant', 'Jour', 'Séances'], keep='first')   

            if 'ordre_arrivee' in df.columns or 'timestamp' in df.columns:
                sort_col = 'ordre_arrivee' if 'ordre_arrivee' in df.columns else 'timestamp'
                df = df.sort_values(sort_col)
           
            loaded_count = 0
            affected_abrvs = set()

            for idx, row in df.iterrows():
                ens_abrv = str(row.get('Enseignant', '')).strip()
                print(ens_abrv)
                print("loula wfet")
                if not ens_abrv:
                    continue
               
                # Trouver la clé de l'enseignant par abréviation
                teacher_key = next((k for k, v in self.teachers.items() if v.get('abrv', '') == ens_abrv), None)
                print(teacher_key)
                if not teacher_key:
                    continue  # Pas d'enseignant correspondant
               
                if 'wish_priority' not in self.teachers[teacher_key]:
                    self.teachers[teacher_key]['wish_priority'] = {}
               
                # Gérer les jours (assumer un seul jour par ligne)
                jour_str = str(int(row['Jour'])) if pd.notna(row.get('Jour')) else None
               
                # Gérer les séances (peut être multiples, séparées par virgule)
                seance_str = str(row.get('Séances', '')).strip()
                seances = [s.strip() for s in seance_str.split(',') if s.strip()]
               
                if jour_str and seances:
                    date = self.day_to_date.get(jour_str)
                    if date:
                        for seance in seances:
                            slot = f"{date} {seance}"
                            if slot not in self.teachers[teacher_key]['indispo']:
                                self.teachers[teacher_key]['indispo'].append(slot)
                                priority = 2.0 - (idx / max(len(df), 1))
                                self.teachers[teacher_key]['wish_priority'][slot] = priority
                                loaded_count += 1
                        affected_abrvs.add(ens_abrv)
           
            # messagebox.showinfo("Succes",
            #                   f"{loaded_count} voeux chargés pour {len(affected_abrvs)} enseignants\n"
            #                   f"Priorités appliquées (premiers arrivés mieux protégés)")
            self.data_loaded['wishes'] = True
            self.update_button_status('wishes', "Charger Voeux", "💭")
            self.show_success_message("✅ Succès", 
                    f"Voeux chargés: {loaded_count} indisponibilités\npour {len(affected_abrvs)} enseignants")
        except Exception as e:
            self.show_error_message("❌ Erreur", f"Erreur lors du chargement des voeux:\n{str(e)}")

    def configure_quotas(self):
        """Ouvre la fenêtre de configuration des quotas"""
        if self.quota_window and self.quota_window.winfo_exists():
            self.quota_window.lift()
            return
        
        self.quota_window = ctk.CTkToplevel(self)
        self.quota_window.title("⚙️ Configuration des Quotas")
        self.quota_window.geometry("450x550")
        self.quota_window.configure(fg_color=self.colors['bg'])
        
        # Header
        header = ctk.CTkFrame(self.quota_window, fg_color=self.colors['card'],
                             corner_radius=12, height=80)
        header.pack(fill='x', padx=20, pady=20)
        header.pack_propagate(False)
        
        ctk.CTkLabel(header, 
                    text="Configuration des Quotas par Grade",
                    font=("Segoe UI", 18, "bold"),
                    text_color=self.colors['text']).pack(pady=25)
        
        # Scrollable frame for quotas
        scroll_frame = ctk.CTkScrollableFrame(self.quota_window, 
                                             fg_color=self.colors['card'],
                                             corner_radius=12)
        scroll_frame.pack(fill='both', expand=True, padx=20, pady=(0, 20))
        
        for grade in sorted(GRADE_QUOTAS.keys()):
            quota_card = ctk.CTkFrame(scroll_frame, fg_color=self.colors['hover'],
                                     corner_radius=10)
            quota_card.pack(fill='x', pady=5, padx=10)
            
            ctk.CTkLabel(quota_card, text=f"{grade}:", 
                        font=("Segoe UI", 13, "bold"),
                        text_color=self.colors['text'],
                        width=80, anchor='w').pack(side='left', padx=15, pady=12)
            
            entry = ctk.CTkEntry(quota_card, width=100, height=35,
                                corner_radius=8,
                                border_width=1,
                                border_color=self.colors['border'])
            entry.insert(0, str(GRADE_QUOTAS[grade]))
            entry.pack(side='right', padx=15, pady=12)
            self.quota_entries[grade] = entry
        
        # Buttons
        button_frame = ctk.CTkFrame(self.quota_window, fg_color='transparent')
        button_frame.pack(fill='x', padx=20, pady=(0, 20))
        
        ctk.CTkButton(button_frame, text="💾 Sauvegarder",
                     font=("Segoe UI", 13, "bold"),
                     fg_color=self.colors['success'],
                     hover_color=self.adjust_color(self.colors['success'], -20),
                     height=45,
                     corner_radius=10,
                     command=self.save_quotas).pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        ctk.CTkButton(button_frame, text="❌ Annuler",
                     font=("Segoe UI", 13),
                     fg_color=self.colors['hover'],
                     hover_color=self.colors['border'],
                     text_color=self.colors['text'],
                     height=45,
                     corner_radius=10,
                     command=self.quota_window.destroy).pack(side='left', fill='x', expand=True)

    def save_quotas(self):
        """Sauvegarde les quotas configurés"""
        try:
            for grade, entry in self.quota_entries.items():
                quota = int(entry.get())
                if quota < 0:
                    raise ValueError(f"Quota négatif pour {grade}")
                GRADE_QUOTAS[grade] = quota
            
            for teacher in self.teachers:
                self.teachers[teacher]['quota'] = GRADE_QUOTAS.get(self.teachers[teacher]['grade'], 2)
            
            self.show_success_message("✅ Succès", "Quotas mis à jour avec succès!")
            if self.quota_window:
                self.quota_window.destroy()
        except ValueError as e:
            self.show_error_message("❌ Erreur", 
                f"Valeur invalide: {str(e)}\nLes quotas doivent être des nombres positifs.")
            
    def generate_planning(self):
        """Génère le planning avec barre de progression"""
        if not self.slots or not self.teachers:
            self.show_error_message("❌ Erreur", 
                "Veuillez charger les créneaux et les enseignants d'abord!")
            return
        
        # Modern progress window
        progress_window = ctk.CTkToplevel(self)
        progress_window.title("⏳ Génération en cours...")
        progress_window.geometry("600x350")
        progress_window.configure(fg_color=self.colors['bg'])
        progress_window.transient(self)
        progress_window.grab_set()
        
        # Center window
        progress_window.update_idletasks()
        x = (progress_window.winfo_screenwidth() // 2) - (600 // 2)
        y = (progress_window.winfo_screenheight() // 2) - (350 // 2)
        progress_window.geometry(f"+{x}+{y}")
        
        # Content card
        card = ctk.CTkFrame(progress_window, fg_color=self.colors['card'],
                           corner_radius=16)
        card.pack(fill='both', expand=True, padx=30, pady=30)
        
        # Icon
        icon_frame = ctk.CTkFrame(card, fg_color=self.colors['primary'],
                                 width=64, height=64, corner_radius=16)
        icon_frame.pack(pady=(30, 20))
        icon_frame.pack_propagate(False)
        
        ctk.CTkLabel(icon_frame, text="🧬", 
                    font=("Segoe UI Emoji", 32)).place(relx=0.5, rely=0.5, anchor='center')
        
        ctk.CTkLabel(card, text="Optimisation génétique en cours",
                    font=("Segoe UI", 20, "bold"),
                    text_color=self.colors['text']).pack(pady=(0, 10))
        
        ctk.CTkLabel(card, text="Recherche de la meilleure solution...",
                    font=("Segoe UI", 13),
                    text_color=self.colors['text_secondary']).pack()
        
        # Progress bar
        progress_bar = ctk.CTkProgressBar(card, width=400, height=8,
                                         corner_radius=4,
                                         progress_color=self.colors['primary'])
        progress_bar.set(0)
        progress_bar.pack(pady=(30, 15))
        
        progress_label = ctk.CTkLabel(card, text="Génération 0/500",
                                     font=("Segoe UI", 12, "bold"),
                                     text_color=self.colors['text'])
        progress_label.pack()
        
        # fitness_label = ctk.CTkLabel(card, text="Fitness: N/A",
        #                             font=("Segoe UI", 12),
        #                             text_color=self.colors['text_secondary'])
        # fitness_label.pack(pady=(5, 10))
        
        status_label = ctk.CTkLabel(card, text="🔵 Initialisation...",
                                   font=("Segoe UI", 11),
                                   text_color=self.colors['text_secondary'])
        status_label.pack(pady=(10, 20))
        def update_progress(gen, total_gen, best_fitness, extra_info, state):
            progress = (gen + 1) / total_gen
            progress_bar.set(progress)
            progress_label.configure(text=f"Génération {gen+1}/{total_gen}")
            # fitness_label.configure(text=f"Meilleur fitness: {best_fitness:.0f}")
            # status_label.configure(text=extra_info)
            
            if best_fitness > -100:
                status_label.configure(text="🟢 Solution excellente trouvée!", 
                                     text_color=self.colors['success'])
            elif best_fitness > -500:
                status_label.configure(text="🟡 Solution acceptable",
                                     text_color=self.colors['warning'])
            elif best_fitness > -1000:
                status_label.configure(text="🟠 Optimisation en cours...",
                                     text_color=self.colors['warning'])
            else:
                status_label.configure(text="🔴 Recherche de solution...",
                                     text_color=self.colors['error'])
            
            progress_window.update()
        
        try:
            self.best, self.best_fitness_history, stop_reason = run_ga_optimized(
                self.slots, self.teachers, update_progress)
            progress_window.destroy()
            self.display_planning_result_with_edit()
            
            stop_messages = {
                "optimal": "Solution optimale trouvee!",
                "stagnated": "Convergence atteinte",
                "converged": "Population convergee",
                "max_gen": "Nombre max de generations"
            }
            
            final_fitness = self.best_fitness_history[-1]

            quality = "🟢 Excellent" if final_fitness > -100 else \
                     "🟡 Acceptable" if final_fitness > -500 else "🔴 A ameliorer"
            self.show_success_message("✅ Planning généré!", 
                # f"{stop_messages.get(stop_reason, 'Termine')}\n\n"
                f"Qualité: \n{quality}\n"
                # f"Score final: {final_fitness:.0f}\n\n"
                # f"Generations: {len(self.best_fitness_history)}"
               )
        except Exception as e:
            progress_window.destroy()
            self.show_error_message("❌ Erreur", f"Erreur lors de la génération:\n{str(e)}")

    # def display_planning_result(self):
    #     self.tree.delete(*self.tree.get_children())
    #     self.tree["columns"] = ("Creneau", "Enseignants")
    #     self.tree.heading("Creneau", text="Creneau")
    #     self.tree.heading("Enseignants", text="Enseignants Assignes")
    #     self.tree.column("Creneau", width=200)
    #     self.tree.column("Enseignants", width=800)
        
    #     data = []
    #     for slot in sorted(self.best.keys()):
    #         valid_teachers = [str(t) for t in self.best[slot] if is_valid_teacher(t)]
    #         teacher_info = []
    #         for t in valid_teachers:
    #             if t in self.teachers:
    #                 nom = self.teachers[t].get('nom', '')
    #                 prenom = self.teachers[t].get('prenom', '')
    #                 teacher_info.append(f"{prenom} {nom}")
    #         data.append((slot, ", ".join(teacher_info)))
        
    #     self.view_data = data
    #     self.populate_flat_view()
        
    #     # Assigner aux salles
    #     assign_teachers_to_rooms(self)
        
    #     self.current_view = "default"
    #     self.view_type_label.config(text="Vue actuelle: Planning General")
    #     self.configure_action_buttons()
    def display_planning_result(self):
        """Affiche le planning généré dans le treeview avec une meilleure présentation"""
        if not self.best:
            return
        
        # Clear existing data
        self.tree.delete(*self.tree.get_children())
        
        # Configure columns with better structure
        self.tree["columns"] = ("Date", "Session", "Heure", "Nombre", "Enseignants")
        
        # Configure column headings
        self.tree.heading("Date", text="📅 Date")
        self.tree.heading("Session", text="🕐 Session")
        self.tree.heading("Heure", text="⏰ Heure")
        self.tree.heading("Nombre", text="👥 Nb")
        self.tree.heading("Enseignants", text="Enseignants Assignés")
        
        # Configure column widths (will be adjusted later based on content)
        self.tree.column("Date", width=180, anchor="w", stretch=False, minwidth=180)
        self.tree.column("Session", width=80, anchor="center", stretch=False, minwidth=80)
        self.tree.column("Heure", width=80, anchor="center", stretch=False, minwidth=80)
        self.tree.column("Nombre", width=60, anchor="center", stretch=False, minwidth=60)
        self.tree.column("Enseignants", width=600, anchor="w", stretch=False, minwidth=600)
        
        # Session times mapping
        SESSION_TIMES = {
            's1': '08:30',
            's2': '10:30',
            's3': '12:30',
            's4': '14:30'
        }
        
        # Session colors (light colors for better readability)
        SESSION_COLORS = {
            's1': '#E3F2FD',  # Light blue
            's2': '#E8F5E9',  # Light green
            's3': '#FFF3E0',  # Light orange
            's4': '#F3E5F5'   # Light purple
        }
        
        # Day names in French
        DAY_NAMES_FR = {
            'Monday': 'Lundi',
            'Tuesday': 'Mardi',
            'Wednesday': 'Mercredi',
            'Thursday': 'Jeudi',
            'Friday': 'Vendredi',
            'Saturday': 'Samedi',
            'Sunday': 'Dimanche'
        }
        
        # Organize data by date
        from collections import defaultdict
        from datetime import datetime
        import tkinter.font as tkfont
        
        planning_by_date = defaultdict(list)
        max_teacher_text_length = 0
        
        for slot in sorted(self.best.keys()):
            try:
                # Parse slot format: "YYYY-MM-DD s1"
                parts = slot.split()
                date_str = parts[0]
                session = parts[1].lower()
                
                teachers_assigned = self.best[slot]
                teacher_count = len(teachers_assigned)
                
                # Format teacher names with their info if available
                teacher_display = []
                for teacher_code in teachers_assigned:
                    teacher_code_str = str(teacher_code)
                    if hasattr(self, 'teachers') and teacher_code_str in self.teachers:
                        teacher_info = self.teachers[teacher_code_str]
                        nom = teacher_info.get('nom', '')
                        prenom = teacher_info.get('prenom', '')
                        if nom and prenom:
                            teacher_display.append(f"{prenom} {nom} (#{teacher_code})")
                        else:
                            teacher_display.append(f"#{teacher_code}")
                    else:
                        teacher_display.append(f"#{teacher_code}")
                
                # Get time for this session
                time = SESSION_TIMES.get(session, "N/A")
                
                # Format date nicely with day name
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    day_name = DAY_NAMES_FR.get(date_obj.strftime('%A'), date_obj.strftime('%A'))
                    formatted_date = f"{day_name} {date_obj.strftime('%d/%m/%Y')}"
                except:
                    formatted_date = date_str
                
                planning_by_date[date_str].append({
                    'date': formatted_date,
                    'session': session.upper(),
                    'time': time,
                    'count': teacher_count,
                    'teachers': ", ".join(teacher_display),
                    'color': SESSION_COLORS.get(session, '#FFFFFF')
                })
                
                # Track the longest teacher text for column width calculation
                teacher_text = ", ".join(teacher_display)
                if len(teacher_text) > max_teacher_text_length:
                    max_teacher_text_length = len(teacher_text)
            except Exception as e:
                # Fallback for unexpected format
                teachers_assigned = [str(teacher) for teacher in self.best[slot]]
                self.tree.insert("", "end", values=(slot, "", "", len(teachers_assigned), ", ".join(teachers_assigned)))
        
        # Insert data with collapsible date groups
        for date_str in sorted(planning_by_date.keys()):
            sessions = planning_by_date[date_str]
            
            # Sort sessions by session number (s1, s2, s3, s4)
            sessions.sort(key=lambda x: x['session'])
            
            # Calculate total teachers for this day
            total_teachers_day = sum(s['count'] for s in sessions)
            num_sessions = len(sessions)
            
            # Create parent item for the date (collapsible group)
            date_label = sessions[0]['date']
            parent = self.tree.insert(
                "", "end",
                values=(
                    f"📅 {date_label}",
                    f"{num_sessions} sessions",
                    "",
                    total_teachers_day,
                    f"{total_teachers_day} enseignants au total"
                ),
                tags=('date_group',),
                open=True  # Start expanded
            )
            
            # Add sessions as children of the date
            for session_data in sessions:
                # Create tag name based on session for color coding
                session_tag = f"session_{session_data['session'].lower()}"
                
                self.tree.insert(
                    parent, "end",
                    values=(
                        "",  # Empty date column for child items
                        session_data['session'],
                        session_data['time'],
                        session_data['count'],
                        session_data['teachers']
                    ),
                    tags=(session_tag,)
                )
        
        # Configure session colors
        self.tree.tag_configure('session_s1', background='#E3F2FD')  # Light blue
        self.tree.tag_configure('session_s2', background='#E8F5E9')  # Light green
        self.tree.tag_configure('session_s3', background='#FFF3E0')  # Light orange
        self.tree.tag_configure('session_s4', background='#F3E5F5')  # Light purple
        
        # Configure date group style (parent rows)
        self.tree.tag_configure('date_group', background='#D1D5DB', font=('TkDefaultFont', 10, 'bold'))
        
        # Calculate and set the optimal width for Enseignants column
        # Each character is approximately 7-8 pixels wide in default font
        calculated_width = min(max(max_teacher_text_length * 8, 600), 4000)
        self.tree.column("Enseignants", width=calculated_width, stretch=False)
        
        # Add summary label if it exists
        if hasattr(self, 'summary_label'):
            total_slots = len(self.best)
            total_teachers = len(set(t for teachers in self.best.values() for t in teachers))
            self.summary_label.configure(
                text=f"📊 Total: {total_slots} créneaux | 👥 {total_teachers} enseignants uniques"
            )
        assign_teachers_to_rooms(self)
        self.setup_edit_mode()


    def display_planning_result_with_edit(self):
        """Affiche le planning avec possibilité d'édition (drag & drop et suppression)"""
        if not self.best:
            return
        
        # Call the existing display function first
        self.display_planning_result()
        
        # Bind events for editing functionality
        self.tree.bind("<Button-3>", self.show_context_menu)  # Right-click
        self.tree.bind("<Double-Button-1>", self.on_double_click)  # Double-click to edit
        
        # Create context menu
        self.create_context_menu()

    def create_context_menu(self):
        """Crée le menu contextuel pour supprimer/déplacer un enseignant"""
        self.context_menu = tk.Menu(self.tree, tearoff=0)
        self.context_menu.add_command(label="🗑️ Supprimer cet enseignant", 
                                    command=self.delete_selected_teacher)
        self.context_menu.add_command(label="↔️ Déplacer vers...", 
                                    command=self.show_move_dialog)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="❌ Annuler", command=lambda: None)

    def show_context_menu(self, event):
        """Affiche le menu contextuel sur clic droit"""
        # Identify the clicked row
        item = self.tree.identify_row(event.y)
        if not item:
            return
        
        # Select the item
        self.tree.selection_set(item)
        
        # Get the item values
        values = self.tree.item(item, "values")
        
        # Check if it's a session row (not a date group)
        if values and values[1]:  # Has a session value
            # Store the selected item info
            self.selected_teacher = {
                'item': item,
                'slot': f"{values[0].split()[-1] if values[0] else ''} {values[1].lower()}",
                'teachers_text': values[4]
            }
            
            # Show the context menu
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                self.context_menu.grab_release()
        
    def setup_edit_mode(self):
        """Active le mode édition sur le treeview"""
        # Bind double-click event
        self.tree.bind("<Double-Button-1>", self.on_double_click)
    def on_double_click(self, event):
        """Gère le double-clic pour éditer la liste des enseignants"""
        item = self.tree.identify_row(event.y)
        if not item:
            return
        if self.current_view != "planning":
            return
        values = self.tree.item(item, "values")
        
        # Check if it's a session row (not a date group)
        if values and values[1]:  # Has a session value
            # Get the parent item to retrieve the date
            parent = self.tree.parent(item)
            if parent:
                parent_values = self.tree.item(parent, "values")
                # Extract date from parent (format: " Lundi 13/05/2025")
                date_text = parent_values[0] if parent_values else ""
                # Pass both item, values, and the date from parent
                print(date_text)
                self.open_teacher_editor(item, values, date_text)
            else:
                # If no parent (shouldn't happen), try with empty date
                self.open_teacher_editor(item, values, "")
    def open_teacher_editor(self, item, values, parent_date_text):
        """Ouvre une fenêtre pour éditer la liste des enseignants d'une session"""
        # Create dialog window
        editor_window = ctk.CTkToplevel(self)
        editor_window.title("✏️ Éditer les enseignants")
        editor_window.geometry("800x600")
        editor_window.transient(self)
        editor_window.grab_set()
        
        # Parse slot info
        session = values[1]
        time = values[2]
        
        # Extract date from parent text: "📅 Lundi 13/05/2025" -> need to get YYYY-MM-DD format
        slot_key = None
        
        # Try to find the slot key by matching session and date in parent text
        for sk in self.best.keys():
            parts = sk.split()
            if len(parts) >= 2:
                sk_date = parts[0]  # YYYY-MM-DD format
                sk_session = parts[1].lower()
                
                # Check if session matches
                if sk_session == session.lower():
                    # Convert sk_date to DD/MM/YYYY to compare with parent_date_text
                    try:
                        from datetime import datetime
                        date_obj = datetime.strptime(sk_date, '%Y-%m-%d')
                        formatted_date = date_obj.strftime('%d/%m/%Y')
                        
                        # Check if this date appears in the parent text
                        if formatted_date in parent_date_text:
                            slot_key = sk
                            break
                    except:
                        continue
        
        # Header
        header = ctk.CTkFrame(editor_window, fg_color="#1976D2", corner_radius=10)
        header.pack(fill="x", padx=20, pady=20)
        
        # Display the slot key for clarity
        display_text = f"📅 {slot_key if slot_key else 'Session inconnue'}"
        
        ctk.CTkLabel(header, 
                    text=display_text,
                    font=ctk.CTkFont(size=18, weight="bold"),
                    text_color="white").pack(pady=15)
        
        # Instructions
        ctk.CTkLabel(editor_window,
                    text="Gérez les enseignants de cette session",
                    font=ctk.CTkFont(size=13)).pack(pady=10)
        
        # Teachers list frame
        list_frame = ctk.CTkFrame(editor_window, fg_color="transparent")
        list_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        # Scrollable frame for teachers
        teachers_scroll = ctk.CTkScrollableFrame(list_frame, fg_color="transparent")
        teachers_scroll.pack(fill="both", expand=True)
        
        # Check if we found the slot key
        if not slot_key:
            ctk.CTkLabel(teachers_scroll,
                        text="❌ Erreur: Session non trouvée",
                        font=ctk.CTkFont(size=14),
                        text_color="red").pack(pady=50)
            return
        
        if slot_key and slot_key in self.best:
            teacher_codes = list(self.best[slot_key])
            
            if not teacher_codes:
                ctk.CTkLabel(teachers_scroll,
                            text="Aucun enseignant assigné",
                            font=ctk.CTkFont(size=14),
                            text_color="gray").pack(pady=50)
            
            # Display each teacher with delete and transfer buttons
            for teacher_code in teacher_codes:
                teacher_frame = ctk.CTkFrame(teachers_scroll, 
                                            fg_color="#f0f0f0",
                                            corner_radius=10,
                                            border_width=2,
                                            border_color="#e0e0e0")
                teacher_frame.pack(fill="x", pady=8, padx=5)
                
                # Teacher info
                teacher_code_str = str(teacher_code)
                if teacher_code_str in self.teachers:
                    teacher_info = self.teachers[teacher_code_str]
                    nom = teacher_info.get('nom', '')
                    prenom = teacher_info.get('prenom', '')
                    grade = teacher_info.get('grade', '')
                    display_text = f"#{teacher_code} - {prenom} {nom} ({grade})"
                else:
                    display_text = f"#{teacher_code}"
                
                # Left side - Teacher info
                info_frame = ctk.CTkFrame(teacher_frame, fg_color="transparent")
                info_frame.pack(side="left", fill="x", expand=True, padx=15, pady=12)
                
                ctk.CTkLabel(info_frame,
                            text=display_text,
                            font=ctk.CTkFont(size=13, weight="bold"),
                            anchor="w").pack(side="left")
                
                # Right side - Action buttons
                buttons_frame = ctk.CTkFrame(teacher_frame, fg_color="transparent")
                buttons_frame.pack(side="right", padx=10, pady=8)
                
                # Transfer button
                transfer_btn = ctk.CTkButton(buttons_frame,
                                            text="↔️ Transférer",
                                            width=120,
                                            height=35,
                                            fg_color="#3B82F6",
                                            hover_color="#2563EB",
                                            font=ctk.CTkFont(size=12, weight="bold"),
                                            command=lambda tc=teacher_code, sk=slot_key, ew=editor_window: 
                                                self.show_transfer_destinations(tc, sk, ew))
                transfer_btn.pack(side="left", padx=5)
                
                # Delete button
                delete_btn = ctk.CTkButton(buttons_frame,
                                        text="🗑️ Supprimer",
                                        width=120,
                                        height=35,
                                        fg_color="#EF4444",
                                        hover_color="#DC2626",
                                        font=ctk.CTkFont(size=12, weight="bold"),
                                        command=lambda tc=teacher_code, sk=slot_key, ew=editor_window: 
                                            self.remove_teacher_from_slot(tc, sk, ew))
                delete_btn.pack(side="left", padx=5)
        
        # Bottom button frame
        bottom_frame = ctk.CTkFrame(editor_window, fg_color="transparent")
        bottom_frame.pack(fill="x", padx=20, pady=20)
        
        # Close button
        close_btn = ctk.CTkButton(bottom_frame,
                                text="✅ Fermer",
                                command=editor_window.destroy,
                                width=200,
                                height=45,
                                font=ctk.CTkFont(size=14, weight="bold"),
                                fg_color="#10B981",
                                hover_color="#059669")
        close_btn.pack()
    def show_transfer_destinations(self, teacher_code, source_slot, editor_window):
        """Affiche la liste des sessions de destination pour transférer un enseignant"""
        # Store teacher info for transfer
        self.selected_teacher_for_transfer = {
            'teacher_code': teacher_code,
            'source_slot': source_slot
        }
        
        # Create destination selection window
        dest_window = ctk.CTkToplevel(self)
        dest_window.title("↔️ Sélectionner la destination")
        dest_window.geometry("700x600")
        dest_window.transient(editor_window)
        dest_window.grab_set()
        
        # Header
        header = ctk.CTkFrame(dest_window, fg_color="#3B82F6", corner_radius=10)
        header.pack(fill="x", padx=20, pady=20)
        
        teacher_code_str = str(teacher_code)
        if teacher_code_str in self.teachers:
            teacher_info = self.teachers[teacher_code_str]
            teacher_name = f"{teacher_info.get('prenom', '')} {teacher_info.get('nom', '')}"
        else:
            teacher_name = f"Enseignant #{teacher_code}"
        
        ctk.CTkLabel(header,
                    text=f"Transférer: {teacher_name}",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color="white").pack(pady=15)
        
        ctk.CTkLabel(dest_window,
                    text="Sélectionnez la session de destination :",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 20))
        
        # Scrollable frame for destinations
        dest_scroll = ctk.CTkScrollableFrame(dest_window, fg_color="transparent")
        dest_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Group slots by date
        from collections import defaultdict
        slots_by_date = defaultdict(list)
        
        for slot_key in sorted(self.best.keys()):
            if slot_key != source_slot:  # Don't show source slot
                try:
                    parts = slot_key.split()
                    date = parts[0]
                    session = parts[1]
                    slots_by_date[date].append((slot_key, session))
                except:
                    continue
        
        # Display slots grouped by date
        for date in sorted(slots_by_date.keys()):
            # Date header
            date_frame = ctk.CTkFrame(dest_scroll, fg_color="#E5E7EB", corner_radius=8)
            date_frame.pack(fill="x", pady=(10, 5))
            
            try:
                from datetime import datetime
                date_obj = datetime.strptime(date, '%Y-%m-%d')
                day_names_fr = {
                    'Monday': 'Lundi', 'Tuesday': 'Mardi', 'Wednesday': 'Mercredi',
                    'Thursday': 'Jeudi', 'Friday': 'Vendredi', 'Saturday': 'Samedi', 'Sunday': 'Dimanche'
                }
                day_name = day_names_fr.get(date_obj.strftime('%A'), date_obj.strftime('%A'))
                formatted_date = f"{day_name} {date_obj.strftime('%d/%m/%Y')}"
            except:
                formatted_date = date
            
            ctk.CTkLabel(date_frame,
                        text=f"📅 {formatted_date}",
                        font=ctk.CTkFont(size=13, weight="bold"),
                        text_color="#374151").pack(pady=8, padx=15)
            
            # Sessions for this date
            sessions_frame = ctk.CTkFrame(dest_scroll, fg_color="transparent")
            sessions_frame.pack(fill="x", pady=(0, 5), padx=10)
            
            SESSION_TIMES = {'s1': '08:30', 's2': '10:30', 's3': '12:30', 's4': '14:30'}
            
            for slot_key, session in sorted(slots_by_date[date], key=lambda x: x[1]):
                session_btn = ctk.CTkButton(
                    sessions_frame,
                    text=f"{session.upper()} - {SESSION_TIMES.get(session.lower(), '')} ({len(self.best[slot_key])} enseignants)",
                    command=lambda sk=slot_key, dw=dest_window, ew=editor_window: 
                        self.show_room_selection(sk, dw, ew),  # Changed to show room selection
                    height=40,
                    font=ctk.CTkFont(size=13),
                    fg_color="#FFFFFF",
                    text_color="#1F2937",
                    hover_color="#F3F4F6",
                    border_width=2,
                    border_color="#D1D5DB"
                )
                session_btn.pack(fill="x", pady=3)
        
        # Cancel button at bottom
        cancel_btn = ctk.CTkButton(dest_window,
                                text="❌ Annuler",
                                command=dest_window.destroy,
                                width=200,
                                height=45,
                                font=ctk.CTkFont(size=14, weight="bold"),
                                fg_color="#6B7280",
                                hover_color="#4B5563")
        cancel_btn.pack(pady=20)


    def show_room_selection(self, dest_slot, dest_window, editor_window):
        """Affiche les salles disponibles pour la session de destination"""
        if not self.selected_teacher_for_transfer:
            return
        
        teacher_code = self.selected_teacher_for_transfer['teacher_code']
        
        # Create room selection window
        room_window = ctk.CTkToplevel(self)
        room_window.title("🏫 Sélectionner la salle")
        room_window.geometry("600x500")
        room_window.transient(dest_window)
        room_window.grab_set()
        
        # Header
        header = ctk.CTkFrame(room_window, fg_color="#10B981", corner_radius=10)
        header.pack(fill="x", padx=20, pady=20)
        
        # Get teacher name
        teacher_code_str = str(teacher_code)
        if teacher_code_str in self.teachers:
            teacher_info = self.teachers[teacher_code_str]
            teacher_name = f"{teacher_info.get('prenom', '')} {teacher_info.get('nom', '')}"
        else:
            teacher_name = f"Enseignant #{teacher_code}"
        
        # Format slot display
        try:
            parts = dest_slot.split()
            date_str = parts[0]
            session = parts[1].upper()
            from datetime import datetime
            date_obj = datetime.strptime(date_str, '%Y-%m-%d')
            formatted_date = date_obj.strftime('%d/%m/%Y')
            slot_display = f"{formatted_date} - {session}"
        except:
            slot_display = dest_slot
        
        ctk.CTkLabel(header,
                    text=f"Destination: {slot_display}",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color="white").pack(pady=15)
        
        ctk.CTkLabel(room_window,
                    text=f"Sélectionnez une salle pour {teacher_name} :",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=(10, 20))
        
        # Scrollable frame for rooms
        rooms_scroll = ctk.CTkScrollableFrame(room_window, fg_color="transparent")
        rooms_scroll.pack(fill="both", expand=True, padx=20, pady=(0, 20))
        
        # Get rooms for this slot
        if hasattr(self, 'room_assignments') and dest_slot in self.room_assignments:
            rooms = self.room_assignments[dest_slot]
            
            if not rooms:
                ctk.CTkLabel(rooms_scroll,
                            text="❌ Aucune salle disponible pour cette session",
                            font=ctk.CTkFont(size=14),
                            text_color="red").pack(pady=50)
            else:
                # Display each room with its current teachers
                for room_name, teachers_in_room in sorted(rooms.items()):
                    room_frame = ctk.CTkFrame(rooms_scroll, 
                                            fg_color="#F9FAFB",
                                            corner_radius=10,
                                            border_width=2,
                                            border_color="#E5E7EB")
                    room_frame.pack(fill="x", pady=8)
                    
                    # Room info section
                    info_section = ctk.CTkFrame(room_frame, fg_color="transparent")
                    info_section.pack(fill="x", padx=15, pady=10)
                    
                    # Room name and teacher count
                    header_frame = ctk.CTkFrame(info_section, fg_color="transparent")
                    header_frame.pack(fill="x")
                    
                    ctk.CTkLabel(header_frame,
                                text=f"🏫 {room_name}",
                                font=ctk.CTkFont(size=15, weight="bold"),
                                text_color="#1F2937").pack(side="left")
                    
                    # Teacher count badge
                    count_badge = ctk.CTkFrame(header_frame, 
                                            fg_color="#3B82F6" if len(teachers_in_room) == 2 
                                            else "#10B981" if len(teachers_in_room) < 4 
                                            else "#EF4444",
                                            corner_radius=12)
                    count_badge.pack(side="right")
                    
                    ctk.CTkLabel(count_badge,
                                text=f"{len(teachers_in_room)} profs",
                                font=ctk.CTkFont(size=11, weight="bold"),
                                text_color="white").pack(padx=10, pady=4)
                    
                    # List current teachers in this room
                    if teachers_in_room:
                        teachers_text = ctk.CTkTextbox(info_section, 
                                                    height=80,
                                                    fg_color="#FFFFFF",
                                                    corner_radius=8,
                                                    border_width=1,
                                                    border_color="#E5E7EB")
                        teachers_text.pack(fill="x", pady=(8, 0))
                        
                        teacher_names = []
                        for t_code in teachers_in_room:
                            t_code_str = str(t_code)
                            if t_code_str in self.teachers:
                                t_info = self.teachers[t_code_str]
                                name = f"• {t_info.get('prenom', '')} {t_info.get('nom', '')} ({t_info.get('grade', '')})"
                            else:
                                name = f"• Enseignant #{t_code}"
                            teacher_names.append(name)
                        
                        teachers_text.insert("1.0", "\n".join(teacher_names))
                        teachers_text.configure(state="disabled")
                    
                    # Select button
                    select_btn = ctk.CTkButton(room_frame,
                                            text="✅ Sélectionner cette salle",
                                            command=lambda r=room_name: 
                                                self.transfer_teacher_to_room(dest_slot, r, room_window, dest_window, editor_window),
                                            height=40,
                                            font=ctk.CTkFont(size=13, weight="bold"),
                                            fg_color="#10B981",
                                            hover_color="#059669")
                    select_btn.pack(fill="x", padx=15, pady=(5, 10))
        else:
            ctk.CTkLabel(rooms_scroll,
                        text="❌ Aucune information de salle disponible",
                        font=ctk.CTkFont(size=14),
                        text_color="red").pack(pady=50)
        
        # Cancel button
        cancel_btn = ctk.CTkButton(room_window,
                                text="⬅️ Retour",
                                command=room_window.destroy,
                                width=200,
                                height=45,
                                font=ctk.CTkFont(size=14, weight="bold"),
                                fg_color="#6B7280",
                                hover_color="#4B5563")
        cancel_btn.pack(pady=20)


    def transfer_teacher_to_room(self, dest_slot, dest_room, room_window, dest_window, editor_window):
        """Transfère l'enseignant vers la salle sélectionnée"""
        if not self.selected_teacher_for_transfer:
            return
        
        teacher_code = self.selected_teacher_for_transfer['teacher_code']
        source_slot = self.selected_teacher_for_transfer['source_slot']
        
        # Remove teacher from source slot
        if source_slot in self.best and teacher_code in self.best[source_slot]:
            # Remove from source slot's teacher list
            self.best[source_slot].remove(teacher_code)
            
            # Remove from source room assignment if exists
            if hasattr(self, 'room_assignments') and source_slot in self.room_assignments:
                for room, teachers in self.room_assignments[source_slot].items():
                    if teacher_code in teachers:
                        teachers.remove(teacher_code)
                        break
            
            # Add to destination slot's teacher list
            if dest_slot in self.best:
                self.best[dest_slot].append(teacher_code)
            else:
                self.best[dest_slot] = [teacher_code]
            
            # Add to destination room assignment
            if hasattr(self, 'room_assignments'):
                if dest_slot not in self.room_assignments:
                    self.room_assignments[dest_slot] = {}
                if dest_room not in self.room_assignments[dest_slot]:
                    self.room_assignments[dest_slot][dest_room] = []
                
                self.room_assignments[dest_slot][dest_room].append(teacher_code)
            
            # Get teacher name for success message
            teacher_code_str = str(teacher_code)
            if teacher_code_str in self.teachers:
                teacher_info = self.teachers[teacher_code_str]
                teacher_name = f"{teacher_info.get('prenom', '')} {teacher_info.get('nom', '')}"
            else:
                teacher_name = f"#{teacher_code}"
            
            self.show_success_message("✅ Transfert réussi",
                f"{teacher_name} transféré vers {dest_slot} - Salle {dest_room}")
            
            # Refresh display
            self.display_planning_result()
            
            # Close all windows
            room_window.destroy()
            dest_window.destroy()
            editor_window.destroy()
        else:
            self.show_error_message("❌ Erreur",
                "Enseignant non trouvé dans le créneau source")
        
        # Reset selection
        self.selected_teacher_for_transfer = None
        def transfer_teacher(self, dest_slot, dest_window, editor_window):
            """Transfère l'enseignant sélectionné vers la session de destination"""
            if not self.selected_teacher_for_transfer:
                return
            
            teacher_code = self.selected_teacher_for_transfer['teacher_code']
            source_slot = self.selected_teacher_for_transfer['source_slot']
            
            if source_slot in self.best and dest_slot in self.best:
                # Remove from source
                if teacher_code in self.best[source_slot]:
                    self.best[source_slot].remove(teacher_code)
                    
                    # Add to destination
                    self.best[dest_slot].append(teacher_code)
                    
                    self.show_success_message("✅ Transfert réussi",
                        f"Enseignant #{teacher_code} transféré vers {dest_slot}")
                    
                    # Refresh display
                    self.display_planning_result()
                    
                    # Close both windows
                    dest_window.destroy()
                    editor_window.destroy()
                else:
                    self.show_error_message("❌ Erreur",
                        "Enseignant non trouvé dans le créneau source")
            
            # Reset selection
            self.selected_teacher_for_transfer = None
        def find_slot_key(self, date, session):
            """Trouve la clé du slot correspondant à une date et session"""
            for slot_key in self.best.keys():
                if date in slot_key and session in slot_key.lower():
                    return slot_key
            return None
        def remove_teacher_from_slot(self, teacher_code, slot_key, editor_window=None):
            """Supprime un enseignant d'un créneau"""
            if slot_key in self.best:
                # Remove teacher from the slot
                if teacher_code in self.best[slot_key]:
                    self.best[slot_key].remove(teacher_code)
                    
                    # Show success message
                    self.show_success_message("✅ Suppression réussie", 
                        f"Enseignant #{teacher_code} supprimé du créneau")
                    
                    # Refresh the display
                    self.display_planning_result()
                    
                    # Close editor if open
                    if editor_window:
                        editor_window.destroy()
                else:
                    self.show_error_message("❌ Erreur", 
                        "Enseignant non trouvé dans ce créneau")

    def delete_selected_teacher(self):
        """Supprime l'enseignant sélectionné via le menu contextuel"""
        if not self.selected_teacher:
            return
        
        # Parse the slot key
        slot_key = self.selected_teacher['slot']
        teachers_text = self.selected_teacher['teachers_text']
        
        # Create dialog to select which teacher to delete
        delete_window = ctk.CTkToplevel(self)
        delete_window.title("🗑️ Supprimer un enseignant")
        delete_window.geometry("500x400")
        delete_window.transient(self)
        delete_window.grab_set()
        
        ctk.CTkLabel(delete_window,
                    text="Sélectionnez l'enseignant à supprimer :",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=20)
        
        # List of teachers
        teachers_frame = ctk.CTkScrollableFrame(delete_window)
        teachers_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        if slot_key in self.best:
            for teacher_code in self.best[slot_key]:
                teacher_code_str = str(teacher_code)
                if teacher_code_str in self.teachers:
                    teacher_info = self.teachers[teacher_code_str]
                    display_text = f"#{teacher_code} - {teacher_info.get('prenom', '')} {teacher_info.get('nom', '')}"
                else:
                    display_text = f"#{teacher_code}"
                
                btn = ctk.CTkButton(teachers_frame,
                                text=display_text,
                                command=lambda tc=teacher_code: [
                                    self.remove_teacher_from_slot(tc, slot_key),
                                    delete_window.destroy()
                                ])
                btn.pack(fill="x", pady=5)
    def show_move_dialog(self):
        """Affiche le dialogue pour déplacer un enseignant vers une autre session"""
        if not self.selected_teacher:
            return
        
        # Create move dialog
        move_window = ctk.CTkToplevel(self)
        move_window.title("↔️ Déplacer un enseignant")
        move_window.geometry("600x500")
        move_window.transient(self)
        move_window.grab_set()
        
        ctk.CTkLabel(move_window,
                    text="Sélectionnez la session de destination :",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=20)
        
        # List all available slots
        slots_frame = ctk.CTkScrollableFrame(move_window)
        slots_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        source_slot = self.selected_teacher['slot']
        
        for slot_key in sorted(self.best.keys()):
            if slot_key != source_slot:  # Don't show source slot
                slot_btn = ctk.CTkButton(slots_frame,
                                        text=slot_key,
                                        command=lambda sk=slot_key: 
                                            self.select_teacher_and_move(source_slot, sk, move_window))
                slot_btn.pack(fill="x", pady=5)
    def select_teacher_and_move(self, source_slot, dest_slot, move_window):
        """Sélectionne l'enseignant à déplacer et effectue le déplacement"""
        move_window.destroy()
        
        # Create teacher selection dialog
        select_window = ctk.CTkToplevel(self)
        select_window.title("Sélectionner l'enseignant")
        select_window.geometry("500x400")
        select_window.transient(self)
        select_window.grab_set()
        
        ctk.CTkLabel(select_window,
                    text=f"Déplacer vers: {dest_slot}",
                    font=ctk.CTkFont(size=12)).pack(pady=10)
        
        ctk.CTkLabel(select_window,
                    text="Sélectionnez l'enseignant à déplacer :",
                    font=ctk.CTkFont(size=14, weight="bold")).pack(pady=10)
        
        teachers_frame = ctk.CTkScrollableFrame(select_window)
        teachers_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        if source_slot in self.best:
            for teacher_code in self.best[source_slot]:
                teacher_code_str = str(teacher_code)
                if teacher_code_str in self.teachers:
                    teacher_info = self.teachers[teacher_code_str]
                    display_text = f"#{teacher_code} - {teacher_info.get('prenom', '')} {teacher_info.get('nom', '')}"
                else:
                    display_text = f"#{teacher_code}"
                
                btn = ctk.CTkButton(teachers_frame,
                                text=display_text,
                                command=lambda tc=teacher_code: [
                                    self.move_teacher(tc, source_slot, dest_slot),
                                    select_window.destroy()
                                ])
                btn.pack(fill="x", pady=5)
    def move_teacher(self, teacher_code, source_slot, dest_slot):
        """Déplace un enseignant d'un créneau à un autre"""
        if source_slot in self.best and dest_slot in self.best:
            # Remove from source
            if teacher_code in self.best[source_slot]:
                self.best[source_slot].remove(teacher_code)
                
                # Add to destination
                self.best[dest_slot].append(teacher_code)
                
                self.show_success_message("✅ Succès",
                    f"Enseignant #{teacher_code} déplacé vers {dest_slot}")
                
                # Refresh display
                self.display_planning_result()
            else:
                self.show_error_message("❌ Erreur",
                    "Enseignant non trouvé dans le créneau source")
    def show_by_teacher(self):
        """Vue par enseignant avec email comme identifiant"""
        if not self.best:
            self.show_error_message("❌ Erreur", "Veuillez générer le planning d'abord!")
            return
        
        from collections import defaultdict
        from datetime import datetime
        
        self.tree.delete(*self.tree.get_children())
        
        # CHANGEMENT : Utiliser "Email" au lieu de "Code"
        self.tree["columns"] = ("Email", "Nom", "Grade", "Stats", "Statut", "Détails")
        
        # Column configuration
        cols = {
            "Email": {"width": 200, "text": "📧 Email", "anchor": "w"},  # Changé de "Code" à "Email"
            "Nom": {"width": 200, "text": "📝 Nom Complet", "anchor": "w"},
            "Grade": {"width": 100, "text": "🎓 Grade", "anchor": "center"},
            "Stats": {"width": 150, "text": "📊 Quota/Assigné", "anchor": "center"},
            "Statut": {"width": 120, "text": "✓ Statut", "anchor": "center"},
            "Détails": {"width": 400, "text": "📅 Créneaux (cliquer pour développer)", "anchor": "w"}
        }
        
        for col, config in cols.items():
            self.tree.heading(col, text=config["text"])
            self.tree.column(col, width=config["width"], anchor=config["anchor"])
        
        # Calculate teacher assignments
        teacher_slots = defaultdict(list)
        for slot in self.best:
            for teacher in self.best[slot]:
                teacher_slots[teacher].append(slot)
        
        # Day names in French
        DAY_NAMES_FR = {
            'Monday': 'Lun', 'Tuesday': 'Mar', 'Wednesday': 'Mer',
            'Thursday': 'Jeu', 'Friday': 'Ven', 'Saturday': 'Sam', 'Sunday': 'Dim'
        }
        
        # Function to format slots compactly
        def format_slots_summary(slots):
            """Create a compact summary of slots"""
            if not slots:
                return "Aucun créneau"
            
            # Group by date
            slots_by_date = defaultdict(list)
            for slot in sorted(slots):
                try:
                    parts = slot.split()
                    date_str = parts[0]
                    session = parts[1].upper()
                    slots_by_date[date_str].append(session)
                except:
                    continue
            
            # Create compact representation
            summary_parts = []
            for date_str in sorted(slots_by_date.keys()):
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    day_name = DAY_NAMES_FR.get(date_obj.strftime('%A'), '')
                    date_short = date_obj.strftime('%d/%m')
                    sessions = sorted(slots_by_date[date_str])
                    summary_parts.append(f"{day_name} {date_short}: {', '.join(sessions)}")
                except:
                    summary_parts.append(f"{date_str}: {', '.join(sorted(slots_by_date[date_str]))}")
            
            # Limit to first 2 dates if too many
            if len(summary_parts) > 2:
                visible = " | ".join(summary_parts[:2])
                remaining = len(summary_parts) - 2
                return f"{visible} ... (+{remaining} dates)"
            else:
                return " | ".join(summary_parts)
        
        # Insert assigned teachers
        for teacher in sorted(teacher_slots.keys()):
            if teacher_slots[teacher]:
                data = self.teachers[teacher]
                num_gardes = len(teacher_slots[teacher])
                quota = data['quota']
                
                # Determine status
                if num_gardes > quota:
                    status = "⚠️ Dépassé"
                    tag = "over_quota"
                elif num_gardes == quota:
                    status = "✅ Complet"
                    tag = "optimal"
                else:
                    status = "🟢 OK"
                    tag = "acceptable"
                
                # Full name
                full_name = f"{data['prenom']} {data['nom']}"
                
                # Stats display
                stats = f"{num_gardes}/{quota}"
                
                # Compact slots summary
                slots_summary = format_slots_summary(teacher_slots[teacher])
                
                # Insert parent row (teacher summary)
                parent = self.tree.insert("", "end", values=(
                    teacher,
                    full_name,
                    data['grade'],
                    stats,
                    status,
                    slots_summary
                ), tags=(tag,), open=False)
                
                # Insert child rows (detailed slots) - hidden by default
                for slot in sorted(teacher_slots[teacher]):
                    try:
                        parts = slot.split()
                        date_str = parts[0]
                        session = parts[1].upper()
                        
                        # Format date
                        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                        day_name = DAY_NAMES_FR.get(date_obj.strftime('%A'), date_obj.strftime('%A'))
                        formatted_date = f"{day_name} {date_obj.strftime('%d/%m/%Y')}"
                        
                        # Session time
                        session_times = {'S1': '08:30', 'S2': '10:30', 'S3': '12:30', 'S4': '14:30'}
                        time = session_times.get(session, "N/A")
                        
                        self.tree.insert(parent, "end", values=(
                            "",
                            formatted_date,
                            session,
                            time,
                            "📅 Créneau",
                            ""
                        ), tags=(tag))
                        # tags = (f"session_{session.lower()}",) for colored sessions.
                    except:
                        self.tree.insert(parent, "end", values=(
                            "", slot, "", "", "", ""
                        ))
                
                # Add unavailability info if exists
                if data['indispo']:
                    unavail_summary = format_slots_summary(data['indispo'])
                    self.tree.insert(parent, "end", values=(
                        "", "🚫 Indisponibilités", "", "", "", unavail_summary
                    ), tags=("separator",))
        
        # Add separator between assigned and unassigned
        if teacher_slots:
            self.tree.insert("", "end", values=(
                "━━━━", "━━━━━━━━━━━━━━━━━━━━━", "━━━━", "━━━━━━━━", "━━━━━━━", "━━━━━━━━━━━━━━━━━━━━━"
            ), tags=("separator",))
        
        # Insert unassigned teachers who should participate
        assigned_teachers = set().union(*self.best.values())
        available_teachers = {t for t in self.teachers 
                            if self.teachers[t]['participe_surveillance'] 
                            and t not in assigned_teachers}
        
        for teacher in sorted(available_teachers):
            data = self.teachers[teacher]
            full_name = f"{data['prenom']} {data['nom']}"
            
            parent = self.tree.insert("", "end", values=(
                teacher,
                full_name,
                data['grade'],
                f"0/{data['quota']}",
                "⚠️ Non assigné",
                "Aucun créneau assigné"
            ), tags=("unassigned",), open=False)
            
            # Show unavailability
            if data['indispo']:
                unavail_summary = format_slots_summary(data['indispo'])
                self.tree.insert(parent, "end", values=(
                    "", "🚫 Indisponibilités", "", "", "", unavail_summary
                ), tags=("separator",))
        
        # Add summary statistics
        if hasattr(self, 'summary_label'):
            total_assigned = len(set().union(*self.best.values()))
            total_eligible = sum(1 for t in self.teachers.values() if t['participe_surveillance'])
            over_quota = sum(1 for t in teacher_slots if len(teacher_slots[t]) > self.teachers[t]['quota'])
            
            self.summary_label.configure(
                text=f"👥 {total_assigned}/{total_eligible} enseignants assignés | ⚠️ {over_quota} dépassements de quota"
            )
    def show_by_day(self):
        """Vue par jour"""
        if not self.best:
            self.show_error_message("❌ Erreur", "Veuillez générer le planning d'abord!")
            return
        
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Jour", "Nombre de créneaux", "Créneaux")
        self.tree.heading("Jour", text="Jour")
        self.tree.heading("Nombre de créneaux", text="Nb Créneaux")
        self.tree.heading("Créneaux", text="Détails des Créneaux")
        
        self.tree.column("Jour", width=150)
        self.tree.column("Nombre de créneaux", width=120)
        self.tree.column("Créneaux", width=600)
        
        day_slots = {}
        for slot in self.best:
            day = slot.split()[0]
            if day not in day_slots:
                day_slots[day] = []
            day_slots[day].append(slot)
        
        for day in sorted(day_slots.keys()):
            slots_str = ", ".join(sorted(day_slots[day]))
            self.tree.insert("", "end", values=(day, len(day_slots[day]), slots_str))

    def show_by_room(self):
        """Vue par salle avec structure collapsible améliorée"""
        if not self.best:
            self.show_error_message("❌ Erreur", "Veuillez générer le planning d'abord!")
            return
        

        
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Salle", "Stats", "Statut", "Détails")
        
        # Column configuration
        cols = {
            "Salle": {"width": 150, "text": "🏫 Salle", "anchor": "center"},
            "Stats": {"width": 150, "text": "📊 Créneaux", "anchor": "center"},
            "Statut": {"width": 120, "text": "✓ Statut", "anchor": "center"},
            "Détails": {"width": 500, "text": "📅 Résumé (cliquer pour développer)", "anchor": "w"}
        }
        
        for col, config in cols.items():
            self.tree.heading(col, text=config["text"])
            self.tree.column(col, width=config["width"], anchor=config["anchor"])
        
        # Organize data by room
        room_data = defaultdict(list)
        
        for slot in sorted(self.best.keys()):
            if slot in self.room_assignments:
                for room, teachers in self.room_assignments[slot].items():
                    room_data[room].append({
                        'slot': slot,
                        'teachers': teachers,
                        'nb_profs': len(teachers)
                    })
        
        # Day names in French
        DAY_NAMES_FR = {
            'Monday': 'Lun', 'Tuesday': 'Mar', 'Wednesday': 'Mer',
            'Thursday': 'Jeu', 'Friday': 'Ven', 'Saturday': 'Sam', 'Sunday': 'Dim'
        }
        
        # Function to create compact summary
        def create_room_summary(assignments):
            """Create compact summary of room usage"""
            total_slots = len(assignments)
            avg_profs = sum(a['nb_profs'] for a in assignments) / total_slots if total_slots > 0 else 0
            
            # Show first 2 slots
            preview = []
            for assign in assignments[:2]:
                try:
                    parts = assign['slot'].split()
                    date_str = parts[0]
                    session = parts[1].upper()
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    day_name = DAY_NAMES_FR.get(date_obj.strftime('%A'), '')
                    date_short = date_obj.strftime('%d/%m')
                    preview.append(f"{day_name} {date_short} {session}")
                except:
                    preview.append(assign['slot'])
            
            summary = " | ".join(preview)
            if total_slots > 2:
                summary += f" ... (+{total_slots - 2})"
            
            return summary
        
        # Insert each room with its assignments
        for room in sorted(room_data.keys()):
            assignments = room_data[room]
            total_slots = len(assignments)
            
            # Calculate statistics
            total_profs = sum(a['nb_profs'] for a in assignments)
            avg_profs = total_profs / total_slots if total_slots > 0 else 0
            problem_count = sum(1 for a in assignments if a['nb_profs'] > 4)
            optimal_count = sum(1 for a in assignments if a['nb_profs'] == 2)
            
            # Determine status
            if problem_count > 0:
                status = f"⚠️ {problem_count} problème(s)"
                tag = "problem"
            elif optimal_count == total_slots:
                status = "✅ Optimal"
                tag = "optimal"
            else:
                status = "🟢 OK"
                tag = "acceptable"
            
            # Stats display
            stats = f"{total_slots} créneaux"
            
            # Create summary
            summary = create_room_summary(assignments)
            
            # Insert parent row (room summary)
            parent = self.tree.insert("", "end", values=(
                room,
                stats,
                status,
                summary
            ), tags=(tag,), open=False)
            
            # Insert child rows (detailed slots) - hidden by default
            for assign in sorted(assignments, key=lambda x: x['slot']):
                try:
                    parts = assign['slot'].split()
                    date_str = parts[0]
                    session = parts[1].upper()
                    
                    # Format date
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    day_name = DAY_NAMES_FR.get(date_obj.strftime('%A'), date_obj.strftime('%A'))
                    formatted_date = f"{day_name} {date_obj.strftime('%d/%m/%Y')}"
                    
                    # Session time
                    session_times = {'S1': '08:30', 'S2': '10:30', 'S3': '12:30', 'S4': '14:30'}
                    time = session_times.get(session, "N/A")
                    
                    # Format teachers
                    nb_profs = assign['nb_profs']
                    teachers_list = []
                    for teacher_code in sorted(assign['teachers']):
                        teacher_code_str = str(teacher_code)
                        if hasattr(self, 'teachers') and teacher_code_str in self.teachers:
                            teacher_info = self.teachers[teacher_code_str]
                            nom = teacher_info.get('nom', '')
                            prenom = teacher_info.get('prenom', '')
                            if nom and prenom:
                                teachers_list.append(f"{prenom} {nom}")
                            else:
                                teachers_list.append(f"#{teacher_code}")
                        else:
                            teachers_list.append(f"#{teacher_code}")
                    
                    teachers_display = ", ".join(teachers_list)
                    
                    # Determine child tag based on number of profs
                    if nb_profs > 4:
                        child_tag = "problem_light"
                        status_icon = "⚠️"
                    elif nb_profs == 2:
                        child_tag = "optimal_light"
                        status_icon = "✅"
                    else:
                        child_tag = "acceptable_light"
                        status_icon = "🟢"
                    
                    self.tree.insert(parent, "end", values=(
                        f"{formatted_date} - {session} ({time})",
                        f"{nb_profs} profs {status_icon}",
                        "",
                        teachers_display
                    ), tags=(child_tag,))
                    
                except Exception as e:
                    # Fallback for unexpected format
                    self.tree.insert(parent, "end", values=(
                        assign['slot'],
                        f"{assign['nb_profs']} profs",
                        "",
                        ", ".join(sorted(assign['teachers']))
                    ))
        
        # Add summary statistics
        if hasattr(self, 'summary_label'):
            total_rooms = len(room_data)
            total_assignments = sum(len(assignments) for assignments in room_data.values())
            problem_assignments = sum(
                sum(1 for a in assignments if a['nb_profs'] > 4) 
                for assignments in room_data.values()
            )
            
            self.summary_label.configure(
                text=f"🏫 {total_rooms} salles utilisées | 📊 {total_assignments} créneaux totaux | ⚠️ {problem_assignments} surcharges"
            )
    def show_general_info(self):
        """Vue des informations générales"""
        if not self.best:
            self.show_error_message("❌ Erreur", "Veuillez générer le planning d'abord!")
            return
        
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Information", "Valeur")
        self.tree.heading("Information", text="Information")
        self.tree.heading("Valeur", text="Valeur")
        
        self.tree.column("Information", width=500)
        self.tree.column("Valeur", width=250)
        
        total_teachers = len(self.teachers)
        participating = sum(1 for t in self.teachers.values() if t['participe_surveillance'])
        assigned_teachers = len(set().union(*self.best.values()))
        unassigned_teachers = sum(1 for t in self.teachers 
                                 if self.teachers[t]['participe_surveillance'] 
                                 and t not in set().union(*self.best.values()))
        total_slots = len(self.best)
        
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
        
        self.tree.insert("", "end", values=("=== ENSEIGNANTS ===", ""), tags=("header",))
        self.tree.insert("", "end", values=("Nombre total d'enseignants", total_teachers))
        self.tree.insert("", "end", values=("Enseignants participant à la surveillance", participating))
        self.tree.insert("", "end", values=("Enseignants assignés", 
            f"{assigned_teachers} ({100*assigned_teachers/participating:.1f}%)"))
        self.tree.insert("", "end", values=("Enseignants non assignés (participe=1)", unassigned_teachers))
        
        self.tree.insert("", "end", values=("", ""))
        self.tree.insert("", "end", values=("=== CRÉNEAUX ===", ""), tags=("header",))
        self.tree.insert("", "end", values=("Nombre total de créneaux", total_slots))
        
        self.tree.insert("", "end", values=("", ""))
        self.tree.insert("", "end", values=("=== STATISTIQUES PAR GRADE ===", ""), tags=("header",))
        
        for grade in sorted(grade_stats.keys()):
            stats = grade_stats[grade]
            self.tree.insert("", "end", values=(
                f"Grade {grade} ({stats['total']} profs)",
                f"Min: {stats['min']}, Max: {stats['max']}, Moy: {stats['avg']:.1f}"
            ))
    def show_planning_quality(self):
        """Affiche la qualité détaillée du planning"""
        if not self.best:
            self.show_error_message("❌ Erreur", "Veuillez générer le planning d'abord!")
            return
        
        # Note: You need fitness function and check_consecutivity_violations
        # This is a simplified version
        
        self.tree.delete(*self.tree.get_children())
        self.tree["columns"] = ("Métrique", "Valeur", "Statut")
        self.tree.heading("Métrique", text="Métrique")
        self.tree.heading("Valeur", text="Valeur")
        self.tree.heading("Statut", text="Statut")
        
        self.tree.column("Métrique", width=400)
        self.tree.column("Valeur", width=150)
        self.tree.column("Statut", width=250)
        
        fitness_score = -100  # Replace with actual calculation
        quality = "🟢 Excellent" if fitness_score > -100 else \
                 "🟡 Acceptable" if fitness_score > -500 else \
                 "🟠 Moyen" if fitness_score > -1000 else "🔴 Problématique"
        
        self.tree.insert("", "end", values=(
            "📊 SCORE GLOBAL DE FITNESS", 
            f"{fitness_score:.0f}", 
            quality
        ), tags=("header",))
        
        self.tree.insert("", "end", values=("", "", ""))
        self.tree.insert("", "end", values=("=== ⚠️ CONTRAINTES RIGIDES ===", "", ""), tags=("header",))
        
        # Add constraint checks here
        constraints = [
            ("Minimum 2 profs/salle", 0, "✅ OK"),
            ("Maximum 4 profs/salle", 0, "✅ OK"),
            ("Dépassements de quota", 0, "✅ OK"),
            ("Vœux d'indisponibilité violés", 0, "✅ OK"),
        ]
        
        for label, count, status in constraints:
            tag = "ok" if count == 0 else "error"
            self.tree.insert("", "end", values=(label, count, status), tags=(tag,))

    def export_csv(self):
        """Exporte le planning en CSV"""
        if not self.best:
            self.show_error_message("❌ Erreur", "Veuillez générer le planning d'abord!")
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
                self.show_success_message("✅ Succès", f"Planning exporté vers:\n{file}")
            except Exception as e:
                self.show_error_message("❌ Erreur", f"Erreur lors de l'export CSV:\n{str(e)}")

    # def populate_flat_view(self):
    #     self.tree.delete(*self.tree.get_children())
    #     for row in self.view_data:
    #         tag = ""
    #         values = row
    #         if len(row) > 0 and isinstance(row[-1], str):
    #             if row[-1] in ["over_quota", "unassigned", "voeux_violes", "voeux_ok", 
    #                            "optimal", "acceptable", "problem", "header", "ok", "warning", "error"]:
    #                 tag = row[-1]
    #                 values = row[:-1]
            
    #         text = " ".join(map(str, values)).lower()
    #         if self.current_filter in text or not self.current_filter:
    #             self.tree.insert("", "end", values=values, tags=(tag,) if tag else ())

    # def configure_action_buttons(self):
    #     for widget in self.action_frame.winfo_children():
    #         widget.destroy()

    # def refresh_view(self):
    #     if self.current_view == "default":
    #         self.display_planning_result()
    #     elif self.current_view == "teacher":
    #         self.show_by_teacher_wrapper()
    #     elif self.current_view == "calendar":
    #         self.show_by_day_calendar_wrapper()
    #     elif self.current_view == "room":
    #         self.show_by_room_wrapper()
    #     elif self.current_view == "quality":
    #         self.show_planning_quality_wrapper()
    def export_teachers_to_pdf(self, output_folder="exports", send_emails=True):
        """Exporte un PDF pour chaque enseignant avec ses créneaux et option d'envoi par email"""
        if not self.best:
            self.show_error_message("❌ Erreur", "Veuillez générer le planning d'abord!")
            return
        
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        
        # Delete old Affectation PDFs
        import glob
        old_pdfs = glob.glob(os.path.join(output_folder, "Affectation_*.pdf"))
        for old_pdf in old_pdfs:
            try:
                os.remove(old_pdf)
            except Exception as e:
                print(f"Could not delete {old_pdf}: {e}")
        
        # Organize assignments by teacher
        from collections import defaultdict
        teacher_slots = defaultdict(list)
        
        for slot in self.best:
            for teacher in self.best[slot]:
                teacher_slots[teacher].append(slot)
        
        # Session times mapping
        SESSION_TIMES = {
            's1': '08:30:00',
            's2': '10:30:00',
            's3': '12:30:00',
            's4': '14:30:00'
        }

        pdf_count = 0
        email_count = 0
        email_errors = []
        
        # Store PDFs info for emailing
        pdfs_to_email = []
        
        # Generate PDF for each assigned teacher
        for teacher_code in sorted(teacher_slots.keys()):
            if not teacher_slots[teacher_code]:
                continue
            
            teacher_data = self.teachers.get(str(teacher_code), {})
            prenom = teacher_data.get('prenom', '')
            nom = teacher_data.get('nom', '')
            email = teacher_data.get('email', '')
            full_name = f"Mr/Ms {prenom} {nom}" if prenom and nom else f"Enseignant #{teacher_code}"
            
            # Create PDF filename
            safe_name = f"{prenom}_{nom}".replace(' ', '_') if prenom and nom else f"Teacher_{teacher_code}"
            pdf_filename = os.path.join(output_folder, f"Affectation_{safe_name}.pdf")
            
            # Create PDF document
            doc = SimpleDocTemplate(pdf_filename, pagesize=A4,
                                rightMargin=2*cm, leftMargin=2*cm,
                                topMargin=2*cm, bottomMargin=2*cm)
            
            elements = []
            styles = getSampleStyleSheet()
            
            # Custom styles
            title_style = ParagraphStyle(
                'CustomTitle',
                parent=styles['Heading1'],
                fontSize=16,
                textColor=colors.HexColor('#1e3a8a'),
                spaceAfter=30,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            subtitle_style = ParagraphStyle(
                'CustomSubtitle',
                parent=styles['Normal'],
                fontSize=14,
                textColor=colors.HexColor('#1e3a8a'),
                spaceAfter=20,
                alignment=TA_CENTER,
                fontName='Helvetica-Bold'
            )
            
            normal_style = ParagraphStyle(
                'CustomNormal',
                parent=styles['Normal'],
                fontSize=11,
                spaceAfter=20,
                alignment=TA_LEFT
            )
            
            # Header section
            header_data = [
                ['GESTION DES EXAMENS ET\nDÉLIBÉRATIONS', 'EXD-FR-08-01'],
                ["Procédure d'exécution des épreuves", f"Date d'approbation\n{datetime.now().strftime('%d-%m-%y')}"],
                ["Liste d'affectation des surveillants", 'Page 1/1']
            ]
            
            header_table = Table(header_data, colWidths=[14*cm, 4*cm])
            header_table.setStyle(TableStyle([
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e3a8a')),
                ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e6f0ff')),
                ('FONT', (0, 0), (-1, -1), 'Helvetica-Bold', 11),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e3a8a')),
            ]))
            
            elements.append(header_table)
            elements.append(Spacer(1, 1*cm))
            
            # "Notes à" section
            elements.append(Paragraph("Notes à", subtitle_style))
            elements.append(Spacer(1, 0.3*cm))
            
            # Teacher name
            elements.append(Paragraph(f"<b>{full_name}</b>", subtitle_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # Greeting text
            greeting = """Cher (e) Collègue,<br/>
            Vous êtes prié (e) d'assurer la surveillance et (ou) la responsabilité des examens selon le calendrier ci-joint."""
            elements.append(Paragraph(greeting, normal_style))
            elements.append(Spacer(1, 0.5*cm))
            
            # Prepare schedule data
            schedule_data = [['Date', 'Heure', 'Durée']]
            
            for slot in sorted(teacher_slots[teacher_code]):
                try:
                    parts = slot.split()
                    date_str = parts[0]
                    session = parts[1].lower()
                    
                    # Format date
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    formatted_date = date_obj.strftime('%Y-%m-%d')
                    
                    # Get time
                    time = SESSION_TIMES.get(session, '08:30:00')
                    
                    # Duration
                    duration = '1.5 H'
                    
                    schedule_data.append([formatted_date, time, duration])
                except:
                    schedule_data.append([slot, 'N/A', '1.5 H'])
            
            # Create schedule table
            schedule_table = Table(schedule_data, colWidths=[6*cm, 6*cm, 6*cm])
            schedule_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 12),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('FONT', (0, 1), (-1, -1), 'Helvetica', 11),
                ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e3a8a')),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#e6f0ff'), colors.white])
            ]))
            
            elements.append(schedule_table)
            
            # Build PDF
            doc.build(elements)
            pdf_count += 1
            
            # Store for emailing if email exists
            if send_emails and email:
                pdfs_to_email.append({
                    'teacher_code': teacher_code,
                    'full_name': full_name,
                    'email': "meriem.trabelsi@etudiant-isi.utm.tn",
                    'pdf_path': pdf_filename
                })
        
        # Send emails if requested
        if send_emails and pdfs_to_email:
            # Show email configuration dialog
            email_config = self.show_email_config_dialog()
            
            if email_config:
                email_count, email_errors = self.send_pdfs_via_email(pdfs_to_email, email_config)
        
        # Show success message
        if send_emails:
            if email_errors:
                error_msg = f"{pdf_count} PDF(s) générés.\n{email_count} email(s) envoyés.\n{len(email_errors)} erreur(s):\n"
                self.show_error_message("⚠️ Export avec erreurs", error_msg)
            else:
                self.show_success_message(
                    "✅ Export et Envoi Réussis", 
                    f"{pdf_count} PDF(s) générés et {email_count} email(s) envoyés!"
                )
        else:
            self.show_success_message(
                "✅ Export Réussi", 
                f"{pdf_count} PDF(s) générés dans le dossier '{output_folder}'"
            )
        
        return pdf_count


    def show_email_config_dialog(self):
        """Affiche une boîte de dialogue pour configurer l'envoi d'emails"""
        config_window = ctk.CTkToplevel(self)
        config_window.title("📧 Configuration Email")
        config_window.geometry("600x650")
        config_window.transient(self)
        config_window.grab_set()
        
        # Header
        header = ctk.CTkFrame(config_window, fg_color="#3B82F6", corner_radius=10)
        header.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(header,
                    text="📧 Configuration de l'envoi par email",
                    font=ctk.CTkFont(size=16, weight="bold"),
                    text_color="white").pack(pady=15)
        
        # Form frame
        form_frame = ctk.CTkFrame(config_window, fg_color="transparent")
        form_frame.pack(fill="both", expand=True, padx=30, pady=10)
        
        # Email sender
        ctk.CTkLabel(form_frame, text="Votre email:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10, 5))
        email_entry = ctk.CTkEntry(form_frame, width=400, placeholder_text="exemple@gmail.com")
        email_entry.pack(pady=(0, 15))
        
        # Password
        ctk.CTkLabel(form_frame, text="Mot de passe d'application:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10, 5))
        password_entry = ctk.CTkEntry(form_frame, width=400, show="*", placeholder_text="Mot de passe")
        password_entry.pack(pady=(0, 15))
        
        # SMTP Server
        ctk.CTkLabel(form_frame, text="Serveur SMTP:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10, 5))
        smtp_entry = ctk.CTkEntry(form_frame, width=400, placeholder_text="smtp.gmail.com")
        smtp_entry.insert(0, "smtp.gmail.com")
        smtp_entry.pack(pady=(0, 15))
        
        # SMTP Port
        ctk.CTkLabel(form_frame, text="Port SMTP:", font=ctk.CTkFont(size=12, weight="bold")).pack(anchor="w", pady=(10, 5))
        port_entry = ctk.CTkEntry(form_frame, width=400, placeholder_text="587")
        port_entry.insert(0, "587")
        port_entry.pack(pady=(0, 15))
        
        # Info label
        info_text = "💡 Pour Gmail, utilisez un mot de passe d'application\n(Compte Google > Sécurité > Validation en 2 étapes > Mots de passe d'application)"
        ctk.CTkLabel(form_frame, text=info_text, font=ctk.CTkFont(size=10), 
                    text_color="gray", wraplength=400).pack(pady=10)
        
        # Result variable
        result = {}
        
        def on_send():
            if not email_entry.get() or not password_entry.get():
                self.show_error_message("❌ Erreur", "Veuillez remplir tous les champs!")
                return
            
            result['sender_email'] = email_entry.get()
            result['password'] = password_entry.get()
            result['smtp_server'] = smtp_entry.get() or "smtp.gmail.com"
            result['smtp_port'] = int(port_entry.get() or "587")
            config_window.destroy()
        
        # Buttons
        button_frame = ctk.CTkFrame(config_window, fg_color="transparent")
        button_frame.pack(pady=20)
        
        ctk.CTkButton(button_frame, text="📧 Envoyer", command=on_send,
                    width=150, height=40, fg_color="#10B981", hover_color="#059669").pack(side="left", padx=10)
        
        ctk.CTkButton(button_frame, text="❌ Annuler", command=config_window.destroy,
                    width=150, height=40, fg_color="#6B7280", hover_color="#4B5563").pack(side="left", padx=10)
        
        config_window.wait_window()
        return result if result else None


    def send_pdfs_via_email(self, pdfs_to_email, email_config):
        """Envoie les PDFs par email à chaque enseignant"""
        sent_count = 0
        errors = []
        
        sender_email = email_config['sender_email']
        password = email_config['password']
        smtp_server = email_config['smtp_server']
        smtp_port = email_config['smtp_port']
        
        try:
            # Connect to SMTP server
            server = smtplib.SMTP(smtp_server, smtp_port)
            server.starttls()
            server.login(sender_email, password)
            
            for pdf_info in pdfs_to_email:
                try:
                    # Create message
                    msg = MIMEMultipart()
                    msg['From'] = sender_email
                    # msg['To'] = "pdf_info['email']"
                    msg['To'] = "meriem.trabelsi@etudiant-isi.utm.tn"

                    msg['Subject'] = "Planning de Surveillance - Affectation des Examens"
                    
                    # Email body
                    body = f"""Bonjour {pdf_info['full_name']},

    Veuillez trouver ci-joint votre affectation pour la surveillance des examens.

    Merci de bien vouloir consulter le document PDF en pièce jointe.

    Cordialement,
    Service des Examens"""
                    
                    msg.attach(MIMEText(body, 'plain', 'utf-8'))
                    
                    # Attach PDF
                    with open(pdf_info['pdf_path'], 'rb') as attachment:
                        part = MIMEBase('application', 'octet-stream')
                        part.set_payload(attachment.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', 
                                    f"attachment; filename= {os.path.basename(pdf_info['pdf_path'])}")
                        msg.attach(part)
                    
                    # Send email
                    server.send_message(msg)
                    sent_count += 1
                    print(f"Email sent to {pdf_info['email']}")
                    
                except Exception as e:
                    error_msg = f"{pdf_info['full_name']}: {str(e)}"
                    errors.append(error_msg)
                    print(f"Error sending to {pdf_info['email']}: {e}")
            
            server.quit()
            
        except Exception as e:
            errors.append(f"Erreur de connexion SMTP: {str(e)}")
            print(f"SMTP connection error: {e}")
        
        return sent_count, errors
    def export_general_pdf(self, output_folder="exports"):
        """Exporte un PDF général avec toutes les sessions et leurs enseignants"""
        if not self.best:
            self.show_error_message("❌ Erreur", "Veuillez générer le planning d'abord!")
            return
        
        # Create output folder if it doesn't exist
        if not os.path.exists(output_folder):
            os.makedirs(output_folder)
        import glob
        old_pdfs = glob.glob(os.path.join(output_folder, "Planning_General_*.pdf"))
        for old_pdf in old_pdfs:
            try:
                os.remove(old_pdf)
                print(f"Deleted old PDF: {old_pdf}")
            except Exception as e:
                print(f"Could not delete {old_pdf}: {e}")
        # Organize data by slot
        from collections import defaultdict
        
        # Group by date and session
        sessions_data = defaultdict(lambda: defaultdict(list))
        
        for slot in sorted(self.best.keys()):
            try:
                parts = slot.split()
                date_str = parts[0]
                session = parts[1].upper()
                
                teachers = self.best[slot]
                
                # Get room assignments for this slot
                room_info = {}
                if hasattr(self, 'room_assignments') and slot in self.room_assignments:
                    for room, room_teachers in self.room_assignments[slot].items():
                        for teacher in room_teachers:
                            room_info[teacher] = room
                
                sessions_data[date_str][session].append({
                    'teachers': teachers,
                    'room_info': room_info
                })
            except:
                continue
        
        # Day names in French
        DAY_NAMES_FR = {
            'Monday': 'Lundi',
            'Tuesday': 'Mardi',
            'Wednesday': 'Mercredi',
            'Thursday': 'Jeudi',
            'Friday': 'Vendredi',
            'Saturday': 'Samedi',
            'Sunday': 'Dimanche'
        }
        
        # Session times
        SESSION_TIMES = {
            'S1': '08:30',
            'S2': '10:30',
            'S3': '12:30',
            'S4': '14:30'
        }

        # Create PDF filename
        pdf_filename = os.path.join(output_folder, f"Planning_General_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf")
        
        # Create PDF document
        doc = SimpleDocTemplate(pdf_filename, pagesize=A4,
                            rightMargin=1.5*cm, leftMargin=1.5*cm,
                            topMargin=1.5*cm, bottomMargin=1.5*cm)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=14,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=12,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=15,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        # Process each date and session
        for date_str in sorted(sessions_data.keys()):
            for session in sorted(sessions_data[date_str].keys()):
                session_info = sessions_data[date_str][session][0]
                
                # Parse date
                try:
                    date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                    day_name = DAY_NAMES_FR.get(date_obj.strftime('%A'), date_obj.strftime('%A'))
                    formatted_date = date_obj.strftime('%d/%m/%Y')
                except:
                    day_name = ""
                    formatted_date = date_str
                
                # Header section
                header_data = [
                    ['GESTION DES EXAMENS ET DÉLIBÉRATIONS', 'EXD-FR-08-01'],
                    ["Procédure d'exécution des épreuves", f"Date d'approbation\n{datetime.now().strftime('%d%m-%y')}"],
                    ["Liste d'affectation des surveillants", 'Page 1/1']
                ]
                
                header_table = Table(header_data, colWidths=[15*cm, 3*cm])
                header_table.setStyle(TableStyle([
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e3a8a')),
                    ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e6f0ff')),
                    ('FONT', (0, 0), (-1, -1), 'Helvetica-Bold', 10),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e3a8a')),
                ]))
                
                elements.append(header_table)
                elements.append(Spacer(1, 0.8*cm))
                
                # Session title
                session_time = SESSION_TIMES.get(session, 'N/A')
                session_title = f"AU : 2024-2025 - Semestre : 2 - Session : Principale<br/>Date : {formatted_date} - Séance : {session}"
                elements.append(Paragraph(session_title, subtitle_style))
                elements.append(Spacer(1, 0.5*cm))
                
                # Prepare teachers table
                table_data = [['Enseignant', 'Salle', 'Signature']]
                
                # Get all teachers for this session
                teachers = session_info['teachers']
                room_info = session_info['room_info']
                
                # Sort teachers by name
                teacher_list = []
                for teacher_code in sorted(teachers):
                    teacher_code_str = str(teacher_code)
                    if hasattr(self, 'teachers') and teacher_code_str in self.teachers:
                        teacher_data = self.teachers[teacher_code_str]
                        nom = teacher_data.get('nom', '')
                        prenom = teacher_data.get('prenom', '')
                        full_name = f"{nom} {prenom}" if nom and prenom else f"#{teacher_code}"
                    else:
                        full_name = f"#{teacher_code}"
                    
                    # Get room for this teacher
                    room = room_info.get(teacher_code, '')
                    
                    teacher_list.append((full_name, room))
                
                # Add teachers to table
                for full_name, room in sorted(teacher_list):
                    table_data.append([full_name, room, ''])
                
                # Create table
                teachers_table = Table(table_data, colWidths=[8*cm, 5*cm, 5*cm])
                teachers_table.setStyle(TableStyle([
                    # Header row
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 11),
                    ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    # Data rows
                    ('FONT', (0, 1), (-1, -1), 'Helvetica', 10),
                    ('ALIGN', (0, 1), (0, -1), 'LEFT'),
                    ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e3a8a')),
                    ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#e6f0ff')]),
                    # Minimum row height for signature space
                    ('ROWHEIGHT', (0, 1), (-1, -1), 0.8*cm)
                ]))
                
                elements.append(teachers_table)
                
                # Add page break between sessions (except for the last one)
                elements.append(PageBreak())
        
        # Remove last page break
        if elements and isinstance(elements[-1], PageBreak):
            elements.pop()
        
        # Build PDF
        doc.build(elements)
        
        # Show success message
        self.show_success_message(
            "✅ Export Réussi", 
            f"PDF général créé: {os.path.basename(pdf_filename)}"
        )
        
        return pdf_filename
    def export_csv(self):
        if not self.best:
            messagebox.showerror("Erreur", "Generez le planning d'abord!")
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
                messagebox.showinfo("Succes", f"CSV exporte:\n{file}")
            except Exception as e:
                messagebox.showerror("Erreur", f"Erreur export CSV:\n{str(e)}")

    def show_by_teacher_wrapper(self):
        try:
            show_by_teacher(self)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur affichage:\n{str(e)}")

    def show_by_day_calendar_wrapper(self):
        try:
            show_by_day_calendar(self)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur affichage:\n{str(e)}")

    def show_by_room_wrapper(self):
        try:
            show_by_room(self)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur affichage:\n{str(e)}")

    def show_planning_quality_wrapper(self):
        try:
            show_planning_quality_with_prof_resp(self)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur affichage:\n{str(e)}")
    
    def show_prof_responsable_wrapper(self):
        try:
            show_prof_responsable_details(self)
        except Exception as e:
            messagebox.showerror("Erreur", f"Erreur affichage:\n{str(e)}")

    # ========== HELPER METHODS ==========
    
    def show_success_message(self, title, message,window_size="400x200"):
        """Show modern success message"""
        msg_window = ctk.CTkToplevel(self)
        msg_window.title(title)
        msg_window.geometry(window_size)
        msg_window.configure(fg_color=self.colors['bg'])
        msg_window.transient(self)
        msg_window.grab_set()
        
        # Center window
        msg_window.update_idletasks()
        x = (msg_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (msg_window.winfo_screenheight() // 2) - (200 // 2)
        msg_window.geometry(f"+{x}+{y}")
        
        card = ctk.CTkFrame(msg_window, fg_color=self.colors['card'], corner_radius=12)
        card.pack(fill='both', expand=True, padx=20, pady=20)
        
        icon_frame = ctk.CTkFrame(card, fg_color=self.colors['success'],
                                 width=56, height=56, corner_radius=14)
        icon_frame.pack(pady=(20, 15))
        icon_frame.pack_propagate(False)
        
        ctk.CTkLabel(icon_frame, text="✅", font=("Segoe UI Emoji", 28)).place(
            relx=0.5, rely=0.5, anchor='center'
        )
        
        ctk.CTkLabel(card, text=message,
                    font=("Segoe UI", 13),
                    text_color=self.colors['text']).pack(pady=(0, 20))
        
        # ctk.CTkButton(card, text="OK",
        #              font=("Segoe UI", 13, "bold"),
        #              fg_color=self.colors['success'],
        #              hover_color=self.adjust_color(self.colors['success'], -20),
        #              height=40,
        #              width=120,
        #              corner_radius=10,
        #              command=msg_window.destroy).pack(pady=(0, 20))
        
    def show_error_message(self, title, message):
        """Show modern error message"""
        msg_window = ctk.CTkToplevel(self)
        msg_window.title(title)
        msg_window.geometry("400x200")
        msg_window.configure(fg_color=self.colors['bg'])
        msg_window.transient(self)
        msg_window.grab_set()
        
        # Center window
        msg_window.update_idletasks()
        x = (msg_window.winfo_screenwidth() // 2) - (400 // 2)
        y = (msg_window.winfo_screenheight() // 2) - (200 // 2)
        msg_window.geometry(f"+{x}+{y}")
        
        card = ctk.CTkFrame(msg_window, fg_color=self.colors['card'], corner_radius=12)
        card.pack(fill='both', expand=True, padx=20, pady=20)
        
        icon_frame = ctk.CTkFrame(card, fg_color=self.colors['error'],
                                 width=56, height=56, corner_radius=14)
        icon_frame.pack(pady=(20, 15))
        icon_frame.pack_propagate(False)
        
        ctk.CTkLabel(icon_frame, text="❌", font=("Segoe UI Emoji", 28)).place(
            relx=0.5, rely=0.5, anchor='center'
        )
        
        ctk.CTkLabel(card, text=message,
                    font=("Segoe UI", 13),
                    text_color=self.colors['text']).pack(pady=(0, 20))
        
        ctk.CTkButton(card, text="OK",
                     font=("Segoe UI", 13, "bold"),
                     fg_color=self.colors['error'],
                     hover_color=self.adjust_color(self.colors['error'], -20),
                     height=40,
                     width=120,
                     corner_radius=10,
                     command=msg_window.destroy).pack(pady=(0, 20))

if __name__ == "__main__":
    # Lancer la fenêtre de login
    # app = LoginApp()

    # def after_login():
    #     try:
    #         app.destroy()  # Ferme la fenêtre de login
    #     except:
    #         pass  # Ignorer les erreurs de destruction
            
    #     # Lancer l'application principale
    main_app = App()
    main_app.mainloop()

    # # Remplacer la méthode existante avec gestion d'erreur
    # def safe_open_main_app():
    #     try:
    #         after_login()
    #     except Exception as e:
    #         print(f"Error during login transition: {e}")
    #         # Fallback: lancer l'app principale même en cas d'erreur
    #         App().mainloop()

    # app.open_main_application = safe_open_main_app
    # app.mainloop()