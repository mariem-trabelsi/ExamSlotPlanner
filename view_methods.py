"""
Méthodes de visualisation pour l'interface utilisateur
"""
import numpy as np
from datetime import datetime
from genetic_algorithm import (
    is_valid_teacher, get_teacher_slots, check_gap_violations,
    check_responsable_presence, calculate_quota_violations, fitness, SESSION_TIMES
)

def show_by_teacher(app):
    """Affiche la vue par enseignant"""
    if not app.best:
        from tkinter import messagebox
        messagebox.showerror("❌ Erreur", "Générez le planning d'abord!")
        return
    
    teacher_slots = {teacher: [] for teacher in app.teachers}
    for slot in app.best:
        valid_teachers = [t for t in app.best[slot] if is_valid_teacher(t)]
        for teacher in valid_teachers:
            if teacher in teacher_slots:
                teacher_slots[teacher].append(slot)
    
    data = []
    for teacher in sorted(app.teachers.keys()):
        t_data = app.teachers[teacher]
        num_gardes = len(teacher_slots[teacher])
        violated_wishes = [slot for slot in teacher_slots[teacher]
                         if slot in t_data.get('indispo', [])]
        
        if violated_wishes:
            voeux_status = f"❌ {len(violated_wishes)} violé(s)"
            tag = "voeux_violes"
        elif t_data.get('indispo'):
            voeux_status = "✅ Respectés"
            tag = "voeux_ok"
        else:
            voeux_status = "Aucun vœu"
            tag = ""
        
        quota = t_data.get('quota', 0)
        if num_gardes > quota:
            tag = "over_quota"
        elif num_gardes == 0 and t_data.get('participe_surveillance', False):
            tag = "unassigned"
        
        data.append((
            teacher, 
            t_data.get('nom', ''), 
            t_data.get('prenom', ''), 
            t_data.get('grade', ''), 
            quota,
            f"{num_gardes} {'⚠️' if num_gardes > quota else '✓'}",
            ", ".join(sorted(teacher_slots[teacher])) if teacher_slots[teacher] else "Non assigné",
            ", ".join(sorted(t_data.get('indispo', []))) if t_data.get('indispo') else "Aucun",
            voeux_status, 
            tag
        ))
    
    app.view_data = data
    app.tree["columns"] = ("Code", "Nom", "Prénom", "Grade", "Quota",
                          "Assigné", "Créneaux", "Vœux", "Statut Vœux")
    cols = {
        "Code": 80, "Nom": 120, "Prénom": 120, "Grade": 60, "Quota": 60,
        "Assigné": 80, "Créneaux": 300, "Vœux": 200, "Statut Vœux": 120
    }
    for col, width in cols.items():
        app.tree.heading(col, text=col)
        app.tree.column(col, width=width)
    
    app.populate_flat_view()
    
    app.tree.tag_configure("over_quota", background="#ffcccc")
    app.tree.tag_configure("unassigned", background="#ffffcc")
    app.tree.tag_configure("voeux_violes", background="#ff9999")
    app.tree.tag_configure("voeux_ok", background="#ccffcc")
    
    app.current_view = "teacher"
    app.view_type_label.config(text="Vue actuelle: Par Enseignant")
    app.configure_action_buttons()

def show_by_day_calendar(app):
    """Affiche la vue calendrier par jour"""
    if not app.best:
        from tkinter import messagebox
        messagebox.showerror("❌ Erreur", "Générez le planning d'abord!")
        return
    
    app.tree.delete(*app.tree.get_children())
    app.tree["columns"] = ("Session/Salle", "Enseignants")
    app.tree.heading("Session/Salle", text="Session / Salle")
    app.tree.heading("Enseignants", text="Enseignants")
    app.tree.column("Session/Salle", width=250)
    app.tree.column("Enseignants", width=800)
    
    days_data = {}
    for slot in sorted(app.best.keys()):
        date_str, session = slot.split()
        if date_str not in days_data:
            days_data[date_str] = {s: {} for s in ["S1", "S2", "S3", "S4"]}
        for room, teachers in app.room_assignments[slot].items():
            valid_teachers = [t for t in teachers if is_valid_teacher(t)]
            days_data[date_str][session][room] = valid_teachers
    
    hide_rooms = app.hide_rooms_var.get()
    
    for date_str in sorted(days_data.keys()):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        date_display = date_obj.strftime('%d/%m/%Y (%A)')
        day_iid = None
        
        for session in ["S1", "S2", "S3", "S4"]:
            session_display = f"{session} ({SESSION_TIMES[session]})"
            session_iid = None
            
            if hide_rooms:
                all_teachers = []
                for room_teachers in days_data[date_str][session].values():
                    all_teachers.extend(room_teachers)
                teachers_str = ", ".join(all_teachers) if all_teachers else "-"
                
                if app.current_filter in teachers_str.lower() or not app.current_filter:
                    if not day_iid:
                        day_iid = app.tree.insert("", "end", values=(date_display, ""), 
                                                 open=True, tags=("day_header",))
                    session_iid = app.tree.insert(day_iid, "end", values=(session_display, ""), 
                                                 open=True, tags=("session_header",))
                    app.tree.insert(session_iid, "end", values=("", teachers_str))
            else:
                for room in sorted(days_data[date_str][session].keys()):
                    teachers = days_data[date_str][session][room]
                    teachers_str = ", ".join(teachers) if teachers else "-"
                    room_display = f"Salle {room}"
                    search_text = (room_display + " " + teachers_str).lower()
                    
                    if app.current_filter in search_text or not app.current_filter:
                        if not day_iid:
                            day_iid = app.tree.insert("", "end", values=(date_display, ""), 
                                                     open=True, tags=("day_header",))
                        if not session_iid:
                            session_iid = app.tree.insert(day_iid, "end", 
                                                         values=(session_display, ""), 
                                                         open=True, tags=("session_header",))
                        app.tree.insert(session_iid, "end", values=(room_display, teachers_str), 
                                      tags=("room_item",))
    
    app.tree.tag_configure("day_header", font=("Arial", 14, "bold"), background="#e3f2fd")
    app.tree.tag_configure("session_header", font=("Arial", 12, "bold"), background="#f0f8ff")
    app.tree.tag_configure("room_item", font=("Arial", 10))
    
    app.current_view = "calendar"
    app.view_type_label.config(text="Vue actuelle: Calendrier par Jour")
    app.configure_action_buttons()

