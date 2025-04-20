import uuid
import os

UPLOAD_DIR = "uploads"

def save_file(file_bytes: bytes, filename: str = None) -> str:
    if not os.path.exists(UPLOAD_DIR):
        os.makedirs(UPLOAD_DIR)

    filename = filename or f"{uuid.uuid4().hex}.jpg"
    path = os.path.join(UPLOAD_DIR, filename)

    with open(path, "wb") as f:
        f.write(file_bytes)

    return path
