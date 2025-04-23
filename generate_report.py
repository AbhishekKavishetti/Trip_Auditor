# from fpdf2 import FPDF
# import os
# import uuid

# def generate_ai_report(insights):
#     class PDF(FPDF):
#         def header(self):
#             self.set_font("Arial", "B", 16)
#             self.cell(0, 10, "AI Insights Report", ln=True, align="C")

#         def chapter_body(self, text):
#             self.set_font("Arial", "", 12)
#             self.multi_cell(0, 10, text)

#     pdf = PDF()
#     pdf.add_page()
#     pdf.chapter_body("\n".join(insights) if insights else "No insights available.")
#     filename = f"ai_report_{uuid.uuid4().hex[:6]}.pdf"
#     file_path = os.path.join(os.getcwd(), filename)
#     pdf.output(file_path)
#     return file_path