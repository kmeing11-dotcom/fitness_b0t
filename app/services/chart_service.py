import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Any
from pathlib import Path
from io import BytesIO
from app.config import Config
from app.models import Measurement

class ChartService:
    def __init__(self):
        Config.ensure_temp_folder()
        plt.style.use('seaborn-v0_8-darkgrid')
        plt.rcParams['font.size'] = 10
        plt.rcParams['figure.figsize'] = (12, 8)
    
    async def generate_stats_chart(self, user_id: int, measurements: List[Measurement]) -> str:
        if not measurements:
            return None
        
        dates = [m.measured_at for m in measurements]
        weights = [m.weight for m in measurements if m.weight]
        waists = [m.waist for m in measurements if m.waist]
        hips = [m.hips for m in measurements if m.hips]
        chests = [m.chest for m in measurements if m.chest]
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12))
        
        if weights:
            ax1.plot(dates, weights, 'b-o', linewidth=2, markersize=6, label='Weight (kg)')
            ax1.set_title('Weight Dynamics', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Weight (kg)')
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            
            if len(weights) > 1:
                z = np.polyfit(range(len(weights)), weights, 1)
                p = np.poly1d(z)
                trend = p(range(len(weights)))
                ax1.plot(dates, trend, 'r--', alpha=0.7, label='Trend')
                ax1.legend()
        
        if any([waists, hips, chests]):
            if waists:
                ax2.plot(dates, waists, 'g-o', linewidth=2, markersize=6, label='Waist (cm)')
            if hips:
                ax2.plot(dates, hips, 'm-o', linewidth=2, markersize=6, label='Hips (cm)')
            if chests:
                ax2.plot(dates, chests, 'c-o', linewidth=2, markersize=6, label='Chest (cm)')
            
            ax2.set_title('Body Measurements', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Circumference (cm)')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
        
        if len(measurements) >= 2:
            first = measurements[0]
            last = measurements[-1]
            
            changes = []
            labels = []
            
            if first.weight and last.weight:
                weight_change = last.weight - first.weight
                changes.append(weight_change)
                labels.append(f"Weight: {weight_change:+.1f} kg")
            
            if first.waist and last.waist:
                waist_change = last.waist - first.waist
                changes.append(waist_change)
                labels.append(f"Waist: {waist_change:+.1f} cm")
            
            if first.hips and last.hips:
                hips_change = last.hips - first.hips
                changes.append(hips_change)
                labels.append(f"Hips: {hips_change:+.1f} cm")
            
            if first.chest and last.chest:
                chest_change = last.chest - first.chest
                changes.append(chest_change)
                labels.append(f"Chest: {chest_change:+.1f} cm")
            
            if changes:
                colors = ['green' if c < 0 else 'red' for c in changes]
                bars = ax3.bar(labels, changes, color=colors, alpha=0.7)
                ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
                ax3.set_title('Monthly Change (Last 30 Days)', fontsize=14, fontweight='bold')
                ax3.set_ylabel('Change')
                ax3.grid(True, alpha=0.3)
                
                for bar, val in zip(bars, changes):
                    height = bar.get_height()
                    ax3.text(
                        bar.get_x() + bar.get_width()/2.,
                        height if height > 0 else height - 0.3,
                        f'{val:+.1f}',
                        ha='center', va='bottom' if height > 0 else 'top',
                        fontsize=10, fontweight='bold'
                    )
        
        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//7)))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        filepath = Path(Config.TEMP_FOLDER) / f"stats_{user_id}.png"
        plt.savefig(filepath, dpi=150, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
    
    async def generate_stats_chart_bytes(self, user_id: int, measurements: List[Measurement]) -> bytes:
        if not measurements:
            return None
        
        dates = [m.measured_at for m in measurements]
        weights = [m.weight for m in measurements if m.weight]
        waists = [m.waist for m in measurements if m.waist]
        hips = [m.hips for m in measurements if m.hips]
        chests = [m.chest for m in measurements if m.chest]
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 12))
        
        if weights:
            ax1.plot(dates, weights, 'b-o', linewidth=2, markersize=6, label='Weight (kg)')
            ax1.set_title('Weight Dynamics', fontsize=14, fontweight='bold')
            ax1.set_ylabel('Weight (kg)')
            ax1.grid(True, alpha=0.3)
            ax1.legend()
            
            if len(weights) > 1:
                z = np.polyfit(range(len(weights)), weights, 1)
                p = np.poly1d(z)
                trend = p(range(len(weights)))
                ax1.plot(dates, trend, 'r--', alpha=0.7, label='Trend')
                ax1.legend()
        
        if any([waists, hips, chests]):
            if waists:
                ax2.plot(dates, waists, 'g-o', linewidth=2, markersize=6, label='Waist (cm)')
            if hips:
                ax2.plot(dates, hips, 'm-o', linewidth=2, markersize=6, label='Hips (cm)')
            if chests:
                ax2.plot(dates, chests, 'c-o', linewidth=2, markersize=6, label='Chest (cm)')
            
            ax2.set_title('Body Measurements', fontsize=14, fontweight='bold')
            ax2.set_ylabel('Circumference (cm)')
            ax2.grid(True, alpha=0.3)
            ax2.legend()
        
        if len(measurements) >= 2:
            first = measurements[0]
            last = measurements[-1]
            
            changes = []
            labels = []
            
            if first.weight and last.weight:
                weight_change = last.weight - first.weight
                changes.append(weight_change)
                labels.append(f"Weight: {weight_change:+.1f} kg")
            
            if first.waist and last.waist:
                waist_change = last.waist - first.waist
                changes.append(waist_change)
                labels.append(f"Waist: {waist_change:+.1f} cm")
            
            if first.hips and last.hips:
                hips_change = last.hips - first.hips
                changes.append(hips_change)
                labels.append(f"Hips: {hips_change:+.1f} cm")
            
            if first.chest and last.chest:
                chest_change = last.chest - first.chest
                changes.append(chest_change)
                labels.append(f"Chest: {chest_change:+.1f} cm")
            
            if changes:
                colors = ['green' if c < 0 else 'red' for c in changes]
                bars = ax3.bar(labels, changes, color=colors, alpha=0.7)
                ax3.axhline(y=0, color='black', linestyle='-', linewidth=0.5)
                ax3.set_title('Monthly Change (Last 30 Days)', fontsize=14, fontweight='bold')
                ax3.set_ylabel('Change')
                ax3.grid(True, alpha=0.3)
                
                for bar, val in zip(bars, changes):
                    height = bar.get_height()
                    ax3.text(
                        bar.get_x() + bar.get_width()/2.,
                        height if height > 0 else height - 0.3,
                        f'{val:+.1f}',
                        ha='center', va='bottom' if height > 0 else 'top',
                        fontsize=10, fontweight='bold'
                    )
        
        for ax in [ax1, ax2, ax3]:
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//7)))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        # Сохраняем в память
        buf = BytesIO()
        plt.savefig(buf, format='png', dpi=150, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf.read()
    
    async def generate_report_chart(self, user_id: int, measurements: List[Measurement]) -> str:
        if not measurements:
            return None
        
        dates = [m.measured_at for m in measurements]
        weights = [m.weight for m in measurements if m.weight]
        
        fig, ax = plt.subplots(figsize=(8, 5))
        
        if weights:
            ax.plot(dates, weights, 'b-o', linewidth=2, markersize=8)
            ax.set_title('Weight Progress', fontsize=12, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel('Weight (kg)')
            ax.grid(True, alpha=0.3)
            
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=max(1, len(dates)//5)))
            plt.setp(ax.xaxis.get_majorticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        filepath = Path(Config.TEMP_FOLDER) / f"report_chart_{user_id}.png"
        plt.savefig(filepath, dpi=120, bbox_inches='tight')
        plt.close()
        
        return str(filepath)
