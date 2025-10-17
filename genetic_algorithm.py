"""
Module contenant l'algorithme génétique pour l'optimisation du planning
"""
import random
import numpy as np
from datetime import datetime

SESSION_ORDER = {"S1": 1, "S2": 2, "S3": 3, "S4": 4}
SESSION_TIMES = {"S1": "08:30", "S2": "10:30", "S3": "12:30", "S4": "14:30"}


def is_valid_teacher(t):
    """Vérifie si un enseignant est valide (pas NaN)"""
    if t is None:
        return False
    t_str = str(t).strip()
    return t_str and t_str.lower() != 'nan'


def get_teacher_slots(assignment, teacher):
    """Récupère les créneaux assignés à un enseignant avec tri"""
    slots = []
    for slot in assignment:
        if teacher in assignment[slot]:
            parsed = parse_datetime(slot)
            if parsed[0]:
                date, order = parsed
                slots.append((date, order, slot))
    return sorted(slots)





def check_gap_violations(assignment, teachers, slots_dict):
    """Vérifie les séances creuses dans la même journée"""
    violations = {'one_gap': 0, 'two_gaps': 0}
    
    for teacher in teachers:
        if not teachers[teacher].get('participe_surveillance', False):
            continue
            
        teacher_slots = get_teacher_slots(assignment, teacher)
        
        # Grouper par jour
        days = {}
        for date, order, slot in teacher_slots:
            date_key = date.strftime('%Y-%m-%d')
            if date_key not in days:
                days[date_key] = []
            days[date_key].append(order)
        
        # Vérifier les gaps pour chaque jour
        for date_key, sessions in days.items():
            if len(sessions) < 2:
                continue
            sessions = sorted(set(sessions))
            
            for i in range(len(sessions) - 1):
                gap = sessions[i + 1] - sessions[i]
                if gap == 2:
                    violations['one_gap'] += 1
                elif gap == 3:
                    violations['two_gaps'] += 1
    
    return violations


def dispersion_penalty(teacher_slots):
    """Pénalise les mauvaises répartitions"""
    if len(teacher_slots) < 2:
        return 0
    
    penalty = 0
    
    # Grouper par jour
    days = {}
    for date, order, slot in teacher_slots:
        date_key = date.strftime('%Y-%m-%d')
        if date_key not in days:
            days[date_key] = []
        days[date_key].append(order)
    
    # Pénaliser le nombre de jours
    num_days = len(days)
    if num_days > 3:
        penalty -= 30 * (num_days - 3)
    
    # Pénaliser les gaps
    for date_key, sessions in days.items():
        if len(sessions) < 2:
            continue
        sessions = sorted(set(sessions))
        
        for i in range(len(sessions) - 1):
            gap = sessions[i + 1] - sessions[i]
            if gap == 1:
                penalty += 20
            elif gap == 2:
                penalty -= 50
            elif gap == 3:
                penalty -= 100
    
    return penalty


def calculate_grade_equity(counts, teachers):
    """Calcule la variance des charges par grade"""
    grades = set(t.get('grade', '') for t in teachers.values() if t.get('participe_surveillance', False))
    total_variance = 0
    
    for grade in grades:
        if not grade:
            continue
        grade_counts = [counts.get(e, 0) for e in teachers 
                       if teachers[e].get('grade') == grade and teachers[e].get('participe_surveillance', False)]
        if grade_counts and len(grade_counts) > 1:
            variance = np.var(grade_counts)
            total_variance += variance
    
    return total_variance


def calculate_quota_violations(counts, teachers):
    """Calcule les dépassements de quota"""
    total_excess = 0
    violation_count = 0
    
    for teacher_code, count in counts.items():
        if teacher_code not in teachers:
            continue
        teacher = teachers[teacher_code]
        quota = teacher.get('quota', 0)
        
        if count > quota:
            excess = count - quota
            total_excess += excess
            violation_count += 1
    
    return total_excess, violation_count


def check_responsable_presence(assignment, slots_dict, teachers):
    """Vérifie la présence des profs responsables"""
    present = 0
    absent = 0
    
    for slot, slot_data in slots_dict.items():
        prof_resp = str(slot_data.get('enseignant', '')).strip()
        
        if not prof_resp or not is_valid_teacher(prof_resp):
            continue
        
        valid_teachers = [t for t in assignment.get(slot, []) if is_valid_teacher(t)]
        
        if prof_resp in valid_teachers:
            present += 1
        else:
            absent += 1
    
    return present, absent


