import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.config import Config

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
except ImportError:
    import fitz

def generate_academic_regulations_pdf(output_path: Path):
    """Generate Academic_Regulations.pdf using ReportLab or PyMuPDF."""
    print(f"Generating sample document: {output_path.name}...")
    
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, leading=22, spaceAfter=12)
    heading_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=14, leading=18, spaceAfter=8)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=6)
    
    story = []
    
    # Page 1
    story.append(Paragraph("ACADEMIC REGULATIONS 2026", title_style))
    story.append(Paragraph("Chapter 1: Attendance Requirements", heading_style))
    story.append(Paragraph(
        "1.1 Minimum Attendance: All undergraduate and postgraduate students must maintain a minimum of 75% attendance "
        "in every registered course to be eligible to appear for the End-Semester Examinations.", body_style
    ))
    story.append(Paragraph(
        "1.2 Condonation of Shortage: A shortage of attendance up to 10% (i.e. attendance between 65% and 74%) may be condoned "
        "by the Dean of Academic Affairs on medical grounds, provided valid medical documents are submitted within 5 working days.", body_style
    ))
    story.append(Paragraph(
        "1.3 Disqualification: Students with attendance below 65% in any course will receive an 'F-ATT' grade and must repeat the course.", body_style
    ))
    story.append(Spacer(1, 15))
    story.append(Paragraph("Chapter 2: Grading System & CGPA", heading_style))
    story.append(Paragraph(
        "2.1 Performance is evaluated on a 10-point Cumulative Grade Point Average (CGPA) scale. Grades range from 'O' (10 points) to 'F' (0 points).", body_style
    ))
    story.append(Paragraph(
        "2.2 Passing Criterion: A minimum letter grade of 'D' (4.0 grade points) is required to pass a theory or practical subject.", body_style
    ))
    
    story.append(PageBreak())
    
    # Page 2
    story.append(Paragraph("ACADEMIC REGULATIONS 2026 (Contd.)", title_style))
    story.append(Paragraph("Chapter 3: Examination and Re-evaluation Rules", heading_style))
    story.append(Paragraph(
        "3.1 Make-up Examinations: If a student misses an End-Semester Examination due to severe illness or hospitalization, "
        "they may apply for a Make-up Exam within 3 days of the missed exam.", body_style
    ))
    story.append(Paragraph(
        "3.2 Re-evaluation Request: Students dissatisfied with their evaluated end-semester answer scripts can apply for re-evaluation "
        "within 10 days of result publication. A non-refundable fee of $25 (or local currency equivalent) per course is applicable.", body_style
    ))
    story.append(Paragraph(
        "3.3 Maximum Duration: The maximum allowable duration to complete a 4-year Bachelor degree is 6 years from the date of admission.", body_style
    ))

    doc.build(story)
    print(f"Successfully created '{output_path}'")

def generate_student_handbook_pdf(output_path: Path):
    """Generate Student_Handbook.pdf using ReportLab."""
    print(f"Generating sample document: {output_path.name}...")
    
    doc = SimpleDocTemplate(str(output_path), pagesize=letter)
    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle('DocTitle', parent=styles['Heading1'], fontSize=18, leading=22, spaceAfter=12)
    heading_style = ParagraphStyle('SectionHeading', parent=styles['Heading2'], fontSize=14, leading=18, spaceAfter=8)
    body_style = ParagraphStyle('Body', parent=styles['Normal'], fontSize=10, leading=14, spaceAfter=6)
    
    story = []
    
    # Page 1
    story.append(Paragraph("STUDENT HANDBOOK & CAMPUS LIFE GUIDE", title_style))
    story.append(Paragraph("Section 1: Library & Digital Resources", heading_style))
    story.append(Paragraph(
        "1.1 Library Operating Hours: The Central Library remains open from 8:00 AM to 11:00 PM on working days, "
        "and 9:00 AM to 5:00 PM on weekends during normal semesters. During examination weeks, library hours are extended to 24/7.", body_style
    ))
    story.append(Paragraph(
        "1.2 Book Borrowing Limit: Undergraduate students may borrow up to 5 books for a duration of 14 days. "
        "Postgraduate students may borrow up to 8 books for 30 days.", body_style
    ))
    story.append(Paragraph(
        "1.3 Campus Wi-Fi Access: High-speed Wi-Fi is available across campus. Students must log in using their Student ID "
        "and university email credentials. Peer-to-peer torrenting and unauthorized traffic are strictly prohibited.", body_style
    ))
    
    story.append(PageBreak())
    
    # Page 2
    story.append(Paragraph("STUDENT HANDBOOK & CAMPUS LIFE GUIDE (Contd.)", title_style))
    story.append(Paragraph("Section 2: Hostel Rules & Curfew", heading_style))
    story.append(Paragraph(
        "2.1 Hostel Curfew Time: All resident students must enter their respective hostel premises by 9:30 PM. "
        "Late entry requires prior approval from the Chief Warden.", body_style
    ))
    story.append(Paragraph(
        "2.2 Mess Timings: Breakfast: 7:30 AM – 9:00 AM; Lunch: 12:00 PM – 2:00 PM; Dinner: 7:30 PM – 9:30 PM.", body_style
    ))
    story.append(Spacer(1, 15))
    story.append(Paragraph("Section 3: Scholarships & Placements", heading_style))
    story.append(Paragraph(
        "3.1 Merit Scholarship: Students securing a CGPA of 9.0 or above in an academic year receive a 25% tuition fee waiver.", body_style
    ))
    story.append(Paragraph(
        "3.2 Placement Eligibility: To participate in campus placement drives, a student must maintain a minimum CGPA of 6.5 "
        "and have no active backlogs at the time of recruitment.", body_style
    ))

    doc.build(story)
    print(f"Successfully created '{output_path}'")

def main():
    Config.ensure_directories()
    pdf1 = Config.DOCUMENTS_DIR / "Academic_Regulations.pdf"
    pdf2 = Config.DOCUMENTS_DIR / "Student_Handbook.pdf"
    
    generate_academic_regulations_pdf(pdf1)
    generate_student_handbook_pdf(pdf2)
    print("\nSample documents generation complete!")

if __name__ == "__main__":
    main()
