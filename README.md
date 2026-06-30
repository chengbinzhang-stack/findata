# Transcript Downloader

A FastAPI-based web application for downloading and organizing earnings call transcripts, investor presentations, financial results, and earnings call audio files.

## Features

- **Company Search** — Search companies by name or BSE Scrip Code
- **Multi-Document Support** — Handles 4 document types per submission
  - Earnings Call Transcript
  - Investor Presentation
  - Financial Results
  - Earnings Call Audio
- **URL Validation** — Validates source URLs before downloading
- **S3 Storage** — Automatically uploads files to AWS S3 (optional)
- **File Listing** — Browse all downloaded files with search and pagination
- **Excel Export** — Download file list as Excel spreadsheet

## Tech Stack

- FastAPI
- aiosqlite (async SQLite)
- httpx (async HTTP)
- openpyxl (Excel export)
- boto3 (AWS S3)
- Jinja2 templates

## Setup

```bash
pip install -r requirements.txt
```

## Run

```bash
python main.py
```

Open http://localhost:8000

## Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `PORT` | No | `8000` | Server port |
| `S3_BUCKET` | No | (empty) | AWS S3 bucket name |
| `AWS_ACCESS_KEY_ID` | No | — | AWS access key |
| `AWS_SECRET_ACCESS_KEY` | No | — | AWS secret key |

Without `S3_BUCKET`, files are stored locally in `downloads/`.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/` | Form submission page |
| `GET` | `/files` | File listing page |
| `GET` | `/status/{task_id}` | Download task status |
| `GET` | `/api/company/search?q=` | Search companies |
| `GET` | `/api/validate-url?url=` | Validate a URL |
| `POST` | `/api/submit` | Submit download task |
| `GET` | `/api/files` | List files (paginated) |
| `GET` | `/api/files/download-excel` | Export Excel |

## Deployment

### Railway (recommended)

1. Push to GitHub
2. Connect repo to Railway
3. Deploy — Railway auto-detects Python

Environment variables (if using S3):
- `S3_BUCKET`
- `AWS_ACCESS_KEY_ID`
- `AWS_SECRET_ACCESS_KEY`

### Docker

```dockerfile
FROM python:3.11
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "main.py"]
```

## File Structure

```
.
├── main.py              # FastAPI app
├── database.py          # SQLite operations
├── downloader.py        # URL validation & download
├── models.py            # Pydantic models
├── s3_utils.py          # AWS S3 utilities
├── templates/
│   ├── index.html       # Submission form
│   ├── files.html       # File listing
│   └── status.html      # Task status
├── downloads/           # Downloaded files (gitignored)
├── transcripts.db       # SQLite database (gitignored)
└── requirements.txt
```
