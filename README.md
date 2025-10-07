# Teacher Supervision Schedule Management Application

## Description
This desktop application, built with Python, automates the generation of exam supervision schedules using a genetic algorithm. It accounts for exam slots, teachers (with their grades, quotas, and unavailabilities), and optimizes the allocation to ensure fairness and full coverage.

## Prerequisites
- Python 3.10 or higher.

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
Use the GUI to load slots.csv and teachers.csv.
Click "Générer Planning" to create the schedule.
Export the result as CSV or PDF using the respective buttons.
