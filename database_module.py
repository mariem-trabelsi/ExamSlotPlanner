"""
Module de gestion de base de données pour l'historique des plannings
"""

import sqlite3
from datetime import datetime


class DatabaseManager:
    """Gestionnaire de base de données pour l'historique des plannings"""
    
    def __init__(self, db_name="surveillance_planning.db"):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Initialise la base de données avec les tables nécessaires"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Table des plannings
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS plannings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date_creation TEXT NOT NULL,
                nom_planning TEXT,
                score_fitness REAL,
                nb_creneaux INTEGER,
                nb_enseignants INTEGER,
                commentaire TEXT
            )
        ''')
        
        # Table des assignations
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS assignations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                planning_id INTEGER,
                creneau TEXT NOT NULL,
                date_examen TEXT,
                session TEXT,
                enseignant_code TEXT,
                salle TEXT,
                FOREIGN KEY (planning_id) REFERENCES plannings(id) ON DELETE CASCADE
            )
        ''')
        
        # Table des statistiques
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS statistiques (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                planning_id INTEGER,
                enseignant_code TEXT,
                nom_complet TEXT,
                grade TEXT,
                quota INTEGER,
                nb_assignations INTEGER,
                taux_utilisation REAL,
                FOREIGN KEY (planning_id) REFERENCES plannings(id) ON DELETE CASCADE
            )
        ''')
        
        conn.commit()
        conn.close()
        print("✅ Base de données initialisée avec succès")
    
    def save_planning(self, planning_data, best_solution, teachers, slots_dict):
        """Sauvegarde un planning complet dans la base de données"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            # Insertion du planning principal
            cursor.execute('''
                INSERT INTO plannings (date_creation, nom_planning, score_fitness, 
                                     nb_creneaux, nb_enseignants, commentaire)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (
                datetime.now().isoformat(),
                planning_data.get('nom', f"Planning_{datetime.now().strftime('%Y%m%d_%H%M%S')}"),
                planning_data.get('score_fitness', 0),
                len(best_solution),
                len([t for t in teachers if teachers[t]['participe_surveillance']]),
                planning_data.get('commentaire', '')
            ))
            
            planning_id = cursor.lastrowid
            
            # Insertion des assignations
            for slot, teachers_list in best_solution.items():
                date_part, session = slot.split()
                for teacher in teachers_list:
                    cursor.execute('''
                        INSERT INTO assignations (planning_id, creneau, date_examen, 
                                                session, enseignant_code, salle)
                        VALUES (?, ?, ?, ?, ?, ?)
                    ''', (planning_id, slot, date_part, session, teacher, ''))
            
            # Calcul et insertion des statistiques
            teacher_counts = {}
            for slot in best_solution:
                for teacher in best_solution[slot]:
                    teacher_counts[teacher] = teacher_counts.get(teacher, 0) + 1
            
            for teacher, count in teacher_counts.items():
                if teacher in teachers:
                    t_data = teachers[teacher]
                    quota = t_data['quota']
                    taux = (count / quota * 100) if quota > 0 else 0
                    
                    cursor.execute('''
                        INSERT INTO statistiques (planning_id, enseignant_code, nom_complet,
                                                grade, quota, nb_assignations, taux_utilisation)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        planning_id,
                        teacher,
                        f"{t_data['nom']} {t_data['prenom']}",
                        t_data['grade'],
                        quota,
                        count,
                        taux
                    ))
            
            conn.commit()
            print(f"✅ Planning sauvegardé avec l'ID: {planning_id}")
            return planning_id
            
        except Exception as e:
            conn.rollback()
            print(f"❌ Erreur lors de la sauvegarde: {e}")
            raise e
        finally:
            conn.close()
    
    def get_all_plannings(self):
        """Récupère la liste de tous les plannings"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, date_creation, nom_planning, score_fitness, 
                   nb_creneaux, nb_enseignants, commentaire
            FROM plannings
            ORDER BY date_creation DESC
        ''')
        
        plannings = cursor.fetchall()
        conn.close()
        return plannings
    
    def get_planning_details(self, planning_id):
        """Récupère les détails d'un planning spécifique"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Récupérer les assignations
        cursor.execute('''
            SELECT creneau, date_examen, session, enseignant_code, salle
            FROM assignations
            WHERE planning_id = ?
            ORDER BY date_examen, session
        ''', (planning_id,))
        
        assignations = cursor.fetchall()
        
        # Récupérer les statistiques
        cursor.execute('''
            SELECT enseignant_code, nom_complet, grade, quota, 
                   nb_assignations, taux_utilisation
            FROM statistiques
            WHERE planning_id = ?
            ORDER BY grade, nom_complet
        ''', (planning_id,))
        
        statistiques = cursor.fetchall()
        
        conn.close()
        return {
            'assignations': assignations,
            'statistiques': statistiques
        }
    
    def delete_planning(self, planning_id):
        """Supprime un planning de la base de données"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('DELETE FROM plannings WHERE id = ?', (planning_id,))
            conn.commit()
            print(f"✅ Planning {planning_id} supprimé")
        except Exception as e:
            conn.rollback()
            print(f"❌ Erreur lors de la suppression: {e}")
            raise e
        finally:
            conn.close()
    
    def search_plannings(self, search_term):
        """Recherche des plannings par nom ou commentaire"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, date_creation, nom_planning, score_fitness, 
                   nb_creneaux, nb_enseignants, commentaire
            FROM plannings
            WHERE nom_planning LIKE ? OR commentaire LIKE ?
            ORDER BY date_creation DESC
        ''', (f'%{search_term}%', f'%{search_term}%'))
        
        plannings = cursor.fetchall()
        conn.close()
        return plannings
    
    def get_statistics(self):
        """Retourne des statistiques globales sur tous les plannings"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM plannings')
        total_plannings = cursor.fetchone()[0]
        
        cursor.execute('SELECT AVG(score_fitness) FROM plannings')
        avg_fitness = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT MAX(score_fitness) FROM plannings')
        best_fitness = cursor.fetchone()[0] or 0
        
        conn.close()
        
        return {
            'total_plannings': total_plannings,
            'average_fitness': avg_fitness,
            'best_fitness': best_fitness
        }