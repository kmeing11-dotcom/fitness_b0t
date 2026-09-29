# app/services/pdf_service.py
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib.enums import TA_CENTER
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from datetime import datetime
from typing import List, Optional
from pathlib import Path

from app.config import Config
from app.utils.logger import get_logger

logger = get_logger(__name__)


# ============================================================
#  РЕГИСТРАЦИЯ ШРИФТОВ С КИРИЛЛИЦЕЙ
# ============================================================

def _register_fonts() -> bool:
    """
    FIX: регистрирует DejaVu Sans (поддерживает кириллицу).
    Без этого русские буквы в PDF — квадратики.
    """
    fonts_dir = Path(__file__).parent.parent / "fonts"

    candidates_regular = [
        fonts_dir / "DejaVuSans.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/DejaVuSans.ttf"),
        Path("C:/Windows/Fonts/arial.ttf"),  # fallback — тоже кириллица
    ]
    candidates_bold = [
        fonts_dir / "DejaVuSans-Bold.ttf",
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
        Path("C:/Windows/Fonts/DejaVuSans-Bold.ttf"),
        Path("C:/Windows/Fonts/arialbd.ttf"),
    ]

    regular_path = next((p for p in candidates_regular if p.exists()), None)
    bold_path = next((p for p in candidates_bold if p.exists()), None)

    if not regular_path:
        logger.warning("❌ Не найден шрифт с кириллицей — PDF будет с квадратиками")
        return False

    try:
        pdfmetrics.registerFont(TTFont('CustomFont', str(regular_path)))
        if bold_path:
            pdfmetrics.registerFont(TTFont('CustomFont-Bold', str(bold_path)))
        logger.info(f"✅ Шрифт зарегистрирован: {regular_path}")
        return True
    except Exception as e:
        logger.error(f"❌ Ошибка регистрации шрифта: {e}")
        return False


_FONTS_OK = _register_fonts()
FONT_REGULAR = 'CustomFont' if _FONTS_OK else 'Helvetica'
FONT_BOLD = 'CustomFont-Bold' if _FONTS_OK else 'Helvetica-Bold'


