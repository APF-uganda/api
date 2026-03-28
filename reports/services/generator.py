import os
import csv
import json
import uuid
import io
import logging

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
        # Define brand purple
        self.brand_purple = colors.HexColor('#6D28D9')

    def execute(self):
        from .fetchdata import ReportDataFetcher
        
        self.report.status = 'processing'
        self.report.processing_started_at = timezone.now()
        self.report.save()

        try:
            filters = self.report.filters_applied or {}
            data_result = ReportDataFetcher.get_data(self.template, filters)
            data = list(data_result)
            
            if not data:
                raise Exception("No records found for the selected period.")
                
            if "Error" in data[0]:
                raise Exception(data[0]["Error"])

            is_empty = (len(data) == 1 and "Message" in data[0])

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
                duration = self.report.processing_completed_at - self.report.processing_started_at
                self.report.processing_duration = duration
            
            self.report.save()
            return relative_path

        except Exception as e:
            logger.error(f"Report Generation Failed: {str(e)}")
            self.report.status = 'failed'
            self.report.error_message = str(e)
            self.report.save()
            raise e

    def _get_period_code(self):
        filters = self.report.filters_applied or {}
        period_label = str(filters.get('period', 'Last 30 Days'))
        if '7' in period_label: return '7d'
        if '90' in period_label: return '90d'
        if '12' in period_label: return '12m'
        return '30d'

    def _create_visual(self, data):
        if not MATPLOTLIB_AVAILABLE or not data or len(data) < 2:
            return None

        try:
            report_type = str(self.template.report_type).lower()
            plt.figure(figsize=(7, 3.8))
            
            # LINE GRAPH 
            if report_type == 'membership':
                dates = [row.get('joined_date') for row in data if row.get('joined_date')]
                dates.sort()
                
                unique_dates = sorted(list(set(dates)))
                counts = [dates.count(d) for d in unique_dates]
                cumulative_counts = [sum(counts[:i+1]) for i in range(len(counts))]

                plt.plot(unique_dates, cumulative_counts, color='#6D28D9', marker='o', linewidth=2, markersize=4)
                plt.fill_between(unique_dates, cumulative_counts, color='#6D28D9', alpha=0.1)
                plt.title("Membership Growth Over Time", fontsize=11, fontweight='bold', pad=15)
                plt.ylabel("Total Members", fontsize=9, fontweight='bold')
                plt.xlabel("Registration Date", fontsize=9, fontweight='bold')
            
            # BAR CHART
            else:
                headers = list(data[0].keys())
                group_col = next((h for h in headers if any(x in h.lower() for x in ['status', 'payment', 'type'])), headers[0])
                
                raw_values = [str(row.get(group_col, 'Unknown')).title() for row in data]
                unique_vals = sorted(list(set(raw_values)))
                counts = [raw_values.count(v) for v in unique_vals]

                plt.bar(unique_vals, counts, color='#6D28D9', edgecolor='#4C1D95', linewidth=0.5, width=0.5)
                plt.title(f"Analysis by {group_col.replace('_', ' ').title()}", fontsize=11, fontweight='bold', pad=15)
                plt.ylabel("Count", fontsize=9, fontweight='bold')

            plt.xticks(fontsize=8, rotation=25 if report_type == 'membership' else 0)
            plt.yticks(fontsize=8)
            plt.grid(axis='y', linestyle='--', alpha=0.2)
            
            ax = plt.gca()
            ax.spines['top'].set_visible(False)
            ax.spines['right'].set_visible(False)
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=130)
            buf.seek(0)
            plt.close()
            
            return Image(buf, width=5.2*inch, height=2.6*inch)
        except Exception as e:
            logger.error(f"Graph Generation Error: {e}")
            return None

    def _generate_pdf(self, data, path, is_empty):
        if not REPORTLAB_AVAILABLE:
            return self._generate_csv(data, path)
        
        doc = SimpleDocTemplate(path, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()
        
        # Paragraph Styles for Table Content
        cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=7, leading=9, wordWrap='CJK')
        header_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=7.5, textColor=colors.whitesmoke, fontName='Helvetica-Bold')

        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=22, textColor=self.brand_purple, spaceAfter=12)
        meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=8, textColor=colors.grey)

        elements.append(Paragraph(self.report.title.upper(), title_style))
        elements.append(Paragraph(f"Period: {self.report.filters_applied.get('period', 'N/A')} | Generated on: {timezone.now().strftime('%B %d, %Y')}", meta_style))
        elements.append(Spacer(1, 0.3*inch))

        if not is_empty and len(data) > 0:
            try:
                p_code = self._get_period_code()
                summary = analytics_coordinator.get_dashboard_summary(p_code)
                metrics = summary.get('key_metrics', {})

                stats_table = Table([
                    [Paragraph("<b>TOTAL RECORDS</b>", styles['Normal']), Paragraph("<b>SYSTEM SCORE</b>", styles['Normal']), Paragraph("<b>LAST SYNC</b>", styles['Normal'])],
                    [str(len(data)), f"{metrics.get('system_health_score', 'N/A')}%", timezone.now().strftime('%H:%M')]
                ], colWidths=[2.6*inch, 2.6*inch, 2.6*inch])

                stats_table.setStyle(TableStyle([
                    ('ALIGN', (0,0), (-1,-1), 'CENTER'),
                    ('BACKGROUND', (0,0), (-1,0), colors.whitesmoke),
                    ('BOX', (0,0), (-1,-1), 0.5, colors.lightgrey),
                    ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ]))
                elements.append(stats_table)
                elements.append(Spacer(1, 0.4*inch))
            except Exception as e:
                logger.warning(f"Stats table skipped: {e}")

            if self.report.filters_applied.get('include_visuals', True):
                chart = self._create_visual(data)
                if chart:
                    elements.append(chart)
                    elements.append(Spacer(1, 0.4*inch))

            # Table Header Processing
            headers = list(data[0].keys())
            
           
            exclude = ['id', 'is_active', 'created_at', 'membership_category', 'payment_method']
            display_headers = [h for h in headers if h not in exclude]
            
            table_data = [[Paragraph(h.replace('_', ' ').upper(), header_style) for h in display_headers]]
            
            for row in data[:500]:
                row_content = []
                for h in display_headers:
                    val = str(row.get(h, ''))
                    row_content.append(Paragraph(val, cell_style))
                table_data.append(row_content)

           
            col_widths = []
            for h in display_headers:
                h_low = h.lower()
                if 'email' in h_low: col_widths.append(1.8*inch)
                elif 'description' in h_low or 'reason' in h_low: col_widths.append(2.0*inch) 
                elif 'first' in h_low or 'last' in h_low: col_widths.append(0.9*inch)
                elif 'org' in h_low: col_widths.append(1.2*inch)
                elif 'date' in h_low: col_widths.append(0.8*inch)
                elif 'status' in h_low or 'payment' in h_low: col_widths.append(0.8*inch)
                elif 'id' in h_low: col_widths.append(1.2*inch)
                else: col_widths.append(0.8*inch)

            t = Table(table_data, repeatRows=1, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), self.brand_purple),
                ('ALIGN', (0,0), (-1,-1), 'LEFT'),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#f5f3ff')]),
                ('VALIGN', (0,0), (-1,-1), 'TOP'), 
                ('LEFTPADDING', (0,0), (-1,-1), 4),
                ('RIGHTPADDING', (0,0), (-1,-1), 4),
            ]))
            elements.append(t)
        else:
            elements.append(Paragraph("NO DATA FOUND.", styles['Heading3']))

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
        ws.title = "Report"
        headers = list(data[0].keys())
        ws.append(headers)
        
        from openpyxl.styles import Font, PatternFill
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="6D28D9", end_color="6D28D9", fill_type="solid")
            
        for row in data:
            ws.append([str(row.get(h, '')) for h in headers])
            
        wb.save(path)