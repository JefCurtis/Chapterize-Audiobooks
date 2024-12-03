from fastapi import FastAPI, UploadFile, File, HTTPException, BackgroundTasks, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
import uvicorn
from pathlib import Path
import tempfile
import os
import shutil
from typing import List, Dict, Optional
import chapterize_ab
from pydantic import BaseModel

class ChapterInfo(BaseModel):
    start: str
    end: str
    chapter_type: Optional[str] = None

class ProcessingStatus(BaseModel):
    status: str
    progress: float
    message: str

app = FastAPI(title="Chapterize Audiobooks API")

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Store processing status
processing_tasks = {}

def process_audiobook(task_id: str, file_path: str, language: str, model_type: str):
    try:
        processing_tasks[task_id] = {"status": "processing", "progress": 0.0, "message": "Starting processing"}
        
        # Generate timecodes
        processing_tasks[task_id].update({"progress": 0.3, "message": "Generating timecodes"})
        timecodes = chapterize_ab.generate_timecodes(file_path, language, model_type)
        
        # Parse timecodes
        processing_tasks[task_id].update({"progress": 0.6, "message": "Parsing chapters"})
        parsed_timecodes = chapterize_ab.parse_timecodes(timecodes, language)
        
        # Split the file
        processing_tasks[task_id].update({"progress": 0.8, "message": "Splitting audiobook"})
        output_dir = Path(file_path).parent / "output"
        metadata = chapterize_ab.extract_metadata(file_path)
        cover_art = chapterize_ab.extract_coverart(file_path)
        
        chapterize_ab.split_file(file_path, parsed_timecodes, metadata, cover_art)
        
        processing_tasks[task_id].update({
            "status": "completed",
            "progress": 1.0,
            "message": "Processing completed",
            "chapters": parsed_timecodes
        })
        
    except Exception as e:
        processing_tasks[task_id].update({
            "status": "failed",
            "progress": 0,
            "message": str(e)
        })

@app.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    language: str = Query("en-us", description="Language model to use"),
    model_type: str = Query("small", description="Model size (small or large)")
):
    try:
        # Create temp directory for processing
        temp_dir = tempfile.mkdtemp()
        temp_path = Path(temp_dir) / file.filename
        
        # Save uploaded file
        with open(temp_path, "wb") as buffer:
            content = await file.read()
            buffer.write(content)
        
        # Generate unique task ID
        task_id = str(hash(temp_path))
        
        # Start processing in background
        background_tasks.add_task(
            process_audiobook,
            task_id,
            str(temp_path),
            language,
            model_type
        )
        
        return {"task_id": task_id, "message": "Processing started"}
            
    except Exception as e:
        if temp_dir:
            shutil.rmtree(temp_dir)
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{task_id}")
async def get_status(task_id: str) -> ProcessingStatus:
    if task_id not in processing_tasks:
        raise HTTPException(status_code=404, detail="Task not found")
    return processing_tasks[task_id]

@app.get("/models")
async def get_available_models():
    return {
        "languages": chapterize_ab.model_languages,
        "small_models": chapterize_ab.models_small,
        "large_models": chapterize_ab.models_large
    }

@app.get("/download/{task_id}")
async def download_files(task_id: str):
    if task_id not in processing_tasks or processing_tasks[task_id]["status"] != "completed":
        raise HTTPException(status_code=404, detail="Processed files not found")
    
    # TODO: Implement file download logic
    # This would typically involve zipping the output files and sending them
    pass

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
