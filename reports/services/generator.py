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
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

from django.conf import settings
from django.utils import timezone

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
                
            if len(data) > 0 and "Error" in data[0]:
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

    def _create_visual(self, data):
        if not MATPLOTLIB_AVAILABLE or not data or len(data) < 2:
            return None

        try:
            report_type = str(self.template.report_type).lower()
            plt.figure(figsize=(9, 4))
            
            #  REVENUE TREND WITH AXIS LABELS 
            if report_type in ['revenue', 'financial', 'payments', 'membership']:
                plot_data = sorted([d for d in data if 'raw_amount' in d], key=lambda x: x['date'])
                if not plot_data: return None
                
                unique_dates = sorted(list(set([d['date'] for d in plot_data])))
                daily_totals = [sum(float(d['raw_amount']) for d in plot_data if d['date'] == dt) for dt in unique_dates]

                plt.plot(unique_dates, daily_totals, color='#6D28D9', marker='o', linewidth=2, markersize=4)
                plt.fill_between(unique_dates, daily_totals, color='#6D28D9', alpha=0.1)
                
                plt.title("Revenue Trend (UGX)", fontsize=12, fontweight='bold', pad=15)
                plt.xlabel("Date", fontsize=9, labelpad=10)
                plt.ylabel("Amount Collected (UGX)", fontsize=9, labelpad=10)
            
            # BAR CHART FOR APPLICATIONS/MEMBERSHIP 
            else:
                headers = list(data[0].keys())
                group_col = next((h for h in headers if any(x in h.lower() for x in ['status', 'payment', 'type'])), headers[0])
                
                raw_values = [str(row.get(group_col, 'Unknown')).title() for row in data]
                unique_vals = sorted(list(set(raw_values)))
                counts = [raw_values.count(v) for v in unique_vals]

                plt.bar(unique_vals, counts, color='#6D28D9', alpha=0.8, width=0.4)
                plt.title(f"Analysis by {group_col.replace('_', ' ').title()}", fontsize=12, fontweight='bold', pad=15)
                plt.xlabel(group_col.replace('_', ' ').title(), fontsize=9)
                plt.ylabel("Total Count", fontsize=9)

            plt.xticks(fontsize=8, rotation=25 if len(unique_dates if 'unique_dates' in locals() else unique_vals) > 4 else 0)
            plt.yticks(fontsize=8)
            plt.grid(axis='y', linestyle='--', alpha=0.3)
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
            buf.seek(0)
            plt.close()
            return Image(buf, width=6.0*inch, height=2.8*inch)
        except Exception as e:
            logger.error(f"Graph Generation Error: {e}")
            return None

    def _generate_pdf(self, data, path, is_empty):
        if not REPORTLAB_AVAILABLE: return self._generate_csv(data, path)
        
        doc = SimpleDocTemplate(path, pagesize=landscape(A4), rightMargin=20, leftMargin=20, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()
        
        # Styles
        cell_style = ParagraphStyle('CellStyle', parent=styles['Normal'], fontSize=8, leading=11)
        header_style = ParagraphStyle('HStyle', parent=styles['Normal'], fontSize=8, textColor=colors.whitesmoke, fontName='Helvetica-Bold')
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, textColor=self.brand_purple, spaceAfter=10)
        meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=9, textColor=colors.grey)

        #  Header Sections
        elements.append(Paragraph(self.report.title.upper(), title_style))
        elements.append(Paragraph(f"Period: {self.report.filters_applied.get('period', 'All Time')} | Generated: {timezone.now().strftime('%d %b %Y, %H:%M')}", meta_style))
        elements.append(Spacer(1, 0.3*inch))

        if not is_empty and len(data) > 0:
            #  Add Visuals
            if self.report.filters_applied.get('include_visuals', True):
                chart = self._create_visual(data)
                if chart:
                    elements.append(chart)
                    elements.append(Spacer(1, 0.4*inch))

            # HEADER MAPPING 
            all_keys = list(data[0].keys())
            header_mapping = {
                'date': 'DATE',
                'reference_id': 'REF / APP ID', 
                'application_id': 'REF / APP ID',
                'description': 'DESCRIPTION',
                'amount_ugx': 'AMOUNT (UGX)',
                'payment': 'PAYMENT',
                'status': 'STATUS',
                'name': 'FULL NAME'
            }

            preferred_order = ['date', 'reference_id', 'application_id', 'name', 'description', 'amount_ugx', 'payment', 'status']
            display_headers = [h for h in preferred_order if h in all_keys]
            
            exclude = ['id', 'raw_amount', 'submitted_at', 'created_at']
            for h in all_keys:
                if h not in display_headers and h not in exclude:
                    display_headers.append(h)

            table_data = [[Paragraph(header_mapping.get(h, h.replace('_', ' ').upper()), header_style) for h in display_headers]]
            
            total_revenue = 0
            for row in data:
                row_content = []
                if 'raw_amount' in row: total_revenue += float(row['raw_amount'])
                for h in display_headers:
                    val = str(row.get(h, ''))
                    row_content.append(Paragraph(val, cell_style))
                table_data.append(row_content)

            #  COLUMN WIDTHS
            col_widths = []
            for h in display_headers:
                h_low = h.lower()
                if 'description' in h_low: col_widths.append(2.4*inch)
                elif 'id' in h_low: col_widths.append(1.5*inch)
                elif 'amount' in h_low: col_widths.append(1.1*inch)
                elif 'date' in h_low: col_widths.append(0.9*inch)
                elif 'name' in h_low: col_widths.append(1.6*inch)
                else: col_widths.append(1.0*inch)

            t = Table(table_data, repeatRows=1, colWidths=col_widths)
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), self.brand_purple),
                ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor('#CBD5E1')),
                ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor('#F8FAFC')]),
                ('VALIGN', (0,0), (-1,-1), 'TOP'),
                ('TOPPADDING', (0,0), (-1,-1), 5),
                ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ]))
            elements.append(t)

            if total_revenue > 0:
                elements.append(Spacer(1, 0.3*inch))
                elements.append(Paragraph(f"<b>TOTAL COLLECTED: UGX {total_revenue:,.0f}</b>", 
                                        ParagraphStyle('Total', parent=styles['Normal'], fontSize=11, alignment=2)))

        else:
            elements.append(Paragraph("NO RECORDS FOUND.", styles['Heading3']))

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
        ws.title = "Report Data"
        headers = list(data[0].keys())
        ws.append(headers)
        
        from openpyxl.styles import Font, PatternFill
        for cell in ws[1]:
            cell.font = Font(bold=True, color="FFFFFF")
            cell.fill = PatternFill(start_color="6D28D9", end_color="6D28D9", fill_type="solid")
            
        for row in data:
            ws.append([str(row.get(h, '')) for h in headers])
            
        wb.save(path)