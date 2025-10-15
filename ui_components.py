"""
Module des composants UI réutilisables
"""

import tkinter as tk
from tkinter import ttk


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


class SimpleButton(tk.Button):
    """Bouton personnalisé avec style moderne"""
    
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
        
        # Effet hover
        self.bind('<Enter>', lambda e: self.config(bg=self.lighten(bg_color)))
        self.bind('<Leave>', lambda e: self.config(bg=bg_color))
    
    def darken(self, color):
        """Assombrit une couleur de 20 unités"""
        color = color.lstrip('#')
        r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        r, g, b = max(0, r-20), max(0, g-20), max(0, b-20)
        return f'#{r:02x}{g:02x}{b:02x}'
    
    def lighten(self, color):
        """Éclaircit une couleur de 10 unités"""
        color = color.lstrip('#')
        r, g, b = tuple(int(color[i:i+2], 16) for i in (0, 2, 4))
        r, g, b = min(255, r+10), min(255, g+10), min(255, b+10)
        return f'#{r:02x}{g:02x}{b:02x}'


class ModernEntry(tk.Entry):
    """Champ de saisie moderne avec placeholder"""
    
    def __init__(self, parent, placeholder="", **kwargs):
        super().__init__(
            parent,
            font=('Arial', 11),
            relief=tk.FLAT,
            bg=COLORS['bg'],
            fg=COLORS['text'],
            **kwargs
        )
        
        self.placeholder = placeholder
        self.placeholder_color = COLORS['text_light']
        self.default_fg_color = COLORS['text']
        
        if placeholder:
            self.put_placeholder()
        
        self.bind("<FocusIn>", self.on_focus_in)
        self.bind("<FocusOut>", self.on_focus_out)
    
    def put_placeholder(self):
        self.insert(0, self.placeholder)
        self.config(fg=self.placeholder_color)
    
    def on_focus_in(self, event):
        if self.get() == self.placeholder:
            self.delete(0, tk.END)
            self.config(fg=self.default_fg_color)
    
    def on_focus_out(self, event):
        if not self.get():
            self.put_placeholder()


class CardFrame(tk.Frame):
    """Frame avec apparence de carte (ombre et bordures arrondies simulées)"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=COLORS['card'],
            relief=tk.FLAT,
            bd=0,
            **kwargs
        )
        
        # Bordure subtile
        self.config(highlightbackground=COLORS['border'], highlightthickness=1)


class SectionHeader(tk.Frame):
    """En-tête de section avec titre et ligne de séparation"""
    
    def __init__(self, parent, title, icon="", **kwargs):
        super().__init__(parent, bg=COLORS['bg'], **kwargs)
        
        # Frame pour le titre
        title_frame = tk.Frame(self, bg=COLORS['bg'])
        title_frame.pack(fill=tk.X, pady=(10, 5))
        
        # Icône et titre
        label_text = f"{icon} {title}" if icon else title
        tk.Label(
            title_frame,
            text=label_text,
            font=('Arial', 14, 'bold'),
            bg=COLORS['bg'],
            fg=COLORS['primary']
        ).pack(side=tk.LEFT)
        
        # Ligne de séparation
        separator = tk.Frame(self, height=2, bg=COLORS['border'])
        separator.pack(fill=tk.X, pady=(0, 10))


class StatusBar(tk.Frame):
    """Barre de statut au bas de l'application"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(
            parent,
            bg=COLORS['primary_dark'],
            height=35,
            **kwargs
        )
        self.pack_propagate(False)
        
        self.label = tk.Label(
            self,
            text="Prêt",
            font=('Arial', 10),
            bg=COLORS['primary_dark'],
            fg='white',
            anchor='w'
        )
        self.label.pack(side=tk.LEFT, padx=15, fill=tk.X, expand=True)
    
    def set_status(self, text, status_type="info"):
        """
        Met à jour le texte de la barre de statut
        status_type: 'info', 'success', 'warning', 'error'
        """
        icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        }
        icon = icons.get(status_type, '')
        self.label.config(text=f"{icon} {text}")


class ModernTreeview(ttk.Treeview):
    """Treeview personnalisé avec styles modernes"""
    
    def __init__(self, parent, **kwargs):
        # Appliquer le style personnalisé
        style = ttk.Style()
        style.theme_use('clam')
        
        style.configure(
            "Modern.Treeview",
            background=COLORS['card'],
            foreground=COLORS['text'],
            rowheight=30,
            fieldbackground=COLORS['card'],
            font=('Arial', 10)
        )
        
        style.map(
            'Modern.Treeview',
            background=[('selected', COLORS['primary'])],
            foreground=[('selected', 'white')]
        )
        
        style.configure(
            "Modern.Treeview.Heading",
            background=COLORS['primary'],
            foreground='white',
            font=('Arial', 11, 'bold'),
            relief=tk.FLAT
        )
        
        super().__init__(parent, style="Modern.Treeview", **kwargs)


