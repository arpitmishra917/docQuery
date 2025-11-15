from dotenv import load_dotenv
load_dotenv()
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.responses import JSONResponse
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timedelta,timezone
import asyncio
import shutil
import logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
from src.core.pipeline import load_and_chunk_file, build_vector_index,retrieve_relevant_chunks,construct_prompt,generate_answer


SESSION_EXPIRY_HOURS = 1
SESSION_TRACKER = {}  # session_id → timestamp

@asynccontextmanager
async def lifespan(app: FastAPI):
    asyncio.create_task(cleanup_expired_sessions())
    yield  # required to complete the context

app = FastAPI(lifespan=lifespan)
INDEX_CACHE = {}  # session_id → vector_store

UPLOAD_DIR = "./data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@app.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    if not file.filename.endswith(".pdf"):
        return JSONResponse(status_code=400, content={"error": "Only PDF files are supported."})

    session_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{session_id}.pdf")
    SESSION_TRACKER[session_id] = datetime.now(timezone.utc)

    with open(file_path, "wb") as f:
        f.write(await file.read())

    chunks = load_and_chunk_file(file_path)
    vector_store = build_vector_index(chunks,session_id)
    INDEX_CACHE[session_id] = vector_store

    return {"session_id": session_id, "message": "PDF uploaded and indexed successfully."}

@app.post("/chat")
async def chat(session_id: str = Form(...), query: str = Form(...)):
    if session_id not in INDEX_CACHE:
        return JSONResponse(status_code=404, content={"error": "Session ID not found. Upload a PDF first."})

    vector_store = INDEX_CACHE[session_id]
    retrieved_chunks = retrieve_relevant_chunks(query, vector_store)
    prompt = construct_prompt(query, retrieved_chunks)
    answer = generate_answer(prompt)

    return {"answer": answer}

import asyncio
from datetime import datetime, timedelta


async def cleanup_expired_sessions():
    while True:
        now = datetime.now(timezone.utc)
        expired = []

        for session_id, timestamp in SESSION_TRACKER.items():
            if now - timestamp > timedelta(hours=SESSION_EXPIRY_HOURS):
                expired.append(session_id)

        for session_id in expired:
            index_path = f"./data/faiss_indexes/{session_id}"
            pdf_path = f"./data/uploads/{session_id}.pdf"

            for path in [index_path, pdf_path]:
                if os.path.exists(path):
                    if os.path.isdir(path):
                        shutil.rmtree(path)
                    else:
                        os.remove(path)

            INDEX_CACHE.pop(session_id, None)
            SESSION_TRACKER.pop(session_id, None)

        await asyncio.sleep(600)  # check every 10 minutes


