import time
import os
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from celery import Celery
import logging
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine

# Import your models
from app.models import Document
from app.config import settings

# Celery setup - use Docker service name for Redis
celery_app = Celery('doc_processor', broker='redis://redis:6379/0')

# Database setup
engine = create_engine(settings.database_url)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocumentHandler(FileSystemEventHandler):
    def __init__(self, watch_folder):
        self.watch_folder = watch_folder
        logger.info(f"📦 DocumentHandler initialized for folder: {watch_folder}")

    def on_created(self, event):
        if not event.is_directory:
            file_path = event.src_path
            filename = os.path.basename(file_path)

            # Check if it's a PDF or EML file
            if filename.lower().endswith(('.pdf', '.eml')):
                logger.info(f"New document detected: {filename}")

                # Check if already processed
                if not self.is_already_processed(filename):
                    # Queue the document for processing with file_path
                    try:
                        celery_app.send_task('workers.tasks.process_document', args=[file_path])
                        logger.info(f"Queued processing for file: {file_path}")
                    except Exception as e:
                        logger.error(f"Error queuing task: {e}")
                else:
                    logger.info(f"Document {filename} already processed, skipping")

    def is_already_processed(self, filename: str) -> bool:
        """Return True only if this document was fully processed before."""
        global db
        try:
            db = SessionLocal()
            doc = (
                db.query(Document)
                  .filter(Document.filename == filename)
                  .first()
            )
            if not doc:
                return False

            # Only skip if it has a processed_at timestamp
            if doc.processed_at is not None:
                logger.info(f"Document {filename} already processed at {doc.processed_at}, skipping")
                return True

            # Otherwise, it was an error or in-flight—reprocess
            logger.info(f"Document {filename} exists with status='{doc.status}' but not finished, re-queuing")
            return False

        except Exception as e:
            logger.error(f"Error checking if document exists: {e}")
            # Be conservative—requeue if in doubt
            return False
        finally:
            db.close()


def start_file_watcher(watch_folder="./robot_folder"):
    logger.info(f"🔍 [file_watcher] starting, watching folder: {watch_folder}")
    if not os.path.exists(watch_folder):
        os.makedirs(watch_folder)

    event_handler = DocumentHandler(watch_folder)
    observer = Observer()
    observer.schedule(event_handler, watch_folder, recursive=False)
    observer.start()

    logger.info(f"File watcher started for folder: {watch_folder}")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        logger.info("File watcher stopped")
    observer.join()