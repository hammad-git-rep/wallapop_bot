# Use Microsoft's official Python Playwright image (has Chromium & Linux libs pre-installed)
FROM mcr.microsoft.com/playwright/python:v1.41.0-jammy

WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application files
COPY . .

EXPOSE 10000

CMD ["python", "main.py"]
