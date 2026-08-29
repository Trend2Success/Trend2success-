# Backend image for dk_ev: the DraftKings DFS EV optimizer API.
FROM python:3.11-slim

WORKDIR /app

COPY dk_ev/requirements.txt ./dk_ev/requirements.txt
RUN pip install --no-cache-dir -r dk_ev/requirements.txt

COPY dk_ev ./dk_ev
COPY sample_data ./sample_data

ENV DK_EV_DATABASE_URL=sqlite:////app/data/dk_ev.db
RUN mkdir -p /app/data

EXPOSE 8000
CMD ["uvicorn", "dk_ev.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
