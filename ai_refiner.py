import json
import config

PROMPT_MANUAL = """
Você é um Especialista em Certificações Salesforce e Arquiteto de Dados.
Sua missão é REESTRUTURAR, LIMPAR e REFINAR um array de objetos JSON que veio de um OCR de vídeo (scrolling).
O texto está "sujo", com repetições e informações deslocadas entre os campos devido ao movimento da tela.

### REGRAS DE REFINAMENTO OBRIGATÓRIAS:
1. **Extração de Dados Ocultos**:
   - Muitas vezes o campo `question` contém as alternativas e até a resposta. Identifique-as!
   - Se encontrar alternativas (A, B, C...) dentro da `question`, mova-as para o array `options`.
   - Limpe o campo `question` para conter apenas o enunciado da pergunta.

2. **Identificação do Gabarito (`correct_answer`)**:
   - O OCR captura marcadores de resposta como "~Orrect", "Correct", "Incorrect", "®", "@".
   - Use esses marcadores para definir a letra correta (A, B, C, D ou E) no campo `correct_answer`.
   - Se o texto disser "Incorrect" para uma opção, use lógica para achar a correta.

3. **Remoção de Duplicidades (Efeito Scroll)**:
   - Remova parágrafos ou frases que se repetem dentro do mesmo campo (artefato comum do scroll de vídeo).
   - Una fragmentos de frases que foram quebrados entre páginas.

4. **Enriquecimento Técnico**:
   - `explanation`: Escreva uma justificativa técnica concisa e correta sobre por que aquela alternativa é a certa (baseado no contexto Salesforce).
   - `topic`: Identifique o tópico da certificação (Ex: Prompt Engineering, AI Models, Trust Layer).
   - `difficulty`: Defina como "Easy", "Medium" ou "Hard".
   - `options`: Formate cada item como "A. Texto", "B. Texto", etc.

5. **Saída**:
   - Retorne APENAS o Array de JSON puro e válido. NENHUM texto introdutório ou explicativo fora do JSON.
   - Mantenha os IDs originais.
"""

