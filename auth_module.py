"""
Module d'authentification pour le système de gestion des surveillances
Contient les classes LoginManager et ModernLoginApp
"""

import tkinter as tk
from tkinter import messagebox
import hashlib
import json
import os
from datetime import datetime

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