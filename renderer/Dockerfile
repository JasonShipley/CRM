FROM python:3.12-slim

RUN pip install --no-cache-dir flask jinja2 playwright \
    && playwright install --with-deps chromium

WORKDIR /app
COPY app.py .
COPY templates templates
COPY assets assets

ENV PORT=8090 TWENTY_URL=http://server:3000 CHROMIUM_PATH=""
EXPOSE 8090
CMD ["python", "app.py"]
