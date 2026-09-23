FROM python:3.12-slim

RUN pip install --no-cache-dir flask jinja2 playwright \
    && playwright install --with-deps chromium

WORKDIR /app
COPY app.py builder.py crm.py quotes_store.py render_ctx.py twenty_api.py ./
COPY calculators calculators
COPY templates templates
COPY assets assets
COPY tools tools

# Quotes live here; docker-compose mounts a named volume so they survive
# a rebuild. Without the mount they are still written, just not persisted.
ENV PORT=8090 TWENTY_URL=http://server:3000 CHROMIUM_PATH="" \
    RENDERER_DATA_DIR=/data
RUN mkdir -p /data

EXPOSE 8090
CMD ["python", "app.py"]
