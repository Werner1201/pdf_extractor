import cv2
import os
import shutil
import numpy as np
from skimage.metrics import structural_similarity as ssim
import config

def extract_frames(video_path, threshold=0.85, interval=0.5, progress_callback=None):
    """
    Extracts frames from a video based on structural similarity (SSIM).
    
    :param video_path: Path to the .mp4 file.
    :param threshold: SSIM threshold (0 to 1). Lower means more sensitivity to change.
    :param interval: Sampling interval in seconds.
    :param progress_callback: Optional function(msg, current, total) for UI updates.
    :return: List of paths to extracted frame images.
    """
    if not os.path.exists(config.VIDEO_TEMP_DIR):
        os.makedirs(config.VIDEO_TEMP_DIR)
    else:
        # Clean temp dir
        for f in os.listdir(config.VIDEO_TEMP_DIR):
            os.remove(os.path.join(config.VIDEO_TEMP_DIR, f))

    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        raise Exception(f"Erro ao abrir o vídeo: {video_path}")

    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration = total_frames / fps
    step = int(fps * interval)
    
    if step < 1: step = 1

    extracted_paths = []
    last_frame_gray = None
    frame_count = 0
    saved_count = 0

    if progress_callback:
        progress_callback("Iniciando extração de frames...", 0, total_frames)

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_count % step == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # SSIM calculation
            should_save = False
            if last_frame_gray is None:
                # First frame always accepted
                should_save = True
            else:
                # Compute SSIM
                score, _ = ssim(last_frame_gray, gray, full=True)
                if score < threshold:
                    should_save = True

            if should_save:
                saved_count += 1
                filename = f"frame_{saved_count:03d}.png"
                filepath = os.path.join(config.VIDEO_TEMP_DIR, filename)
                cv2.imwrite(filepath, frame)
                extracted_paths.append(filepath)
                last_frame_gray = gray
                
                if progress_callback:
                    progress_callback(f"Frame {saved_count} extraído (SSIM: {score if 'score' in locals() else 1.0:.2f})", frame_count, total_frames)

        frame_count += 1
        # Update progress less frequently for performance
        if frame_count % (step * 5) == 0 and progress_callback:
             progress_callback(f"Processando: {int(frame_count/total_frames*100)}%...", frame_count, total_frames)

    cap.release()
    if progress_callback:
        progress_callback(f"Extração concluída! {saved_count} frames gerados.", total_frames, total_frames)
    
    return extracted_paths

if __name__ == "__main__":
    # Test stub
    pass
