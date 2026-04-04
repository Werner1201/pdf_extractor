import os
import json
import threading
import subprocess
import customtkinter as ctk
from tkinter import filedialog, messagebox

import config
from ocr import extrair_texto_do_pdf
from parser_questoes import processar_todas
from ai_refiner import refinar_questoes_por_ia, PROMPT_MANUAL

ctk.set_appearance_mode("Dark")
ctk.set_default_color_theme("blue")

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("PDF OCR Extractor - Em Fases")
        self.geometry("1100x880")
        self.minsize(1000, 700)
        
        self.pdf_path = ""
        self.txt_path = config.OUTPUT_TXT if os.path.exists(config.OUTPUT_TXT) else ""
        self.json_path = config.OUTPUT_JSON if os.path.exists(config.OUTPUT_JSON) else ""
        
        # --- ROOT TABVIEW ---
        self.tabview = ctk.CTkTabview(self)
        self.tabview.pack(fill="both", expand=True, padx=10, pady=10)
        self.tabview.add("🗂️ Extrator")
        self.tabview.add("🔗 Unificador JSON")
        
        tab_ext = self.tabview.tab("🗂️ Extrator")
        tab_uni = self.tabview.tab("🔗 Unificador JSON")
        
        self._build_extrator(tab_ext)
        self._build_unificador(tab_uni)

    def _build_extrator(self, parent):
        # --- TITLE ---
        self.lbl_title = ctk.CTkLabel(parent, text="Extrator de Questões - Dividido em Fases", font=ctk.CTkFont(size=20, weight="bold"))
        self.lbl_title.pack(pady=5)
        
        # --- CONFIG FRAME (TOP) ---
        self.frame_config = ctk.CTkFrame(parent)
        self.frame_config.pack(padx=20, pady=5, fill="x")
        
        self.lbl_tess = ctk.CTkLabel(self.frame_config, text="Tesseract EXE:")
        self.lbl_tess.grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.entry_tess = ctk.CTkEntry(self.frame_config, width=300)
        self.entry_tess.grid(row=0, column=1, padx=10, pady=5, sticky="ew")
        self.entry_tess.insert(0, config.TESSERACT_CMD)
        
        self.lbl_pop = ctk.CTkLabel(self.frame_config, text="Poppler Bin:")
        self.lbl_pop.grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.entry_pop = ctk.CTkEntry(self.frame_config, width=300)
        self.entry_pop.grid(row=1, column=1, padx=10, pady=5, sticky="ew")
        self.entry_pop.insert(0, config.POPPLER_PATH)

        self.lbl_api = ctk.CTkLabel(self.frame_config, text="Gemini API Key:")
        self.lbl_api.grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.entry_api = ctk.CTkEntry(self.frame_config, width=300, show="*")
        self.entry_api.grid(row=2, column=1, padx=10, pady=5, sticky="ew")
        self.entry_api.insert(0, config.GEMINI_API_KEY)
        
        self.btn_save_cfg = ctk.CTkButton(self.frame_config, text="Salvar\nConfigurações", height=60, width=120, command=self.save_configs)
        self.btn_save_cfg.grid(row=0, column=2, rowspan=3, padx=20, pady=10)
        
        self.frame_config.grid_columnconfigure(1, weight=1)
        
        # --- SPLIT CONTAINER (Fase 1 e Fase 2) ---
        self.frame_main = ctk.CTkFrame(parent, fg_color="transparent")
        self.frame_main.pack(padx=20, pady=10, fill="both", expand=True)
        self.frame_main.grid_columnconfigure(0, weight=1)
        self.frame_main.grid_columnconfigure(1, weight=1)
        
        # ==========================================
        # LEFT COLUMN (FASE 1: OCR)
        # ==========================================
        self.frame_fase1 = ctk.CTkFrame(self.frame_main)
        self.frame_fase1.grid(row=0, column=0, padx=(0, 10), sticky="nsew")
        
        self.lbl_f1_title = ctk.CTkLabel(self.frame_fase1, text="Fase 1: OCR -> Arquivo TXT", font=ctk.CTkFont(weight="bold", size=16))
        self.lbl_f1_title.pack(pady=10)
        
        self.lbl_file = ctk.CTkLabel(self.frame_fase1, text="Nenhum PDF selecionado.", wraplength=400)
        self.lbl_file.pack(pady=10)
        self.btn_select_file = ctk.CTkButton(self.frame_fase1, text="Procurar PDF", command=self.select_pdf)
        self.btn_select_file.pack(pady=5)
        
        self.btn_start_ocr = ctk.CTkButton(self.frame_fase1, text="GERAR TXT (OCR)", height=40, fg_color="#ff9900", hover_color="#cc7a00", command=self.start_fase1)
        self.btn_start_ocr.pack(pady=10)
        
        self.progress_ocr = ctk.CTkProgressBar(self.frame_fase1)
        self.progress_ocr.pack(padx=20, pady=5, fill="x")
        self.progress_ocr.set(0)
        
        self.log_ocr = ctk.CTkTextbox(self.frame_fase1, height=100, font=("Consolas", 11))
        self.log_ocr.pack(padx=20, pady=5, fill="both", expand=True)
        self.log_ocr.configure(state="disabled")

        # ==========================================
        # RIGHT COLUMN (FASE 2: PARSING)
        # ==========================================
        self.frame_fase2 = ctk.CTkFrame(self.frame_main)
        self.frame_fase2.grid(row=0, column=1, padx=(10, 0), sticky="nsew")
        
        self.lbl_f2_title = ctk.CTkLabel(self.frame_fase2, text="Fase 2: TXT -> Arquivo JSON", font=ctk.CTkFont(weight="bold", size=16))
        self.lbl_f2_title.pack(pady=10)
        
        txt_name = os.path.basename(self.txt_path) if self.txt_path else "Nenhum TXT."
        self.lbl_txt = ctk.CTkLabel(self.frame_fase2, text=f"TXT: {txt_name}", wraplength=400)
        self.lbl_txt.pack(pady=10)
        self.btn_select_txt = ctk.CTkButton(self.frame_fase2, text="Procurar TXT Base", command=self.select_txt)
        self.btn_select_txt.pack(pady=5)
        
        self.btn_start_json = ctk.CTkButton(self.frame_fase2, text="GERAR JSON (Parse)", height=40, fg_color="#28a745", hover_color="#218838", command=self.start_fase2)
        self.btn_start_json.pack(pady=10)
        
        self.log_json = ctk.CTkTextbox(self.frame_fase2, height=100, font=("Consolas", 11))
        self.log_json.pack(padx=20, pady=5, fill="both", expand=True)
        self.log_json.configure(state="disabled")

        # ==========================================
        # BOTTOM ROW (FASE 3: IA)
        # ==========================================
        self.frame_fase3 = ctk.CTkFrame(parent)
        self.frame_fase3.pack(padx=20, pady=(0, 10), fill="x")
        
        self.lbl_f3_title = ctk.CTkLabel(self.frame_fase3, text="Fase 3: Refinamento de Inteligência Artificial (Opcional)", font=ctk.CTkFont(weight="bold", size=16))
        self.lbl_f3_title.pack(pady=10)

        self.f3_content = ctk.CTkFrame(self.frame_fase3, fg_color="transparent")
        self.f3_content.pack(fill="x", padx=10, pady=5)
        self.f3_content.grid_columnconfigure(0, weight=1)
        self.f3_content.grid_columnconfigure(1, weight=1)

        # Esquerda IA (Automático)
        self.f3_auto = ctk.CTkFrame(self.f3_content)
        self.f3_auto.grid(row=0, column=0, padx=10, sticky="nsew")
        
        # Informativo de Cotas
        cota_alerta = "Limites (Free Tier): 15 Req/Min & 20 Req/Dia.\nO sistema aguardará os segundos necessários!"
        self.lbl_auto_ia = ctk.CTkLabel(self.f3_auto, text="Automação via API do Gemini", font=ctk.CTkFont(size=14, weight="bold"))
        self.lbl_auto_ia.pack(pady=(5, 0))
        self.lbl_cota = ctk.CTkLabel(self.f3_auto, text=cota_alerta, text_color="yellow", font=ctk.CTkFont(size=12, slant="italic"))
        self.lbl_cota.pack(pady=(0, 5))
        
        self.btn_run_ia = ctk.CTkButton(self.f3_auto, text="REFINAR JSON VIA API", fg_color="#8a2be2", hover_color="#5a189a", height=35, command=self.start_fase3_auto)
        self.btn_run_ia.pack(pady=5)
        
        self.btn_shield = ctk.CTkButton(self.f3_auto, text="⚙️ Testar & Configurar Fallbacks", hover_color="#444", fg_color="transparent", border_width=1, command=self.open_shield_window)
        self.btn_shield.pack(pady=(0, 5))
        
        self.lbl_countdown = ctk.CTkLabel(self.f3_auto, text="", text_color="cyan", font=ctk.CTkFont(weight="bold"))
        self.lbl_countdown.pack(pady=(0, 5))
        
        self.log_ia = ctk.CTkTextbox(self.f3_auto, height=80, font=("Consolas", 11))
        self.log_ia.pack(padx=10, pady=5, fill="both")
        self.log_ia.configure(state="disabled")

        # Direita IA (Manual Prompt)
        self.f3_manual = ctk.CTkFrame(self.f3_content)
        self.f3_manual.grid(row=0, column=1, padx=10, sticky="nsew")

        self.lbl_man_ia = ctk.CTkLabel(self.f3_manual, text="Alternativa Manual (Usar ChatGPT/Claude)", font=ctk.CTkFont(weight="bold"))
        self.lbl_man_ia.pack(pady=5)

        self.btn_toggle_prompt = ctk.CTkButton(self.f3_manual, text="Expandir Prompt de Ouro", fg_color="transparent", border_width=1, hover_color="#444", command=self.toggle_prompt)
        self.btn_toggle_prompt.pack(pady=5)

        self.textbox_prompt = ctk.CTkTextbox(self.f3_manual, height=80, font=("Consolas", 11))
        # Nao exibe de imediato
        self.textbox_prompt.insert("1.0", PROMPT_MANUAL.strip())
        self.textbox_prompt.configure(state="disabled")
        
        self.btn_copy_prompt = ctk.CTkButton(self.f3_manual, text="Copiar Prompt", width=100, command=self.copy_prompt)

    # --- HELPERS ---
    def save_configs(self):
        config.save_settings(self.entry_tess.get(), self.entry_pop.get(), self.entry_api.get())
        messagebox.showinfo("Sucesso", "Configurações salvas.")
        
    def select_pdf(self):
        path = filedialog.askopenfilename(filetypes=[("PDF Files", "*.pdf")])
        if path:
            self.pdf_path = path
            self.lbl_file.configure(text=f"PDF: {os.path.basename(path)}")
            
    def select_txt(self):
        path = filedialog.askopenfilename(filetypes=[("Text Files", "*.txt")])
        if path:
            self.txt_path = path
            self.lbl_txt.configure(text=f"TXT: {os.path.basename(path)}")

    def _write_log(self, textbox, msg):
        textbox.configure(state="normal")
        textbox.insert("end", msg + "\n")
        textbox.see("end")
        textbox.configure(state="disabled")

    # --- FASE 1 (OCR) ---
    def progress_callback_ocr(self, msg, current, total):
        self.after(0, self._update_ui_ocr, msg, current, total)
        
    def _update_ui_ocr(self, msg, current, total):
        self._write_log(self.log_ocr, msg)
        if total > 0:
            self.progress_ocr.set(current / total)

    def start_fase1(self):
        if not self.pdf_path:
            messagebox.showwarning("Aviso", "Selecione o PDF para o OCR!")
            return
            
        self.save_configs()
        self.btn_start_ocr.configure(state="disabled")
        self.log_ocr.configure(state="normal")
        self.log_ocr.delete("1.0", "end")
        self.log_ocr.configure(state="disabled")
        self._write_log(self.log_ocr, "--- INICIANDO OCR (FASE 1) ---")
        self.progress_ocr.set(0)
        
        threading.Thread(target=self._run_fase1, daemon=True).start()
        
    def _run_fase1(self):
        os.makedirs(config.OUTPUT_DIR, exist_ok=True)
        try:
            texto_bruto = extrair_texto_do_pdf(self.pdf_path, self.progress_callback_ocr)
            txt_dest = config.OUTPUT_TXT
            with open(txt_dest, "w", encoding="utf-8") as f:
                f.write(texto_bruto)
                
            self.progress_callback_ocr("✅ Etapa concluída! Texto salvo no TXT.", 1, 1)
            self.txt_path = txt_dest
            self.after(0, lambda: self.lbl_txt.configure(text=f"TXT Automático: {os.path.basename(txt_dest)}"))
            self.progress_callback_ocr("=> Abrindo pasta do documento...", 1, 1)
            try:
                os.startfile(config.OUTPUT_DIR)
            except: pass
                
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erro de OCR", f"Erro: {e}"))
            
        self.after(0, lambda: self.btn_start_ocr.configure(state="normal"))

    # --- FASE 2 (JSON) ---
    def start_fase2(self):
        if not self.txt_path or not os.path.exists(self.txt_path):
            messagebox.showwarning("Aviso", "Escolha um arquivo .txt válido gerado previamente.")
            return
            
        self.btn_start_json.configure(state="disabled")
        self.log_json.configure(state="normal")
        self.log_json.delete("1.0", "end")
        self.log_json.configure(state="disabled")
        self._write_log(self.log_json, "--- INICIANDO PROCESSAMENTO (FASE 2) ---")
        
        threading.Thread(target=self._run_fase2, daemon=True).start()
        
    def _run_fase2(self):
        try:
            with open(self.txt_path, "r", encoding="utf-8") as f:
                texto = f.read()
                
            self._write_log(self.log_json, "Lendo texto bruto e corrigindo alternativas...")
            questoes = processar_todas(texto)
            
            total = len(questoes)
            com_res = sum(1 for q in questoes if q.get("correct_answer"))
            
            os.makedirs(config.OUTPUT_DIR, exist_ok=True)
            with open(config.OUTPUT_JSON, "w", encoding="utf-8") as f:
                json.dump(questoes, f, ensure_ascii=False, indent=2)
                
            self.json_path = config.OUTPUT_JSON
            self._write_log(self.log_json, f"JSON Salvo: {config.OUTPUT_JSON}")
            self._write_log(self.log_json, f"Encontradas {total} questões.\n({com_res} com reposta definida)")
            
            try: os.startfile(config.OUTPUT_JSON)
            except: pass
                
        except Exception as e:
            self.after(0, lambda: messagebox.showerror("Erro no Parser", str(e)))
            
        self.after(0, lambda: self.btn_start_json.configure(state="normal"))

    # --- FASE 3 (IA REFINER) ---
    def toggle_prompt(self):
        # Exibe ou oculta a text area do prompt manual
        try:
            if not self.textbox_prompt.winfo_viewable():
                self.textbox_prompt.pack(padx=10, pady=5, fill="both", expand=True)
                self.btn_copy_prompt.pack(pady=5)
                self.btn_toggle_prompt.configure(text="Recolher Prompt")
            else:
                self.textbox_prompt.pack_forget()
                self.btn_copy_prompt.pack_forget()
                self.btn_toggle_prompt.configure(text="Expandir Prompt de Ouro")
        except AttributeError:
             self.textbox_prompt.pack(padx=10, pady=5, fill="both", expand=True)
             self.btn_copy_prompt.pack(pady=5)
             self.btn_toggle_prompt.configure(text="Recolher Prompt")

    def copy_prompt(self):
        self.clipboard_clear()
        self.clipboard_append(PROMPT_MANUAL.strip())
        self.update()
        messagebox.showinfo("Copiado!", "Prompt copiado para a área de transferência.\nBasta colar no ChatGPT e jogar o JSON embaixo!")

    # --- FASE 3 BLINDAGEM (TEST & SELECT) ---
    def open_shield_window(self):
        w = ctk.CTkToplevel(self)
        w.title("Escudo Anti-Queda - Model Tester")
        w.geometry("600x500")
        w.transient(self)
        
        lbl = ctk.CTkLabel(w, text="Testador de Api (Dry-Run)", font=ctk.CTkFont(weight="bold", size=16))
        lbl.pack(pady=10)
        
        sv_log = ctk.CTkTextbox(w, height=120)
        
        frame_cb = ctk.CTkScrollableFrame(w)
        btn_save = ctk.CTkButton(w, text="Salvar Escudo (Cascata Oficial)", state="disabled", command=lambda: self._save_cascade(w))
        
        btn_test = ctk.CTkButton(w, text="▶️ Iniciar Bateria de Testes ao Vivo", command=lambda: threading.Thread(target=self._run_tester, args=(w, sv_log, frame_cb, btn_save, btn_test), daemon=True).start())
        btn_test.pack(pady=5)
        
        sv_log.pack(fill="x", padx=10, pady=5)
        
        lbl2 = ctk.CTkLabel(w, text="Modelos Aprovados no Teste (Marque os que deseja usar):")
        lbl2.pack(pady=(10, 0))
        
        frame_cb.pack(fill="both", expand=True, padx=10, pady=5)
        btn_save.pack(pady=10)
        
        w.cb_vars = {}

    def _run_tester(self, w, sv_log, frame_cb, btn_save, btn_test):
        self.after(0, lambda: btn_test.configure(state="disabled"))
        self.after(0, lambda: sv_log.insert("end", "Conectando e puxando lista...\n"))
        try:
            import config
            from google import genai
            from google.genai import types
            import time
            client = genai.Client(api_key=config.GEMINI_API_KEY)
            models = client.models.list()
            flash_models = [m.name.replace("models/", "") for m in models if "flash" in m.name.lower()]
            
            for m in flash_models:
                self.after(0, lambda x=m: sv_log.insert("end", f"Testando: {x}... "))
                self.after(0, sv_log.see, "end")
                try:
                    client.models.generate_content(
                        model=m,
                        contents="Say hi in json format exactly: {'msg': 'hi'}",
                        config=types.GenerateContentConfig(response_mime_type="application/json")
                    )
                    self.after(0, lambda: sv_log.insert("end", "✅ Aprovado\n"))
                    self.after(0, lambda x=m: self._add_checkbox(w, frame_cb, x))
                except Exception as e:
                    e_str = str(e).lower()
                    if '400' in e_str or 'invalid' in e_str:
                        self.after(0, lambda: sv_log.insert("end", "❌ 400 (Multimodalidade Incompatível)\n"))
                    elif '429' in e_str or 'quota' in e_str:
                         self.after(0, lambda: sv_log.insert("end", "⚠️ 429 (Cota Limite)\n"))
                    elif '404' in e_str:
                         self.after(0, lambda: sv_log.insert("end", "❌ 404 (Endpoint Rejeitado)\n"))
                    else:
                         self.after(0, lambda err=e_str: sv_log.insert("end", f"❔ Falha Desconhecida: {err[:30]}\n"))
                time.sleep(2)
                
            self.after(0, lambda: sv_log.insert("end", "Bateria Finalizada!\n"))
            self.after(0, lambda: btn_save.configure(state="normal"))
        except Exception as e:
             self.after(0, lambda err=str(e): sv_log.insert("end", f"Erro fatal ao conectar: {err[:50]}\n"))

    def _add_checkbox(self, w, frame_cb, model_name):
        var = ctk.StringVar(value=model_name)
        import config
        is_there = model_name in config.PREFERRED_MODELS
        if not is_there and len(config.PREFERRED_MODELS) == 0:
             is_there = True
        
        cb = ctk.CTkCheckBox(frame_cb, text=model_name, variable=var, onvalue=model_name, offvalue="")
        if is_there:
             cb.select()
        else:
             cb.deselect()
        cb.pack(anchor="w", pady=2)
        w.cb_vars[model_name] = var

    def _save_cascade(self, w):
        import config
        selected = []
        for name, var in w.cb_vars.items():
            val = var.get()
            if val:
                selected.append(val)
        config.save_settings(self.entry_tess.get(), self.entry_pop.get(), self.entry_api.get(), preferred_models=selected)
        messagebox.showinfo("Escudo Salvo", f"Modelo Cascata blindado com os seguintes em ordem:\n{', '.join(selected)}")
        w.destroy()

    # --- FASE 3 (EXECUCAO NORMAL) ---
    def start_fase3_auto(self):
        if not self.json_path or not os.path.exists(self.json_path):
            messagebox.showwarning("Fase 2 Ausente", "Execute a Fase 2 primeiro. Nao foi encontrado um questoes.json!")
            return
            
        self.save_configs()
        self.btn_run_ia.configure(state="disabled")
        self.log_ia.configure(state="normal")
        self.log_ia.delete("1.0", "end")
        self.log_ia.configure(state="disabled")
        
        threading.Thread(target=self._run_fase3, daemon=True).start()

    def _run_fase3(self):
        api_key = config.GEMINI_API_KEY
        
        def cb(msg, curr, tot):
            self.after(0, lambda: self._write_log(self.log_ia, msg))
            
        def timer_cb(msg):
            # Escreve o countdown dinamico no label reservado e nao no log
            self.after(0, lambda: self.lbl_countdown.configure(text=msg))
            
        try:
            new_file_path = refinar_questoes_por_ia(self.json_path, api_key, cb, timer_cb)
            # Limpa timer ao finalizar
            self.after(0, lambda: self.lbl_countdown.configure(text=""))
            # Tenta abrir
            try: os.startfile(new_file_path)
            except: pass
        except Exception as e:
            err_msg = str(e)
            self.after(0, lambda msg=err_msg: messagebox.showerror("Erro na Interface de IA", msg))
        
        self.after(0, lambda: self.btn_run_ia.configure(state="normal"))

    # ==========================================
    # ABA: UNIFICADOR JSON
    # ==========================================
    def _build_unificador(self, parent):
        lbl = ctk.CTkLabel(parent, text="🔗 Unificador de Arquivos JSON", font=ctk.CTkFont(size=20, weight="bold"))
        lbl.pack(pady=(10, 2))
        
        lbl_sub = ctk.CTkLabel(parent, text="Adicione múltiplos arquivos .json (de diferentes PDFs) e unifique-os em um único arquivo.", text_color="gray70")
        lbl_sub.pack(pady=(0, 10))
        
        # --- Botões de Controle ---
        frame_btns = ctk.CTkFrame(parent, fg_color="transparent")
        frame_btns.pack(fill="x", padx=20, pady=5)
        
        self.btn_add_json = ctk.CTkButton(frame_btns, text="➕  Adicionar Arquivo(s) JSON", command=self._uni_add_files)
        self.btn_add_json.pack(side="left", padx=(0, 10))
        
        self.btn_clear_list = ctk.CTkButton(frame_btns, text="🗑️  Limpar Lista", fg_color="transparent", border_width=1, hover_color="#555", command=self._uni_clear)
        self.btn_clear_list.pack(side="left")
        
        self.lbl_total_uni = ctk.CTkLabel(frame_btns, text="", text_color="cyan")
        self.lbl_total_uni.pack(side="right", padx=10)
        
        # --- Lista de Arquivos ---
        lbl_list = ctk.CTkLabel(parent, text="Arquivos na fila:", anchor="w")
        lbl_list.pack(fill="x", padx=22, pady=(8, 2))
        
        self.uni_listbox = ctk.CTkScrollableFrame(parent, height=180)
        self.uni_listbox.pack(fill="x", padx=20, pady=5)
        self._uni_file_labels = []  # track label widgets
        
        # --- Opções ---
        frame_opts = ctk.CTkFrame(parent)
        frame_opts.pack(fill="x", padx=20, pady=10)
        
        self.var_dedup = ctk.BooleanVar(value=True)
        self.chk_dedup = ctk.CTkCheckBox(frame_opts, text="Remover duplicatas (por 'id' ou índice)", variable=self.var_dedup)
        self.chk_dedup.pack(side="left", padx=15, pady=10)
        
        self.var_resort = ctk.BooleanVar(value=True)
        self.chk_resort = ctk.CTkCheckBox(frame_opts, text="Re-numerar IDs sequencialmente no resultado", variable=self.var_resort)
        self.chk_resort.pack(side="left", padx=15, pady=10)
        
        # --- Botão de Unificar ---
        self.btn_unify = ctk.CTkButton(parent, text="⚡  UNIFICAR E SALVAR", fg_color="#d4670a", hover_color="#a84f07",
                                        height=45, font=ctk.CTkFont(size=14, weight="bold"), command=self._uni_run)
        self.btn_unify.pack(pady=10, padx=20, fill="x")
        
        # --- Log ---
        self.log_uni = ctk.CTkTextbox(parent, height=100, font=("Consolas", 11))
        self.log_uni.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        self.log_uni.configure(state="disabled")
        
        self._uni_files = []  # lista de paths

    def _uni_add_files(self):
        paths = filedialog.askopenfilenames(filetypes=[("JSON Files", "*.json")])
        for p in paths:
            if p not in self._uni_files:
                self._uni_files.append(p)
        self._uni_refresh_list()

    def _uni_clear(self):
        self._uni_files.clear()
        self._uni_refresh_list()

    def _uni_refresh_list(self):
        for w in self._uni_file_labels:
            w.destroy()
        self._uni_file_labels.clear()
        
        for i, path in enumerate(self._uni_files):
            row = ctk.CTkFrame(self.uni_listbox, fg_color="transparent")
            row.pack(fill="x", pady=2)
            
            lbl = ctk.CTkLabel(row, text=f"  {i+1}. {os.path.basename(path)}", anchor="w",
                                text_color="white", font=("Consolas", 11))
            lbl.pack(side="left", fill="x", expand=True)
            
            lbl_path = ctk.CTkLabel(row, text=path, anchor="w", text_color="gray55", font=("Consolas", 9))
            lbl_path.pack(side="left", fill="x", expand=True)
            
            def _make_remove(idx):
                def _remove():
                    self._uni_files.pop(idx)
                    self._uni_refresh_list()
                return _remove
            
            btn_rm = ctk.CTkButton(row, text="✕", width=28, height=22, fg_color="transparent",
                                    hover_color="#8b0000", command=_make_remove(i))
            btn_rm.pack(side="right", padx=5)
            self._uni_file_labels.append(row)
        
        total = len(self._uni_files)
        self.lbl_total_uni.configure(text=f"{total} arquivo(s) na fila" if total else "")

    def _uni_run(self):
        if not self._uni_files:
            messagebox.showwarning("Lista Vazia", "Adicione ao menos um arquivo JSON para unificar!")
            return
        
        save_path = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON Files", "*.json")],
            initialfile="questoes_unificadas.json",
            title="Salvar JSON Unificado como..."
        )
        if not save_path:
            return
        
        self.btn_unify.configure(state="disabled")
        threading.Thread(target=self._uni_worker, args=(save_path,), daemon=True).start()

    def _uni_worker(self, save_path):
        def log(msg):
            self.after(0, lambda m=msg: self._write_log(self.log_uni, m))
        
        log("--- INICIANDO UNIFICAÇÃO ---")
        merged = []
        seen_ids = set()
        dedup = self.var_dedup.get()
        resort = self.var_resort.get()
        
        for path in self._uni_files:
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                if not isinstance(data, list):
                    log(f"⚠️  {os.path.basename(path)} não é um array JSON — pulando.")
                    continue
                
                added = 0
                for item in data:
                    item_id = item.get("id", None)
                    if dedup and item_id is not None:
                        if item_id in seen_ids:
                            continue
                        seen_ids.add(item_id)
                    merged.append(item)
                    added += 1
                
                log(f"✅  {os.path.basename(path)}: {added} questões adicionadas.")
                
            except Exception as e:
                log(f"❌  Erro ao ler {os.path.basename(path)}: {e}")
        
        if not merged:
            log("Nenhuma questão foi carregada. Verifique os arquivos.")
            self.after(0, lambda: self.btn_unify.configure(state="normal"))
            return
        
        if resort:
            for idx, item in enumerate(merged, start=1):
                item["id"] = idx
            log(f"🔢  IDs re-numerados de 1 a {len(merged)}.")
        
        try:
            with open(save_path, "w", encoding="utf-8") as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)
            log(f"💾  Salvo em: {save_path}")
            log(f"📊  Total final: {len(merged)} questões unificadas.")
            try: os.startfile(save_path)
            except: pass
        except Exception as e:
            log(f"❌  Erro ao salvar: {e}")
        
        self.after(0, lambda: self.btn_unify.configure(state="normal"))

if __name__ == "__main__":
    app = App()
    app.mainloop()
