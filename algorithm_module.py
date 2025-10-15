"""
Module de l'algorithme génétique pour la génération de planning
"""

import random
import numpy as np
from datetime import datetime


# Configuration des sessions
SESSION_ORDER = {"S1": 1, "S2": 2, "S3": 3, "S4": 4}


def parse_datetime(slot_str):
    """Parse une chaîne de créneau en date et ordre de session"""
    date_part, session = slot_str.split()
    return datetime.strptime(date_part, '%Y-%m-%d'), SESSION_ORDER[session]


def get_teacher_slots(assignment, teacher):
    """Retourne les créneaux d'un enseignant triés par date et session"""
    return sorted([
        (parse_datetime(slot)[0], parse_datetime(slot)[1]) 
        for slot in assignment if teacher in assignment[slot]
    ])


def check_consecutivity_violations(assignment, teachers, slots_dict):
    """Vérifie les violations de consécutivité (ex: S1 puis S4 le même jour)"""
    violations = 0
    for teacher in teachers:
        if not teachers[teacher]['participe_surveillance']:
            continue
        teacher_slots = get_teacher_slots(assignment, teacher)
        for i in range(len(teacher_slots) - 1):
            date1, order1 = teacher_slots[i]
            date2, order2 = teacher_slots[i + 1]
            if date1 == date2 and abs(order2 - order1) > 1:
                violations += 1
    return violations


def dispersion_penalty(teacher_slots):
    """Calcule une pénalité pour mauvaise dispersion des créneaux"""
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


def calculate_grade_equity(counts, teachers):
    """Calcule l'équité entre enseignants du même grade"""
    grades = set(t['grade'] for t in teachers.values())
    total_variance = 0
    for grade in grades:
        grade_counts = [counts[e] for e in teachers if teachers[e]['grade'] == grade]
        if grade_counts and len(grade_counts) > 1:
            variance = np.var(grade_counts)
            total_variance += variance
    return total_variance


def fitness(assignment, teachers, slots_dict):
    """
    Fonction de fitness pour évaluer la qualité d'un planning
    Plus le score est élevé, meilleure est la solution
    """
    score = 0.0
    counts = {e: 0 for e in teachers}
    
    for slot in assignment:
        unique_assigned = set(assignment[slot])
        slot_data = slots_dict[slot]
        room_count = slot_data['room_count']
        min_needed = 2 * room_count
        max_needed = 4 * room_count
        
        # Pénalité si pas assez d'enseignants
        if len(unique_assigned) < min_needed:
            score -= 1000 * (min_needed - len(unique_assigned))
        
        # Pénalité si trop d'enseignants
        if len(unique_assigned) > max_needed:
            score -= 1000 * (len(unique_assigned) - max_needed)
        
        # Bonus si nombre optimal
        if len(unique_assigned) == min_needed:
            score += 100
        
        # Pénalité pour doublons
        if len(assignment[slot]) != len(unique_assigned):
            score -= 500
        
        # Vérifier quotas et indisponibilités
        for e in assignment[slot]:
            counts[e] += 1
            if counts[e] > teachers[e]['quota']:
                score -= 1000 * (counts[e] - teachers[e]['quota'])
            if slot in teachers[e]['indispo']:
                score -= 1000
    
    # Pénalité pour violations de consécutivité
    violations = check_consecutivity_violations(assignment, teachers, slots_dict)
    score -= 1000 * violations
    
    # Bonus pour bonne dispersion
    for e in teachers:
        if not teachers[e]['participe_surveillance']:
            continue
        t_slots = get_teacher_slots(assignment, e)
        score += dispersion_penalty(t_slots)
    
    # Pénalité pour inéquité entre grades
    total_variance = calculate_grade_equity(counts, teachers)
    score -= 10 * total_variance
    
    return score


def generate_population(pop_size, slots, teachers):
    """Génère une population initiale de solutions"""
    population = []
    teacher_list = [str(e) for e in teachers if teachers[e]['participe_surveillance']]
    
    for _ in range(pop_size):
        assignment = {}
        for slot, slot_data in slots:
            min_needed = 2 * slot_data['room_count']
            available = [e for e in teacher_list if slot not in teachers[e]['indispo']]
            
            if available:
                selected = random.sample(available, min(min_needed, len(available)))
                while len(selected) < min_needed and available:
                    selected.append(random.choice(available))
                assignment[slot] = selected[:4 * slot_data['room_count']]
            else:
                assignment[slot] = []
        
        population.append(assignment)
    return population


def crossover(parent1, parent2):
    """Croisement entre deux parents"""
    child = {}
    keys = list(parent1.keys())
    midpoint = len(keys) // 2
    
    for i in range(midpoint):
        child[keys[i]] = parent1[keys[i]][:]
    for i in range(midpoint, len(keys)):
        child[keys[i]] = parent2[keys[i]][:]
    
    return child


