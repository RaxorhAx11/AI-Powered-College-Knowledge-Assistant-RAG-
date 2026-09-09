"""
Script to create synthetic GLS-style test documents for Phase 5.
Generates PDFs covering academic regulations, student handbook (multi-column),
BCA syllabus (with credit tables), exam circulars (with dates/deadlines),
and BCA timetables.
"""

import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import (
        SimpleDocTemplate, Paragraph, Spacer, PageBreak, Table, TableStyle, Frame, PageTemplate
    )
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    import fitz
    HAS_REPORTLAB = False

def create_academic_regulations(output_path: Path):
    """Generate GLS_Academic_Regulations_2025.pdf."""
    print(f"Generating GLS document: {output_path.name}...")
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=16, leading=20, spaceAfter=10)
    heading_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=12, leading=16, spaceAfter=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=9, leading=13, spaceAfter=5)

    story = []
    # Header
    story.append(Paragraph("GLS UNIVERSITY — ACADEMIC REGULATIONS 2025", title_style))
    story.append(Paragraph("Document Ref: GLS/ACAD/REG/2025/v1 | Effective Date: July 1, 2025", body_style))
    story.append(Spacer(1, 10))

    # Chapter 1
    story.append(Paragraph("Chapter 1: Attendance & Condonation Rules", heading_style))
    story.append(Paragraph(
        "1.1 Minimum Requirement: All undergraduate (BCA, BBA, BCom) and postgraduate (MCA, MBA) students "
        "must maintain a minimum of 75% attendance in each course to appear for End-Semester Examinations.", body_style
    ))
    story.append(Paragraph(
        "1.2 Medical Condonation: Attendance shortage up to 10% (between 65% and 74%) may be condoned by the Dean "
        "on valid medical grounds, provided medical certificates are submitted within 5 working days.", body_style
    ))
    story.append(Paragraph(
        "1.3 Disqualification: Students with attendance below 65% will receive 'F-ATT' grade and must repeat the course.", body_style
    ))
    story.append(Spacer(1, 10))

    # Chapter 2 with Table
    story.append(Paragraph("Chapter 2: Grading System & GPA Calculation", heading_style))
    story.append(Paragraph("Performance is evaluated on a 10-point scale as specified in Table 1 below:", body_style))

    table_data = [
        ["Grade", "Grade Points", "Marks Range", "Performance Description"],
        ["O", "10.0", "90% – 100%", "Outstanding"],
        ["A+", "9.0", "80% – 89%", "Excellent"],
        ["A", "8.0", "70% – 79%", "Very Good"],
        ["B+", "7.0", "60% – 69%", "Good"],
        ["B", "6.0", "55% – 59%", "Above Average"],
        ["C", "5.0", "50% – 54%", "Average"],
        ["D", "4.0", "40% – 49%", "Pass"],
        ["F", "0.0", "< 40%", "Fail"]
    ]
    t = Table(table_data, colWidths=[60, 75, 90, 150])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    story.append(t)

    doc.build(story)
    print(f"Created {output_path.name}")

