from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import os
import uuid

def generate_ai_report(insights):
    filename = f"ai_report_{uuid.uuid4().hex[:6]}.pdf"
    file_path = os.path.join(os.getcwd(), filename)

    c = canvas.Canvas(file_path, pagesize=letter)
    width, height = letter
    y_position = height - 40

    c.setFont("Helvetica-Bold", 16)
    c.drawCentredString(width / 2.0, y_position, "AI Insights Report")

    c.setFont("Helvetica", 12)
    y_position -= 40

    if not insights:
        c.drawString(50, y_position, "No insights available.")
    else:
        for line in insights:
            if y_position < 50:
                c.showPage()
                y_position = height - 40
            c.drawString(50, y_position, f"- {line}")
            y_position -= 20

    c.save()
    return file_path
