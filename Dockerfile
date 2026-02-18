#Python image
FROM python:3.10-slim

##
ENV PYTHONUNBUFFERED=1

##Working directory
WORKDIR /api

##Install Dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

##Copy project files
COPY . .

EXPOSE 8000

CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
