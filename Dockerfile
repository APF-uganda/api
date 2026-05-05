#Python image
FROM python:3.11-slim

RUN echo "precedence ::ffff:0:0/96  100" >> /etc/gai.conf

##
ENV PYTHONUNBUFFERED=1

##Working directory
WORKDIR /api

##Install Dependencies
COPY requirements.txt .
RUN pip install --upgrade pip && pip install --no-cache-dir -r requirements.txt

##Copy project files
COPY . .

RUN chmod +x entrypoint.sh

EXPOSE 8000

#CMD ["gunicorn", "api.wsgi:application", "--bind", "0.0.0.0:8000"]

#CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

CMD ["sh", "entrypoint.sh"]
