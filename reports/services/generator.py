import os
import csv
import json
import uuid
import io


import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

from django.conf import settings
from django.utils import timezone
from .analytics_coordination import analytics_coordinator

# Import dependencies
try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None

try:
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape 
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

class ReportGenerator:
    def __init__(self, generated_report_instance):
        self.report = generated_report_instance
        self.template = generated_report_instance.template

    def execute(self):
        from .fetchdata import ReportDataFetcher
        
        self.report.status = 'processing'
        self.report.processing_started_at = timezone.now()
        self.report.save()

        try:
            filters = self.report.filters_applied or {}
            data = list(ReportDataFetcher.get_data(self.template, filters))
            
            # Catch errors returned by the fetcher
            if data and "Error" in data[0]:
                raise Exception(data[0]["Error"])

            is_empty = not data or (len(data) == 1 and "Message" in data[0])

            ext = self.report.file_format.lower()
            if ext == 'excel': ext = 'xlsx'
            
            filename = f"report_{uuid.uuid4().hex[:10]}.{ext}"
            relative_path = os.path.join('reports', filename)
            absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)

            os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

            if ext == 'pdf':
                self._generate_pdf(data, absolute_path, is_empty)
            elif ext == 'xlsx':
                self._generate_excel(data, absolute_path)
            elif ext == 'json':
                self._generate_json(data, absolute_path)
            else:
                self._generate_csv(data, absolute_path)

            self.report.file_path = relative_path
            self.report.file_size = os.path.getsize(absolute_path)
            self.report.status = 'completed'
            self.report.processing_completed_at = timezone.now()
            
            if self.report.processing_started_at:
                self.report.processing_duration = self.report.processing_completed_at - self.report.processing_started_at
            
            self.report.save()
            return relative_path

        except Exception as e:
            self.report.status = 'failed'
            self.report.error_message = str(e)
            self.report.save()
            raise e

    def _get_period_code(self):
        """Maps UI filter labels to Coordinator period codes"""
        period_label = self.report.filters_applied.get('period', '30d')
        if '7' in str(period_label): return '7d'
        if '90' in str(period_label): return '90d'
        if '12' in str(period_label): return '12m'
        return '30d'

    def _create_visual(self, data):
        """Generates a chart based on the data and returns a ReportLab Image"""
        if not MATPLOTLIB_AVAILABLE or not data or len(data) < 2:
            return None

        try:
            # Find a column to group by (status, is_active, etc)
            headers = list(data[0].keys())
            group_col = next((h for h in headers if 'status' in h.lower() or 'active' in h.lower()), headers[0])
            
            values = [str(row.get(group_col, 'Unknown')) for row in data]
            unique_vals = list(set(values))
            counts = [values.count(v) for v in unique_vals]

            plt.figure(figsize=(6, 3))
            plt.bar(unique_vals, counts, color='#1e293b')
            plt.title(f"Distribution by {group_col.replace('_', ' ').title()}", fontsize=10, fontweight='bold')
            plt.xticks(fontsize=8)
            plt.yticks(fontsize=8)
            plt.grid(axis='y', linestyle='--', alpha=0.3)
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
            buf.seek(0)
            plt.close()
            
            return Image(buf, width=4.5*inch, height=2.2*inch)
        except Exception as e:
            print(f"Graph Generation Error: {e}")
            return None

    def _generate_pdf(self, data, path, is_empty):
        if not REPORTLAB_AVAILABLE:
            return self._generate_csv(data, path)
        
        doc = SimpleDocTemplate(path, pagesize=landscape(A4))
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, textColor=colors.HexColor('#1e293b'))
        stat_style = ParagraphStyle('Stat', parent=styles['Normal'], fontSize=9, fontName='Helvetica-Bold')

        # Header
        elements.append(Paragraph(self.report.title.upper(), title_style))
        elements.append(Paragraph(f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M')}", styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))

        if not is_empty:
            # 1. Stats from AnalyticsCoordinator
            try:
                p_code = self._get_period_code()
                summary = analytics_coordinator.get_dashboard_summary(p_code)
                metrics = summary.get('key_metrics', {})
                
                stats_data = [
                    [Paragraph("TOTAL RECORDS", stat_style), str(len(data))],
                    [Paragraph("SYSTEM HEALTH", stat_style), f"{metrics.get('system_health_score', 0)}%"],
                    [Paragraph("TOTAL REVENUE", stat_style), f"{metrics.get('total_revenue', 0)}"]
                ]
                st = Table(stats_data, colWidths=[1.5*inch, 2*inch])
                elements.append(st)
            except:
                pass

            elements.append(Spacer(1, 0.3*inch))

            # 2. Add Chart
            if self.report.filters_applied.get('include_visuals', True):
                chart = self._create_visual(data)
                if chart:
                    elements.append(chart)
                    elements.append(Spacer(1, 0.3*inch))

            # 3. Main Data Table
            headers = list(data[0].keys())
            table_data = [[h.replace('_', ' ').upper() for h in headers]]
            for row in data[:1000]:
                table_data.append([str(row.get(h, '')) for h in headers])

            t = Table(table_data, repeatRows=1)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('FONTSIZE', (0,0), (-1,-1), 8),
            ]))
            elements.append(t)
        else:
            elements.append(Paragraph("NO DATA FOUND.", styles['Heading3']))

        doc.build(elements)

    def _generate_csv(self, data, path):
        keys = data[0].keys()
        with open(path, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)

    def _generate_json(self, data, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, default=str)

    def _generate_excel(self, data, path):
        if Workbook is None: return self._generate_csv(data, path.replace('.xlsx', '.csv'))
        wb = Workbook(); ws = wb.active
        if data:
            headers = list(data[0].keys())
            ws.append(headers)
            for row in data: ws.append([row.get(h) for h in headers])
        wb.save(path)