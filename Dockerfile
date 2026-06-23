FROM python:3.12-slim

WORKDIR /app

RUN pip install flask requests anthropic

COPY locations_fly.py .
COPY daily_summary.py .
COPY generate_html.py .
COPY generate_monthly.py .
COPY generate_calendar.py .

RUN mkdir -p /data/summary
COPY html/ /app/html/

EXPOSE 5001

CMD ["python3", "locations_fly.py"]