def fitness(assignment, teachers, slots_dict):
    """Fonction de fitness"""
    score = 0.0
    counts = {}
    
    # Compter les assignations
    for slot in assignment:
        valid_teachers = [t for t in assignment[slot] if is_valid_teacher(t) and t in teachers]
        unique_assigned = set(valid_teachers)
        slot_data = slots_dict.get(slot, {})
        room_count = slot_data.get('room_count', 1)
        min_needed = 2 * room_count
        max_needed = 4 * room_count
        
        # Contraintes sur le nombre de profs
        if len(unique_assigned) < min_needed:
            score -= 500 * (min_needed - len(unique_assigned)) ** 2
        elif len(unique_assigned) > max_needed:
            score -= 500 * (len(unique_assigned) - max_needed) ** 2
        elif len(unique_assigned) == min_needed:
            score += 100
        
        # Pénalité pour doublons
        if len(valid_teachers) != len(unique_assigned):
            score -= 500 * (len(valid_teachers) - len(unique_assigned))
        
        # Compter pour chaque enseignant
        for e in valid_teachers:
            counts[e] = counts.get(e, 0) + 1
            
            # Pénalité pour indisponibilité
            if slot in teachers[e].get('indispo', []):
                wish_priority = teachers[e].get('wish_priority', {}).get(slot, 1.0)
                score -= 2000 * wish_priority
    
    # Vérifier dépassements de quota
    total_excess, violation_count = calculate_quota_violations(counts, teachers)
    score -= 500 * (total_excess ** 2)
    
    # Vérifier présence des profs responsables
    present, absent = check_responsable_presence(assignment, slots_dict, teachers)
    score += 200 * present
    score -= 100 * absent
    
    if absent == 0 and present > 0:
        score += 500
    
    # Pénaliser les séances creuses
    gap_violations = check_gap_violations(assignment, teachers, slots_dict)
    score -= 200 * gap_violations['one_gap']
    score -= 500 * gap_violations['two_gaps']
    
    if gap_violations['one_gap'] == 0 and gap_violations['two_gaps'] == 0:
        score += 500
    
    # Dispersion pour chaque enseignant
    for teacher_code in teachers:
        if not teachers[teacher_code].get('participe_surveillance', False):
            continue
        t_slots = get_teacher_slots(assignment, teacher_code)
        score += dispersion_penalty(t_slots)
    
    # Équité par grade
    total_variance = calculate_grade_equity(counts, teachers)
    score -= 50 * total_variance
    
    return score


def generate_population(pop_size, slots, teachers):
    """Génère une population initiale"""
    population = []
    teacher_list = [str(e) for e in teachers
                   if teachers[e].get('participe_surveillance', False) and is_valid_teacher(e)]
    
    for _ in range(pop_size):
        assignment = {}
        sorted_teachers = sorted(teacher_list, 
                               key=lambda t: teachers[t].get('quota', 0), 
                               reverse=True)
        
        for slot, slot_data in slots:
            min_needed = 2 * slot_data.get('room_count', 1)
            available = [e for e in sorted_teachers 
                        if slot not in teachers[e].get('indispo', [])]
            
            # Prioriser le prof responsable
            enseignant_responsable = str(slot_data.get('enseignant', '')).strip()
            selected = []
            
            if (enseignant_responsable and 
                is_valid_teacher(enseignant_responsable) and 
                enseignant_responsable in available):
                selected.append(enseignant_responsable)
                available.remove(enseignant_responsable)
            
            if available:
                needed = min(min_needed - len(selected), len(available))
                if needed > 0:
                    selected.extend(random.sample(available, needed))
                
                # Compléter si nécessaire
                while len(selected) < min_needed and available:
                    selected.append(random.choice(available))
                
                max_needed = 4 * slot_data.get('room_count', 1)
                assignment[slot] = selected[:max_needed]
            else:
                assignment[slot] = selected if selected else []
        
        population.append(assignment)
    
    return population


