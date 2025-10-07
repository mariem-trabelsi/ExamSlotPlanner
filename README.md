# Teacher Supervision Schedule Management Application

## Description
This desktop application, built with Python, automates the generation of exam supervision schedules using a genetic algorithm. It accounts for exam slots, teachers (with their grades, quotas, and unavailabilities), and optimizes the allocation to ensure fairness and full coverage.

## Prerequisites
- Ubuntu system (or compatible Linux).
- Python 3.10 or higher.

## Installation Instructions

### 1. Set Up a Virtual Environment
To isolate dependencies, create and activate a virtual environment:
```bash
python3 -m venv env_surveillance
source env_surveillance/bin/activate```

### 2. Install Required Python Libraries
```bash
pip install numpy pandas reportlab matplotlib```

numpy: For numerical operations in the genetic algorithm.
pandas: For data handling and CSV operations.
reportlab: For PDF export functionality.
matplotlib: For potential visualization (optional).

### 3. Run the Application
```bash
python3 app_surveillance.py
 ```
