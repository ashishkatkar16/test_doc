# main.py

import os
import shutil
import threading
import logging

from fastapi import FastAPI, UploadFile, File, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db, create_tables
from app.models import Document, ProcessingResult

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Document Processing System", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def on_startup():
    # 1) Create your DB tables
    try:
        create_tables()
        logger.info("✅ Database tables created successfully")
    except Exception as e:
        logger.error(f"❌ Error creating database tables: {e}")

    # 2) Launch the file-watcher
    try:
        # import your watcher (make sure file_watcher.py lives next to main.py)
        from workers.file_watcher import start_file_watcher

        # pass exactly the same folder you write uploads into
        watch_folder = settings.robot_folder_path
        os.makedirs(watch_folder, exist_ok=True)

        watcher = threading.Thread(
            target=lambda: start_file_watcher(watch_folder),
            daemon=True
        )
        watcher.start()
        # 🔥 Debug line to confirm thread is alive:
        logger.info(f"▶️ File watcher thread started, watching: {watch_folder}")

    except ImportError:
        logger.warning("⚠️  file_watcher module not found, skipping file watcher")
    except Exception as e:
        logger.error(f"❌ Failed to start file watcher thread: {e}")


@app.get("/")
@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": app.title, "version": app.version}


@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    """
    Save the file into the watch folder;
    the watcher will pick it up instantly.
    """
    try:
        dest = settings.robot_folder_path
        os.makedirs(dest, exist_ok=True)

        path = os.path.join(dest, file.filename)
        with open(path, "wb") as buf:
            shutil.copyfileobj(file.file, buf)

        logger.info(f"File uploaded: {file.filename}")
        return {
            "message": f"File {file.filename} uploaded successfully",
            "file_path": path,
            "note": "Processing will begin automatically via file watcher"
        }

    except Exception as e:
        logger.error(f"Error uploading file: {e}")
        raise HTTPException(status_code=500, detail="Error uploading file")


@app.get("/documents")
async def get_documents(db: Session = Depends(get_db)):
    try:
        docs = db.query(Document).all()
        return [
            {
                "id": d.id,
                "filename": d.filename,
                "file_path": d.file_path,
                "status": d.status,
                "created_at": getattr(d, "created_at", None),
                "processed_at": d.processed_at,
            }
            for d in docs
        ]
    except Exception as e:
        logger.error(f"Error fetching documents: {e}")
        raise HTTPException(status_code=500, detail="Error fetching documents")


@app.get("/documents/{doc_id}")
async def get_document(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")
    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_path": doc.file_path,
        "status": doc.status,
        "created_at": getattr(doc, "created_at", None),
        "processed_at": doc.processed_at,
    }


@app.get("/documents/{doc_id}/results")
async def get_results(doc_id: int, db: Session = Depends(get_db)):
    res = (
        db.query(ProcessingResult)
        .filter(ProcessingResult.document_id == doc_id)
        .first()
    )
    if not res:
        raise HTTPException(404, "Results not found")
    return {
        "id": res.id,
        "document_id": res.document_id,
        "overall_score": res.overall_score,
        "requires_manual_review": res.requires_manual_review,
        "created_at": res.created_at,
    }


@app.post("/documents/{doc_id}/approve")
async def manual_approve(doc_id: int, db: Session = Depends(get_db)):
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(404, "Document not found")

    doc.status = "manually_approved"
    db.commit()

    # queue email prep if Celery is available
    try:
        from app.tasks import celery_app
        celery_app.send_task("app.tasks.prepare_email", args=[doc_id])
        logger.info(f"Queued email preparation for document {doc_id}")
    except ImportError:
        logger.warning("Celery not installed, skipped email queue")
    except Exception as e:
        logger.error(f"Error queuing email: {e}")

    return {"message": "Document approved manually"}


@app.get("/debug/status")
async def debug_status(db: Session = Depends(get_db)):
    try:
        return {
            "db_connected": True,
            "documents": db.query(Document).count(),
            "results": db.query(ProcessingResult).count(),
            "watch_folder": os.listdir(settings.robot_folder_path),
        }
    except Exception as e:
        logger.error(f"Debug error: {e}")
        raise HTTPException(500, "Debug status failed")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)