def show_by_room(app):
    """Affiche la vue par salle"""
    if not app.best:
        from tkinter import messagebox
        messagebox.showerror("❌ Erreur", "Générez le planning d'abord!")
        return
    
    app.tree["columns"] = ("Créneau", "Salle", "Nb Profs", "Enseignants")
    app.tree.heading("Créneau", text="Créneau")
    app.tree.heading("Salle", text="Salle")
    app.tree.heading("Nb Profs", text="Nb Profs")
    app.tree.heading("Enseignants", text="Enseignants")
    app.tree.column("Créneau", width=200)
    app.tree.column("Salle", width=100)
    app.tree.column("Nb Profs", width=100)
    app.tree.column("Enseignants", width=600)
    
    data = []
    for slot in sorted(app.best.keys()):
        for room in sorted(app.room_assignments[slot].keys()):
            teachers = app.room_assignments[slot][room]
            valid_teachers = [t for t in teachers if is_valid_teacher(t)]
            nb = len(valid_teachers)
            tag = "optimal" if nb == 2 else "acceptable" if nb <= 4 else "problem"
            data.append((slot, room, 
                        f"{nb} {'✓' if nb == 2 else '⚠️' if nb > 4 else ''}", 
                        ", ".join(valid_teachers), tag))
    
    app.view_data = data
    app.populate_flat_view()
    
    app.tree.tag_configure("optimal", background="#ccffcc")
    app.tree.tag_configure("acceptable", background="#ffffcc")
    app.tree.tag_configure("problem", background="#ffcccc")
    
    app.current_view = "room"
    app.view_type_label.config(text="Vue actuelle: Par Salle")
    app.configure_action_buttons()