def refinar_questoes_por_ia(path_json_origem, api_key, progress_callback, countdown_callback=None):
    """
    Lê o JSON original, configura o Gemini e solicita refinamento inteligente
    para arrumar o JSON inteiro. Retorna o json refinado como texto e salva.
    """
    if not api_key:
        raise Exception("API Key do Gemini está vazia! Adicione no painel superior.")
        
    try:
        with open(path_json_origem, "r", encoding="utf-8") as f:
            texto_sujo = f.read()
            dados = json.loads(texto_sujo)
    except Exception as e:
        raise Exception(f"Não foi possível ler o arquivo {path_json_origem}.\nErro: {e}")

    from google import genai
    from google.genai import types
    import os
    
    client = genai.Client(api_key=api_key)
    
    # 1. Tenta carregar progresso anterior, se houver
    resultados_finais = []
    if os.path.exists(config.OUTPUT_JSON_REFINED):
        try:
            with open(config.OUTPUT_JSON_REFINED, "r", encoding="utf-8") as f:
                resultados_finais = json.load(f)
        except Exception:
            resultados_finais = []
            
    # 2. Descobre os IDs que já foram processados
    ids_processados = {item.get("id") for item in resultados_finais if "id" in item}
    
    # 3. Filtra apenas as questões que AINDA NÃO foram processadas
    lote_pendente = [item for item in dados if item.get("id") not in ids_processados]
    
    if not lote_pendente:
         progress_callback("Todas as questões já estavam refinadas no arquivo final! Concluído.", 1, 1)
         return config.OUTPUT_JSON_REFINED
         
    tamanho_lote = 5
    total_lotes = (len(lote_pendente) + tamanho_lote - 1) // tamanho_lote
         
    # Usa a lista do usuario salva no escudo!
    MODELOS_DISPONIVEIS = config.PREFERRED_MODELS
            
    # Garante que tenha pelo menos a base se tiver vazio (Fallback absurdo)
    if not MODELOS_DISPONIVEIS:
        MODELOS_DISPONIVEIS = ['gemini-2.5-flash', 'gemini-3-flash']
        
    indice_modelo = 0
    
    for i in range(total_lotes):
        inicio = i * tamanho_lote
        fim = inicio + tamanho_lote
        lote = lote_pendente[inicio:fim]
        
        progress_callback(f"Processando lote {i+1}/{total_lotes} à IA...", i+1, total_lotes+1)
        full_prompt = PROMPT_MANUAL + "\n\n### ARQUIVO JSON DO LOTE:\n" + json.dumps(lote, ensure_ascii=False)

        max_retries = 3 # Reduzido por modelo, já que vamos rotacionar
        sucesso = False
        ultimo_erro = ""
        
        while indice_modelo < len(MODELOS_DISPONIVEIS):
            modelo_atual = MODELOS_DISPONIVEIS[indice_modelo]
            lote_completado_neste_modelo = False
            
            for tentativa in range(max_retries):
                try:
                    import concurrent.futures
                    
                    # Executa a chamada real dentro de uma thread separada acompanhada de Timeout!
                    def _do_gen():
                        return client.models.generate_content(
                            model=modelo_atual,
                            contents=full_prompt,
                            config=types.GenerateContentConfig(
                                response_mime_type="application/json",
                                temperature=0.2,
                                top_p=0.95,
                                top_k=64,
                                max_output_tokens=8192
                            ),
                        )
                    
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        fut = executor.submit(_do_gen)
                        try:
                             # Limite arbitrário forte de 60s para prever se a Google congelou
                             response = fut.result(timeout=60)
                        except concurrent.futures.TimeoutError:
                             raise Exception("408 Timeout: O servidor da Google travou ou demorou mais de 60 segundos!")
                    
                    lote_refinado = json.loads(response.text)
                    if isinstance(lote_refinado, list):
                        resultados_finais.extend(lote_refinado)
                        
                        with open(config.OUTPUT_JSON_REFINED, "w", encoding="utf-8") as file_save:
                            json.dump(resultados_finais, file_save, ensure_ascii=False, indent=2)
                            
                        sucesso = True
                        lote_completado_neste_modelo = True
                        break
                    else:
                        ultimo_erro = "A IA não retornou uma lista JSON."
                except Exception as e_json:
                    ultimo_erro = str(e_json).lower()
                    
                    # Se for erro de cota ou timeout, ja tentamos pular de modelo se houver proximo
                    is_quota = '429' in ultimo_erro or 'exhausted' in ultimo_erro or 'quota' in ultimo_erro
                    is_timeout = '408' in ultimo_erro or 'timeout' in ultimo_erro
                    is_not_found = '404' in ultimo_erro or 'not found' in ultimo_erro
                    
                    if (is_quota or is_timeout or is_not_found) and (indice_modelo < len(MODELOS_DISPONIVEIS) - 1):
                        progress_callback(f"⚠️ Erro no modelo {modelo_atual}. Rotacionando...", i+1, total_lotes+1)
                        break # Sai do loop de tentativas deste modelo para ir pro proximo no while
                    
                    import time
                    time.sleep(2) # Espera padrao antes de tentar novamente no mesmo modelo
            
            if lote_completado_neste_modelo:
                break # Sai do while de modelos e vai pro proximo Lote
            else:
                # Se terminou as tentativas do modelo atual e nao sucesso, tenta o proximo modelo
                indice_modelo += 1
                if indice_modelo < len(MODELOS_DISPONIVEIS):
                    progress_callback(f"🔄 Tentativas esgotadas no modelo anterior. Próxima IA: {MODELOS_DISPONIVEIS[indice_modelo]}", i+1, total_lotes+1)
                else:
                    # Fim da linha
                    raise Exception(f"Falha total após esgotar todos os modelos ({len(MODELOS_DISPONIVEIS)}). Última falha: {ultimo_erro}")

        # TEMPORIZADOR ANTI-LIMIT (Limites Free Tier do Gemini 2.5 Flash: 15 RPM ou 5 RPM dependendo do país)
        # Vamos rodar no maximo um request a cada ~14 a 15 segundos para dar folga.
        if i < total_lotes - 1:
            tempo_espera = 15
            for sec in range(tempo_espera, 0, -1):
                if countdown_callback:
                    countdown_callback(f"Aguardando limite da API: {sec}s...")
                import time
                time.sleep(1)
            if countdown_callback:
                countdown_callback("")

    progress_callback("Geração processada. Arquivo atualizado aos poucos com sucesso!", total_lotes+1, total_lotes+1)
    if countdown_callback:
        countdown_callback("FINALIZADO!")
    return config.OUTPUT_JSON_REFINED
