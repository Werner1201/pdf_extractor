import os
import json
from dotenv import load_dotenv, set_key

# =========================================================
# CAMINHOS
# =========================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_DIR = os.path.join(BASE_DIR, "input")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
ENV_FILE = os.path.join(BASE_DIR, ".env")

PDF_PATH = "" 
OUTPUT_JSON = os.path.join(OUTPUT_DIR, "questoes.json")
OUTPUT_JSON_REFINED = os.path.join(OUTPUT_DIR, "questoes_refinadas.json")
OUTPUT_TXT = os.path.join(OUTPUT_DIR, "ocr_texto_bruto.txt")

# Video Capture Settings
VIDEO_TEMP_DIR = os.path.join(OUTPUT_DIR, "frames_temp")
VIDEO_OUTPUT_PDF = os.path.join(OUTPUT_DIR, "video_captura.pdf")
DEFAULT_SSIM_THRESHOLD = 0.85
DEFAULT_SAMPLE_INTERVAL = 0.5

# =========================================================
# OCR
# =========================================================
TESSERACT_LANG = "eng"
DPI = 300

TESSERACT_CMD = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
POPPLER_PATH = r"C:\Program Files\poppler-25.12.0\Library\bin"

# =========================================================
# AI SETTINGS
# =========================================================
load_dotenv(ENV_FILE)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
PREFERRED_MODELS = []

def load_settings():
    global TESSERACT_CMD, POPPLER_PATH, GEMINI_API_KEY, PREFERRED_MODELS
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                TESSERACT_CMD = data.get("tesseract_cmd", TESSERACT_CMD)
                POPPLER_PATH = data.get("poppler_path", POPPLER_PATH)
                PREFERRED_MODELS = data.get("preferred_models", PREFERRED_MODELS)
        except Exception as e:
            print(f"Erro ao carregar settings.json: {e}")

def save_settings(tesseract_cmd, poppler_path, api_key="", preferred_models=None):
    global TESSERACT_CMD, POPPLER_PATH, GEMINI_API_KEY, PREFERRED_MODELS
    TESSERACT_CMD = tesseract_cmd
    POPPLER_PATH = poppler_path
    GEMINI_API_KEY = api_key
    if preferred_models is not None:
        PREFERRED_MODELS = preferred_models
    
    data = {
        "tesseract_cmd": tesseract_cmd,
        "poppler_path": poppler_path,
        "preferred_models": PREFERRED_MODELS
    }
    try:
        if api_key:
            if not os.path.exists(ENV_FILE):
                open(ENV_FILE, "w").close()
            set_key(ENV_FILE, "GEMINI_API_KEY", api_key)
            
        with open(SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Erro ao salvar settings.json: {e}")

load_settings()
