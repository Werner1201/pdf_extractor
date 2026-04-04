"""
Módulo responsável por:
1. Converter PDF em imagens
2. Pré-processar cada imagem (melhorar qualidade)
3. Rodar OCR com Tesseract
4. Retornar texto bruto
"""

import cv2
import numpy as np
import pytesseract
from pdf2image import convert_from_path

import config


def preprocessar_imagem(pil_image):
    """
    Converte a imagem PIL para escala de cinza,
    aplica blur e binarização para melhorar o OCR.
    """
    # PIL → numpy array
    img = np.array(pil_image)

    # Converter para escala de cinza
    gray = cv2.cvtColor(img, cv2.COLOR_RGB2GRAY)

    # Reduzir ruído
    blur = cv2.GaussianBlur(gray, (3, 3), 0)

    # Binarização (Otsu) — separa texto do fundo
    _, binary = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

    return binary


def extrair_texto_do_pdf(pdf_path=None, progress_callback=None):
    """
    Converte cada página do PDF em imagem,
    pré-processa e roda OCR.
    Retorna o texto completo com marcadores de página.
    """
    pdf_path = pdf_path or config.PDF_PATH
    
    # Atualiza o tesseract_cmd a partir do config antes de rodar
    if config.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD

    if progress_callback:
        progress_callback("Convertendo PDF em imagens (isso pode demorar e usar memoria)...", 0, 0)
    else:
        print(f"📄 Convertendo PDF em imagens (DPI={config.DPI})...")
        
    try:
        paginas = convert_from_path(
            pdf_path,
            dpi=config.DPI,
            poppler_path=config.POPPLER_PATH
        )
    except Exception as e:
        if progress_callback:
            progress_callback(f"ERRO AO CONVERTER PDF (VERIFIQUE O POPPLER): {e}", 0, 0)
        raise e

    texto_completo = []
    total = len(paginas)

    for i, pagina in enumerate(paginas, start=1):
        if progress_callback:
            progress_callback(f"🔍 OCR página {i} de {total}...", i, total)
        else:
            print(f"   🔍 OCR página {i}/{total}...")

        # Pré-processar a imagem pode demorar mais mas melhorará qualidade
        # img_processada = preprocessar_imagem(pagina)  # opcional, estava sem uso direto no script original
        img_processada = pagina

        try:
            texto = pytesseract.image_to_string(
                img_processada,
                lang=config.TESSERACT_LANG,
                config="--oem 3 --psm 6"
            )
        except Exception as e:
            if progress_callback:
                progress_callback(f"ERRO DE TESSERACT: {e}", i, total)
            raise e

        texto_completo.append(f"\n--- PAGINA {i} ---\n{texto}")

    resultado = "\n".join(texto_completo)
    
    if progress_callback:
        progress_callback(f"✅ OCR concluído! {total} páginas processadas.", total, total)
    else:
        print(f"✅ OCR concluído! {total} páginas processadas.")

    return resultado