def crossover(parent1, parent2):
    """Croisement uniforme"""
    child = {}
    for key in parent1.keys():
        if random.random() < 0.5:
            child[key] = parent1[key][:]
        else:
            child[key] = parent2[key][:]
    return child


def mutate_improved(assignment, teachers, slots, slots_dict):
    """Mutation améliorée"""
    mutation_type = random.choice(['swap', 'reassign', 'redistribute', 'remove_overload'])
    teacher_list = [t for t in teachers 
                   if teachers[t].get('participe_surveillance', False) and is_valid_teacher(t)]
    
    if mutation_type == 'swap' and len(assignment) >= 2:
        slot_keys = list(assignment.keys())
        slot1, slot2 = random.sample(slot_keys, 2)
        valid1 = [t for t in assignment[slot1] if t in teacher_list]
        valid2 = [t for t in assignment[slot2] if t in teacher_list]
        
        if valid1 and valid2:
            e1 = random.choice(valid1)
            e2 = random.choice(valid2)
            
            if (slot2 not in teachers[e1].get('indispo', []) and 
                slot1 not in teachers[e2].get('indispo', [])):
                idx1 = assignment[slot1].index(e1)
                idx2 = assignment[slot2].index(e2)
                assignment[slot1][idx1] = e2
                assignment[slot2][idx2] = e1
    
    elif mutation_type in ['reassign', 'remove_overload']:
        counts = {e: sum(1 for slot in assignment if e in assignment[slot]) 
                 for e in teacher_list}
        overloaded = [e for e in counts 
                     if e in teachers and counts[e] > teachers[e].get('quota', 0)]
        underloaded = [e for e in counts 
                      if e in teachers and counts[e] < teachers[e].get('quota', 0)]
        
        if overloaded and underloaded:
            e_over = random.choice(overloaded)
            e_under = random.choice(underloaded)
            slots_with_over = [s for s in assignment if e_over in assignment[s]]
            
            if slots_with_over:
                slot = random.choice(slots_with_over)
                if slot not in teachers[e_under].get('indispo', []):
                    idx = assignment[slot].index(e_over)
                    assignment[slot][idx] = e_under
    
    elif mutation_type == 'redistribute':
        grades = list(set(t.get('grade', '') for t in teachers.values() 
                         if t.get('participe_surveillance', False)))
        
        if grades:
            grade = random.choice(grades)
            grade_teachers = [e for e in teacher_list if teachers[e].get('grade') == grade]
            
            if len(grade_teachers) >= 2:
                counts = {e: sum(1 for slot in assignment if e in assignment[slot]) 
                         for e in grade_teachers}
                most = max(counts, key=counts.get)
                least = min(counts, key=counts.get)
                
                if counts[most] - counts[least] >= 2:
                    slots_with_most = [s for s in assignment if most in assignment[s]]
                    if slots_with_most:
                        slot = random.choice(slots_with_most)
                        if slot not in teachers[least].get('indispo', []):
                            idx = assignment[slot].index(most)
                            assignment[slot][idx] = least
    
    return assignment


def repair_solution(child, teachers, slots_dict):
    """Répare une solution"""
    teacher_list = [t for t in teachers 
                   if teachers[t].get('participe_surveillance', False) and is_valid_teacher(t)]
    
    for slot in child:
        # Nettoyer
        child[slot] = [t for t in child[slot] if is_valid_teacher(t) and t in teacher_list]
        
        slot_data = slots_dict.get(slot, {})
        min_needed = 2 * slot_data.get('room_count', 1)
        max_needed = 4 * slot_data.get('room_count', 1)
        
        # Supprimer doublons
        child[slot] = list(dict.fromkeys(child[slot]))
        
        # Compter
        current_counts = {e: sum(1 for s in child if e in child[s]) for e in teacher_list}
        
        # Compléter
        attempts = 0
        while len(child[slot]) < min_needed and attempts < 100:
            available = sorted([e for e in teacher_list
                               if slot not in teachers[e].get('indispo', []) 
                               and e not in child[slot]],
                             key=lambda e: teachers[e].get('quota', 0) - current_counts.get(e, 0),
                             reverse=True)
            
            if available:
                child[slot].append(available[0])
                current_counts[available[0]] = current_counts.get(available[0], 0) + 1
            else:
                break
            attempts += 1
        
        # Tronquer
        if len(child[slot]) > max_needed:
            child[slot] = child[slot][:max_needed]
    
    return child


