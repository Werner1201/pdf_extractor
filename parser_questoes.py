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
    """Remove espaços extras, linhas em branco e lixo de UI do FocusOnForce."""
    texto = texto.replace("\r", "\n")
    
    # Remove marcadores de paginação do OCR interno
    texto = re.sub(r"--- PAGINA \d+ ---", "", texto)
    
    # Lista de ruídos conhecidos do FocusOnForce/Navegador
    ruidos = [
        r"focusonforce\.com/.*",
        r"Todos os favoritos",
        r"Certifications Courses About Salesforce.*",
        r"A K2 Partnering Solutions Company.*",
        r"v Si Boe Ba.*",
        r"Agent force Zero to.*",
        r"Al Use Cases with S.*",
        r"focusonforce\.com",
        r"K2 Partnering Solutions",
        r"Choose \d+ answer", # will use as separator later, clean up from raw lines
    ]
    for r in ruidos:
        texto = re.sub(r"(?im)^.*" + r + r".*$", "", texto)

    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()


# =========================================================
# SEPARAR QUESTÕES
# =========================================================
def separar_questoes(texto):
    """
    Identifica o início de cada questão suportando múltiplos padrões.
    Lida com duplicatas de vídeo escolhendo o maior bloco por ID.
    """
    # Padrões de início de questão (PDF, Web 1. , Web 1) )
    patterns = [
        re.compile(r"(?im)^(?:Question\s+(\d+)\s+of\s+\d+).*?$"),
        re.compile(r"(?im)^(\d+)\.\s+[A-Z].*$"),
        re.compile(r"(?im)^(\d+)\)\s+[A-Z].*$")
    ]

    all_matches = []
    for p in patterns:
        all_matches.extend(list(p.finditer(texto)))
    
    # Ordena matches por posição no texto
    all_matches.sort(key=lambda x: x.start())

    if not all_matches:
        print("⚠️  Nenhuma questão numerada padrão encontrada!")
        return []

    temp_questoes = []
    for idx, match in enumerate(all_matches):
        inicio = match.start()
        fim = all_matches[idx + 1].start() if idx + 1 < len(all_matches) else len(texto)
        bloco = texto[inicio:fim].strip()
        numero = match.group(1)
        temp_questoes.append({
            "numero": int(numero),
            "bloco": bloco
        })

    # Deduplicação (comum em vídeos): mantém o maior bloco para cada número
    questoes_dict = {}
    for q in temp_questoes:
        num = q["numero"]
        if num not in questoes_dict or len(q["bloco"]) > len(questoes_dict[num]["bloco"]):
            questoes_dict[num] = q

    v_final = sorted(questoes_dict.values(), key=lambda x: x["numero"])
    print(f"📝 {len(v_final)} questões únicas encontradas no processamento avançado.")
    return v_final


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
    Encontra alternativas suportando formato A. B. C. ou sequencial livre.
    """
    pat_alternativa = re.compile(r"(?im)^(.{0,4}?)([A-E68¢€2])[\.\,\)]\s+")
    alt_starts = list(pat_alternativa.finditer(bloco))
    
    alternativas = {}
    resposta_correta = None

    if alt_starts:
        for i, m in enumerate(alt_starts):
            prefixo = m.group(1)
            letra_suja = m.group(2)
            letra_limpa = mepear_letra(letra_suja)
            inicio_texto = m.end()
            if "®" in prefixo or "@" in prefixo:
                resposta_correta = letra_limpa
            fim_texto = alt_starts[i + 1].start() if i + 1 < len(alt_starts) else len(bloco)
            texto_alt = bloco[inicio_texto:fim_texto].strip()
            texto_alt = re.sub(r"\s+", " ", texto_alt)
            if letra_limpa not in alternativas:
                alternativas[letra_limpa] = texto_alt
    else:
        # Formato livre (sem letras explícitas - comum em web OCR)
        # Tenta identificar por quebras de linha após frases de comando
        pivot = re.search(r"(?im)Choose\s+\d+\s+answer\.?", bloco)
        if pivot:
            lines = bloco[pivot.end():].split("\n")
            lines = [l.strip() for l in lines if l.strip()]
            
            for idx, line in enumerate(lines):
                if len(alternativas) >= 5 or idx > 10: break
                # Se for uma linha indicadora de correção
                if re.search(r"(?i)^[~+]*orrect", line) or re.search(r"(?i)^correct", line):
                    if alternativas:
                        last_letter = chr(64 + len(alternativas))
                        resposta_correta = last_letter
                    continue
                # Se for texto de explicação longo, para
                if len(line) > 200 and idx > 2: break
                
                letter = chr(65 + len(alternativas))
                alternativas[letter] = line

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
