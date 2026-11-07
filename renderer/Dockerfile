FROM python:3.12-slim

RUN pip install --no-cache-dir flask jinja2 playwright \
       pydantic==2.14.1 openpyxl==3.1.5 reportlab==5.0.1 pillow==13.0.0 \
    && playwright install --with-deps chromium

WORKDIR /app
COPY app.py .
COPY templates templates
COPY assets assets
COPY calc.py .
COPY vendor vendor

ENV PORT=8090 TWENTY_URL=http://server:3000 CHROMIUM_PATH="" PYTHONPATH=/app/vendor MCE_AUDIT_ROOT=/data/audit
VOLUME /data/audit
EXPOSE 8090
CMD ["python", "app.py"]
