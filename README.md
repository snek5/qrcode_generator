# QR Code Generator

A lightweight Flask app for creating custom QR codes with style, color, gradient, and logo embedding options.

## Features

- Generate QR codes from text or URLs
- Multiple module styles: square, circle, rounded, gapped, vertical bars, horizontal bars
- Solid and gradient color support
- Optional background color
- Optional logo embedding in the QR code center
- Download generated QR codes as PNG files

## Requirements

- Python 3.13+
- Flask
- Pillow
- qrcode[pil]

## Local Setup

1. Clone the repository:

    ```bash
    git clone <repo-url>
    cd qrcode_generator
    ```

2. Create and activate a Python virtual environment:

    ```bash
    python -m venv .venv
    source .venv/bin/activate
    ```

3. Install dependencies:

    ```bash
    pip install --upgrade pip
    pip install .
    ```

4. Run the app:

    ```bash
    python app.py
    ```

5. Open your browser at `http://127.0.0.1:5000`

## Docker

Build the Docker image:

```bash
docker build -t qrcode-generator .
```

Run the container:

```bash
docker run --rm -p 5000:5000 qrcode-generator
```

Then open `http://127.0.0.1:5000`.

## Project Structure

- `app.py` - Flask application and QR generation logic
- `templates/index.html` - front-end form and output display
- `pyproject.toml` - project metadata and dependency list
- `requirement.txt` - full dependency snapshot

## Notes

- The app uses Flask to serve a single-page QR code generator.
- Gradients are generated in Python and applied to QR code modules.
- If you add a logo, it is resized and composited at the QR center.
