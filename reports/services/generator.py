import os
import csv
import json
import uuid
from django.conf import settings
from django.utils import timezone

try:
    from openpyxl import Workbook
except ImportError:
    Workbook = None

try:
    from reportlab.lib import colors
    # Added landscape to imports
    from reportlab.lib.pagesizes import letter, A4, landscape 
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import inch
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

class ReportGenerator:
    """Handles file creation using standard libraries to match GeneratedReport model"""
    
    def __init__(self, generated_report_instance):
        self.report = generated_report_instance
        self.template = generated_report_instance.template

    def execute(self):
        from .fetchdata import ReportDataFetcher
        
        # 1. Start Processing
        self.report.status = 'processing'
        self.report.processing_started_at = timezone.now()
        self.report.save()

        try:
            # 2. Fetch data
            filters = self.report.filters_applied or {}
            data = list(ReportDataFetcher.get_data(self.template, filters))
            
            if not data:
                data = [{"Message": "No data found for this report criteria"}]

            # 3. Pathing logic 
            ext = self.report.file_format.lower()
            if ext == 'excel': ext = 'xlsx'
            
            filename = f"report_{uuid.uuid4().hex[:10]}.{ext}"
            relative_path = os.path.join('reports', filename)
            absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)

            os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

            # 4. Generate actual file
            if ext == 'pdf':
                self._generate_pdf(data, absolute_path)
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
            
            # Calculate duration 
            if self.report.processing_started_at:
                self.report.processing_duration = self.report.processing_completed_at - self.report.processing_started_at
            
            self.report.save()
            return relative_path

        except Exception as e:
            self.report.status = 'failed'
            self.report.error_message = str(e)
            self.report.save()
            print(f"REPORT GENERATION ERROR: {e}")
            raise e

    def _generate_pdf(self, data, path):
        """Generate PDF report with Landscape orientation and word wrapping"""
        if not REPORTLAB_AVAILABLE:
            csv_path = path.replace('.pdf', '.csv')
            self._generate_csv(data, csv_path)
            os.rename(csv_path, path)
            return
        
        
        doc = SimpleDocTemplate(
            path, 
            pagesize=landscape(A4),
            rightMargin=20,
            leftMargin=20,
            topMargin=30,
            bottomMargin=30
        )
        elements = []
        styles = getSampleStyleSheet()
        
        
        body_style = ParagraphStyle(
            'BodyStyle',
            parent=styles['Normal'],
            fontSize=7,
            leading=8,
            wordWrap='CJK' 
        )

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            textColor=colors.HexColor('#5E2590'),
            spaceAfter=15,
            alignment=1 
        )
        elements.append(Paragraph(self.report.title, title_style))
        
        info_text = f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} | Report Type: {self.template.get_report_type_display()}"
        elements.append(Paragraph(info_text, styles['Normal']))
        elements.append(Spacer(1, 0.2*inch))
        
        if data:
            headers = list(data[0].keys())
            
            
            table_data = []
            header_row = [Paragraph(f"<b>{h.replace('_', ' ').upper()}</b>", body_style) for h in headers]
            table_data.append(header_row)
            
            max_rows = 1000
            for row in data[:max_rows]:
                table_data.append([Paragraph(str(row.get(h, '')), body_style) for h in headers])
            
            
            available_width = doc.width
            num_cols = len(headers)
            
         
            col_widths = []
            for h in headers:
                h_low = h.lower()
                if 'email' in h_low:
                    col_widths.append(available_width * 0.22) # Email gets 22%
                elif 'name' in h_low:
                    col_widths.append(available_width * 0.15) # Names get 15%
                elif 'id' in h_low or 'status' in h_low:
                    col_widths.append(available_width * 0.08) # Small IDs get 8%
                else:
                    # Distribute rest equally
                    remaining_count = sum(1 for x in headers if 'email' not in x.lower() and 'name' not in x.lower() and 'id' not in x.lower() and 'status' not in x.lower())
                    if remaining_count == 0: remaining_count = 1
                    col_widths.append((available_width * 0.55) / remaining_count)

            table = Table(table_data, colWidths=col_widths, repeatRows=1)
            
            table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5E2590')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F8F8F8')]),
                ('TOPPADDING', (0, 0), (-1, -1), 6),
                ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ]))
            
            elements.append(table)
        else:
            elements.append(Paragraph("No data available for this report.", styles['Normal']))
        
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
        if Workbook is None:
            return self._generate_csv(data, path.replace('.xlsx', '.csv'))
        wb = Workbook()
        ws = wb.active
        if data:
            headers = list(data[0].keys())
            ws.append(headers)
            for row in data:
                ws.append([row.get(h) for h in headers])
        wb.save(path)