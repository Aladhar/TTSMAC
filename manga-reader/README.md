# manga-reader Docker instructions

Build the Docker image from the `manga-reader` directory and install Python dependencies from `requirements.txt`:

```bash
cd manga-reader
docker build -t manga-reader:latest .
```

Run the container (will run `main.py`):

```bash
docker run --rm -it manga-reader:latest
```

If you need to mount local data or interact with files, add a volume:

```bash
docker run --rm -it -v "$(pwd)/cache:/app/cache" manga-reader:latest
```

Notes:
- `paddlepaddle` and `paddleocr` are large packages and may require extra system libraries or GPUs for certain variants; this Dockerfile installs the CPU Python packages via pip.
- If you need a different Python base (e.g., GPU-enabled), switch the `FROM` line accordingly.