def mutate_improved(assignment, teachers, slots, slots_dict):
    """Mutation améliorée avec plusieurs stratégies"""
    mutation_type = random.choice(['swap', 'reassign', 'redistribute'])
    
    if mutation_type == 'swap':
        # Échange d'enseignants entre deux créneaux
        slot_keys = list(assignment.keys())
        if len(slot_keys) >= 2:
            slot1, slot2 = random.sample(slot_keys, 2)
            if assignment[slot1] and assignment[slot2]:
                e1 = random.choice(assignment[slot1])
                e2 = random.choice(assignment[slot2])
                
                if (slot2 not in teachers[e1]['indispo'] and 
                    slot1 not in teachers[e2]['indispo']):
                    idx1 = assignment[slot1].index(e1)
                    idx2 = assignment[slot2].index(e2)
                    assignment[slot1][idx1] = e2
                    assignment[slot2][idx2] = e1
    
    elif mutation_type == 'reassign':
        # Réassignation pour équilibrer les quotas
        counts = {}
        for e in teachers:
            if teachers[e]['participe_surveillance']:
                counts[e] = sum(1 for slot in assignment if e in assignment[slot])
        
        overloaded = [e for e in counts if counts[e] > teachers[e]['quota']]
        underloaded = [e for e in counts if counts[e] < teachers[e]['quota']]
        
        if overloaded and underloaded:
            e_over = random.choice(overloaded)
            e_under = random.choice(underloaded)
            slots_with_over = [s for s in assignment if e_over in assignment[s]]
            
            if slots_with_over:
                slot = random.choice(slots_with_over)
                if slot not in teachers[e_under]['indispo']:
                    idx = assignment[slot].index(e_over)
                    assignment[slot][idx] = e_under
    
    elif mutation_type == 'redistribute':
        # Redistribution au sein d'un même grade
        grades = list(set(t['grade'] for t in teachers.values() if t['participe_surveillance']))
        if grades:
            grade = random.choice(grades)
            grade_teachers = [e for e in teachers 
                            if teachers[e]['grade'] == grade 
                            and teachers[e]['participe_surveillance']]
            
            if len(grade_teachers) >= 2:
                counts = {e: sum(1 for slot in assignment if e in assignment[slot]) 
                         for e in grade_teachers}
                
                most = max(counts, key=counts.get)
                least = min(counts, key=counts.get)
                
                if counts[most] - counts[least] >= 2:
                    slots_with_most = [s for s in assignment if most in assignment[s]]
                    if slots_with_most:
                        slot = random.choice(slots_with_most)
                        if slot not in teachers[least]['indispo']:
                            idx = assignment[slot].index(most)
                            assignment[slot][idx] = least
    
    return assignment


def repair_solution(child, teachers, slots_dict):
    """Répare une solution pour respecter les contraintes minimales"""
    for slot in child:
        slot_data = slots_dict[slot]
        min_needed = 2 * slot_data['room_count']
        max_needed = 4 * slot_data['room_count']
        
        # Supprimer les doublons
        child[slot] = list(set(child[slot]))
        
        # Ajouter des enseignants si nécessaire
        attempts = 0
        while len(child[slot]) < min_needed and attempts < 100:
            available = [e for e in teachers 
                        if slot not in teachers[e]['indispo'] 
                        and e not in child[slot]
                        and teachers[e]['participe_surveillance']]
            if available:
                child[slot].append(random.choice(available))
            else:
                break
            attempts += 1
        
        # Supprimer l'excédent
        if len(child[slot]) > max_needed:
            child[slot] = child[slot][:max_needed]
    
    return child


def run_ga_improved(slots, teachers, progress_callback=None):
    """
    Exécute l'algorithme génétique amélioré
    
    Args:
        slots: Liste des créneaux
        teachers: Dictionnaire des enseignants
        progress_callback: Fonction appelée pour suivre la progression
    
    Returns:
        Tuple (meilleure_solution, historique_fitness)
    """
    slots_dict = {slot: data for slot, data in slots}
    pop_size = 100
    generations = 100
    elite_size = 10
    
    print(f"🧬 Démarrage algorithme génétique: {pop_size} individus, {generations} générations")
    
    pop = generate_population(pop_size, slots, teachers)
    best_fitness_history = []
    stagnation_counter = 0
    
    for gen in range(generations):
        # Évaluation
        pop_with_fitness = [(ind, fitness(ind, teachers, slots_dict)) for ind in pop]
        pop_with_fitness.sort(key=lambda x: x[1], reverse=True)
        
        best_fitness = pop_with_fitness[0][1]
        best_fitness_history.append(best_fitness)
        
        # Détection de stagnation
        if gen > 50:
            if best_fitness_history[-1] == best_fitness_history[-50]:
                stagnation_counter += 1
            else:
                stagnation_counter = 0
        
        # Ajustement dynamique du taux de mutation
        mutation_rate = 0.2 if stagnation_counter < 10 else 0.5
        
        # Callback pour l'interface
        if progress_callback:
            progress_callback(gen, generations, best_fitness)
        
        # Élitisme: garder les meilleurs
        new_pop = [ind for ind, _ in pop_with_fitness[:elite_size]]
        
        # Création de la nouvelle génération
        while len(new_pop) < pop_size:
            # Sélection par tournoi
            tournament1 = random.sample(pop_with_fitness[:pop_size//2], 5)
            p1 = max(tournament1, key=lambda x: x[1])[0]
            
            tournament2 = random.sample(pop_with_fitness[:pop_size//2], 5)
            p2 = max(tournament2, key=lambda x: x[1])[0]
            
            # Croisement
            child = crossover(p1, p2)
            
            # Mutation
            if random.random() < mutation_rate:
                child = mutate_improved(child, teachers, slots, slots_dict)
            
            # Réparation
            child = repair_solution(child, teachers, slots_dict)
            
            new_pop.append(child)
        
        pop = new_pop
    
    best_solution = pop_with_fitness[0][0]
    final_fitness = pop_with_fitness[0][1]
    
    print(f"✅ Algorithme terminé! Fitness final: {final_fitness:.2f}")
    
    return best_solution, best_fitness_history