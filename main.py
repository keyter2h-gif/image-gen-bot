import os
import time
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks, HTTPException
from fastapi.responses import FileResponse
from openai import OpenAI
from base64 import b64decode
import requests

app = FastAPI()

PROMPT_LIST = [
    "A futuristic neon cyberpunk city street at night, highly detailed, 4k",
    "A serene Japanese zen garden with cherry blossoms falling, peaceful atmosphere"
]
VARIATIONS_PER_PROMPT = 1
MODEL_NAME = "dall-e-3"

OUTPUT_DIR = Path.cwd() / "bot_images"
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

def run_image_bot():
    client = OpenAI()
    print("Starting multi-prompt bot batch...")
    
    # Automatically count existing images so numbering continues correctly
    existing_files = list(OUTPUT_DIR.glob("*.png"))
    file_counter = len(existing_files) + 1
    
    for prompt_index, prompt_text in enumerate(PROMPT_LIST, 1):
        for var_index in range(1, VARIATIONS_PER_PROMPT + 1):
            try:
                response = client.images.generate(
                    model=MODEL_NAME,
                    prompt=prompt_text,
                    n=1,
                    size="1024x1024"
                )
                image_data = response.data[0]
                
                if hasattr(image_data, "b64_json") and image_data.b64_json:
                    image_bytes = b64decode(image_data.b64_json)
                else:
                    image_bytes = requests.get(image_data.url).content

                # Save file using a clean sequential number
                filename = OUTPUT_DIR / f"{file_counter}.png"
                with open(filename, "wb") as f:
                    f.write(image_bytes)
                
                print(f"Saved: {filename.name}")
                file_counter += 1
                time.sleep(2)
                
            except Exception as e:
                print(f"Error: {e}")

@app.post("/generate")
def trigger_generation(background_tasks: BackgroundTasks):
    background_tasks.add_task(run_image_bot)
    return {"status": "Generation started!"}

@app.get("/download-latest")
def download_latest():
    files = list(OUTPUT_DIR.glob("*.png"))
    if not files:
        raise HTTPException(status_code=404, detail="No images found yet.")
    
    latest_file = max(files, key=os.path.getctime)
    return FileResponse(path=latest_file, filename=latest_file.name, media_type='image/png')

@app.get("/")
def health_check():
    return {"status": "Bot server is running!"}
