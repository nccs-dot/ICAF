import os
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet


class PDFGenerator:

    def __init__(self, output_dir):

        self.output_dir = output_dir
        self.styles = getSampleStyleSheet()

    def generate(self, context, results):

        report_path = os.path.join(self.output_dir, "tcaf_report.pdf")

        elements = []

        elements.append(
            Paragraph(
                "Telecom Compliance Automation Framework (TCAF)",
                self.styles["Title"]
            )
        )

        elements.append(Spacer(1, 20))

        elements.append(
            Paragraph(f"Execution ID: {context.execution_id}", self.styles["Normal"])
        )

        elements.append(
            Paragraph(f"DUT IP: {context.ssh_ip}", self.styles["Normal"])
        )

        elements.append(
            Paragraph(f"Clause: {context.clause}", self.styles["Normal"])
        )

        elements.append(Spacer(1, 20))

        for tc in results:

            elements.append(
                Paragraph(f"Test Case: {tc.name}", self.styles["Heading2"])
            )

            elements.append(
                Paragraph(f"Description: {tc.description}", self.styles["Normal"])
            )

            elements.append(
                Paragraph(f"Status: {tc.status}", self.styles["Normal"])
            )

            elements.append(Spacer(1, 10))

            for evidence in tc.evidence:

                if os.path.exists(evidence):

                    elements.append(Image(evidence, width=450, height=250))

                    elements.append(Spacer(1, 10))

            elements.append(Spacer(1, 20))

        doc = SimpleDocTemplate(report_path, pagesize=A4)

        doc.build(elements)

        return report_path