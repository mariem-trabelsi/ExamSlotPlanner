
import customtkinter as ctk
from tkinter import messagebox
import bcrypt
import json
import os
from pathlib import Path
from PIL import Image, ImageTk
import requests
from io import BytesIO

class AuthManager:
    """Gestionnaire d'authentification avec hashage bcrypt"""
    
    def __init__(self):
        self.db_file = Path("admin_credentials.json")
        self.load_credentials()
    
    def load_credentials(self):
        """Charge les identifiants depuis le fichier JSON"""
        if self.db_file.exists():
            with open(self.db_file, 'r', encoding='utf-8') as f:
                self.credentials = json.load(f)
        else:
            # Créer un administrateur par défaut
            self.credentials = {}
            self.add_admin("admin", "admin123")  # À changer en production!
    
    def save_credentials(self):
        """Sauvegarde les identifiants dans le fichier JSON"""
        with open(self.db_file, 'w', encoding='utf-8') as f:
            json.dump(self.credentials, f, indent=4)
    
    def hash_password(self, password: str) -> str:
        """Hash un mot de passe avec bcrypt"""
        salt = bcrypt.gensalt(rounds=12)
        hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
        return hashed.decode('utf-8')
    
    def verify_password(self, password: str, hashed: str) -> bool:
        """Vérifie un mot de passe contre son hash"""
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    
    def add_admin(self, username: str, password: str) -> bool:
        """Ajoute un nouvel administrateur"""
        if username in self.credentials:
            return False
        
        self.credentials[username] = {
            'password_hash': self.hash_password(password),
            'role': 'admin',
            'active': True
        }
        self.save_credentials()
        return True
    
    def authenticate(self, username: str, password: str) -> dict:
        """Authentifie un utilisateur"""
        if username not in self.credentials:
            return {'success': False, 'message': 'Identifiant incorrect'}
        
        user_data = self.credentials[username]
        
        if not user_data.get('active', False):
            return {'success': False, 'message': 'Compte désactivé'}
        
        if self.verify_password(password, user_data['password_hash']):
            return {
                'success': True, 
                'message': 'Connexion réussie',
                'username': username,
                'role': user_data.get('role', 'admin')
            }
        else:
            return {'success': False, 'message': 'Mot de passe incorrect'}
    
    def change_password(self, username: str, old_password: str, new_password: str) -> dict:
        """Change le mot de passe d'un utilisateur"""
        if username not in self.credentials:
            return {'success': False, 'message': 'Utilisateur introuvable'}
        
        user_data = self.credentials[username]
        
        if not self.verify_password(old_password, user_data['password_hash']):
            return {'success': False, 'message': 'Ancien mot de passe incorrect'}
        
        user_data['password_hash'] = self.hash_password(new_password)
        self.save_credentials()
        return {'success': True, 'message': 'Mot de passe modifié avec succès'}


class LoginApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        
        # Initialiser le gestionnaire d'authentification
        self.auth_manager = AuthManager()
        self.current_user = None
        
        # Configuration de la fenêtre
        self.title("Portail Administratif")
        self.geometry("1200x700")
        
        # Configuration du thème
        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")
        
        # Empêcher le redimensionnement
        self.resizable(True, True)
        
        # Création du conteneur principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # Panneau gauche (bleu)
        self.create_left_panel()
        
        # Panneau droit (formulaire)
        self.create_right_panel()
    
    def create_left_panel(self):
        # Frame gauche avec fond bleu
        left_frame = ctk.CTkFrame(self, fg_color="#1e3a8a", corner_radius=0)
        left_frame.grid(row=0, column=0, sticky="nsew")
        
        # Conteneur centré
        content_frame = ctk.CTkFrame(left_frame, fg_color="transparent")
        content_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Icône/Logo
        self.display_logo(content_frame)
        
        # Titre
        title = ctk.CTkLabel(content_frame, 
                            text="Portail Administratif",
                            font=("Arial", 36, "bold"),
                            text_color="white")
        title.pack(pady=(0, 20))
        
        # Sous-titre
        subtitle = ctk.CTkLabel(content_frame,
                               text="Accédez à vos services universitaires",
                               font=("Arial", 18),
                               text_color="white")
        subtitle.pack(pady=(0, 30))
        
        # Services
        services = ctk.CTkLabel(content_frame,
                               text="Notes • Emploi du temps • Bibliothèque • Services",
                               font=("Arial", 14),
                               text_color="#d1d5db")
        services.pack()
        
        # Badge sécurisé
        security_badge = ctk.CTkLabel(content_frame,
                                     text="🔒 Connexion sécurisée (Bcrypt)",
                                     font=("Arial", 12, "bold"),
                                     text_color="#86efac")
        security_badge.pack(pady=(40, 0))
    
    def display_logo(self, parent_frame):
        """Affiche le logo de l'administration"""
        logo_path = Path("logo_isi--.png")  # Chemin vers votre logo
        
        if logo_path.exists():
            try:
                # Charger et redimensionner l'image
                logo_image = Image.open(logo_path)
                logo_image = logo_image.resize((120, 120), Image.Resampling.LANCZOS)
                
                # Créer un cadre circulaire (optionnel)
                logo_ctk = ctk.CTkImage(light_image=logo_image, 
                                       dark_image=logo_image,
                                       size=(120, 120))
                
                logo_label = ctk.CTkLabel(parent_frame, 
                                         image=logo_ctk,
                                         text="")
                logo_label.pack(pady=(0, 30))
                
            except Exception as e:
                print(f"Erreur lors du chargement du logo: {e}")
                self.display_default_icon(parent_frame)
        else:
            # Si le logo n'existe pas, afficher l'icône par défaut
            self.display_default_icon(parent_frame)
    
    def display_default_icon(self, parent_frame):
        """Affiche l'icône par défaut si le logo n'est pas trouvé"""
        icon_frame = ctk.CTkFrame(parent_frame, fg_color="white", 
                                 width=120, height=120, corner_radius=60)
        icon_frame.pack(pady=(0, 30))
        
        icon_label = ctk.CTkLabel(icon_frame, text="🎓", font=("Arial", 60))
        icon_label.place(relx=0.5, rely=0.5, anchor="center")
    
    def create_right_panel(self):
        # Frame droite avec fond blanc
        right_frame = ctk.CTkFrame(self, fg_color="white", corner_radius=0)
        right_frame.grid(row=0, column=1, sticky="nsew")
        
        # Conteneur du formulaire
        form_frame = ctk.CTkFrame(right_frame, fg_color="transparent")
        form_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Bouton retour
        back_btn = ctk.CTkButton(form_frame,
                                text="← Retour",
                                font=("Arial", 14),
                                fg_color="transparent",
                                text_color="gray",
                                hover_color="#f0f0f0",
                                width=100,
                                command=self.go_back)
        back_btn.pack(anchor="w", pady=(0, 30))
        
        # Titre Connexion
        title = ctk.CTkLabel(form_frame,
                            text="Connexion Administrateur",
                            font=("Arial", 32, "bold"),
                            text_color="#1e293b")
        title.pack(anchor="w", pady=(0, 10))
        
        # Sous-titre
        subtitle = ctk.CTkLabel(form_frame,
                               text="Accès réservé au personnel administratif",
                               font=("Arial", 14),
                               text_color="gray")
        subtitle.pack(anchor="w", pady=(0, 30))
        
        # Identifiant administrateur
        id_label = ctk.CTkLabel(form_frame,
                               text="Identifiant administrateur",
                               font=("Arial", 14, "bold"),
                               text_color="#1e293b")
        id_label.pack(anchor="w", pady=(0, 8))
        
        self.id_entry = ctk.CTkEntry(form_frame,
                                    placeholder_text="Nom d'utilisateur",
                                    font=("Arial", 14),
                                    width=400,
                                    height=45,
                                    border_color="#e2e8f0",
                                    fg_color="white")
        self.id_entry.pack(pady=(0, 20))
        
        # Lier la touche Entrée pour passer au champ suivant
        self.id_entry.bind('<Return>', lambda e: self.pass_entry.focus())
        
        # Mot de passe
        pass_label = ctk.CTkLabel(form_frame,
                                 text="Mot de passe",
                                 font=("Arial", 14, "bold"),
                                 text_color="#1e293b")
        pass_label.pack(anchor="w", pady=(0, 8))
        
        self.pass_entry = ctk.CTkEntry(form_frame,
                                      placeholder_text="Entrez votre mot de passe",
                                      font=("Arial", 14),
                                      width=400,
                                      height=45,
                                      border_color="#e2e8f0",
                                      fg_color="white",
                                      show="•")
        self.pass_entry.pack(pady=(0, 15))
        
        # Lier la touche Entrée pour soumettre le formulaire
        self.pass_entry.bind('<Return>', lambda e: self.login())
        
        # Options (Se souvenir / Mot de passe oublié)
        options_frame = ctk.CTkFrame(form_frame, fg_color="transparent")
        options_frame.pack(fill="x", pady=(0, 25))
        
        self.remember_var = ctk.BooleanVar()
        remember_check = ctk.CTkCheckBox(options_frame,
                                        text="Se souvenir de moi",
                                        font=("Arial", 13),
                                        variable=self.remember_var,
                                        text_color="gray")
        remember_check.pack(side="left")
        
        forgot_btn = ctk.CTkButton(options_frame,
                                  text="Changer le mot de passe",
                                  font=("Arial", 13),
                                  fg_color="transparent",
                                  text_color="#2563eb",
                                  hover_color="#f0f0f0",
                                  width=50,
                                  command=self.change_password_dialog)
        forgot_btn.pack(side="right")
        
        # Bouton Se connecter
        self.login_btn = ctk.CTkButton(form_frame,
                                 text="Se connecter →",
                                 font=("Arial", 15, "bold"),
                                 fg_color="#1e3a8a",
                                 hover_color="#1e40af",
                                 width=400,
                                 height=45,
                                 corner_radius=8,
                                 command=self.login)
        self.login_btn.pack(pady=(0, 20))
        
        # Aide
        help_frame = ctk.CTkFrame(form_frame, fg_color="#eff6ff", corner_radius=8)
        help_frame.pack(fill="x", padx=5, pady=(10, 0))
        
        help_text = ctk.CTkLabel(help_frame,
                                text="ℹ Aide : Contactez le service informatique pour\ntoute difficulté de connexion.",
                                font=("Arial", 12),
                                text_color="#3b82f6",
                                justify="left")
        help_text.pack(padx=15, pady=12)
        
    def login(self):
        """Authentification avec hashage sécurisé"""
        username = self.id_entry.get().strip()
        password = self.pass_entry.get()
        
        if not username or not password:
            messagebox.showwarning("Attention", "Veuillez remplir tous les champs")
            return
        
        # Désactiver le bouton pendant l'authentification
        self.login_btn.configure(state="disabled", text="Authentification...")
        self.update()
        
        # Authentifier l'utilisateur
        result = self.auth_manager.authenticate(username, password)
        
        if result['success']:
            self.current_user = {
                'username': result['username'],
                'role': result['role']
            }
            messagebox.showinfo("Succès", f"Bienvenue {result['username']}!\n\nVous êtes connecté en tant qu'{result['role']}.")
            # Ici vous pouvez ouvrir la fenêtre principale de l'application
            self.open_main_application()
        else:
            messagebox.showerror("Échec de connexion", result['message'])
            self.pass_entry.delete(0, 'end')
        
        # Réactiver le bouton
        self.login_btn.configure(state="normal", text="Se connecter →")
    
    def change_password_dialog(self):
        """Ouvre une fenêtre pour changer le mot de passe"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Changer le mot de passe")
        dialog.geometry("450x400")
        dialog.resizable(True, True)
        
        # Centrer la fenêtre
        dialog.transient(self)
        dialog.grab_set()
        
        # Titre
        title = ctk.CTkLabel(dialog,
                            text="Modifier le mot de passe",
                            font=("Arial", 24, "bold"))
        title.pack(pady=(30, 20))
        
        # Username
        username_label = ctk.CTkLabel(dialog, text="Nom d'utilisateur", font=("Arial", 12, "bold"))
        username_label.pack(anchor="w", padx=25, pady=(10, 5))
        
        username_entry = ctk.CTkEntry(dialog, width=400, height=40)
        username_entry.pack(padx=25)
        
        # Ancien mot de passe
        old_pass_label = ctk.CTkLabel(dialog, text="Ancien mot de passe", font=("Arial", 12, "bold"))
        old_pass_label.pack(anchor="w", padx=25, pady=(15, 5))
        
        old_pass_entry = ctk.CTkEntry(dialog, width=400, height=40, show="•")
        old_pass_entry.pack(padx=25)
        
        # Nouveau mot de passe
        new_pass_label = ctk.CTkLabel(dialog, text="Nouveau mot de passe", font=("Arial", 12, "bold"))
        new_pass_label.pack(anchor="w", padx=25, pady=(15, 5))
        
        new_pass_entry = ctk.CTkEntry(dialog, width=400, height=40, show="•")
        new_pass_entry.pack(padx=25)
        
        def submit_change():
            username = username_entry.get().strip()
            old_pass = old_pass_entry.get()
            new_pass = new_pass_entry.get()
            
            if not username or not old_pass or not new_pass:
                messagebox.showwarning("Attention", "Veuillez remplir tous les champs")
                return
            
            if len(new_pass) < 6:
                messagebox.showwarning("Attention", "Le nouveau mot de passe doit contenir au moins 6 caractères")
                return
            
            result = self.auth_manager.change_password(username, old_pass, new_pass)
            
            if result['success']:
                messagebox.showinfo("Succès", result['message'])
                dialog.destroy()
            else:
                messagebox.showerror("Erreur", result['message'])
        
        # Bouton Valider
        submit_btn = ctk.CTkButton(dialog,
                                   text="Modifier le mot de passe",
                                   font=("Arial", 14, "bold"),
                                   fg_color="#1e3a8a",
                                   hover_color="#1e40af",
                                   width=400,
                                   height=45,
                                   command=submit_change)
        submit_btn.pack(pady=25, padx=25)
    
    
    def go_back(self):
        """Retour à la page précédente"""
        if messagebox.askyesno("Quitter", "Voulez-vous quitter l'application ?"):
            self.quit()

if __name__ == "__main__":
    app = LoginApp()
    app.mainloop()