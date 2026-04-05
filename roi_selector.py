import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import cv2

class ROISelector(ctk.CTkToplevel):
    def __init__(self, parent, image_np, on_confirm=None):
        super().__init__(parent)
        self.title("Selecionar Área Útil (ROI)")
        self.grab_set()  # Modal window
        self.after(100, self.lift) # Bring to front
        
        self.original_image_np = image_np
        self.on_confirm = on_confirm
        self.roi = None
        
        # Image dimensions
        self.img_h, self.img_w = image_np.shape[:2]
        
        # Max display size (80% of screen)
        screen_w = self.winfo_screenwidth()
        screen_h = self.winfo_screenheight()
        max_w = int(screen_w * 0.8)
        max_h = int(screen_h * 0.8)
        
        # Calculate scale to fit
        scale_w = max_w / self.img_w
        scale_h = max_h / self.img_h
        self.scale = min(scale_w, scale_h, 1.0) # Don't upscale
        
        self.disp_w = int(self.img_w * self.scale)
        self.disp_h = int(self.img_h * self.scale)
        
        # Resize image for display
        img_rgb = cv2.cvtColor(image_np, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        img_resized = img_pil.resize((self.disp_w, self.disp_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(img_resized)
        
        # --- UI LAYOUT ---
        self.geometry(f"{self.disp_w + 40}x{self.disp_h + 120}")
        
        lbl_instr = ctk.CTkLabel(self, text="Clique e arraste para desenhar o retângulo na área de conteúdo (exclua barras estáticas).", font=ctk.CTkFont(size=13))
        lbl_instr.pack(pady=10)
        
        self.canvas = tk.Canvas(self, width=self.disp_w, height=self.disp_h, bg="black", highlightthickness=0)
        self.canvas.pack(padx=20)
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        
        # Drawing state
        self.rect_id = None
        self.start_x = None
        self.start_y = None
        self.cur_roi_disp = None # (x1, y1, x2, y2)
        
        self.canvas.bind("<ButtonPress-1>", self._on_press)
        self.canvas.bind("<B1-Motion>", self._on_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_release)
        
        # Buttons
        self.btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.btn_frame.pack(pady=15)
        
        self.btn_cancel = ctk.CTkButton(self.btn_frame, text="Cancelar", fg_color="transparent", border_width=1, command=self._cancel)
        self.btn_cancel.pack(side="left", padx=10)
        
        self.btn_ok = ctk.CTkButton(self.btn_frame, text="✅ Confirmar ROI", command=self._confirm)
        self.btn_ok.pack(side="left", padx=10)
        
    def _on_press(self, event):
        self.start_x = event.x
        self.start_y = event.y
        if self.rect_id:
            self.canvas.delete(self.rect_id)
        self.rect_id = self.canvas.create_rectangle(self.start_x, self.start_y, self.start_x, self.start_y, outline="cyan", width=2, dash=(4,4))
        
    def _on_drag(self, event):
        cur_x, cur_y = event.x, event.y
        # Clamp to canvas
        cur_x = max(0, min(self.disp_w, cur_x))
        cur_y = max(0, min(self.disp_h, cur_y))
        
        self.canvas.coords(self.rect_id, self.start_x, self.start_y, cur_x, cur_y)
        self.cur_roi_disp = (self.start_x, self.start_y, cur_x, cur_y)
        
    def _on_release(self, event):
        if self.cur_roi_disp:
            x1, y1, x2, y2 = self.cur_roi_disp
            # Normalize (ensure x1 < x2, etc)
            nx1, nx2 = (min(x1, x2), max(x1, x2))
            ny1, ny2 = (min(y1, y2), max(y1, y2))
            self.cur_roi_disp = (nx1, ny1, nx2, ny2)
            
            # Map back to original image coordinates
            ox1 = int(nx1 / self.scale)
            oy1 = int(ny1 / self.scale)
            ox2 = int(nx2 / self.scale)
            oy2 = int(ny2 / self.scale)
            
            # Clamp to image size
            ox1 = max(0, min(self.img_w, ox1))
            oy1 = max(0, min(self.img_h, oy1))
            ox2 = max(0, min(self.img_w, ox2))
            oy2 = max(0, min(self.img_h, oy2))
            
            width = ox2 - ox1
            height = oy2 - oy1
            
            if width > 10 and height > 10:
                self.roi = (ox1, oy1, width, height)
            else:
                self.roi = None
                if self.rect_id: 
                    self.canvas.delete(self.rect_id)
                    self.rect_id = None
        
    def _cancel(self):
        self.roi = None
        self.destroy()
        
    def _confirm(self):
        if not self.roi:
            # Default to full image if nothing selected? Or ask?
            # Better to force a selection or warn.
            import messagebox
            tk.messagebox.showwarning("Aviso", "Por favor, selecione uma área no frame antes de confirmar.")
            return
            
        if self.on_confirm:
            self.on_confirm(self.roi)
        self.destroy()

# Static helper to run and wait for result
def get_roi_selection(parent, image_np):
    """
    Shows a ROI selection window and blocks until closed.
    Returns (x, y, w, h) or None if cancelled.
    """
    result = {"roi": None}
    
    def on_confirm(roi):
        result["roi"] = roi
        
    dialog = ROISelector(parent, image_np, on_confirm=on_confirm)
    parent.wait_window(dialog)
    return result["roi"]
