import os
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image, PageBreak
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
import logging

from app.config import Config
from app.models import User, Measurement

logger = logging.getLogger(__name__)


class PDFService:
    """Сервис для генерации PDF-отчётов"""

    def __init__(self):
        Config.ensure_temp_folder()
        self.temp_folder = Path(Config.TEMP_FOLDER)
        self.styles = getSampleStyleSheet()
        self._create_custom_styles()
        self._cleanup_old_pdfs()

    def _create_custom_styles(self):
        """Создаёт кастомные стили для PDF"""
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontSize=20,
            textColor=colors.HexColor('#2E4053'),
            spaceAfter=30,
            alignment=TA_CENTER,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontSize=14,
            textColor=colors.HexColor('#2E4053'),
            spaceAfter=12,
            spaceBefore=10,
            fontName='Helvetica-Bold'
        ))

        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontSize=10,
            spaceAfter=6,
            fontName='Helvetica'
        ))

        self.styles.add(ParagraphStyle(
            name='CustomSmall',
            parent=self.styles['Normal'],
            fontSize=8,
            textColor=colors.HexColor('#7F8C8D'),
            spaceAfter=4,
            fontName='Helvetica'
        ))

    def _cleanup_old_pdfs(self, days: int = 7):
        """Удаляет PDF-файлы старше указанного количества дней."""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            for pdf_file in self.temp_folder.glob("report_*.pdf"):
                try:
                    file_mtime = datetime.fromtimestamp(pdf_file.stat().st_mtime)
                    if file_mtime < cutoff_time:
                        pdf_file.unlink()
                except Exception as e:
                    logger.warning(f"Could not remove old PDF {pdf_file.name}: {e}")
        except Exception as e:
            logger.warning(f"Error during PDF cleanup: {e}")

    async def generate_client_report(
        self,
        user_id: int,
        client: User,
        measurements: List[Measurement],
        chart_path: Optional[str] = None
    ) -> Optional[str]:
        """Генерирует PDF-отчёт для клиента."""
        filepath = self.temp_folder / f"report_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pdf"

        try:
            doc = SimpleDocTemplate(
                str(filepath),
                pagesize=A4,
                rightMargin=72,
                leftMargin=72,
                topMargin=72,
                bottomMargin=72,
                title=f"Fitness Report - {client.full_name or 'Client'}",
                author="Fitness Bot"
            )

            story = []

            # Заголовок
            story.append(Paragraph("📊 Отчёт о прогрессе", self.styles['CustomTitle']))
            story.append(Spacer(1, 0.25 * inch))

            # Информация о клиенте
            story.append(Paragraph("Информация о клиенте", self.styles['CustomHeading']))
            story.append(Spacer(1, 0.1 * inch))

            goal_map = {
                "weight_loss": "Похудение",
                "muscle_gain": "Набор массы",
                "maintain": "Поддержание"
            }

            info_data = [
                ["Имя:", client.full_name or "Не указано"],
                ["Возраст:", str(client.age) if client.age else "Не указан"],
                ["Рост:", f"{client.height} см" if client.height else "Не указан"],
                ["Цель:", goal_map.get(client.goal, client.goal or "Не указана")],
                ["Дата отчёта:", datetime.now().strftime("%d.%m.%Y %H:%M")],
                ["Кол-во замеров:", str(len(measurements))]
            ]

            info_table = Table(info_data, colWidths=[2 * inch, 3.5 * inch])
            info_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#EBF5FB')),
                ('TEXTCOLOR', (0, 0), (0, -1), colors.HexColor('#2E4053')),
                ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
                ('ALIGN', (1, 0), (1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D5D8DC')),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 6),
            ]))
            story.append(info_table)
            story.append(Spacer(1, 0.3 * inch))

            # Таблица замеров
            story.append(Paragraph("Замеры (последние 4 недели)", self.styles['CustomHeading']))
            story.append(Spacer(1, 0.1 * inch))

            if measurements:
                sorted_measurements = sorted(measurements, key=lambda m: m.measured_at, reverse=True)
                recent_measurements = sorted_measurements[:14]

                table_data = [["Дата", "Вес (кг)", "Талия (см)", "Бёдра (см)", "Грудь (см)", "Бицепс (см)"]]

                for m in recent_measurements:
                    table_data.append([
                        m.measured_at.strftime("%d.%m.%Y"),
                        f"{m.weight:.1f}" if m.weight else "—",
                        f"{m.waist:.1f}" if m.waist else "—",
                        f"{m.hips:.1f}" if m.hips else "—",
                        f"{m.chest:.1f}" if m.chest else "—",
                        f"{m.biceps:.1f}" if m.biceps else "—"
                    ])

                col_widths = [1.2 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch, 1.0 * inch]
                measure_table = Table(table_data, colWidths=col_widths, repeatRows=1)
                measure_table.setStyle(TableStyle([
                    ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
                    ('FONTSIZE', (0, 0), (-1, -1), 8),
                    ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4053')),
                    ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#D5D8DC')),
                    ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                    ('PADDING', (0, 0), (-1, -1), 4),
                    ('FONTSIZE', (0, 1), (-1, -1), 7),
                ]))
                story.append(measure_table)

                if len(measurements) > 14:
                    story.append(Paragraph(
                        f"Показаны последние 14 замеров из {len(measurements)}",
                        self.styles['CustomSmall']
                    ))
                story.append(Spacer(1, 0.3 * inch))
            else:
                story.append(Paragraph(
                    "Нет записей замеров. Начните отслеживать прогресс.",
                    self.styles['CustomNormal']
                ))
                story.append(Spacer(1, 0.3 * inch))

            # График
            if chart_path and Path(chart_path).exists():
                story.append(PageBreak())
                story.append(Paragraph("График прогресса", self.styles['CustomHeading']))
                story.append(Spacer(1, 0.1 * inch))

                try:
                    img = Image(chart_path, width=6 * inch, height=3.5 * inch)
                    story.append(img)
                    story.append(Spacer(1, 0.3 * inch))
                except Exception as e:
                    logger.error(f"Failed to add chart to PDF: {e}")

            # Сводка прогресса
            if measurements:
                story.append(PageBreak())
                story.append(Paragraph("Сводка прогресса", self.styles['CustomHeading']))
                story.append(Spacer(1, 0.1 * inch))

                sorted_by_date = sorted(measurements, key=lambda m: m.measured_at)

                if len(sorted_by_date) >= 2:
                    first = sorted_by_date[0]
                    last = sorted_by_date[-1]

                    summary_parts = []

                    if first.weight and last.weight:
                        weight_change = last.weight - first.weight
                        if weight_change < 0:
                            summary_parts.append(f"✅ Потеря веса: {abs(weight_change):.1f} кг")
                        elif weight_change > 0:
                            summary_parts.append(f"⚠️ Увеличение веса: {weight_change:.1f} кг")
                        else:
                            summary_parts.append("➖ Вес стабилен")

                    if first.waist and last.waist:
                        waist_change = last.waist - first.waist
                        if waist_change < 0:
                            summary_parts.append(f"✅ Уменьшение талии: {abs(waist_change):.1f} см")
                        elif waist_change > 0:
                            summary_parts.append(f"⚠️ Увеличение талии: {waist_change:.1f} см")
                        else:
                            summary_parts.append("➖ Талия стабильна")

                    if summary_parts:
                        for part in summary_parts:
                            story.append(Paragraph(part, self.styles['CustomNormal']))
                    else:
                        story.append(Paragraph(
                            "Недостаточно данных для анализа прогресса",
                            self.styles['CustomNormal']
                        ))
                else:
                    story.append(Paragraph(
                        "Недостаточно замеров для анализа прогресса (нужно минимум 2 замера)",
                        self.styles['CustomNormal']
                    ))

            # Футер
            story.append(Spacer(1, 0.5 * inch))
            story.append(Paragraph(
                f"Отчёт сгенерирован автоматически {datetime.now().strftime('%d.%m.%Y %H:%M')}",
                self.styles['CustomSmall']
            ))

            doc.build(story)

            logger.info(f"✅ PDF report generated: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"❌ Failed to generate PDF: {e}")
            return None
