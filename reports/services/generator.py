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
        self.brand_white = colors.HexColor('#FFFFFF')
        self.light_bg = colors.HexColor('#F9FAFB')

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
            
            plot_data = [d for d in data if (d.get('date') or d.get('joined_date')) != 'N/A']
            if not plot_data: return None

            plot_data.sort(key=lambda x: x.get('date') or x.get('joined_date') or '1900-01-01')
            
            if report_type in ['revenue', 'financial', 'payments', 'membership']:
                unique_dates = sorted(list(set([d.get('date') or d.get('joined_date') for d in plot_data])))
                
                if report_type == 'membership':
                    daily_totals = [len([d for d in plot_data if (d.get('date') or d.get('joined_date')) == dt]) for dt in unique_dates]
                    plt.ylabel("New Members", fontsize=9)
                    plt.title("Membership Growth Trend", fontsize=12, fontweight='bold')
                else:
                    daily_totals = []
                    for dt in unique_dates:
                        day_sum = 0
                        for d in plot_data:
                            if (d.get('date') or d.get('joined_date')) == dt:
                                try:
                                    val = d.get('raw_amount', 0)
                                    day_sum += float(val if val is not None else 0)
                                except (ValueError, TypeError): continue
                        daily_totals.append(day_sum)
                    
                    plt.ylabel("Amount (UGX)", fontsize=9)
                    plt.title("Revenue Trend", fontsize=12, fontweight='bold')

                plt.plot(unique_dates, daily_totals, color='#6D28D9', marker='o', linewidth=2)
                plt.fill_between(unique_dates, daily_totals, color='#6D28D9', alpha=0.1)
            
            else:
                group_col = 'status' if 'status' in plot_data[0] else 'payment'
                raw_values = [str(row.get(group_col, 'Unknown')).title() for row in plot_data]
                unique_vals = sorted(list(set(raw_values)))
                counts = [raw_values.count(v) for v in unique_vals]

                plt.bar(unique_vals, counts, color='#6D28D9', alpha=0.8)
                plt.title(f"Analysis by {group_col.title()}", fontsize=12, fontweight='bold')

            plt.xticks(rotation=25 if len(plot_data) > 5 else 0, fontsize=8)
            plt.tight_layout()
            
            buf = io.BytesIO()
            plt.savefig(buf, format='png', bbox_inches='tight', dpi=150)
            plt.close()
            buf.seek(0)
            return Image(buf, width=6.0*inch, height=2.8*inch)
        except Exception as e:
            logger.error(f"Chart Visual Error: {e}")
            plt.close()
            return None

    def _generate_pdf(self, data, path, is_empty):
        if not REPORTLAB_AVAILABLE: return self._generate_csv(data, path)
        
        # Using Landscape A4 for maximum column room
        doc = SimpleDocTemplate(path, pagesize=landscape(A4), rightMargin=30, leftMargin=30, topMargin=30, bottomMargin=30)
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom Styles
        title_style = ParagraphStyle('Title', parent=styles['Heading1'], fontSize=20, textColor=self.brand_purple, spaceAfter=12)
        meta_style = ParagraphStyle('Meta', parent=styles['Normal'], fontSize=9, textColor=colors.grey)
        cell_style = ParagraphStyle('Cell', parent=styles['Normal'], fontSize=8, leading=10)
        header_text_style = ParagraphStyle('HeaderStyle', parent=styles['Normal'], fontSize=9, textColor=self.brand_white, alignment=1)

        elements.append(Paragraph(self.report.title or "SYSTEM REPORT", title_style))
        elements.append(Paragraph(f"Generated on: {timezone.now().strftime('%Y-%m-%d %H:%M')} | Scope: Unified Metrics", meta_style))
        elements.append(Spacer(1, 0.2*inch))

        if not is_empty and len(data) > 0:
            chart = self._create_visual(data)
            if chart:
                elements.append(chart)
                elements.append(Spacer(1, 0.3*inch))

            # Column handling
            all_keys = list(data[0].keys())
            exclude = ['raw_amount', 'id', 'submitted_at', 'created_at']
            display_headers = [k for k in all_keys if k not in exclude]
            
            # Header Row
            header_row = [Paragraph(f"<b>{h.replace('_', ' ').upper()}</b>", header_text_style) for h in display_headers]
            table_data = [header_row]
            
            total_sum = 0
            for row in data:
                if 'raw_amount' in row:
                    try: total_sum += float(row.get('raw_amount', 0))
                    except: pass
                
                formatted_row = [Paragraph(str(row.get(h, '')), cell_style) for h in display_headers]
                table_data.append(formatted_row)

            # Dynamic Width Calculation 
            available_width = landscape(A4)[0] - 60
            col_width = available_width / len(display_headers)

            t = Table(table_data, repeatRows=1, hAlign='CENTER', colWidths=[col_width]*len(display_headers))
            t.setStyle(TableStyle([
                ('BACKGROUND', (0,0), (-1,0), self.brand_purple),
                ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
                ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
                ('BOTTOMPADDING', (0,0), (-1,0), 10),
                ('TOPPADDING', (0,0), (-1,0), 10),
                # Zebra Striping
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, self.light_bg]),
            ]))
            elements.append(t)

            if total_sum > 0:
                elements.append(Spacer(1, 0.3*inch))
                total_box_style = ParagraphStyle('Total', parent=styles['Normal'], fontSize=12, textColor=self.brand_purple, alignment=2)
                elements.append(Paragraph(f"<b>GRAND TOTAL: UGX {total_sum:,.0f}</b>", total_box_style))
        else:
            elements.append(Paragraph("No data available for the selected criteria.", styles['Normal']))

        doc.build(elements)

    def _generate_csv(self, data, path):
        if not data: return
        keys = data[0].keys()
        with open(path, 'w', newline='', encoding='utf-8') as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)

    def _generate_json(self, data, path):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, default=str)

    def _generate_excel(self, data, path):
        if Workbook is None: return self._generate_csv(data, path.replace('.xlsx', '.csv'))
        wb = Workbook()
        ws = wb.active
        headers = list(data[0].keys())
        ws.append(headers)
        for row in data:
            ws.append([str(row.get(h, '')) for h in headers])
        wb.save(path)