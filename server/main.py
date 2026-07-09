"""Twirra backend: private Twitter/X video downloader API."""
import os

from dotenv import load_dotenv

load_dotenv()  # must run before importing modules that read env vars at import time

from fastapi import BackgroundTasks, Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

import auth
from downloader import DownloadError, InvalidUrlError, cleanup_file, download_video

RATE_LIMIT_PER_MINUTE = os.getenv("RATE_LIMIT_PER_MINUTE", "10")
CORS_ORIGINS = [o.strip() for o in os.getenv("CORS_ORIGINS", "*").split(",")]

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(title="Twirra API")
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)


@app.get("/health")
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
def health(request: Request):
    return {"status": "ok"}


@app.get("/download")
@limiter.limit(f"{RATE_LIMIT_PER_MINUTE}/minute")
def download(
    request: Request,
    url: str,
    background_tasks: BackgroundTasks,
    user: str = Depends(auth.get_current_user),
):
    try:
        file_path = download_video(url)
    except InvalidUrlError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except DownloadError as exc:
        raise HTTPException(status_code=502, detail=f"Failed to fetch video: {exc}") from exc

    background_tasks.add_task(cleanup_file, file_path)
    filename = os.path.basename(file_path)
    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=filename,
        background=background_tasks,
    )
