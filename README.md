# 🧬 Algorithme Génétique - Optimisation du Planning de Surveillance

## 📋 Vue d'ensemble

Implémentant un **algorithme génétique pour optimiser un planning de surveillance** en assignant des enseignants à des créneaux horaires. L'algorithme cherche à respecter les contraintes tout en maximisant l'équité et la qualité globale du planning.

---
## Structures du projet

projet/
├── main.py                 # ✅ Nouveau fichier restructuré
├── constants.py            # ✅ Nouveau module
├── database.py             # ✅ Nouveau module
├── data_loader.py          # ✅ Nouveau module
├── ui_components.py        # ✅ Nouveau module
├── email_utils.py          # ✅ Nouveau module
├── export_methods.py       # ✅ Nouveau module
│
├── genetic_algorithm.py    # 📂 Fichier existant (à conserver)
├── view_methods.py         # 📂 Fichier existant (à conserver)
├── pdf_export.py           # 📂 Fichier existant (à conserver)
├── login.py                # 📂 Fichier existant (à conserver)
│
└── exports/                # 📁 Dossier créé automatiquement
    ├── Affectation_*.pdf
    └── Planning_General_*.pdf
    
## 🔧 Méthodes principales

### 1. **`fitness(assignment, teachers, slots_dict)`** — Évaluation de la qualité

Fonction centrale qui attribue un **score** à chaque solution. Plus le score est élevé, meilleure est la solution.

#### **Contraintes sur le nombre de professeurs par créneau**
- Chaque créneau doit avoir entre `min_needed` (2 × nombre de salles) et `max_needed` (4 × nombre de salles) professeurs
- **Pénalité forte** (-500) si le minimum n'est pas respecté
- **Bonus** (+100) si exactement le minimum est atteint

#### **Pénalité pour doublons**
- Si un professeur est assigné deux fois au même créneau : **-500 points par doublon**

#### **Respect des indisponibilités**
- Si un professeur est assigné à un créneau où il est indisponible : **-2000 × priorité du souhait**

#### **Dépassements de quota**
- Chaque professeur a un quota maximum de créneaux
- **Pénalité quadratique** : -500 × (excédent)²

#### **Présence des responsables**
- **Bonus** (+200) si le professeur responsable du créneau est assigné
- **Pénalité** (-100) s'il est absent
- **Bonus additionnel** (+500) si tous les responsables sont présents

#### **Gestion des "séances creuses" (gap violations)**
- Un professeur ne doit pas avoir de trous importants entre ses créneaux sur une même journée
- Une pause de 2 sessions : **-200 points**
- Une pause de 3 sessions : **-500 points**
- **Bonus** (+500) si aucun gap détecté

#### **Dispersion des créneaux**
- Les créneaux de chaque professeur doivent être bien répartis sur plusieurs jours
- **Pénalité** si > 3 jours
- **Bonus** si répartition uniforme avec gaps consécutifs

#### **Équité par grade**
- La variance des charges entre professeurs du même grade est **pénalisée** : -50 × variance
- Assure une distribution équitable entre les niveaux d'enseignement

---

### 2. **`generate_population(pop_size, slots, teachers)`** — Création initiale

Génère `pop_size` solutions aléatoires pour initialiser l'algorithme.

**Processus :**
- Trie les professeurs par quota décroissant (priorité aux plus chargés)
- Pour chaque créneau :
  - Priorise le professeur responsable s'il est disponible
  - Ajoute aléatoirement d'autres professeurs jusqu'au minimum requis
  - Complète si nécessaire jusqu'au maximum

---

### 3. **`crossover(parent1, parent2)`** — Reproduction

Croisement **uniforme** simple :
- Pour chaque créneau, choisit aléatoirement (50/50) l'assignation du parent1 ou parent2
- Crée un enfant combinant les caractéristiques des deux parents

**Avantage** : Permet d'explorer l'espace des solutions en combinant des individus prometteurs

---

### 4. **`mutate_improved(assignment, teachers, slots, slots_dict)`** — Mutation adaptative

Applique **quatre types de mutations** pour explorer l'espace des solutions :

