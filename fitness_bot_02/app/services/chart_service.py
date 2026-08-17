import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from app.config import Config
from app.models import Measurement

class ChartService:
    def __init__(self):
        Config.ensure_temp_folder()
        plt.style.use('seaborn-v0_8-darkgrid')
        plt.rcParams['figure.figsize'] = (12, 8)

    async def generate_stats_chart(self, user_id: int, measurements: list[Measurement]) -> str:
        if not measurements:
            return None

        dates = [m.measured_at for m in measurements]
        weights = [m.weight for m in measurements if m.weight]
        waists = [m.waist for m in measurements if m.waist]
        hips = [m.hips for m in measurements if m.hips]
        chests = [m.chest for m in measurements if m.chest]

        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))

        if weights:
            ax1.plot(dates, weights, 'b-o', linewidth=2, markersize=6, label='Вес (кг)')
            ax1.set_title('Динамика веса', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Вес (кг)')
            ax1.grid(True, alpha=0.3)
            ax1.legend()

        if any([waists, hips, chests]):
            if waists:
                ax2.plot(dates, waists, 'g-o', linewidth=2, markersize=6, label='Талия (см)')
            if hips:
                ax2.plot(dates, hips, 'm-o', linewidth=2, markersize=6, label='Бедра (см)')
            if chests:
                ax2.plot(dates, chests, 'c-o', linewidth=2, markersize=6, label='Грудь (см)')
            ax2.set_title('Обхваты', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Обхват (см)')
            ax2.grid(True, alpha=0.3)
            ax2.legend()

        for ax in [ax1, ax2]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//7)))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')

        plt.tight_layout()
        filepath = Path(Config.TEMP_FOLDER) / f"stats_{user_id}.png"
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        return str(filepath)