def parse_datetime(slot_str):
    """Parse un slot au format 'YYYY-MM-DD SESSION' (e.g., '2025-05-13 S2')."""
    try:
        date_part, session = slot_str.split()
        date = datetime.strptime(date_part, '%Y-%m-%d')
        return date, SESSION_ORDER.get(session, 0)
    except (ValueError, AttributeError):
        return None, 0

def run_ga_optimized(slots, teachers, progress_callback=None):
    """
    Algorithme génétique optimisé avec gestion sécurisée du multiprocessing
    """
    EARLY_STOP_THRESHOLD = -50
    STAGNATION_LIMIT = 100
    MIN_IMPROVEMENT = 1.0
    slots_dict = {slot: data for slot, data in slots}
    pop_size = 200
    max_generations =10
    elite_size = int(pop_size * 0.2)
    pop = generate_population(pop_size, slots, teachers)
    best_fitness_history = []
    stagnation_counter = 0
    last_significant_improvement_gen = 0
    mutation_rate = 0.25
    for gen in range(max_generations):
        try:
            # Évaluation séquentielle pour éviter problèmes de mémoire
            pop_with_fitness = []
            for ind in pop:
                try:
                    fitness_score = fitness(ind, teachers, slots_dict)
                    pop_with_fitness.append((ind, fitness_score))
                except Exception as e:
                    print(f"Erreur dans l'évaluation de fitness: {e}")
                    pop_with_fitness.append((ind, -999999))
            pop_with_fitness.sort(key=lambda x: x[1], reverse=True)
            best_fitness = pop_with_fitness[0][1]
            best_fitness_history.append(best_fitness)
            if best_fitness > EARLY_STOP_THRESHOLD:
                if progress_callback:
                    progress_callback(gen, max_generations, best_fitness,
                                     "🎯 Solution optimale trouvée!", "optimal")
                return pop_with_fitness[0][0], best_fitness_history, "optimal"
            if gen > 0:
                improvement = best_fitness - best_fitness_history[-2]
                if improvement >= MIN_IMPROVEMENT:
                    last_significant_improvement_gen = gen
                    stagnation_counter = 0
                    mutation_rate = max(mutation_rate * 0.8, 0.1)
                else:
                    stagnation_counter += 1
            if gen - last_significant_improvement_gen > STAGNATION_LIMIT:
                if progress_callback:
                    progress_callback(gen, max_generations, best_fitness,
                                     "✅ Convergence atteinte", "stagnated")
                return pop_with_fitness[0][0], best_fitness_history, "stagnated"
            if stagnation_counter < 20:
                mutation_rate = 0.25
            elif stagnation_counter < 50:
                mutation_rate = 0.5
            else:
                mutation_rate = 0.8
            if progress_callback:
                fitness_values = [f for _, f in pop_with_fitness]
                diversity = np.std(fitness_values) if len(fitness_values) > 1 else 0
                status = f"Stag: {stagnation_counter} | Div: {diversity:.1f} | Mut: {mutation_rate:.2f}"
                progress_callback(gen, max_generations, best_fitness, status, "running")
            new_pop = [ind for ind, _ in pop_with_fitness[:elite_size]]
            while len(new_pop) < pop_size:
                tournament_size = 10
                tournament1 = random.sample(pop_with_fitness[:pop_size//2],
                                           min(tournament_size, len(pop_with_fitness)//2))
                p1 = max(tournament1, key=lambda x: x[1])[0]
                tournament2 = random.sample(pop_with_fitness[:pop_size//2],
                                           min(tournament_size, len(pop_with_fitness)//2))
                p2 = max(tournament2, key=lambda x: x[1])[0]
                child = crossover(p1, p2)
                if random.random() < mutation_rate:
                    child = mutate_improved(child, teachers, slots, slots_dict)
                child = repair_solution(child, teachers, slots_dict)
                new_pop.append(child)
            pop = new_pop
        except Exception as e:
            print(f"Erreur génération {gen}: {e}")
            continue
    return pop_with_fitness[0][0], best_fitness_history, "max_gen"