#### **Type 1 : `swap` (Échange)**
- Échange un professeur d'un créneau avec un professeur d'un autre créneau
- Respecte les contraintes d'indisponibilité

#### **Type 2 : `reassign` (Réassignation)**
- Déplace un professeur surchargé vers un professeur sous-chargé
- Activé s'il y a des professeurs en surquota et d'autres en sous-quota

#### **Type 3 : `redistribute` (Redistribution par grade)**
- Dans un grade donné, transfère un créneau du professeur le plus chargé au moins chargé
- Rééquilibre la charge au sein d'une catégorie d'enseignement

#### **Type 4 : `remove_overload` (Suppression surcharge)**
- Remplace un professeur en surquota par un professeur en sous-quota
- Soulage les professeurs écrasés de travail

**Sélection** : Le type de mutation est choisi aléatoirement à chaque application

---

### 5. **`repair_solution(child, teachers, slots_dict)`** — Réparation

Assure la viabilité de chaque solution généré après mutation.

**Étapes de réparation :**

1. **Nettoyage** : supprime les enseignants invalides ou non disponibles
2. **Suppression des doublons** : garde la première occurrence de chaque professeur par créneau
3. **Complétion** : ajoute des professeurs manquants jusqu'au minimum requis
   - Priorité aux professeurs avec quota restant
   - Maximum 100 tentatives pour éviter boucles infinies
4. **Troncature** : réduit à `max_needed` si dépassement

---

### 6. **Méthodes utilitaires**

#### **`is_valid_teacher(t)`**
Vérifie si un enseignant est valide (pas None, pas "NaN", pas vide)

#### **`get_teacher_slots(assignment, teacher)`**
Récupère tous les créneaux assignés à un enseignant, triés par date et heure

#### **`check_gap_violations(assignment, teachers, slots_dict)`**
Détecte les "séances creuses" (gaps) dans la journée d'un professeur
- Retourne le nombre de gaps simples (2 sessions) et doubles (3 sessions)

#### **`calculate_grade_equity(counts, teachers)`**
Calcule la variance des charges par grade pour évaluer l'équité

#### **`check_responsable_presence(assignment, slots_dict, teachers)`**
Compte le nombre de professeurs responsables présents/absents

#### **`parse_datetime(slot_str)`**
Parse les créneaux au format 'YYYY-MM-DD SESSION' (ex: '2025-05-13 S2')

---

## 🎯 Critères d'arrêt

L'algorithme s'arrête selon trois critères implémentés dans **`run_ga_optimized()`** :

### **1. Seuil de fitness optimal**
```python
EARLY_STOP_THRESHOLD = 3000
```
- Si un individu atteint un score > 3000 → **arrêt immédiat**
- **Raison** : une solution "suffisamment bonne" a été trouvée
- **Status retourné** : `"optimal"`

### **2. Stagnation (Plateau de convergence)**
```python
STAGNATION_LIMIT = 100
MIN_IMPROVEMENT = 1.0
```
- Si **aucune amélioration significative** (> 1 point) pendant **100 générations** → **arrêt**
- **Raison** : l'algorithme n'avance plus, continuer ne serait pas productif
- **Status retourné** : `"stagnated"`

**Mécanisme de détection :**
- Compare le score actuel avec celui de la génération précédente
- Compte les générations sans progrès (`stagnation_counter`)
- Réinitialise le compteur dès qu'une amélioration > 1 point est observée

### **3. Nombre maximum de générations**
```python
max_generations = 3000
```
- Limite absolue du nombre d'itérations
- **Status retourné** : `"max_gen"`

---

## 🧬 Dynamique de mutation

La **mutation rate** s'adapte automatiquement selon le niveau de stagnation pour équilibrer **exploration** et **exploitation** :

```python
if stagnation_counter < 20:
    mutation_rate = 0.25  # Exploration faible (25%)
elif stagnation_counter < 50:
    mutation_rate = 0.5   # Exploration modérée (50%)
else:
    mutation_rate = 0.8   # Exploration agressive (80%)
```

### **Logique d'adaptation**

- **Peu de stagnation** (< 20 générations) 
  - → Mutations légères (25%)
  - → L'algorithme converge bien, ne pas trop perturber

