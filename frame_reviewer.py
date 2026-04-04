import os
import customtkinter as ctk
from PIL import Image, ImageTk

class FrameReviewer(ctk.CTkToplevel):
    """
    A GUI window to manually review and filter extracted video frames.
    """
    def __init__(self, parent, frame_paths, on_finish_callback=None):
        super().__init__(parent)
        self.title("Revisão de Frames Extraídos")
        self.geometry("900x750")
        self.transient(parent)
        self.grab_set()  # Modal relative to the parent
        
        self.frame_paths = frame_paths
        self.on_finish_callback = on_finish_callback
        self.accepted_frames = []
        self.current_idx = 0
        
        self._setup_ui()
        self._bind_keys()
        self._show_current_frame()
        
    def _setup_ui(self):
        # Info Panel
        self.info_panel = ctk.CTkFrame(self)
        self.info_panel.pack(fill="x", padx=10, pady=5)
        
        self.lbl_progress = ctk.CTkLabel(self.info_panel, text="Revisando 0/0", font=ctk.CTkFont(size=16, weight="bold"))
        self.lbl_progress.pack(pady=5)
        
        self.lbl_instr = ctk.CTkLabel(self.info_panel, text="Seta ESQUERDA: Rejeitar | Seta DIREITA: Aceitar", text_color="gray70")
        self.lbl_instr.pack()
        
        # Image Display
        self.display_frame = ctk.CTkFrame(self, fg_color="black")
        self.display_frame.pack(fill="both", expand=True, padx=20, pady=10)
        
        self.img_label = ctk.CTkLabel(self.display_frame, text="Carregando...")
        self.img_label.pack(fill="both", expand=True)

        # Control Panel
        self.ctrl_panel = ctk.CTkFrame(self)
        self.ctrl_panel.pack(fill="x", padx=10, pady=10)
        
        self.btn_reject = ctk.CTkButton(self.ctrl_panel, text="❌ Rejeitar (←)", fg_color="#c0392b", hover_color="#96281b", 
                                       width=150, height=40, command=self._reject)
        self.btn_reject.pack(side="left", padx=20, pady=10)
        
        self.btn_accept = ctk.CTkButton(self.ctrl_panel, text="✅ Aceitar (→) →", fg_color="#27ae60", hover_color="#1e8449",
                                       width=150, height=40, command=self._accept)
        self.btn_accept.pack(side="left", padx=20, pady=10)
        
        self.btn_all = ctk.CTkButton(self.ctrl_panel, text="🚀 Aceitar Todos Restantes", fg_color="#2980b9", hover_color="#1c5980",
                                    width=200, height=40, command=self._accept_all)
        self.btn_all.pack(side="right", padx=20, pady=10)
        
    def _bind_keys(self):
        self.bind("<Left>", lambda e: self._reject())
        self.bind("<Right>", lambda e: self._accept())
        
    def _show_current_frame(self):
        if self.current_idx >= len(self.frame_paths):
            self._finish()
            return
        
        self.lbl_progress.configure(text=f"Revisando {self.current_idx + 1} / {len(self.frame_paths)}")
        
        img_path = self.frame_paths[self.current_idx]
        try:
            # Pillow image
            pil_img = Image.open(img_path)
            
            # Resize logic (simple fit)
            display_w = 860
            display_h = 560
            pil_img.thumbnail((display_w, display_h))
            
            # Convert to CTkImage
            ctk_img = ctk.CTkImage(light_image=pil_img, dark_image=pil_img, size=pil_img.size)
            
            # No text, just image
            self.img_label.configure(image=ctk_img, text="")
        except Exception as e:
            self.img_label.configure(text=f"Erro ao carregar imagem:\n{str(e)[:50]}")
            
    def _accept(self):
        self.accepted_frames.append(self.frame_paths[self.current_idx])
        self._next()
        
    def _reject(self):
        # Just skip
        self._next()
        
    def _next(self):
        self.current_idx += 1
        self._show_current_frame()
        
    def _accept_all(self):
        # Accept current and all following
        remaining = self.frame_paths[self.current_idx:]
        self.accepted_frames.extend(remaining)
        self._finish()
        
    def _finish(self):
        if self.on_finish_callback:
            self.on_finish_callback(self.accepted_frames)
        self.destroy()

if __name__ == "__main__":
    # Test script if needed
    pass
