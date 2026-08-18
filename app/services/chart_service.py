import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime, timedelta
from typing import List, Optional
from pathlib import Path
from io import BytesIO
import logging

from app.config import Config
from app.models import Measurement

logger = logging.getLogger(__name__)


class ChartService:
    """Сервис для генерации графиков"""

    COLORS = {
        'weight': '#2E86C1',
        'waist': '#28B463',
        'hips': '#8E44AD',
        'chest': '#D4AC0D',
        'biceps': '#E67E22',
        'trend': '#E74C3C',
        'improvement': '#27AE60',
        'decline': '#E74C3C',
    }

    def __init__(self):
        Config.ensure_temp_folder()
        self.temp_folder = Path(Config.TEMP_FOLDER)
        self._setup_style()
        self._cleanup_old_charts()

    def _setup_style(self):
        """Настраивает стиль графиков"""
        plt.style.use('seaborn-v0_8-darkgrid')
        plt.rcParams['font.size'] = 10
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['axes.labelsize'] = 11
        plt.rcParams['axes.titlesize'] = 13
        plt.rcParams['legend.fontsize'] = 10
        plt.rcParams['figure.titlesize'] = 14

    def _cleanup_old_charts(self, days: int = 7):
        """Удаляет старые графики"""
        try:
            cutoff = datetime.now() - timedelta(days=days)
            for chart_file in self.temp_folder.glob("stats_*.png"):
                if datetime.fromtimestamp(chart_file.stat().st_mtime) < cutoff:
                    chart_file.unlink()
            for chart_file in self.temp_folder.glob("report_chart_*.png"):
                if datetime.fromtimestamp(chart_file.stat().st_mtime) < cutoff:
                    chart_file.unlink()
        except Exception as e:
            logger.warning(f"Chart cleanup error: {e}")

    def _sort_measurements(self, measurements: List[Measurement]) -> List[Measurement]:
        return sorted(measurements, key=lambda m: m.measured_at)

    def _get_measurement_arrays(self, measurements: List[Measurement]) -> dict:
        sorted_measurements = self._sort_measurements(measurements)
        dates = [m.measured_at for m in sorted_measurements]

        return {
            'dates': dates,
            'weights': [m.weight for m in sorted_measurements if m.weight is not None],
            'waists': [m.waist for m in sorted_measurements if m.waist is not None],
            'hips': [m.hips for m in sorted_measurements if m.hips is not None],
            'chests': [m.chest for m in sorted_measurements if m.chest is not None],
            'biceps': [m.biceps for m in sorted_measurements if m.biceps is not None],
            'measurements': sorted_measurements
        }

    async def generate_stats_chart(self, user_id: int, measurements: List[Measurement]) -> Optional[str]:
        if not measurements:
            logger.warning(f"No measurements for user {user_id}")
            return None

        try:
            data = self._get_measurement_arrays(measurements)
            dates = data['dates']

            fig, axes = plt.subplots(3, 1, figsize=(12, 14))
            ax1, ax2, ax3 = axes

            if data['weights']:
                self._plot_weight_chart(ax1, dates, data['weights'])
            else:
                ax1.text(0.5, 0.5, 'Нет данных о весе', ha='center', va='center', transform=ax1.transAxes, fontsize=14)
                ax1.set_title('Динамика веса', fontsize=14, fontweight='bold')

            has_body_measurements = any([data['waists'], data['hips'], data['chests'], data['biceps']])
            if has_body_measurements:
                self._plot_body_measurements(ax2, dates, data)
            else:
                ax2.text(0.5, 0.5, 'Нет данных об объёмах', ha='center', va='center', transform=ax2.transAxes, fontsize=14)
                ax2.set_title('Динамика объёмов', fontsize=14, fontweight='bold')

            if len(measurements) >= 2:
                self._plot_changes(ax3, data['measurements'])
            else:
                ax3.text(0.5, 0.5, 'Недостаточно данных для анализа изменений\n(нужно минимум 2 замера)',
                        ha='center', va='center', transform=ax3.transAxes, fontsize=12)
                ax3.set_title('Изменения за период', fontsize=14, fontweight='bold')

            for ax in axes:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
                if len(dates) > 1:
                    interval = max(1, len(dates) // 7)
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
                ax.grid(True, alpha=0.3)

            plt.tight_layout()

            filepath = self.temp_folder / f"stats_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filepath, dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()

            logger.info(f"✅ Chart generated: {filepath}")
            return str(filepath)

        except Exception as e:
            logger.error(f"❌ Failed to generate chart: {e}")
            plt.close()
            return None

    def _plot_weight_chart(self, ax, dates, weights):
        ax.plot(dates, weights, 'o-', color=self.COLORS['weight'], linewidth=2.5, markersize=8, label='Вес (кг)')
        ax.set_title('Динамика веса', fontsize=14, fontweight='bold')
        ax.set_ylabel('Вес (кг)')
        ax.legend(loc='upper right')

        if len(weights) > 2:
            x = np.arange(len(weights))
            z = np.polyfit(x, weights, 1)
            p = np.poly1d(z)
            trend = p(x)
            ax.plot(dates, trend, '--', color=self.COLORS['trend'], alpha=0.7, label='Тренд', linewidth=2)
            ax.legend(loc='upper right')

    def _plot_body_measurements(self, ax, dates, data):
        measurements_to_plot = [
            (data['waists'], 'Талия (см)', self.COLORS['waist']),
            (data['hips'], 'Бёдра (см)', self.COLORS['hips']),
            (data['chests'], 'Грудь (см)', self.COLORS['chest']),
            (data['biceps'], 'Бицепс (см)', self.COLORS['biceps']),
        ]

        for values, label, color in measurements_to_plot:
            if values:
                ax.plot(dates, values, 'o-', color=color, linewidth=2, markersize=6, label=label)

        ax.set_title('Динамика объёмов', fontsize=14, fontweight='bold')
        ax.set_ylabel('Объём (см)')
        ax.legend(loc='upper right')

    def _plot_changes(self, ax, measurements):
        first = measurements[0]
        last = measurements[-1]

        changes = []
        labels = []
        colors = []

        measurement_fields = [
            ('weight', 'Вес (кг)', 1),
            ('waist', 'Талия (см)', 1),
            ('hips', 'Бёдра (см)', 1),
            ('chest', 'Грудь (см)', 1),
            ('biceps', 'Бицепс (см)', 1),
        ]

        for field, label, _ in measurement_fields:
            first_val = getattr(first, field)
            last_val = getattr(last, field)

            if first_val is not None and last_val is not None:
                change = last_val - first_val
                changes.append(change)
                labels.append(label)

                if field in ['weight', 'waist']:
                    colors.append(self.COLORS['improvement'] if change < 0 else self.COLORS['decline'])
                else:
                    colors.append(self.COLORS['improvement'] if change > 0 else self.COLORS['decline'])

        if changes:
            bars = ax.bar(labels, changes, color=colors, alpha=0.8, edgecolor='black', linewidth=0.5)
            ax.axhline(y=0, color='black', linestyle='-', linewidth=1)
            ax.set_title('Изменения за период', fontsize=14, fontweight='bold')
            ax.set_ylabel('Изменение')

            for bar, val in zip(bars, changes):
                height = bar.get_height()
                ax.text(
                    bar.get_x() + bar.get_width() / 2.,
                    height if height > 0 else height - max(0.5, abs(height) * 0.15),
                    f'{val:+.1f}',
                    ha='center',
                    va='bottom' if height > 0 else 'top',
                    fontsize=10,
                    fontweight='bold'
                )

            max_change = max(abs(c) for c in changes) if changes else 1
            ax.set_ylim(-max_change * 1.3, max_change * 1.3)

    async def generate_stats_chart_bytes(self, user_id: int, measurements: List[Measurement]) -> Optional[bytes]:
        if not measurements:
            return None

        try:
            data = self._get_measurement_arrays(measurements)
            dates = data['dates']

            fig, axes = plt.subplots(2, 1, figsize=(10, 10))
            ax1, ax2 = axes

            if data['weights']:
                self._plot_weight_chart(ax1, dates, data['weights'])
            else:
                ax1.text(0.5, 0.5, 'Нет данных', ha='center', va='center', transform=ax1.transAxes)
                ax1.set_title('Динамика веса', fontsize=14, fontweight='bold')

            has_body = any([data['waists'], data['hips'], data['chests'], data['biceps']])
            if has_body:
                self._plot_body_measurements(ax2, dates, data)
            else:
                ax2.text(0.5, 0.5, 'Нет данных', ha='center', va='center', transform=ax2.transAxes)
                ax2.set_title('Динамика объёмов', fontsize=14, fontweight='bold')

            for ax in axes:
                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
                if len(dates) > 1:
                    interval = max(1, len(dates) // 7)
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
                ax.grid(True, alpha=0.3)

            plt.tight_layout()

            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=150, bbox_inches='tight', facecolor='white')
            plt.close()
            buf.seek(0)

            return buf.read()

        except Exception as e:
            logger.error(f"❌ Failed to generate chart bytes: {e}")
            plt.close()
            return None

    async def generate_report_chart(self, user_id: int, measurements: List[Measurement]) -> Optional[str]:
        if not measurements:
            return None

        try:
            data = self._get_measurement_arrays(measurements)
            dates = data['dates']
            weights = data['weights']

            fig, ax = plt.subplots(figsize=(10, 6))

            if weights:
                ax.plot(dates, weights, 'o-', color=self.COLORS['weight'], linewidth=2.5, markersize=8)
                ax.set_title('Динамика веса', fontsize=14, fontweight='bold')
                ax.set_xlabel('Дата')
                ax.set_ylabel('Вес (кг)')
                ax.grid(True, alpha=0.3)

                if len(weights) > 2:
                    x = np.arange(len(weights))
                    z = np.polyfit(x, weights, 1)
                    p = np.poly1d(z)
                    trend = p(x)
                    ax.plot(dates, trend, '--', color=self.COLORS['trend'], alpha=0.7, label='Тренд')
                    ax.legend()

                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
                if len(dates) > 1:
                    interval = max(1, len(dates) // 5)
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            else:
                ax.text(0.5, 0.5, 'Нет данных о весе', ha='center', va='center', transform=ax.transAxes, fontsize=14)

            plt.tight_layout()

            filepath = self.temp_folder / f"report_chart_{user_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            plt.savefig(filepath, dpi=120, bbox_inches='tight', facecolor='white')
            plt.close()

            return str(filepath)

        except Exception as e:
            logger.error(f"❌ Failed to generate report chart: {e}")
            plt.close()
            return None

    async def generate_simple_chart(self, measurements: List[Measurement]) -> Optional[bytes]:
        if not measurements:
            return None

        try:
            data = self._get_measurement_arrays(measurements)
            dates = data['dates']
            weights = data['weights']

            fig, ax = plt.subplots(figsize=(8, 5))

            if weights:
                ax.plot(dates, weights, 'o-', color=self.COLORS['weight'], linewidth=2.5, markersize=8)
                ax.set_title('Прогресс веса', fontsize=14, fontweight='bold')
                ax.set_xlabel('Дата')
                ax.set_ylabel('Вес (кг)')
                ax.grid(True, alpha=0.3)

                ax.xaxis.set_major_formatter(mdates.DateFormatter('%d.%m'))
                if len(dates) > 1:
                    interval = max(1, len(dates) // 5)
                    ax.xaxis.set_major_locator(mdates.DayLocator(interval=interval))
                plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
            else:
                ax.text(0.5, 0.5, 'Нет данных', ha='center', va='center', transform=ax.transAxes, fontsize=14)

            plt.tight_layout()

            buf = BytesIO()
            plt.savefig(buf, format='png', dpi=120, bbox_inches='tight', facecolor='white')
            plt.close()
            buf.seek(0)

            return buf.read()

        except Exception as e:
            logger.error(f"❌ Failed to generate simple chart: {e}")
            plt.close()
            return None
