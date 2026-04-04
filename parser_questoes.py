"""
Módulo responsável por:
1. Limpar o texto bruto do OCR
2. Separar em blocos de questões
3. Extrair pergunta, alternativas e resposta correta (baseado no PDF específico)
"""

import re

# =========================================================
# LIMPEZA E CORREÇÕES CLÁSSICAS DE OCR
# =========================================================
def limpar_texto(texto):
    """Remove espaços extras e linhas em branco, além de correções OCR comuns."""
    texto = texto.replace("\r", "\n")
    texto = re.sub(r"[ \t]+", " ", texto) # remove multi-espaços
    texto = re.sub(r"\n{3,}", "\n\n", texto) # limita linhas em branco
    return texto.strip()


# =========================================================
# SEPARAR QUESTÕES
# =========================================================
def separar_questoes(texto):
    """
    Identifica o início de cada questão de acordo com o padrão do PDF.
    Padrão: Question X of \d+
    """
    pattern = re.compile(r"(?im)^(?:Question\s+(\d+)\s+of\s+\d+).*?$")

    matches = list(pattern.finditer(texto))
    if not matches:
        # Fallback caso a palavra Question esteja errada
        pattern = re.compile(r"(?im)^(?:\w{6,9}\s+(\d+)\s+of\s+\d+).*?$")
        matches = list(pattern.finditer(texto))
        if not matches:
            print("⚠️  Nenhuma questão numerada padrão encontrada!")
            return []

    questoes = []
    for idx, match in enumerate(matches):
        inicio = match.start()
        fim = matches[idx + 1].start() if idx + 1 < len(matches) else len(texto)

        bloco = texto[inicio:fim].strip()
        numero = match.group(1)

        questoes.append({
            "numero": int(numero),
            "bloco": bloco
        })

    print(f"📝 {len(questoes)} questões encontradas no bloco base.")
    return questoes


# =========================================================
# MAPEAMENTO DE ERROS DE OCR NAS ALTERNATIVAS
# =========================================================
def mepear_letra(ocr_char):
    ocr_char = ocr_char.upper()
    if ocr_char in ['A']: return 'A'
    if ocr_char in ['B', '6', '8']: return 'B'
    if ocr_char in ['C', '¢', '€', '2']: return 'C'
    if ocr_char in ['D']: return 'D'
    if ocr_char in ['E']: return 'E'
    return ocr_char


# =========================================================
# EXTRAIR ALTERNATIVAS E RESPOSTA DA PRÓPRIA LETRA
# =========================================================
def extrair_alternativas_e_resposta(bloco):
    """
    Encontra alternativas garantindo flexibilidade pra erros e
    identifica a resposta correta baseado no prefixo (@ ou ®).
    """
    # Procura o inicio de linhas como "O A. ", "® 6. ", "@ ¢, "
    # Grupo 1: Prefixo (onde pode ter o ® ou @) - até 5 chars
    # Grupo 2: A Letra suja (A, B, 6, C, ¢, etc)
    pat_alternativa = re.compile(r"(?im)^(.{0,5}?)([A-E68¢€2])[\.\,\)]\s+")
    
    alt_starts = list(pat_alternativa.finditer(bloco))
    alternativas = {}
    resposta_correta = None

    for i, m in enumerate(alt_starts):
        prefixo = m.group(1)
        letra_suja = m.group(2)
        letra_limpa = mepear_letra(letra_suja)
        
        inicio_texto = m.end()

        # Verifica se o prefixo contém marcador de resposta certa do PDF
        if "®" in prefixo or "@" in prefixo:
            resposta_correta = letra_limpa

        # O texto vai até a próxima alternativa, ou fim do bloco
        if i + 1 < len(alt_starts):
            fim_texto = alt_starts[i + 1].start()
        else:
            fim_texto = len(bloco)

        texto_alt = bloco[inicio_texto:fim_texto].strip()
        texto_alt = re.sub(r"\s+", " ", texto_alt)
        
        # Pode ocorrer do OCR duplicar uma mesma letra se falhar feio
        if letra_limpa not in alternativas:
            alternativas[letra_limpa] = texto_alt

    return alternativas, resposta_correta


# =========================================================
# EXTRAIR PERGUNTA
# =========================================================
def extrair_pergunta(bloco):
    """A pergunta é tudo antes da primeira alternativa."""
    first_alt = re.search(r"(?im)^.{0,5}?[A-E68¢€2][\.\,\)]\s+", bloco)

    if first_alt:
        pergunta = bloco[:first_alt.start()].strip()
    else:
        pergunta = bloco.strip()

    # Remove o header "Question X of Y" ou lixo do topo
    pergunta = re.sub(r"(?im)^\w{6,9}\s+\d+\s+of\s+\d+.*?[\n\r]", "", pergunta)
    # Remove "| Choose 1 option. |"
    pergunta = re.sub(r"(?im)^.*Choose\s+\d+\s+option.*$", "", pergunta)
    
    pergunta = re.sub(r"\s+", " ", pergunta).strip()

    return pergunta


# =========================================================
# PROCESSAR CORE
# =========================================================
def processar_questao(item):
    numero = item["numero"]
    bloco = item["bloco"]

    alternativas, resposta_letra = extrair_alternativas_e_resposta(bloco)
    pergunta = extrair_pergunta(bloco)
    
    # Formata o array de options exigido ("A. texto da alternativa")
    options_list = []
    for letra in sorted(alternativas.keys()):
        options_list.append(f"{letra}. {alternativas[letra]}")

    return {
        "id": int(numero),
        "question": pergunta,
        "options": options_list,
        "correct_answer": resposta_letra if resposta_letra else "",
        "explanation": "",
        "topic": "",
        "difficulty": ""
    }

def processar_todas(texto):
    texto_limpo = limpar_texto(texto)
    blocos = separar_questoes(texto_limpo)

    questoes = [processar_questao(q) for q in blocos]
    return questoes
