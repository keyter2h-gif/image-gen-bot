import os
import time
from pathlib import Path
from fastapi import FastAPI, BackgroundTasks
from openai import OpenAI
from base64 import b64decode

app = FastAPI()

# Configuration: Add your custom prompt list and variation limits here
PROMPT_LIST = [
    "A futuristic neon cyberpunk city street at night, highly detailed, 4k",
    "A serene Japanese zen garden with cherry blossoms falling, peaceful atmosphere",
    "An astronaut exploring a vibrant alien crystal planet, cinematic lighting"
]

VARIATIONS_PER_PROMPT = 2  # Number of images to generate per prompt
MODEL_NAME = "gpt-image-2.5-flare"  # Update to your target model name (or dall-e-3)

# Storage: Automatically uses Render Persistent Disk if mounted, otherwise local folder
OUTPUT_DIR = Path(os.getenv("RENDER_DISK_PATH", Path.cwd() / "bot_images"))
OUTPUT_DIR.mkdir(exist_ok=True, parents=True)

def run_image_bot():
    # Automatically pulls OPENAI_API_KEY from your environment variables
    client = OpenAI()
    print("Starting multi-prompt bot batch...")
    
    total_successful = 0
    
    # Outer loop: Iterates through each unique prompt
    for prompt_index, prompt_text in enumerate(PROMPT_LIST, 1):
        print(f"\n--- Processing Prompt {prompt_index}/{len(PROMPT_LIST)}: \"{prompt_text}\" ---")
        
        # Inner loop: Generates the requested number of variations for the current prompt
        for var_index in range(1, VARIATIONS_PER_PROMPT + 1):
            print(f"[{prompt_index}.{var_index}] Generating variation {var_index} of {VARIATIONS_PER_PROMPT}...")
            
            try:
                response = client.images.generate(
                    model=MODEL_NAME,
                    prompt=prompt_text,
                    n=1,
                    size="1024x1024"
                )
                image_data = response.data[0]
                
                # Handle image payload format (Base64 vs URL fallback)
                if hasattr(image_data, "b64_json") and image_data.b64_json:
                    image_bytes = b64decode(image_data.b64_json)
                else:
                    import requests
                    image_bytes = requests.get(image_data.url).content

                # Save file with clear tracking names
                filename = OUTPUT_DIR / f"prompt{prompt_index}_var{var_index}_{int(time.time())}.png"
                with open(filename, "wb") as f:
                    f.write(image_bytes)
                    
                total_successful += 1
                print(f" -> Successfully saved: {filename.name}")
                
                # Sleep interval to prevent triggering API rate limits
                time.sleep(2)

            except Exception as e:
                print(f" -> Error encountered on prompt {prompt_index}, variation {var_index}: {e}")
                time.sleep(5)

    print(f"\nBatch complete! Successfully generated {total_successful} total images across {len(PROMPT_LIST)} prompts.")

@app.post("/generate")
def trigger_generation(background_tasks: BackgroundTasks):
    # Runs the generation sequence safely in the background to prevent HTTP timeouts
    background_tasks.add_task(run_image_bot)
    return {"status": "Multi-prompt generation started in the background!"}
    @app.get("/download-latest")
def download_latest():
    files = list(OUTPUT_DIR.glob("*.png"))
    if not files:
        raise HTTPException(status_code=404, detail="No images found yet.")
    
    # Sort by creation time to get the newest file
    latest_file = max(files, key=os.path.getctime)
    return FileResponse(path=latest_file, filename=latest_file.name, media_type='image/png')

@app.get("/")
def health_check():
    return {"status": "Bot server is running!"}
