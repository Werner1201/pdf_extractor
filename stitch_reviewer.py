import customtkinter as ctk
import tkinter as tk
from PIL import Image, ImageTk
import os
import shutil
import cv2
import config

class StitchReviewer(ctk.CTkToplevel):
    def __init__(self, parent, stitched_images, on_finish=None):
        super().__init__(parent)
        self.title("Revisão de Stitching Contínuo")
        self.grab_set()
        self.after(100, self.focus_set)
        
        self.stitched_images = stitched_images
        self.on_finish = on_finish
        self.current_idx = 0
        self.zoom_level = 1.0 # 1.0 = fit to width (800px)
        
        # UI Size
        self.win_w = 1000
        self.win_h = 900
        self.geometry(f"{self.win_w}x{self.win_h}")
        
        # --- HEADER ---
        self.header = ctk.CTkFrame(self)
        self.header.pack(fill="x", padx=10, pady=10)
        
        self.lbl_info = ctk.CTkLabel(self.header, text="Revise a imagem costurada contínua.", font=ctk.CTkFont(weight="bold", size=16))
        self.lbl_info.pack(pady=2)
        
        self.lbl_stats = ctk.CTkLabel(self.header, text="", text_color="gray70")
        self.lbl_stats.pack()
        
        # Zoom Controls
        self.zoom_frame = ctk.CTkFrame(self.header, fg_color="transparent")
        self.zoom_frame.pack(pady=5)
        
        ctk.CTkButton(self.zoom_frame, text="-", width=30, command=self._zoom_out).pack(side="left", padx=5)
        self.lbl_zoom = ctk.CTkLabel(self.zoom_frame, text="Zoom: 100%")
        self.lbl_zoom.pack(side="left", padx=10)
        ctk.CTkButton(self.zoom_frame, text="+", width=30, command=self._zoom_in).pack(side="left", padx=5)
        ctk.CTkLabel(self.zoom_frame, text="(Dica: Ctrl + Scroll do Mouse)", font=ctk.CTkFont(size=11, slant="italic")).pack(side="left", padx=20)

        # --- CANVAS AREA ---
        self.main_frame = ctk.CTkFrame(self)
        self.main_frame.pack(fill="both", expand=True, padx=20, pady=5)
        
        # Scrollbars
        self.v_scrollbar = tk.Scrollbar(self.main_frame, orient="vertical")
        self.v_scrollbar.pack(side="right", fill="y")
        self.h_scrollbar = tk.Scrollbar(self.main_frame, orient="horizontal")
        self.h_scrollbar.pack(side="bottom", fill="x")
        
        self.canvas = tk.Canvas(self.main_frame, bg="#1a1a1a", highlightthickness=0, 
                               yscrollcommand=self.v_scrollbar.set, xscrollcommand=self.h_scrollbar.set)
        self.canvas.pack(side="left", fill="both", expand=True)
        
        self.v_scrollbar.config(command=self.canvas.yview)
        self.h_scrollbar.config(command=self.canvas.xview)
        
        # Bindings
        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self.bind("<Control-MouseWheel>", self._on_ctrl_mousewheel)
        self.bind("<Destroy>", self._on_destroy)
        
        # --- FOOTER ---
        self.footer = ctk.CTkFrame(self)
        self.footer.pack(fill="x", padx=20, pady=15)
        
        self.btn_reject = ctk.CTkButton(self.footer, text="❌ Rejeitar e Voltar", fg_color="#e74c3c", hover_color="#c0392b", command=self._on_reject)
        self.btn_reject.pack(side="left", padx=10)
        
        # Navigation
        self.nav_frame = ctk.CTkFrame(self.footer, fg_color="transparent")
        self.nav_frame.pack(side="left", expand=True)
        self.btn_prev = ctk.CTkButton(self.nav_frame, text="◀ Anterior", width=100, command=self._prev_section)
        self.btn_prev.pack(side="left", padx=5)
        self.btn_next = ctk.CTkButton(self.nav_frame, text="Próximo ▶", width=100, command=self._next_section)
        self.btn_next.pack(side="left", padx=5)
        
        self.btn_approve = ctk.CTkButton(self.footer, text="✅ Aprovar e Salvar Única", fg_color="#27ae60", hover_color="#219150", font=ctk.CTkFont(weight="bold"), command=self._on_approve)
        self.btn_approve.pack(side="right", padx=10)
        
        self._load_current()
        
    def _load_current(self):
        if not self.stitched_images: return
        
        img_np = self.stitched_images[self.current_idx]
        h, w = img_np.shape[:2]
        
        self.lbl_stats.configure(text=f"Seção {self.current_idx+1}/{len(self.stitched_images)} | Tamanho: {w}x{h}px")
        
        # Base width for 100% zoom (fit to canvas width approx)
        base_w = 850
        display_w = int(base_w * self.zoom_level)
        scale = display_w / w
        display_h = int(h * scale)
        
        # Avoid crashing if too large for PhotoImage
        # (Though PhotoImage is usually fine up to system limits)
        img_rgb = cv2.cvtColor(img_np, cv2.COLOR_BGR2RGB)
        img_pil = Image.fromarray(img_rgb)
        img_resized = img_pil.resize((display_w, display_h), Image.Resampling.LANCZOS)
        self.photo = ImageTk.PhotoImage(img_resized)
        
        self.canvas.delete("all")
        self.canvas.create_image(0, 0, image=self.photo, anchor="nw")
        self.canvas.config(scrollregion=(0, 0, display_w, display_h))
        self.lbl_zoom.configure(text=f"Zoom: {int(self.zoom_level * 100)}%")

        # Update button states
        self.btn_prev.configure(state="normal" if self.current_idx > 0 else "disabled")
        self.btn_next.configure(state="normal" if self.current_idx < len(self.stitched_images)-1 else "disabled")

    def _zoom_in(self):
        self.zoom_level = min(self.zoom_level + 0.2, 5.0)
        self._load_current()

    def _zoom_out(self):
        self.zoom_level = max(self.zoom_level - 0.2, 0.2)
        self._load_current()

    def _on_mousewheel(self, event):
        # Regular scroll
        try:
            if self.canvas.winfo_exists():
                self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        except:
            pass
        
    def _on_ctrl_mousewheel(self, event):
        # Zoom scroll
        if event.delta > 0: self._zoom_in()
        else: self._zoom_out()

    def _on_destroy(self, event):
        # Desvincula o evento global para não dar erro após fechar
        try:
            self.canvas.unbind_all("<MouseWheel>")
        except:
            pass

    def _prev_section(self):
        if self.current_idx > 0:
            self.current_idx -= 1
            self._load_current()
            
    def _next_section(self):
        if self.current_idx < len(self.stitched_images) - 1:
            self.current_idx += 1
            self._load_current()
            
    def _on_approve(self):
        # Clear accepted folder
        if not os.path.exists(config.VIDEO_ACCEPTED_DIR):
            os.makedirs(config.VIDEO_ACCEPTED_DIR)
        else:
            for f in os.listdir(config.VIDEO_ACCEPTED_DIR):
                os.remove(os.path.join(config.VIDEO_ACCEPTED_DIR, f))
                
        # Save all stitched images (usually just one)
        for i, img_np in enumerate(self.stitched_images):
            filepath = os.path.join(config.VIDEO_ACCEPTED_DIR, f"stitched_full_{i+1:02d}.png")
            cv2.imwrite(filepath, img_np)
            
        if self.on_finish:
            self.on_finish(True)
        self.destroy()
        
    def _on_reject(self):
        if self.on_finish:
             self.on_finish(False)
        self.destroy()
