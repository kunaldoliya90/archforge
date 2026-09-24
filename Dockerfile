FROM python:3.12-alpine

# Graphviz renders the diagrams; DejaVu gives consistent label fonts across machines.
RUN apk add --no-cache graphviz ttf-dejavu

WORKDIR /data

COPY requirements.txt requirements-docs.txt ./
RUN pip install --no-cache-dir -r requirements.txt

# Bind mounts from Windows/macOS hosts don't deliver inotify events, so poll.
ENV WATCH_POLLING=1 \
    PYTHONUNBUFFERED=1

EXPOSE 8000
ENTRYPOINT ["python"]
CMD ["watch.py", "--serve", "--host", "0.0.0.0:8000"]
