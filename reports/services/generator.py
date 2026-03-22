import os
import csv
import json
import uuid
import io
import logging

# Configure Logging to catch background worker errors
logger = logging.getLogger(__name__)

import matplotlib
matplotlib.use('Agg') 
import matplotlib.pyplot as plt

try:
    import matplotlib
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from django.conf import settings
from django.utils import timezone
from .analytics_coordinator import analytics_coordinator

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
        # Local import to prevent circular dependency
        from .fetchdata import ReportDataFetcher
        
        self.report.status = 'processing'
        self.report.processing_started_at = timezone.now()
        self.report.save()

        try:
            filters = self.report.filters_applied or {}
            # Fetch data using the corrected field mapping (e.g., created_at)
            data_result = ReportDataFetcher.get_data(self.template, filters)
            data = list(data_result)
            
            # Handle empty data or errors from Fetcher
            if not data:
                raise Exception("No records found for the selected period.")
                
            if "Error" in data[0]:
                raise Exception(data[0]["Error"])

            is_empty = (len(data) == 1 and "Message" in data[0])

            # File Extension Logic
            ext = self.report.file_format.lower()
            if ext == 'excel': ext = 'xlsx'
            
            filename = f"report_{uuid.uuid4().hex[:10]}.{ext}"
            relative_path = os.path.join('reports', filename)
            absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)

            os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

            # Route to correct generator method
            if ext == 'pdf':
                self._generate_pdf(data, absolute_path, is_empty)
            elif ext == 'xlsx':
                self._generate_excel(data, absolute_path)
            elif ext == 'json':
                self._generate_json(data, absolute_path)
            else:
                self._generate_csv(data, absolute_path)

            # Finalize Report Instance
            self.report.file_path = relative_path
            self.report.file_size = os.path.getsize(absolute_path)
            self.report.status = 'completed'
            self.report.processing_completed_at = timezone.now()
            
            if self.report.processing_started_at:
                duration = self.report.processing_completed_at - self.report.processing_started_at
                self.report.processing_duration = duration
            
            self.report.save()
            return relative_path

        except Exception as e:
            logger.error(f"Report Generation Failed: {str(e)}")
            self.report.status = 'failed'
            # Save the specific DB error 
            self.report.error_message = str(e)
            self.report.save()
            raise e

    def _get_period_code(self):
        """Maps UI filter labels to Coordinator period codes"""
        filters = self.report.filters_applied or {}
        period_label = str(filters.get('period', 'Last 30 Days'))
        if '7' in period_label: return '7d'
        if '90' in period_label: return '90d'
        if '12' in period_label: return '12m'
        return '30d'

    def _create_visual(self, data):
        """Generates a chart based on data and returns a ReportLab Image"""
        if not MATPLOTLIB_AVAILABLE or not data or len(data) < 2:
            return None

        try:
            headers = list(data[0].keys())
            # Find a column to group by: status, role, or category
            group_col = next((h for h in headers if any(x in h.lower() for x in ['status', 'active', 'role', 'type'])), headers[0])
            
            values = [str(row.get(group_col, 'Unknown')) for row in data]
            unique_vals = sorted(list(set(values)))
            counts = [values.count(v) for v in unique_vals]

            plt.figure(figsize=(7, 3.5))
            plt.bar(unique_vals, counts, color='#1e293b', edgecolor='#334155', linewidth=0.5)
            
            plt.title(f"Summary by {group_col.replace('_', ' ').title()}", fontsize=11, fontweight='bold', pad=15)
            plt.xticks(fontsize=8, rotation=15)
            plt.yticks(fontsize=8)
            plt.grid(axis='y', linestyle='--', alpha=0.2)
            
            # Remove top and right spines for a modern look
            ax = plt.gca()
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=120)
            buf.seek(0)
            plt.close()
            
            return Image(buf, width=5.0*inch, height=2.5*inch)
        except Exception as e:
            logger.error(f"Graph Generation Error: {e}")
            return None

    def _generate_pdf(self, data, path, is_empty):
        if not REPORTLAB_AVAILABLE:
            return self._generate_csv(data, path)
        
        # Use landscape A4 for more column space
        doc = SimpleDocTemplate(path, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()
        
        # Header Style
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=22, textColor=colors.HexColor('#0f172a'), spaceAfter=12)
        meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=9, textColor=colors.grey)

        # 1. Document Title
        elements.append(Paragraph(self.report.title.upper(), title_style))
        elements.append(Paragraph(f"Period: {self.report.filters_applied.get('period', 'N/A')} | Format: PDF | ID: {self.report.id}", meta_style))
        elements.append(Paragraph(f"Generated on: {timezone.now().strftime('%B %d, %Y at %H:%M')}", meta_style))
        elements.append(Spacer(1, 0.4*inch))

        if not is_empty and len(data) > 0:
            # 2. Key Performance Metrics Row 
            try:
                p_code = self._get_period_code()
                summary = analytics_coordinator.get_dashboard_summary(p_code)
                metrics = summary.get('key_metrics', {})
                
                # Simple summary table
                stats_table = Table([
                    [Paragraph("<b>TOTAL RECORDS</b>", styles['Normal']), Paragraph("<b>SYSTEM SCORE</b>", styles['Normal']), Paragraph("<b>LAST SYNC</b>", styles['Normal'])],
                    [str(len(data)), f"{metrics.get('system_health_score', 'N/A')}%", timezone.now().strftime('%H:%M')]
                ], colWidths=[2.5*inch, 2.5*inch, 2.5*inch])
                
                stats_table.setStyle(TableStyle([
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                    ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
                    ('BOX', (0,0), (-1,-1), 0.5, colors.lightgrey),
                ]))
                elements.append(stats_table)
                elements.append(Spacer(1, 0.4*inch))
            except Exception as e:
                logger.warning(f"Stats summary skip: {e}")

            # 3. Visualization
            if self.report.filters_applied.get('include_visuals', True):
                chart = self._create_visual(data)
                if chart:
                    elements.append(chart)
                    elements.append(Spacer(1, 0.4*inch))

            # 4. Data Table
            headers = list(data[0].keys())
            # Limit columns to 12 for PDF readability
            display_headers = headers[:12]
            table_data = [[h.replace('_', ' ').upper() for h in display_headers]]
            
            # Populate Rows
            for row in data[:500]: # Limit PDF rows for performance
                table_data.append([str(row.get(h, '')) for h in display_headers])

            # Auto-calculate column widths
            col_width = (doc.width) / len(display_headers)
            t = Table(table_data, repeatRows=1, colWidths=[col_width]*len(display_headers))
            
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#1e293b')),
                ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
                ('FONTSIZE', (0,0), (-1,0), 9),
                ('BOTTOMPADDING', (0,0), (-1,0), 10),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('FONTSIZE', (0,1), (-1,-1), 8),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f8fafc')]),
            ]))
            elements.append(t)
        else:
            elements.append(Paragraph("NO DATA RECORDS FOUND IN SPECIFIED TIME PERIOD.", styles['Heading3']))

        doc.build(elements)

    def _generate_csv(self, data, path):
        if not data: return
        keys = data[0].keys()
        with open(path, 'w', newline='', encoding='utf-8') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)

    def _generate_json(self, data, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, default=str)

    def _generate_excel(self, data, path):
        if Workbook is None or not data: 
            return self._generate_csv(data, path.replace('.xlsx', '.csv'))
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Analytics Report"
        
        headers = list(data[0].keys())
        ws.append(headers)
        
        # Style the header row
        from openpyxl.styles import Font, PatternFill
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="1E293B", end_color="1E293B", fill_type="solid")
            
        for row in data:
            ws.append([str(row.get(h, '')) for h in headers])
            
        wb.save(path)