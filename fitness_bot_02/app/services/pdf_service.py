from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from datetime import datetime
from pathlib import Path
from app.config import Config
from app.models import User, Measurement

class PDFService:
    def __init__(self):
        Config.ensure_temp_folder()
        self.styles = getSampleStyleSheet()
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#2E4053'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))

    async def generate_client_report(self, user_id: int, client: User, measurements: list[Measurement], chart_path: str) -> str:
        filepath = Path(Config.TEMP_FOLDER) / f"report_{user_id}.pdf"
        doc = SimpleDocTemplate(str(filepath), pagesize=A4, topMargin=72, bottomMargin=72)
        story = []

        story.append(Paragraph("Отчёт о прогрессе", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.25*inch))

        # Инфо о клиенте
        info_data = [
            ["Имя:", client.full_name or "N/A"],
            ["Возраст:", str(client.age) if client.age else "N/A"],
            ["Рост:", f"{client.height} см" if client.height else "N/A"],
            ["Цель:", client.goal or "N/A"],
            ["Дата отчёта:", datetime.now().strftime("%d/%m/%Y")]
        ]
        info_table = Table(info_data, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0,0), (-1,-1), 'Helvetica'),
            ('BACKGROUND', (0,0), (0,-1), colors.lightgrey),
            ('ALIGN', (0,0), (0,-1), 'RIGHT'),
            ('ALIGN', (1,0), (1,-1), 'LEFT'),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('PADDING', (0,0), (-1,-1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))

        # Таблица замеров
        if measurements:
            table_data = [["Дата", "Вес (кг)", "Талия (см)", "Бедра (см)", "Грудь (см)"]]
            for m in measurements[-10:]:
                table_data.append([
                    m.measured_at.strftime("%d/%m/%Y"),
                    f"{m.weight:.1f}" if m.weight else "-",
                    f"{m.waist:.1f}" if m.waist else "-",
                    f"{m.hips:.1f}" if m.hips else "-",
                    f"{m.chest:.1f}" if m.chest else "-"
                ])
            measure_table = Table(table_data, colWidths=[1.2*inch]*5)
            measure_table.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#2E4053')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.white),
                ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.lightgrey),
            ]))
            story.append(measure_table)
            story.append(Spacer(1, 0.3*inch))

        # График
        if chart_path:
            story.append(Image(chart_path, width=6*inch, height=3.5*inch))

        doc.build(story)
        return str(filepath)