class ProgressWindow:
    """Fenêtre de progression pour les opérations longues"""
    
    def __init__(self, parent, title="Opération en cours"):
        self.window = tk.Toplevel(parent)
        self.window.title(title)
        self.window.geometry("600x250")
        self.window.configure(bg=COLORS['bg'])
        self.window.transient(parent)
        self.window.grab_set()
        
        # Header
        header = tk.Frame(self.window, bg=COLORS['success'], height=70)
        header.pack(fill=tk.X)
        header.pack_propagate(False)
        
        tk.Label(
            header,
            text=f"⏳ {title}",
            font=('Arial', 16, 'bold'),
            bg=COLORS['success'],
            fg='white'
        ).pack(pady=20)
        
        # Content
        content = tk.Frame(self.window, bg=COLORS['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=40, pady=20)
        
        # Barre de progression
        self.progress_bar = ttk.Progressbar(
            content,
            length=500,
            mode='determinate',
            style="Custom.Horizontal.TProgressbar"
        )
        self.progress_bar.pack(pady=15)
        
        # Label de progression
        self.progress_label = tk.Label(
            content,
            text="Initialisation...",
            font=('Arial', 12),
            bg=COLORS['bg'],
            fg=COLORS['text']
        )
        self.progress_label.pack(pady=10)
        
        # Label de statut
        self.status_label = tk.Label(
            content,
            text="Préparation...",
            font=('Arial', 10),
            bg=COLORS['bg'],
            fg=COLORS['text_light']
        )
        self.status_label.pack(pady=5)
    
    def update_progress(self, current, total, message=""):
        """Met à jour la progression"""
        progress = (current / total * 100) if total > 0 else 0
        self.progress_bar['value'] = progress
        self.progress_label.config(text=f"{current} / {total}")
        if message:
            self.status_label.config(text=message)
        self.window.update()
    
    def close(self):
        """Ferme la fenêtre"""
        self.window.destroy()


class ConfirmDialog:
    """Dialogue de confirmation personnalisé"""
    
    def __init__(self, parent, title, message):
        self.result = False
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title(title)
        self.dialog.geometry("450x200")
        self.dialog.configure(bg=COLORS['bg'])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        # Centrer la fenêtre
        self.dialog.update_idletasks()
        x = (self.dialog.winfo_screenwidth() // 2) - (450 // 2)
        y = (self.dialog.winfo_screenheight() // 2) - (200 // 2)
        self.dialog.geometry(f"+{x}+{y}")
        
        # Icône et message
        content = tk.Frame(self.dialog, bg=COLORS['bg'])
        content.pack(fill=tk.BOTH, expand=True, padx=30, pady=20)
        
        tk.Label(
            content,
            text="⚠️",
            font=('Arial', 32),
            bg=COLORS['bg']
        ).pack(pady=(10, 20))
        
        tk.Label(
            content,
            text=message,
            font=('Arial', 12),
            bg=COLORS['bg'],
            fg=COLORS['text'],
            wraplength=380,
            justify='center'
        ).pack(pady=10)
        
        # Boutons
        btn_frame = tk.Frame(self.dialog, bg=COLORS['bg'])
        btn_frame.pack(pady=20)
        
        SimpleButton(
            btn_frame,
            text="Oui",
            command=self.on_yes,
            bg_color=COLORS['success'],
            width=10
        ).pack(side=tk.LEFT, padx=10)
        
        SimpleButton(
            btn_frame,
            text="Non",
            command=self.on_no,
            bg_color=COLORS['danger'],
            width=10
        ).pack(side=tk.LEFT, padx=10)
        
        self.dialog.protocol("WM_DELETE_WINDOW", self.on_no)
    
    def on_yes(self):
        self.result = True
        self.dialog.destroy()
    
    def on_no(self):
        self.result = False
        self.dialog.destroy()
    
    def show(self):
        """Affiche le dialogue et attend la réponse"""
        self.dialog.wait_window()
        return self.result


class InfoCard(CardFrame):
    """Carte d'information avec icône, titre et valeur"""
    
    def __init__(self, parent, icon, title, value, color=None, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.config(padx=20, pady=15)
        
        if color is None:
            color = COLORS['primary']
        
        # Icône
        tk.Label(
            self,
            text=icon,
            font=('Arial', 32),
            bg=COLORS['card'],
            fg=color
        ).pack(pady=(0, 10))
        
        # Titre
        tk.Label(
            self,
            text=title,
            font=('Arial', 10),
            bg=COLORS['card'],
            fg=COLORS['text_light']
        ).pack()
        
        # Valeur
        self.value_label = tk.Label(
            self,
            text=str(value),
            font=('Arial', 24, 'bold'),
            bg=COLORS['card'],
            fg=color
        )
        self.value_label.pack(pady=(5, 0))
    
    def update_value(self, new_value):
        """Met à jour la valeur affichée"""
        self.value_label.config(text=str(new_value))


class SearchBar(tk.Frame):
    """Barre de recherche avec icône"""
    
    def __init__(self, parent, on_search_callback=None, **kwargs):
        super().__init__(parent, bg=COLORS['card'], **kwargs)
        
        self.on_search_callback = on_search_callback
        
        # Icône de recherche
        tk.Label(
            self,
            text="🔍",
            font=('Arial', 12),
            bg=COLORS['card']
        ).pack(side=tk.LEFT, padx=10)
        
        # Champ de recherche
        self.search_var = tk.StringVar()
        self.search_entry = ModernEntry(
            self,
            textvariable=self.search_var,
            placeholder="Rechercher..."
        )
        self.search_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=5, ipady=5)
        
        # Trace pour recherche en temps réel
        if on_search_callback:
            self.search_var.trace('w', lambda *args: on_search_callback(self.search_var.get()))
        
        # Bouton effacer
        self.clear_btn = tk.Button(
            self,
            text="✕",
            font=('Arial', 10),
            bg=COLORS['card'],
            fg=COLORS['text_light'],
            relief=tk.FLAT,
            cursor='hand2',
            command=self.clear_search
        )
        self.clear_btn.pack(side=tk.LEFT, padx=10)
    
    def clear_search(self):
        """Efface le contenu de la recherche"""
        self.search_var.set("")
        self.search_entry.focus()
    
    def get_text(self):
        """Retourne le texte de recherche"""
        return self.search_var.get()


class Notification:
    """Notification toast style"""
    
    @staticmethod
    def show(parent, message, duration=3000, notification_type="info"):
        """
        Affiche une notification temporaire
        notification_type: 'info', 'success', 'warning', 'error'
        """
        colors = {
            'info': COLORS['secondary'],
            'success': COLORS['success'],
            'warning': COLORS['warning'],
            'error': COLORS['danger']
        }
        
        icons = {
            'info': 'ℹ️',
            'success': '✅',
            'warning': '⚠️',
            'error': '❌'
        }
        
        bg_color = colors.get(notification_type, COLORS['secondary'])
        icon = icons.get(notification_type, '')
        
        # Créer la notification
        notif = tk.Toplevel(parent)
        notif.overrideredirect(True)
        notif.configure(bg=bg_color)
        
        # Positionner en haut à droite
        notif.update_idletasks()
        screen_width = notif.winfo_screenwidth()
        x = screen_width - 350
        y = 50
        notif.geometry(f"320x80+{x}+{y}")
        
        # Contenu
        content = tk.Frame(notif, bg=bg_color)
        content.pack(fill=tk.BOTH, expand=True, padx=15, pady=15)
        
        tk.Label(
            content,
            text=icon,
            font=('Arial', 20),
            bg=bg_color,
            fg='white'
        ).pack(side=tk.LEFT, padx=(0, 10))
        
        tk.Label(
            content,
            text=message,
            font=('Arial', 11),
            bg=bg_color,
            fg='white',
            wraplength=250,
            justify='left'
        ).pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Fermer automatiquement
        notif.after(duration, notif.destroy)
        
        # Animation d'entrée (optionnelle)
        notif.attributes('-alpha', 0.0)
        for i in range(1, 11):
            notif.attributes('-alpha', i / 10)
            notif.update()
            notif.after(20)


def setup_styles():
    """Configure les styles globaux pour ttk"""
    style = ttk.Style()
    style.theme_use('clam')
    
    # Style pour Treeview
    style.configure(
        "Custom.Treeview",
        background=COLORS['card'],
        foreground=COLORS['text'],
        rowheight=30,
        fieldbackground=COLORS['card'],
        font=('Arial', 10)
    )
    
    style.map(
        'Custom.Treeview',
        background=[('selected', COLORS['primary'])],
        foreground=[('selected', 'white')]
    )
    
    style.configure(
        "Custom.Treeview.Heading",
        background=COLORS['primary'],
        foreground='white',
        font=('Arial', 11, 'bold'),
        relief=tk.FLAT
    )
    
    # Style pour Progressbar
    style.configure(
        "Custom.Horizontal.TProgressbar",
        background=COLORS['success'],
        troughcolor=COLORS['border'],
        borderwidth=0,
        thickness=20
    )
    
    # Style pour Scrollbar
    style.configure(
        "Custom.Vertical.TScrollbar",
        background=COLORS['border'],
        troughcolor=COLORS['bg'],
        borderwidth=0,
        arrowcolor=COLORS['primary']
    )


# Utilitaires de couleur
def hex_to_rgb(hex_color):
    """Convertit une couleur hex en RGB"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def rgb_to_hex(r, g, b):
    """Convertit RGB en hex"""
    return f'#{r:02x}{g:02x}{b:02x}'


def lighten_color(hex_color, factor=0.2):
    """Éclaircit une couleur"""
    r, g, b = hex_to_rgb(hex_color)
    r = min(255, int(r + (255 - r) * factor))
    g = min(255, int(g + (255 - g) * factor))
    b = min(255, int(b + (255 - b) * factor))
    return rgb_to_hex(r, g, b)


def darken_color(hex_color, factor=0.2):
    """Assombrit une couleur"""
    r, g, b = hex_to_rgb(hex_color)
    r = max(0, int(r * (1 - factor)))
    g = max(0, int(g * (1 - factor)))
    b = max(0, int(b * (1 - factor)))
    return rgb_to_hex(r, g, b)