class PDFService:
    def __init__(self):
        Config.ensure_temp_folder()
        self.temp_folder = Path(Config.get_temp_folder())
        self.styles = getSampleStyleSheet()
        self.create_custom_styles()

    @staticmethod
    def _get(obj, key, default=None):
        if obj is None:
            return default
        if isinstance(obj, dict):
            return obj.get(key, default)
        return getattr(obj, key, default)

    def create_custom_styles(self):
        self.styles.add(ParagraphStyle(
            name='CustomTitle',
            parent=self.styles['Heading1'],
            fontName=FONT_BOLD,
            fontSize=18,
            textColor=colors.HexColor('#2E4053'),
            spaceAfter=30,
            alignment=TA_CENTER
        ))
        self.styles.add(ParagraphStyle(
            name='CustomHeading',
            parent=self.styles['Heading2'],
            fontName=FONT_BOLD,
            fontSize=14,
            textColor=colors.HexColor('#2E4053'),
            spaceAfter=12
        ))
        self.styles.add(ParagraphStyle(
            name='CustomNormal',
            parent=self.styles['Normal'],
            fontName=FONT_REGULAR,
            fontSize=10,
            spaceAfter=6
        ))

    async def generate_client_report(
        self,
        user_id: int,
        client,
        measurements: List,
        chart_path: Optional[str] = None
    ) -> Optional[str]:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filepath = self.temp_folder / f"report_{user_id}_{timestamp}.pdf"

        doc = SimpleDocTemplate(
            str(filepath),
            pagesize=A4,
            rightMargin=72,
            leftMargin=72,
            topMargin=72,
            bottomMargin=72
        )

        story = []

        # Заголовок
        story.append(Paragraph("Отчёт о прогрессе", self.styles['CustomTitle']))
        story.append(Spacer(1, 0.25 * inch))

        # Информация о клиенте
        story.append(Paragraph("Информация о клиенте", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1 * inch))

        goal_map = {
            "weight_loss": "Похудение",
            "muscle_gain": "Набор массы",
            "maintain": "Поддержание",
        }

        full_name = self._get(client, 'full_name') or "Не указано"
        age = self._get(client, 'age')
        height = self._get(client, 'height')
        goal = self._get(client, 'goal')

        info_data = [
            ["Имя:", str(full_name)],
            ["Возраст:", str(age) if age else "Не указан"],
            ["Рост:", f"{height} см" if height else "Не указан"],
            ["Цель:", goal_map.get(goal, goal or "Не указана")],
            ["Дата отчёта:", datetime.now().strftime("%d.%m.%Y")],
        ]

        info_table = Table(info_data, colWidths=[2 * inch, 3 * inch])
        info_table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), FONT_REGULAR),
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
        story.append(Spacer(1, 0.3 * inch))

        # Таблица замеров
        story.append(Paragraph("Замеры (последние 4 недели)", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1 * inch))

        if measurements:
            table_data = [[
                "Дата", "Вес (кг)", "Талия (см)",
                "Бёдра (см)", "Грудь (см)", "Бицепс (см)"
            ]]

            for m in measurements[-10:]:
                measured_at = self._get(m, 'measured_at')
                date_str = measured_at.strftime("%d.%m.%Y") if measured_at else "-"

                def fmt(v):
                    return f"{v:.1f}" if v is not None else "-"

                table_data.append([
                    date_str,
                    fmt(self._get(m, 'weight')),
                    fmt(self._get(m, 'waist')),
                    fmt(self._get(m, 'hips')),
                    fmt(self._get(m, 'chest')),
                    fmt(self._get(m, 'biceps')),
                ])

            measure_table = Table(table_data, colWidths=[1.1 * inch] * 6)
            measure_table.setStyle(TableStyle([
                ('FONTNAME', (0, 0), (-1, -1), FONT_REGULAR),
                ('FONTSIZE', (0, 0), (-1, -1), 8),
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2E4053')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.lightgrey),
                ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
                ('PADDING', (0, 0), (-1, -1), 4),
            ]))
            story.append(measure_table)
            story.append(Spacer(1, 0.3 * inch))
        else:
            story.append(Paragraph("Замеры пока отсутствуют.", self.styles['CustomNormal']))
            story.append(Spacer(1, 0.3 * inch))

        # График
        if chart_path and Path(chart_path).exists():
            story.append(Paragraph("График прогресса веса", self.styles['CustomHeading']))
            story.append(Spacer(1, 0.1 * inch))
            try:
                img = Image(chart_path, width=6 * inch, height=3.5 * inch)
                story.append(img)
                story.append(Spacer(1, 0.3 * inch))
            except Exception as e:
                logger.warning(f"Не удалось вставить график в PDF: {e}")

        # Сводка
        story.append(Paragraph("Сводка изменений", self.styles['CustomHeading']))
        story.append(Spacer(1, 0.1 * inch))

        if len(measurements) >= 2:
            first = measurements[0]
            last = measurements[-1]

            summary_text = ""

            first_w = self._get(first, 'weight')
            last_w = self._get(last, 'weight')
            if first_w is not None and last_w is not None:
                change = last_w - first_w
                if change < 0:
                    summary_text += f"Снижение веса на {abs(change):.1f} кг. "
                elif change > 0:
                    summary_text += f"Набор веса {change:.1f} кг. "
                else:
                    summary_text += "Вес без изменений. "

            first_waist = self._get(first, 'waist')
            last_waist = self._get(last, 'waist')
            if first_waist is not None and last_waist is not None:
                change = last_waist - first_waist
                if change < 0:
                    summary_text += f"Уменьшение талии на {abs(change):.1f} см. "
                elif change > 0:
                    summary_text += f"Увеличение талии на {change:.1f} см. "

            if not summary_text:
                summary_text = "Недостаточно данных для анализа."

            story.append(Paragraph(summary_text, self.styles['CustomNormal']))
            story.append(Spacer(1, 0.1 * inch))

            goal = self._get(client, 'goal')
            if first_w is not None and last_w is not None:
                if last_w < first_w:
                    story.append(Paragraph(
                        "Отличный результат! Продолжайте в том же духе.",
                        self.styles['CustomNormal']
                    ))
                elif last_w > first_w and goal == "weight_loss":
                    story.append(Paragraph(
                        "Вес вырос. Рекомендуется пересмотреть питание и нагрузку.",
                        self.styles['CustomNormal']
                    ))
        else:
            story.append(Paragraph(
                "Для анализа нужно минимум 2 замера.",
                self.styles['CustomNormal']
            ))

        try:
            doc.build(story)
            logger.info(f"✅ PDF generated: {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"❌ Failed to build PDF: {e}")
            return None
