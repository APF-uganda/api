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
    """Handles file creation using standard libraries (No Pandas)"""
    
    def __init__(self, generated_report_instance):
        self.report = generated_report_instance
        self.template = generated_report_instance.template

    def execute(self):
        from .data_fetcher import ReportDataFetcher
        
        #  Fetch raw data 
        data = list(ReportDataFetcher.get_data(self.template, self.report.filters_applied))
        
        if not data:
            data = [{"System Message": "No data found for this period"}]

        # Pathing logic
        ext = self.report.file_format.lower()
        if ext == 'excel': ext = 'xlsx'
        
        filename = f"report_{uuid.uuid4().hex[:10]}.{ext}"
        relative_path = os.path.join('reports', filename)
        absolute_path = os.path.join(settings.MEDIA_ROOT, relative_path)

        os.makedirs(os.path.dirname(absolute_path), exist_ok=True)

        # 3. Save file based on format
        if ext == 'csv':
            self._generate_csv(data, absolute_path)
        elif ext == 'xlsx':
            self._generate_excel(data, absolute_path)
        elif ext == 'json':
            self._generate_json(data, absolute_path)
        else:
            
            self._generate_csv(data, absolute_path)

        # 4. Update the DB instance
        self.report.file_path = relative_path
        self.report.file_size = os.path.getsize(absolute_path)
        self.report.status = 'completed'
        self.report.processing_completed_at = timezone.now()
        self.report.save()
        
        return relative_path

    def _generate_csv(self, data, path):
        keys = data[0].keys()
        with open(path, 'w', newline='') as output_file:
            dict_writer = csv.DictWriter(output_file, fieldnames=keys)
            dict_writer.writeheader()
            dict_writer.writerows(data)

    def _generate_json(self, data, path):
        with open(path, 'w') as f:
            json.dump(data, f, indent=4, default=str)

    def _generate_excel(self, data, path):
        if Workbook is None:
           
            return self._generate_csv(data, path.replace('.xlsx', '.csv'))
            
        wb = Workbook()
        ws = wb.active
        
        if data:
            # Write Header
            headers = list(data[0].keys())
            ws.append(headers)
            # Write Rows
            for row in data:
                ws.append([row.get(h) for h in headers])
        
        wb.save(path)