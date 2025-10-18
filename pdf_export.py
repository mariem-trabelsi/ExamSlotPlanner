"""
Module d'export PDF pour les différentes vues
"""
from reportlab.lib.pagesizes import letter, A4, landscape
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch,cm
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.pdfgen import canvas
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from datetime import datetime
from tkinter import filedialog, messagebox
import os
from genetic_algorithm import (
    is_valid_teacher, fitness, check_gap_violations, 
    check_responsable_presence, calculate_quota_violations, SESSION_TIMES
)
from view_methods import check_prof_responsable_presence_simple

def export_calendar_pdf(filename, app):
    """Exporte la vue calendrier en PDF"""
    doc = SimpleDocTemplate(filename, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle', parent=styles['Heading1'], fontSize=18,
        textColor=colors.HexColor('#1976D2'), spaceAfter=20, alignment=1
    )
    
    hide_rooms = app.hide_rooms_var.get()
    title_text = "Planning des Surveillances - Vue Calendrier"
    if hide_rooms:
        title_text += " (Salles masquées)"
    elements.append(Paragraph(title_text, title_style))
    elements.append(Spacer(1, 0.3*inch))
    
    days_data = {}
    for slot in sorted(app.best.keys()):
        date_str, session = slot.split()
        if date_str not in days_data:
            days_data[date_str] = {s: {} for s in ["S1", "S2", "S3", "S4"]}
        for room, teachers in app.room_assignments[slot].items():
            valid_teachers = [t for t in teachers if is_valid_teacher(t)]
            days_data[date_str][session][room] = valid_teachers
    
    for date_str in sorted(days_data.keys()):
        date_obj = datetime.strptime(date_str, '%Y-%m-%d')
        date_display = date_obj.strftime('%d/%m/%Y - %A')
        elements.append(Paragraph(f"<b>{date_display}</b>", styles['Heading2']))
        
        if hide_rooms:
            data = [["S1\n08:30", "S2\n10:30", "S3\n12:30", "S4\n14:30"]]
            row = []
            for session in ["S1", "S2", "S3", "S4"]:
                all_teachers = []
                for room, teachers in days_data[date_str][session].items():
                    all_teachers.extend(teachers)
                row.append("\n".join(all_teachers) if all_teachers else "-")
            data.append(row)
        else:
            all_rooms = set()
            for session in ["S1", "S2", "S3", "S4"]:
                all_rooms.update(days_data[date_str][session].keys())
            data = [["Salle", "S1\n08:30", "S2\n10:30", "S3\n12:30", "S4\n14:30"]]
            for room in sorted(all_rooms):
                row = [f"Salle {room}"]
                for session in ["S1", "S2", "S3", "S4"]:
                    teachers = days_data[date_str][session].get(room, [])
                    row.append("\n".join(teachers) if teachers else "-")
                data.append(row)
        
        table = Table(data)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1976D2')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(table)
        elements.append(Spacer(1, 0.3*inch))
    
    doc.build(elements)

def export_teacher_pdf(filename, app):
    """Exporte la vue par enseignant en PDF"""
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("Planning par Enseignant", styles['Title']))
    elements.append(Spacer(1, 0.2*inch))
    
    teacher_slots = {teacher: [] for teacher in app.teachers}
    for slot in app.best:
        valid = [t for t in app.best[slot] if is_valid_teacher(t)]
        for teacher in valid:
            if teacher in teacher_slots:
                teacher_slots[teacher].append(slot)
    
    data = [["Code", "Nom", "Grade", "Quota", "Assigné", "Vœux"]]
    for teacher in sorted(app.teachers.keys()):
        t_data = app.teachers[teacher]
        num = len(teacher_slots[teacher])
        violated = [s for s in teacher_slots[teacher] if s in t_data.get('indispo', [])]
        voeux_status = f"Violé {len(violated)}" if violated else \
                      "OK" if t_data.get('indispo') else "Aucun"
        data.append([
            teacher,
            f"{t_data.get('nom', '')} {t_data.get('prenom', '')}",
            t_data.get('grade', ''),
            str(t_data.get('quota', 0)),
            str(num),
            voeux_status
        ])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    doc.build(elements)

