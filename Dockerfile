# DumbConvert web version (for iPad and other browsers), as a container for a NAS or home server.
#   docker build -t dumbconvert .   (needs the NegPy submodule: git clone --recurse-submodules)
#   docker run -p 8000:8000 -v dumbconvert-data:/data -e DUMBCONVERT_TOKEN=secret dumbconvert

FROM python:3.13-slim AS build
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl ca-certificates \
    && rm -rf /var/lib/apt/lists/*
RUN curl -sSf https://sh.rustup.rs | sh -s -- -y --profile minimal
ENV PATH="/root/.cargo/bin:$PATH"
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
WORKDIR /src
COPY requirements.txt requirements-web.txt ./
# The desktop UI (PySide6) is not needed in the container.
RUN grep -v -i -E '^(pyside6|maturin)' requirements.txt > req.txt \
    && pip install --no-cache-dir maturin -r req.txt -r requirements-web.txt
COPY vendor/negpy ./vendor/negpy
RUN pip install --no-cache-dir ./vendor/negpy/negpy_core \
    && pip install --no-cache-dir --no-deps ./vendor/negpy

FROM python:3.13-slim
RUN useradd --create-home --uid 1000 app && mkdir /data && chown app /data
COPY --from=build /venv /venv
ENV PATH="/venv/bin:$PATH" PYTHONUNBUFFERED=1 DUMBCONVERT_DATA=/data
WORKDIR /app
COPY simpleneg ./simpleneg
COPY vendor/negpy/gear ./vendor/negpy/gear
USER app
VOLUME /data
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s CMD python -c "import urllib.request as u; u.urlopen('http://127.0.0.1:8000/api/info')" || exit 1
CMD ["python", "-m", "simpleneg.web", "--host", "0.0.0.0", "--port", "8000"]
