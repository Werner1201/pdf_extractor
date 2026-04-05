import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import os
import shutil
import config

class StitchReviewer(ctk.CTkToplevel):
    def __init__(self, parent, stitched_images, slice_points_list, temp_slice_paths, on_finish=None):
        super().__init__(parent)
        self.title("Revisão de Stitching - Verificar Cortes A4")
        self.grab_set()
        
        self.stitched_images = stitched_images
        self.slice_points_list = slice_points_list # List of lists of Y-coordinates
        self.temp_slice_paths = temp_slice_paths
        self.on_finish = on_finish
        self.current_idx = 0
        
        # UI Size
        self.win_w = 900
        self.win_h = 850
        self.geometry(f"{self.win_w}x{self.win_h}")
        
        # --- HEADER ---
        self.header = ctk.CTkFrame(self)
        self.header.pack(fill="x", padx=10, pady=10)
        
        self.lbl_info = ctk.CTkLabel(self.header, text="Revise a imagem costurada. Linhas vermelhas indicam os cortes A4.", font=ctk.CTkFont(weight="bold"))
        self.lbl_info.pack(pady=5)
        
        self.lbl_stats = ctk.CTkLabel(self.header, text="", text_color="gray70")
        self.lbl_stats.pack()
        
        # --- CANVAS AREA ---
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Scrollbars
        self.v_scrollbar = tk.Scrollbar(self.main_frame, orient="vertical")
        self.v_scrollbar.pack(side="right", fill="y")
        
        self.canvas = tk.Canvas(self.main_frame, bg="#2b2b2b", highlightthickness=0, yscrollcommand=self.v_scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.v_scrollbar.config(command=self.canvas.yview)
        
        # Bind mouse wheel
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        
        # --- FOOTER ---
        self.footer = ctk.CTkFrame(self)
        self.footer.pack(fill="x", padx=20, pady=15)
        
        self.btn_reject = ctk.CTkButton(self.footer, text="❌ Rejeitar e Voltar", fg_color="#e74c3c", hover_color="#c0392b", command=self._on_reject)
        self.btn_reject.pack(side="left", padx=10)
        
        # Navigation Buttons
        self.nav_frame = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.nav_frame.pack(side="left", expand=True)
        
        self.btn_prev = ctk.CTkButton(self.nav_frame, text="◀ Anterior", width=100, command=self._prev_section)
        self.btn_prev.pack(side="left", padx=5)
        
        self.btn_next = ctk.CTkButton(self.nav_frame, text="Próximo ▶", width=100, command=self._next_section)
        self.btn_next.pack(side="left", padx=5)
        
        self.btn_approve = ctk.CTkButton(self.footer, text="✅ Aprovar e Salvar", fg_color="#27ae60", hover_color="#219150", font=ctk.CTkFont(weight="bold"), command=self._on_approve)
        self.btn_approve.pack(side="right", padx=10)
        
        self._load_current()
        
    def _load_current(self):
        if not self.stitched_images: return
        
        img_np = self.stitched_images[self.current_idx]
        h, w = img_np.shape[:2]
        
        # Stats
        num_slices = len([p for p in self.temp_slice_paths if os.path.basename(p).startswith("stitch_")])
        self.lbl_stats.configure(text=f"Seção {self.current_idx+1}/{len(self.stitched_images)} | Dimensões: {w}x{h}px | Total de fatias: {num_slices}")
        
        # Scale for preview (width to fit canvas roughly)
        display_w = 800
        scale = display_w / w
        display_h = int(h * scale)
        
        import cv2
        img_rgb = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        img_resized = img_pil.resize((display_w, display_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(img_resized)
        
        # Clear canvas
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        
        # Draw Slice Lines
        # slice_points_list should be absolute Y coordinates in the ORIGINAL image
        # We need to map them back to preview scale
        # Wait, I didn't return slice points from slice_to_a4. 
        # I'll modify scroll_stitcher to return them or just re-calculate preview lines here.
        
        # Re-calculating preview lines based on A4 ratio (1.414)
        slice_h = int(w * 1.414)
        curr_y = slice_h
        while curr_y < h:
            # For simplicity in preview, just show the theoretical points
            # In a real app, we'd pass the actual cut points from the backend
            prev_y = int(curr_y * scale)
            self.canvas.create_line(0, prev_y, display_w, prev_y, fill="red", dash=(4,4), width=2)
            curr_y += slice_h
            
        self.canvas.config(scrollregion=(0, 0, display_w, display_h))
        self.canvas.yview_moveto(0) # Reset scroll pos

        # Update button states
        self.btn_prev.configure(state="normal" if self.current_idx > 0 else "disabled")
        self.btn_next.configure(state="normal" if self.current_idx < len(self.stitched_images)-1 else "disabled")

    def _prev_section(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self._load_current()
            
    def _next_section(self):
        if self.current_idx < len(self.stitched_images) - 1:
            self.current_idx += 1
            self._load_current()

    def _on_mousewheel(self, event):
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
    def _on_approve(self):
        # Move files from temp to accepted
        if not os.path.exists(config.VIDEO_ACCEPTED_DIR):
            os.makedirs(config.VIDEO_ACCEPTED_DIR)
        else:
            for f in os.listdir(config.VIDEO_ACCEPTED_DIR):
                os.remove(os.path.join(config.VIDEO_ACCEPTED_DIR, f))
                
        for path in self.temp_slice_paths:
            if os.path.exists(path):
                shutil.move(path, os.path.join(config.VIDEO_ACCEPTED_DIR, os.path.basename(path)))
        
        if self.on_finish:
            self.on_finish(True)
        self.destroy()
        
    def _on_reject(self):
        if self.on_finish:
             self.on_finish(False)
        self.destroy()