def export_room_pdf(filename, app):
    """Exporte la vue par salle en PDF"""
    doc = SimpleDocTemplate(filename, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("Planning par Salle", styles['Title']))
    elements.append(Spacer(1, 0.2*inch))
    
    data = [["Créneau", "Salle", "Nb Profs", "Enseignants"]]
    for slot in sorted(app.best.keys()):
        for room in sorted(app.room_assignments[slot].keys()):
            teachers = app.room_assignments[slot][room]
            valid = [t for t in teachers if is_valid_teacher(t)]
            data.append([slot, room, str(len(valid)), ", ".join(valid)])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    doc.build(elements)

def export_quality_pdf(filename, app):
    """Exporte le rapport de qualité en PDF"""
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("Rapport de Qualité du Planning", styles['Title']))
    elements.append(Spacer(1, 0.2*inch))
    
    slots_dict = {slot: data for slot, data in app.slots}
    fitness_score = fitness(app.best, app.teachers, slots_dict)
    quality = "Excellent" if fitness_score > -100 else \
             "Acceptable" if fitness_score > -500 else "À améliorer"
    elements.append(Paragraph(f"<b>Score global:</b> {fitness_score:.0f} ({quality})",
                            styles['Normal']))
    elements.append(Spacer(1, 0.2*inch))
    
    # Calculer les violations
    counts = {}
    for slot in app.best:
        valid = [t for t in app.best[slot] if is_valid_teacher(t)]
        for e in valid:
            counts[e] = counts.get(e, 0) + 1
    
    violations = {'min_profs': 0, 'max_profs': 0}
    
    for slot in app.best:
        valid = [t for t in app.best[slot] if is_valid_teacher(t)]
        unique = len(set(valid))
        slot_data = slots_dict[slot]
        min_needed = 2 * slot_data.get('room_count', 1)
        max_needed = 4 * slot_data.get('room_count', 1)
        
        if unique < min_needed:
            violations['min_profs'] += (min_needed - unique)
        if unique > max_needed:
            violations['max_profs'] += (unique - max_needed)
    
    # Dépassements de quota (CORRIGÉ)
    total_excess, quota_violations_count = calculate_quota_violations(counts, app.teachers)
    
    # Profs responsables (CORRIGÉ)
    prof_resp_results = check_prof_responsable_presence_simple(app)
    prof_resp_present = sum(r['present'] for r in prof_resp_results)
    prof_resp_absent = len(prof_resp_results) - prof_resp_present
    total_resp = len(prof_resp_results)
    
    # Séances creuses
    gap_violations = check_gap_violations(app.best, app.teachers, slots_dict)
    
    data = [["Contrainte", "Violations"]]
    data.append(["Minimum 2 profs/salle", str(violations['min_profs'])])
    data.append(["Maximum 4 profs/salle", str(violations['max_profs'])])
    data.append(["Dépassements de quota (total)", f"{total_excess} ({quota_violations_count} enseignants)"])
    data.append(["Séances avec 1 creux (S1→S3, S2→S4)", str(gap_violations['one_gap'])])
    data.append(["Séances avec 2 creux (S1→S4)", str(gap_violations['two_gaps'])])
    
    if total_resp > 0:
        taux = (prof_resp_present / total_resp) * 100
        data.append(["Profs responsables présents", 
                    f"{prof_resp_present}/{total_resp} ({taux:.1f}%)"])
    
    table = Table(data)
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(table)
    doc.build(elements)

