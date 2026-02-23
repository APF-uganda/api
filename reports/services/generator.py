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

class ReportGenerator:
    """Handles file creation using standard libraries to match GeneratedReport model"""
    
    def __init__(self, generated_report_instance):
        self.report = generated_report_instance
        self.template = generated_report_instance.template

    def execute(self):
        from .data_fetcher import ReportDataFetcher
        
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
            if ext == 'xlsx':
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