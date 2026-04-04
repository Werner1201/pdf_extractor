import json
import config
import config

PROMPT_MANUAL = """
Você atua como um assistente de estruturação de dados de certificação (Salesforce). Abaixo enviarei um array de objetos JSON contendo questões de múltipla escolha geradas por um OCR com pequenos typos e lacunas.
Sua tarefa é retornar APENAS UM NOVO JSON VÁLIDO contendo os itens enviados, sob as seguintes regras:
1. Corrija minúcias de OCR e erros ortográficos nas propriedades `question` e `options`.
2. Pense e preencha a propriedade `explanation` com uma justificativa de tamanho aceitável mas conciso do porquê o gabarito (correct_answer) é a resposta correta baseado no contexto da pergunta.
3. Preencha `topic` com o assunto principal abordado nas alternativas.
4. Preencha `difficulty` como "Easy", "Medium" ou "Hard".

Me retorne apenas o Array de JSON puro e válido. NENHUM texto introdutório.
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

        max_retries = 6
        sucesso = False
        ultimo_erro = ""
        
        for tentativa in range(max_retries):
            modelo_atual = MODELOS_DISPONIVEIS[indice_modelo]
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
                    break
                else:
                    ultimo_erro = "A IA não retornou uma lista JSON."
            except Exception as e_json:
                ultimo_erro = str(e_json).lower()
                
                if '429' in ultimo_erro or 'exhausted' in ultimo_erro or 'quota' in ultimo_erro:
                    if indice_modelo < len(MODELOS_DISPONIVEIS) - 1:
                        indice_modelo += 1
                        novo_modelo = MODELOS_DISPONIVEIS[indice_modelo]
                        progress_callback(f"⚠️ Cota do modelo esgotada! Trocando rota para: {novo_modelo}", i+1, total_lotes+1)
                        import time
                        time.sleep(2)  # Pausa antes da proxima chamada pro novo modelo
                        continue  # Tenta novamente caindo fora do sleep basico
                elif '404' in ultimo_erro or 'not found' in ultimo_erro:
                    # Se o modelo dinamico for incompativel c/ v1beta textual
                    if indice_modelo < len(MODELOS_DISPONIVEIS) - 1:
                        indice_modelo += 1
                        novo_modelo = MODELOS_DISPONIVEIS[indice_modelo]
                        progress_callback(f"⚠️ Modelo rejeitado pela API (404). Rotacionando para: {novo_modelo}", i+1, total_lotes+1)
                        continue
                elif '408 timeout' in ultimo_erro or 'timeout' in ultimo_erro:
                    # Se congelou feio, força pular pro proximo modelo tambem caso reste repeticoes!
                    if indice_modelo < len(MODELOS_DISPONIVEIS) - 1:
                        indice_modelo += 1
                        novo_modelo = MODELOS_DISPONIVEIS[indice_modelo]
                        progress_callback(f"⏳ Tempo Excedido! O modelo congelou. Trocando rota para: {novo_modelo}", i+1, total_lotes+1)
                        continue
                
                import time
                time.sleep(2) # Espera padrao antes de tentar mesmo json parse array novamente
                
        if not sucesso:
            raise Exception(f"Falha repetida na formatação do texto da IA após {max_retries} tentativas (Lote {i+1}).\nDetalhes:\n{ultimo_erro}")

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
