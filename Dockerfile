FROM python:3.12-slim

WORKDIR /app

# ortools/numba wheels are prebuilt for standard manylinux; no build-essential needed.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY dfs_ev/ dfs_ev/
COPY data/ data/

ENV PYTHONUNBUFFERED=1
ENV DFS_EV_DB_PATH=/app/data/dfs_ev.sqlite3

ENTRYPOINT ["python", "-m", "dfs_ev"]
CMD ["--help"]