def export_generic_pdf(filename, app):
    """Exporte le planning général en PDF"""
    doc = SimpleDocTemplate(filename, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    elements.append(Paragraph("Planning de Surveillance", styles['Title']))
    elements.append(Spacer(1, 0.2*inch))
    
    for slot in sorted(app.best.keys()):
        valid = [str(t) for t in app.best[slot] if is_valid_teacher(t)]
        elements.append(Paragraph(f"<b>{slot}</b>: {', '.join(valid)}",
                               styles['Normal']))
    doc.build(elements)

def export_selected_teacher_pdf(values, teachers):
    """Exporte le PDF pour un enseignant sélectionné"""
    code, nom, prenom, grade, quota, assigne, creneaux_str, voeux, statut_voeux = values
    creneaux = creneaux_str.split(", ") if creneaux_str != "Non assigné" else []
    
    file = filedialog.asksaveasfilename(
        defaultextension=".pdf",
        filetypes=[("PDF files", "*.pdf")],
        initialfile=f"planning_{nom}_{prenom}_{datetime.now().strftime('%Y%m%d')}.pdf"
    )
    if not file:
        return
    
    try:
        doc = SimpleDocTemplate(file, pagesize=A4)
        elements = []
        styles = getSampleStyleSheet()
        title_style = ParagraphStyle('CustomTitle', parent=styles['Heading1'], 
                                     fontSize=16, alignment=1)
        
        elements.append(Paragraph(f"Planning de Surveillance pour {nom} {prenom} ({code})", 
                                title_style))
        elements.append(Spacer(1, 0.2*inch))
        
        info_data = [
            ["Grade", grade],
            ["Quota", quota],
            ["Assigné", assigne],
            ["Vœux", voeux],
            ["Statut Vœux", statut_voeux]
        ]
        info_table = Table(info_data)
        info_table.setStyle(TableStyle([
            ('GRID', (0,0), (-1,-1), 1, colors.black),
            ('BACKGROUND', (0,0), (0,-1), colors.lightgrey)
        ]))
        elements.append(info_table)
        elements.append(Spacer(1, 0.3*inch))
        
        elements.append(Paragraph("Créneaux Assignés:", styles['Heading2']))
        if creneaux:
            creneaux_data = [["Créneau"]] + [[c] for c in sorted(creneaux)]
            creneaux_table = Table(creneaux_data)
            creneaux_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.grey),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('GRID', (0,0), (-1,-1), 1, colors.black)
            ]))
            elements.append(creneaux_table)
        else:
            elements.append(Paragraph("Aucun créneau assigné.", styles['Normal']))
        
        doc.build(elements)
        messagebox.showinfo("✅ Succès", f"PDF généré: {file}")
    except Exception as e:
        messagebox.showerror("❌ Erreur", f"Erreur: {str(e)}")