def create_student_handbook(output_path: Path):
    """Generate GLS_Student_Handbook_2025.pdf."""
    print(f"Generating GLS document: {output_path.name}...")
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=16, leading=20, spaceAfter=10)
    heading_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=12, leading=16, spaceAfter=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=9, leading=13, spaceAfter=5)

    story = []
    story.append(Paragraph("GLS UNIVERSITY — STUDENT HANDBOOK 2025", title_style))
    story.append(Paragraph("Document Type: student_handbook | Academic Year: 2025-2026", body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Section 1: Central Library Regulations", heading_style))
    story.append(Paragraph("1.1 Library Operating Hours: Working days: 8:00 AM to 11:00 PM. Weekends: 9:00 AM to 5:00 PM.", body_style))
    story.append(Paragraph("1.2 Borrowing Limits: UG Students: 5 books for 14 days. PG Students: 8 books for 30 days.", body_style))
    story.append(Paragraph("1.3 Overdue Fines: A fine of $1.00 (or local equivalent) per day per book applies to late returns.", body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Section 2: Hostel Rules & Curfew", heading_style))
    story.append(Paragraph("2.1 Hostel Curfew: All resident students must enter hostel premises by 9:30 PM.", body_style))
    story.append(Paragraph("2.2 Mess Timings: Breakfast: 7:30 AM – 9:00 AM | Lunch: 12:00 PM – 2:00 PM | Dinner: 7:30 PM – 9:30 PM.", body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("Section 3: Placement Policy & Eligibility", heading_style))
    story.append(Paragraph("3.1 Eligibility: Minimum CGPA of 6.5 with no active backlogs at the time of campus recruitment drives.", body_style))
    story.append(Paragraph("3.2 Merit Scholarship: CGPA 9.0 or above qualifies for a 25% tuition fee waiver.", body_style))

    doc.build(story)
    print(f"Created {output_path.name}")

def create_bca_syllabus(output_path: Path):
    """Generate GLS_BCA_Syllabus_Sem3.pdf with structured tables."""
    print(f"Generating GLS document: {output_path.name}...")
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=16, leading=20, spaceAfter=10)
    heading_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=12, leading=16, spaceAfter=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=9, leading=13, spaceAfter=5)

    story = []
    story.append(Paragraph("GLS UNIVERSITY — DEPARTMENT OF COMPUTER APPLICATIONS", title_style))
    story.append(Paragraph("Course: Bachelor of Computer Applications (BCA) | Semester 3 Syllabus | Academic Year: 2025", body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("BCA Semester 3 Course Structure & Credit Table", heading_style))

    table_data = [
        ["Course Code", "Subject Name", "Course Type", "Credits", "Theory Marks", "Practical Marks"],
        ["BCA-301", "Database Management Systems (DBMS)", "Core Theory", "4", "70", "30"],
        ["BCA-302", "Object Oriented Programming with Java", "Core Theory", "4", "70", "30"],
        ["BCA-303", "Data Structures & Algorithms", "Core Theory", "4", "70", "30"],
        ["BCA-304", "Web Application Development (RAG/Python)", "Core Theory", "4", "70", "30"],
        ["BCA-305", "DBMS & Java Lab", "Practical Lab", "2", "0", "50"]
    ]
    t = Table(table_data, colWidths=[65, 170, 75, 45, 60, 60])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#0F172A')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'LEFT'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Detailed Syllabus Units for BCA-301: Database Management Systems", heading_style))
    story.append(Paragraph("Unit 1: Introduction to Relational Databases, ER Diagrams, Relational Algebra.", body_style))
    story.append(Paragraph("Unit 2: SQL Fundamentals, DDL, DML, Complex Queries, Joins, and Subqueries.", body_style))
    story.append(Paragraph("Unit 3: Database Normalization (1NF, 2NF, 3NF, BCNF), Functional Dependencies.", body_style))
    story.append(Paragraph("Unit 4: Transaction Management, ACID Properties, Concurrency Control, Recovery.", body_style))

    doc.build(story)
    print(f"Created {output_path.name}")

def create_exam_notice(output_path: Path):
    """Generate GLS_Exam_Notice_Nov2025.pdf."""
    print(f"Generating GLS document: {output_path.name}...")
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=16, leading=20, spaceAfter=10)
    heading_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=12, leading=16, spaceAfter=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=9, leading=13, spaceAfter=5)

    story = []
    story.append(Paragraph("GLS UNIVERSITY — OFFICE OF THE CONTROLLER OF EXAMINATIONS", title_style))
    story.append(Paragraph("CIRCULAR / NOTICE Ref: GLS/EXAM/2025/1102 | Date of Issue: November 5, 2025", body_style))
    story.append(Spacer(1, 10))

    story.append(Paragraph("IMPORTANT NOTICE: End-Semester Examination Registration & Fee Deadline", heading_style))
    story.append(Paragraph(
        "All undergraduate and postgraduate students are hereby notified that the registration portal for the "
        "Winter 2025 End-Semester Examinations is now open. "
        "The hard deadline to complete exam registration and fee payment is November 25, 2025 at 5:00 PM.", body_style
    ))
    story.append(Paragraph(
        "Late Registration: Registration submitted between November 26, 2025 and November 30, 2025 will incur a late fee of $15. "
        "No applications will be accepted after November 30, 2025.", body_style
    ))
    story.append(Paragraph("Issuing Authority: Controller of Examinations, GLS University.", body_style))

    doc.build(story)
    print(f"Created {output_path.name}")

def create_bca_timetable(output_path: Path):
    """Generate GLS_BCA_Timetable_Sem3.pdf with grid layout."""
    print(f"Generating GLS document: {output_path.name}...")
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=16, leading=20, spaceAfter=10)
    heading_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=12, leading=16, spaceAfter=6)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=9, leading=13, spaceAfter=5)

    story = []
    story.append(Paragraph("GLS UNIVERSITY — BCA SEMESTER 3 CLASS TIMETABLE", title_style))
    story.append(Paragraph("Document Type: timetable | Academic Year: 2025-2026 | Effective Date: Aug 1, 2025", body_style))
    story.append(Spacer(1, 10))

    table_data = [
        ["Day / Time", "09:00 – 10:00 AM", "10:00 – 11:00 AM", "11:15 – 12:15 PM", "01:00 – 03:00 PM"],
        ["Monday", "BCA-301 (DBMS) Room 201", "BCA-302 (Java) Room 201", "BCA-303 (DSA) Room 201", "BCA-305 DBMS Lab (Lab 2)"],
        ["Tuesday", "BCA-303 (DSA) Room 201", "BCA-304 (Web Dev) Room 201", "BCA-301 (DBMS) Room 201", "BCA-305 Java Lab (Lab 3)"],
        ["Wednesday", "BCA-302 (Java) Room 201", "BCA-301 (DBMS) Room 201", "BCA-304 (Web Dev) Room 201", "Library Study Session"],
        ["Thursday", "BCA-304 (Web Dev) Room 201", "BCA-303 (DSA) Room 201", "BCA-302 (Java) Room 201", "Mentoring & Seminars"],
        ["Friday", "BCA-301 (DBMS) Room 201", "BCA-302 (Java) Room 201", "BCA-303 (DSA) Room 201", "Sports & Co-curricular"]
    ]
    t = Table(table_data, colWidths=[70, 100, 100, 100, 110])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1E293B')),
        ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
        ('FONTSIZE', (0,0), (-1,-1), 8),
        ('BOTTOMPADDING', (0,0), (-1,0), 4),
        ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
    ]))
    story.append(t)

    doc.build(story)
    print(f"Created {output_path.name}")

def main():
    Config.ensure_directories()
    docs_dir = Config.DOCUMENTS_DIR

    create_academic_regulations(docs_dir / "GLS_Academic_Regulations_2025.pdf")
    create_student_handbook(docs_dir / "GLS_Student_Handbook_2025.pdf")
    create_bca_syllabus(docs_dir / "GLS_BCA_Syllabus_Sem3.pdf")
    create_exam_notice(docs_dir / "GLS_Exam_Notice_Nov2025.pdf")
    create_bca_timetable(docs_dir / "GLS_BCA_Timetable_Sem3.pdf")

    print("\nAll synthetic GLS-style test documents generated in data/documents/ successfully!")

if __name__ == "__main__":
    main()
