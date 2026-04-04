import os
from PIL import Image
import img2pdf
import config

def build_pdf_from_frames(frame_paths, output_pdf_path=None):
    """
    Combines a list of frame images into a single PDF, optimized for OCR.
    
    :param frame_paths: List of file paths to the .png frames.
    :param output_pdf_path: Path to the final .pdf file.
    :return: The path to the generated PDF.
    """
    if not output_pdf_path:
        output_pdf_path = config.VIDEO_OUTPUT_PDF
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_pdf_path), exist_ok=True)
    
    if not frame_paths:
        raise Exception("Lista de frames vazia. Nenhum PDF gerado.")

    # Optimized image list for img2pdf
    bytes_list = []
    
    for path in frame_paths:
        with open(path, "rb") as f:
            bytes_list.append(f.read())
            
    # Simple conversion using img2pdf (which is very fast)
    with open(output_pdf_path, "wb") as f:
        f.write(img2pdf.convert(bytes_list))
        
    return output_pdf_path

def cleanup_temp_frames():
    """Removes temporary extracted frames."""
    if os.path.exists(config.VIDEO_TEMP_DIR):
        for f in os.listdir(config.VIDEO_TEMP_DIR):
            try:
                os.remove(os.path.join(config.VIDEO_TEMP_DIR, f))
            except: pass

if __name__ == "__main__":
    # Test stub
    pass