- **Stagnation modérée** (20-50)
  - → Augmenter les mutations (50%)
  - → Essayer de sortir d'un plateau

- **Forte stagnation** (> 50)
  - → Mutation agressive (80%)
  - → Exploration maximale pour découvrir nouvelles régions

### **Ajustement lors de progression**

```python
if improvement >= MIN_IMPROVEMENT:
    mutation_rate = max(mutation_rate * 0.8, 0.1)
```

- **Si progrès** → réduire la mutation de 20% (minimum 10%)
- **Raison** : exploiter intensivement la région prometteuse découverte
- **Limite de 10%** : maintenir une diversité minimale

---

## 📊 Flux d'exécution par génération

```
GÉNÉRATION n
│
├─ ÉVALUATION 
│  └─ Calculer fitness pour chaque individu
│     └─ Tri décroissant par score
│
├─ VÉRIFICATION D'ARRÊT
│  ├─ Meilleure fitness > 3000 ?
│  │  └─ OUI → ARRÊT : "optimal"
│  ├─ Stagnation > 100 générations ?
│  │  └─ OUI → ARRÊT : "stagnated"
│  └─ Générations >= max ?
│     └─ OUI → ARRÊT : "max_gen"
│
├─ SÉLECTION ÉLITAIRE
│  └─ Conserver top 20% (meilleurs individus)
│
├─ CRÉATION NOUVELLE POPULATION
│  └─ Boucle jusqu'à pop_size complète :
│     ├─ SÉLECTION TOURNOI (x2)
│     │  └─ Sélectionner 2 parents via tournoi de 10 individus
│     ├─ CROSSOVER
│     │  └─ Créer enfant par croisement uniforme
│     ├─ MUTATION
│     │  └─ Appliquer si random < mutation_rate
│     ├─ RÉPARATION
│     │  └─ Corriger violations de contraintes
│     └─ Ajouter à nouvelle population
│
└─ RAPPORT DE PROGRESSION
   └─ Afficher génération, fitness, stagnation, diversité
```

---

## 🎲 Exemple concret

**Scénario : Professeur "Alice" surchargé à la génération 5**

1. **Évaluation**
   - Alice assignée à 6 créneaux, quota = 5
   - Excédent = 1 → fitness = -500 × 1² = -500 points

2. **Détection de surcharge**
   - Mutation type `reassign` sélectionnée
   - Identifie Bob (sous-quota, disponible)

3. **Application de mutation**
   - Échange un créneau : Alice → Bob
   - Vérifie disponibilités

4. **Réparation**
   - Valide contraintes
   - Complète si nécessaire

5. **Nouvelle évaluation**
   - Meilleure fitness → amélioration détectée
   - `stagnation_counter` réinitialisé
   - `mutation_rate` réduit de 20%

6. **Bénéfice**
   - Alice passe à 5 créneaux (quota respecté)
   - Bob mieux utilisé
   - Fitness augmentée, algorithme continue exploitation

---

## 🚀 Paramètres clés

| Paramètre | Valeur | Description |
|-----------|--------|-------------|
| `pop_size` | 200 | Taille de la population par génération |
| `max_generations` | 300 | Nombre maximal de générations |
| `elite_size` | 20% | Proportion d'élites conservées |
| `EARLY_STOP_THRESHOLD` | 3000 | Score fitness pour arrêt optimal |
| `STAGNATION_LIMIT` | 100 | Générations sans amélioration avant arrêt |
| `MIN_IMPROVEMENT` | 1.0 | Seuil minimum d'amélioration |
| `tournament_size` | 10 | Taille du tournoi de sélection |

---

## 💡 Stratégie d'optimisation

1. **Initialisation** : création aléatoire avec biais vers professeurs responsables
2. **Évaluation** : score multi-critères équilibrant respect de contraintes et équité
3. **Sélection** : élitarisme + tournoi pour favoriser bonnes solutions
4. **Variation** : 4 types de mutations complémentaires + crossover uniforme
5. **Réparation** : garantit validité de chaque solution
6. **Adaptation** : mutation rate dynamique selon progression
7. **Arrêt** : trois critères pour optimiser temps vs qualité

**Résultat** : un planning viable, équitable et respectant les contraintes majeure
