import cv2
import numpy as np
import os
import config

def find_vertical_overlap(img_a, img_b, search_ratio=0.5):
    """
    Finds the vertical offset where img_b overlaps img_a.
    search_ratio: how much of the image height to use for matching (default 50%).
    """
    h, w = img_a.shape[:2]
    search_h = int(h * search_ratio)
    
    # Template: take the top part of the NEW frame
    template = img_b[0:search_h, :]
    # Search area: take the bottom part of the OLD frame
    search_area = img_a[int(h * (1 - search_ratio)):, :]
    
    # Template matching
    res = cv2.matchTemplate(search_area, template, cv2.TM_CCOEFF_NORMED)
    min_val, max_val, min_loc, max_loc = cv2.minMaxLoc(res)
    
    # max_loc[1] is the Y-offset relative to the start of the search area
    # The actual offset from top of A to top of B is:
    # (h - search_h) + max_loc[1]
    # However, we want to know how much of B is NEW content.
    # The overlap height is: search_h - max_loc[1]
    
    overlap_h = search_h - max_loc[1]
    return max_val, overlap_h

def stitch_frames(frame_paths, roi=None, min_correlation=0.7, progress_callback=None):
    """
    Stitches a list of frames into one or more long images.
    Returns: List of stitched numpy images.
    """
    if not frame_paths:
        return []

    stitched_images = []
    current_stitched = None
    
    total = len(frame_paths)
    
    for i, path in enumerate(frame_paths):
        frame = cv2.imread(path)
        if frame is None: continue
        
        # Apply ROI crop
        if roi:
            x, y, w, h = roi
            frame = frame[y:y+h, x:x+w]
            
        if current_stitched is None:
            current_stitched = frame
            continue
            
        # Match with last frame (we only need the last 'h' pixels of current_stitched)
        # to avoid template matching against a massive image
        h_current, w_current = current_stitched.shape[:2]
        h_frame, w_frame = frame.shape[:2]
        
        # Take the last frame-height portion of the stitched image for comparison
        last_portion = current_stitched[-h_frame:, :]
        
        corr, overlap_h = find_vertical_overlap(last_portion, frame)
        
        if progress_callback:
            progress_callback(f"Stitching frame {i+1}/{total} (Corr: {corr:.2f})", i+1, total)
            
        if corr >= min_correlation and overlap_h > 0:
            # We found a match! Extract only the NEW part of the current frame
            new_part = frame[overlap_h:, :]
            if new_part.size > 0:
                current_stitched = np.vstack((current_stitched, new_part))
        else:
            # Section break or bad match
            # If the image is already large, start a new one
            stitched_images.append(current_stitched)
            current_stitched = frame
            
        # Memory safety: if the image is too tall, force a break
        if current_stitched.shape[0] > 60000:
             stitched_images.append(current_stitched)
             current_stitched = None

    if current_stitched is not None:
        stitched_images.append(current_stitched)
        
    return stitched_images

def find_safe_cut(image, target_y, search_range=50):
    """
    Searches for a line with minimum horizontal variation around target_y.
    """
    h, w = image.shape[:2]
    y_start = max(0, target_y - search_range)
    y_end = min(h, target_y + search_range)
    
    if y_start >= y_end: return target_y
    
    # Convert to gray for faster processing
    gray = cv2.cvtColor(image[y_start:y_end, :], cv2.COLOR_BGR2GRAY)
    
    # Calculate variance of each row
    variances = np.var(gray, axis=1)
    
    # Find index of minimum variance
    min_idx = np.argmin(variances)
    return y_start + min_idx

def slice_to_a4(stitched_images, output_dir, target_ratio=1.414):
    """
    Slices long images into A4-proportioned PNGs.
    Returns: List of saved file paths.
    """
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    else:
        # Clean
        for f in os.listdir(output_dir):
            if f.startswith("stitch_"):
                os.remove(os.path.join(output_dir, f))
                
    saved_paths = []
    global_count = 1
    
    for idx, img in enumerate(stitched_images):
        h, w = img.shape[:2]
        slice_h = int(w * target_ratio)
        
        current_y = 0
        while current_y < h:
            target_next_y = current_y + slice_h
            
            if target_next_y >= h:
                # Last slice
                actual_next_y = h
            else:
                # Look for a safe cut point
                actual_next_y = find_safe_cut(img, target_next_y)
                
            # Crop and save
            slice_img = img[current_y:actual_next_y, :]
            
            # Avoid tiny leftover slices
            if slice_img.shape[0] > 50:
                filename = f"stitch_{global_count:03d}.png"
                filepath = os.path.join(output_dir, filename)
                cv2.imwrite(filepath, slice_img)
                saved_paths.append(filepath)
                global_count += 1
                
            current_y = actual_next_y
            
    return saved_paths
