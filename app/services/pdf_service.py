from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, cm
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime, timedelta
from typing import List, Dict
from pathlib import Path
from app.config import Config
from app.models import User, Measurement

class PDFService:
    def __init__(self):
        Config.ensure_temp_folder()
        self.styles = getSampleStyleSheet()
        self.create_custom_styles()
    
    def create_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#2E4053'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2E4053'),
            spaceAfter=12
        ))
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6
        ))
    
    async def generate_client_report(self, user_id: int, client: User, 
                                     measurements: List[Measurement], chart_path: str) -> str:
        filepath = Path(Config.TEMP_FOLDER) / f"report_{user_id}.pdf"
        
        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )
        
        story = []
        
        story.append(Paragraph("Fitness Progress Report", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.25*inch))
        
        story.append(Paragraph("Client Information", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        
        info_data = [
            ["Name:", client.full_name or "N/A"],
            ["Age:", str(client.age) if client.age else "N/A"],
            ["Height:", f"{client.height} cm" if client.height else "N/A"],
            ["Goal:", client.goal or "N/A"],
            ["Report Date:", datetime.now().strftime("%d/%m/%Y")]
        ]
        
        info_table = Table(info_data, colWidths=[2*inch, 3*inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2E4053')),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('PADDING', (0, 0), (-1, -1), 6),
        ]))
        story.append(info_table)
        story.append(Spacer(1, 0.3*inch))
        
        story.append(Paragraph("Measurements (Last 4 Weeks)", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        
        if measurements:
            table_data = [["Date", "Weight (kg)", "Waist (cm)", "Hips (cm)", "Chest (cm)", "Biceps (cm)"]]
            
            for m in measurements[-10:]:
                table_data.append([
                    m.measured_at.strftime("%d/%m/%Y"),
                    f"{m.weight:.1f}" if m.weight else "-",
                    f"{m.waist:.1f}" if m.waist else "-",
                    f"{m.hips:.1f}" if m.hips else "-",
                    f"{m.chest:.1f}" if m.chest else "-",
                    f"{m.biceps:.1f}" if m.biceps else "-"
                ])
            
            measure_table = Table(table_data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
            measure_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4053')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(measure_table)
            story.append(Spacer(1, 0.3*inch))
        else:
            story.append(Paragraph("No measurements recorded yet.", self.styles['CustomNormal']))
            story.append(Spacer(1, 0.3*inch))
        
        if chart_path:
            story.append(Paragraph("Weight Progress Chart", self.styles['CustomHeading']))
            story.append(Spacer(1, 0.1*inch))
            img = Image(chart_path, width=6*inch, height=3.5*inch)
            story.append(img)
            story.append(Spacer(1, 0.3*inch))
        
        story.append(Paragraph("Progress Summary", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1*inch))
        
        if len(measurements) >= 2:
            first = measurements[0]
            last = measurements[-1]
            
            summary_text = ""
            
            if first.weight and last.weight:
                weight_change = last.weight - first.weight
                if weight_change < 0:
                    summary_text += f"✅ Lost {abs(weight_change):.1f} kg of body weight. "
                else:
                    summary_text += f"⚠️ Gained {weight_change:.1f} kg of body weight. "
            
            if first.waist and last.waist:
                waist_change = last.waist - first.waist
                if waist_change < 0:
                    summary_text += f"✅ Reduced waist by {abs(waist_change):.1f} cm. "
                else:
                    summary_text += f"⚠️ Waist increased by {waist_change:.1f} cm. "
            
            if not summary_text:
                summary_text = "Insufficient data for progress analysis."
            
            story.append(Paragraph(summary_text, self.styles['CustomNormal']))
            story.append(Spacer(1, 0.1*inch))
            
            if first.weight and last.weight and last.weight < first.weight:
                story.append(Paragraph("💪 Good job on weight loss! Continue with your current routine.", 
                                      self.styles['CustomNormal']))
            elif first.weight and last.weight and last.weight > first.weight and client.goal == "weight_loss":
                story.append(Paragraph("⚠️ Weight increased. Consider reviewing your diet and exercise plan.", 
                                      self.styles['CustomNormal']))
        else:
            story.append(Paragraph("Need at least 2 measurements for progress analysis.", 
                                  self.styles['CustomNormal']))
        
        doc.build(story)
        return str(filepath)