def export_teachers_to_pdf(filename,app):
    """Exporte un PDF pour chaque enseignant avec ses créneaux"""

    output_folder="exports"
    if not app.best:
        app.show_error_message("❌ Erreur", "Veuillez générer le planning d'abord!")
        return
    
    # Create output folder if it doesn't exist
    if not os.path.exists("exports"):
        os.makedirs("exports")
    
    # Organize assignments by teacher
    from collections import defaultdict
    teacher_slots = defaultdict(list)
    
    for slot in app.best:
        for teacher in app.best[slot]:
            teacher_slots[teacher].append(slot)
    
    # Session times mapping
    SESSION_TIMES = {
        's1': '08:30:00',
        's2': '10:30:00',
        's3': '10:30:00',  # Adjust based on your actual times
        's4': '10:30:00'
    }
    
    # Day names in French
    DAY_NAMES_FR = {
        'Monday': 'Lundi',
        'Tuesday': 'Mardi',
        'Wednesday': 'Mercredi',
        'Thursday': 'Jeudi',
        'Friday': 'Vendredi',
        'Saturday': 'Samedi',
        'Sunday': 'Dimanche'
    }
    
    pdf_count = 0
    
    # Generate PDF for each assigned teacher
    for teacher_code in sorted(teacher_slots.keys()):
        if not teacher_slots[teacher_code]:
            continue
        
        teacher_data = app.teachers.get(str(teacher_code), {})
        prenom = teacher_data.get('prenom', '')
        nom = teacher_data.get('nom', '')
        full_name = f"Mr {prenom} {nom}" if prenom and nom else f"Enseignant #{teacher_code}"
        
        # Create PDF filename
        safe_name = f"{prenom}_{nom}".replace(' ', '_') if prenom and nom else f"Teacher_{teacher_code}"
        pdf_filename = os.path.join(output_folder, f"Affectation_{safe_name}.pdf")
        
        # Create PDF document
        doc = SimpleDocTemplate(pdf_filename, pagesize=A4,
                              rightMargin=2*cm, leftMargin=2*cm,
                              topMargin=2*cm, bottomMargin=2*cm)
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        subtitle_style = ParagraphStyle(
            'CustomSubtitle',
            parent=styles['Normal'],
            fontSize=14,
            textColor=colors.HexColor('#1e3a8a'),
            spaceAfter=20,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=20,
            alignment=TA_LEFT
        )
        
        # Header section (mimicking the document)
        header_data = [
            ['GESTION DES EXAMENS ET\nDÉLIBÉRATIONS', 'EXD-FR-08-01'],
            ["Procédure d'exécution des épreuves", f"Date d'approbation\n{datetime.now().strftime('%d-%m-%y')}"],
            ["Liste d'affectation des surveillants", 'Page 1/1']
        ]
        
        header_table = Table(header_data, colWidths=[14*cm, 4*cm])
        header_table.setStyle(TableStyle([
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e3a8a')),
            ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#e6f0ff')),
            ('FONT', (0, 0), (-1, -1), 'Helvetica-Bold', 11),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#1e3a8a')),
            ('ROWBACKGROUNDS', (0, 0), (-1, -1), [colors.white, colors.HexColor('#f0f4ff')])
        ]))
        
        elements.append(header_table)
        elements.append(Spacer(1, 1*cm))
        
        # "Notes à" section
        elements.append(Paragraph("Notes à", subtitle_style))
        elements.append(Spacer(1, 0.3*cm))
        
        # Teacher name
        elements.append(Paragraph(f"<b>{full_name}</b>", subtitle_style))
        elements.append(Spacer(1, 0.5*cm))
        
        # Greeting text
        greeting = """Cher (e) Collègue,<br/>
        Vous êtes prié (e) d'assurer la surveillance et (ou) la responsabilité des examens selon le calendrier ci-joint."""
        elements.append(Paragraph(greeting, normal_style))
        elements.append(Spacer(1, 0.5*cm))
        
        # Prepare schedule data
        schedule_data = [['Date', 'Heure', 'Durée']]
        
        for slot in sorted(teacher_slots[teacher_code]):
            try:
                parts = slot.split()
                date_str = parts[0]
                session = parts[1].lower()
                
                # Format date
                date_obj = datetime.strptime(date_str, '%Y-%m-%d')
                formatted_date = date_obj.strftime('%Y-%m-%d')
                
                # Get time
                time = SESSION_TIMES.get(session, '08:30:00')
                
                # Duration (default 1.5H)
                duration = '1.5 H'
                
                schedule_data.append([formatted_date, time, duration])
            except:
                schedule_data.append([slot, 'N/A', '1.5 H'])
        
        # Create schedule table
        schedule_table = Table(schedule_data, colWidths=[6*cm, 6*cm, 6*cm])
        schedule_table.setStyle(TableStyle([
            # Header row
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1e3a8a')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONT', (0, 0), (-1, 0), 'Helvetica-Bold', 12),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            # Data rows
            ('FONT', (0, 1), (-1, -1), 'Helvetica', 11),
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#1e3a8a')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#e6f0ff'), colors.white])
        ]))
        
        elements.append(schedule_table)
        
        # Build PDF
        doc.build(elements)
        pdf_count += 1
    
    # Show success message
    app.show_success_message(
        "✅ Export Réussi", 
        f"{pdf_count} PDF(s) générés dans le dossier '{output_folder}'"
    )
    
    return pdf_count