def show_planning_quality(app):
    """Affiche le rapport de qualité du planning"""
    if not app.best:
        from tkinter import messagebox
        messagebox.showerror("❌ Erreur", "Générez le planning d'abord!")
        return
    
    slots_dict = {slot: data for slot, data in app.slots}
    fitness_score = fitness(app.best, app.teachers, slots_dict)
    
    # Calculer les violations
    counts = {}
    for slot in app.best:
        valid_teachers = [t for t in app.best[slot] if is_valid_teacher(t)]
        for e in valid_teachers:
            counts[e] = counts.get(e, 0) + 1
    
    violations = {
        'min_profs': 0, 'max_profs': 0, 'voeux_violes': 0, 
        'voeux_prioritaires_violes': 0, 'duplicates': 0, 
        'one_gap': 0, 'two_gaps': 0
    }
    
    # Calculer les dépassements de quota (CORRIGÉ)
    total_excess, quota_violations_count = calculate_quota_violations(counts, app.teachers)
    
    for slot in app.best:
        valid_teachers = [t for t in app.best[slot] if is_valid_teacher(t)]
        unique = len(set(valid_teachers))
        slot_data = slots_dict[slot]
        room_count = slot_data.get('room_count', 1)
        min_needed = 2 * room_count
        max_needed = 4 * room_count
        
        if unique < min_needed:
            violations['min_profs'] += (min_needed - unique)
        if unique > max_needed:
            violations['max_profs'] += (unique - max_needed)
        if len(valid_teachers) != unique:
            violations['duplicates'] += (len(valid_teachers) - unique)
        
        for e in valid_teachers:
            if e in app.teachers:
                if slot in app.teachers[e].get('indispo', []):
                    violations['voeux_violes'] += 1
                    priority = app.teachers[e].get('wish_priority', {}).get(slot, 1.0)
                    if priority > 1.5:
                        violations['voeux_prioritaires_violes'] += 1
    
    # Vérifier présence des profs responsables (CORRIGÉ)
    prof_resp_present, prof_resp_absent = check_responsable_presence(app.best, slots_dict, app.teachers)
    
    # Vérifier les séances creuses
    gap_violations = check_gap_violations(app.best, app.teachers, slots_dict)
    violations['one_gap'] = gap_violations['one_gap']
    violations['two_gaps'] = gap_violations['two_gaps']
    
    # Statistiques par grade
    grade_stats = {}
    for grade in set(t.get('grade', '') for t in app.teachers.values() if t.get('participe_surveillance', False)):
        if not grade:
            continue
        grade_counts = [counts.get(e, 0) for e in app.teachers
                      if app.teachers[e].get('grade') == grade]
        if grade_counts:
            grade_stats[grade] = {
                'min': min(grade_counts), 
                'max': max(grade_counts),
                'avg': np.mean(grade_counts), 
                'std': np.std(grade_counts)
            }
    
    # Construire les données pour l'affichage
    app.tree["columns"] = ("Métrique", "Valeur", "Statut")
    for col in ["Métrique", "Valeur", "Statut"]:
        app.tree.heading(col, text=col)
    app.tree.column("Métrique", width=400)
    app.tree.column("Valeur", width=150)
    app.tree.column("Statut", width=200)
    
    data = []
    quality = "🟢 Excellent" if fitness_score > -100 else \
             "🟡 Acceptable" if fitness_score > -500 else "🔴 À améliorer"
    data.append(("📊 SCORE GLOBAL", f"{fitness_score:.0f}", quality, "header"))
    data.append(("", "", "", ""))
    data.append(("=== ⚠️ CONTRAINTES RIGIDES ===", "", "", "header"))
    
    constraints = {
        'min_profs': "Minimum 2 profs/salle",
        'max_profs': "Maximum 4 profs/salle",
        'duplicates': "Doublons"
    }
    
    for key, label in constraints.items():
        count = violations[key]
        status = "✅ OK" if count == 0 else f"❌ {count} violation(s)"
        tag = "ok" if count == 0 else "error"
        data.append((label, count, status, tag))
    
    # DÉPASSEMENTS DE QUOTA (CORRIGÉ)
    data.append(("Dépassements de quota (total)", total_excess, 
                f"{'✅ OK' if total_excess == 0 else f'❌ {quota_violations_count} enseignant(s)'}",
                "ok" if total_excess == 0 else "error"))
    
    # PRIORITÉ DES VŒUX
    data.append(("", "", "", ""))
    data.append(("=== 🎯 PRIORITÉ DES VŒUX ===", "", "", "header"))
    voeux_prioritaires = violations['voeux_prioritaires_violes']
    voeux_normaux = violations['voeux_violes'] - voeux_prioritaires
    status_prio = "✅ Bien respectés" if voeux_prioritaires == 0 else f"⚠️ {voeux_prioritaires} violé(s)"
    tag_prio = "ok" if voeux_prioritaires == 0 else "warning"
    data.append(("Vœux prioritaires violés (premiers arrivés)", voeux_prioritaires, status_prio, tag_prio))
    data.append(("Vœux normaux violés (arrivés tard)", voeux_normaux,
                f"{voeux_normaux} violé(s)" if voeux_normaux > 0 else "✅ OK", ""))
    
    # CONTINUITÉ DES SÉANCES
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
    
    # PROFS RESPONSABLES (CORRIGÉ)
    data.append(("", "", "", ""))
    data.append(("=== 👨‍🏫 PROFS RESPONSABLES ===", "", "", "header"))
    total_resp = prof_resp_present + prof_resp_absent
    if total_resp > 0:
        taux_presence = (prof_resp_present / total_resp) * 100
        status_resp = f"🟢 Excellent" if taux_presence >= 90 else \
                     f"🟡 Acceptable" if taux_presence >= 70 else "🔴 Insuffisant"
        data.append(("Profs responsables présents",
                    f"{prof_resp_present}/{total_resp}",
                    f"{taux_presence:.1f}% {status_resp}", ""))
        data.append(("Profs responsables absents", prof_resp_absent,
                    "❌" if prof_resp_absent > 0 else "✅", ""))
    else:
        data.append(("Profs responsables identifiés", 0, "⚠️ Aucun", "warning"))
    
    # ÉQUITÉ PAR GRADE
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
    
    # CONVERGENCE
    if app.best_fitness_history:
        data.append(("", "", "", ""))
        data.append(("=== 📈 CONVERGENCE ===", "", "", "header"))
        total_gen = len(app.best_fitness_history)
        improvement = app.best_fitness_history[-1] - app.best_fitness_history[0]
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
    
    app.view_data = data
    app.populate_flat_view()
    
    app.tree.tag_configure("header", font=("Arial", 11, "bold"), background="#e0e0e0")
    app.tree.tag_configure("ok", background="#ccffcc")
    app.tree.tag_configure("warning", background="#fff3cd")
    app.tree.tag_configure("error", background="#ffcccc")
    
    app.current_view = "quality"
    app.view_type_label.config(text="Vue actuelle: Qualité du Planning")
    app.configure_action_buttons()