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
    from reportlab.lib.pagesizes import letter, A4
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
        """Generate PDF report using ReportLab"""
        if not REPORTLAB_AVAILABLE:
            # Fallback to CSV if ReportLab is not installed
            csv_path = path.replace('.pdf', '.csv')
            self._generate_csv(data, csv_path)
            # Rename to keep .pdf extension but it's actually CSV
            os.rename(csv_path, path)
            return
        
        doc = SimpleDocTemplate(
            path, 
            pagesize=A4,
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            textColor=colors.HexColor('#5E2590'),
            spaceAfter=20,
            alignment=1  # Center alignment
        )
        title = Paragraph(self.report.title, title_style)
        elements.append(title)
        
        # Report info
        info_style = ParagraphStyle(
            'InfoStyle',
            parent=styles['Normal'],
            fontSize=9,
            textColor=colors.grey,
            spaceAfter=20,
            alignment=1  # Center alignment
        )
        info_text = f"Generated: {timezone.now().strftime('%Y-%m-%d %H:%M:%S')} | Report Type: {self.template.get_report_type_display()}"
        info = Paragraph(info_text, info_style)
        elements.append(info)
        elements.append(Spacer(1, 0.2*inch))
        
        # Table data
        if data:
            # Prepare table data
            headers = list(data[0].keys())
            table_data = [headers]
            
            # Limit rows for very large datasets
            max_rows = 1000
            data_to_show = data[:max_rows]
            
            for row in data_to_show:
                table_data.append([str(row.get(h, ''))[:100] for h in headers])  # Truncate long values
            
            # Add note if data was truncated
            if len(data) > max_rows:
                elements.append(Paragraph(
                    f"<i>Note: Showing first {max_rows} of {len(data)} records. Download as Excel/CSV for complete data.</i>",
                    styles['Normal']
                ))
                elements.append(Spacer(1, 0.1*inch))
            
            # Calculate column widths dynamically
            available_width = doc.width
            num_cols = len(headers)
            col_width = available_width / num_cols
            
            # Create table with dynamic column widths
            table = Table(table_data, colWidths=[col_width] * num_cols, repeatRows=1)
            
            # Style the table
            table.setStyle(TableStyle([
                # Header styling
                ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#5E2590')),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, 0), 9),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
                ('TOPPADDING', (0, 0), (-1, 0), 10),
                
                # Body styling
                ('BACKGROUND', (0, 1), (-1, -1), colors.white),
                ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
                ('FONTSIZE', (0, 1), (-1, -1), 7),
                ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
                ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                ('LEFTPADDING', (0, 0), (-1, -1), 5),
                ('RIGHTPADDING', (0, 0), (-1, -1), 5),
                ('TOPPADDING', (0, 1), (-1, -1), 5),
                ('BOTTOMPADDING', (0, 1), (-1, -1), 5),
            ]))
            
            elements.append(table)
        else:
            elements.append(Paragraph("No data available for this report.", styles['Normal']))
        
        # Build PDF
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