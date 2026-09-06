FROM python:3.12-slim

WORKDIR /app

# CBC (bundled with PuLP) and scientific-python wheels don't need extra OS
# packages on this base image, but keep pip tooling current.
RUN pip install --no-cache-dir --upgrade pip

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY app ./app

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
