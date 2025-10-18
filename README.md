
# Teacher Supervision Schedule Management Application

## Description
This desktop application, built with Python, automates the generation of exam supervision schedules using a genetic algorithm. It accounts for exam slots, teachers (with their grades, quotas, and unavailabilities), and optimizes the allocation to ensure fairness and full coverage.

## Brief Explanation of the Genetic Algorithm (GA)
The genetic algorithm is an optimization method inspired by natural evolution, used here to generate optimal supervision schedules. Here’s a concise summary:

#### Initialization: 
A population of schedules (chromosomes) is randomly created, each representing an assignment of teachers to slots.
####  Evaluation: 
Each schedule is scored using a fitness function, which measures slot coverage, equity (balanced distribution), dispersion (spacing of slots), and compliance with constraints (unavailabilities, quotas).
####  Selection: 
The best schedules (elite) are retained, and others are chosen to reproduce.
####  Crossover:
Two parent schedules exchange parts of their assignments to create a new offspring, combining their strengths.
####  Mutation: 
Random changes (teacher swaps) introduce diversity.
####  Iteration: 
This process repeats over multiple generations (e.g., 200), with repairs to enforce strict constraints.
#### Result: 
The best schedule, based on the highest fitness, is selected as the final solution.

This approach efficiently explores a large solution space, though it does not guarantee a global optimum, making it suitable for meeting the project’s constraints.

## Installation Instructions

### 1. Set Up a Virtual Environment
To isolate dependencies, create and activate a virtual environment:
```bash
python3 -m venv env_surveillance
source env_surveillance/bin/activate
```

### 2. Install Required Python Libraries
```bash
pip install numpy pandas reportlab matplotlib
```

numpy: For numerical operations in the genetic algorithm.
pandas: For data handling and CSV operations.
reportlab: For PDF export functionality.
matplotlib: For potential visualization (optional).

### 3. Run the Application
slots.csv: Contains exam slots and required number of supervisors (columns: slot, nb_needed).
teachers.csv: Contains teacher details (columns: id, grade, quota, indispo)
```bash
python3 app_surveillance.py
 ```

