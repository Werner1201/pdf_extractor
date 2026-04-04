# PDF Extractor OCR GUI - Walkthrough

A aplicação foi completamente refatorada para adicionar uma interface gráfica moderna que lida com o pesado processamento de OCR em background e provê um ótimo feedback visual para o usuário.

## O Que Foi Alterado

### 1. Interface Gráfica com CustomTkinter
Instalamos o pacote `customtkinter` e criamos o arquivo [gui.py](file:///c:/Users/Werner/Desktop/PESSOAL/TESSERACT/pdf_extractor/gui.py), que levanta uma janela onde o usuário pode:
- **Escolher o arquivo PDF**: Um botão "Procurar PDF" abre uma janela de diálogo normal do sistema de arquivos para escolha segura e fácil.
- **Configurar Poppler e Tesseract**: Criamos caixas de texto contendo o local de instalação que o sistema usará para o *Tesseract* e para o *Poppler*. Se for preciso consertar ou mudar as pastas depois, você pode alterá-las ali mesmo e clicar em "Salvar Configs".
- **Monitorar o Progresso**: Como o PDF alvo continha apenas imagens, o OCR vai demorar bastante por página. Agora existe uma barra de progresso e uma caixa de histórico ("Logs") onde é retornado exatamente o que está ocorrendo em tempo real.

### 2. OCR em Background (Threads)
No momento em que o usuário clica em "INICIAR EXTRAÇÃO OCR", o script chama a função `threading.Thread`. Ou seja: o processamento pesado e lento das imagens vai rodar separado da interface. Isso foi importante pois sem threads, tentar rodar o OCR faria a sua janela inteira ficar travada e com o aviso "(Não Respondendo)" do Windows. 

Em complemento a isso, o [ocr.py](file:///c:/Users/Werner/Desktop/PESSOAL/TESSERACT/pdf_extractor/ocr.py) foi adaptado para receber *Callbacks*. Logo, a cada página lida, ele notifica a janela principal para encher a barra de progresso.

### 3. Execução
O [main.py](file:///c:/Users/Werner/Desktop/PESSOAL/TESSERACT/pdf_extractor/main.py) foi diminuído ao mínimo necessário e agora ele tem a finalidade de ligar a aplicação gráfica principal.

## Como Executar e Validar

No seu terminal ou pasta `pdf_extractor`, basta chamar o `main.py` da mesma forma que antes com o seu Python ativado:

```bash
.\venv\Scripts\python.exe main.py
```
*(Ou dar dois cliques nele pelo Windows Explorer, dependendo da configuração da sua máquina e ambiente virtual).*

> [!TIP]
> **Dica Importante:**
> 1. Certifique-se de que os caminhos *Tesseract EXE* e *Poppler Bin Path* na parte superior da janela estejam apontando para a pasta **real** na sua máquina que contenha o `.exe` e a pasta `bin` respectivamente. Se os arquivos não existirem naquele local da formatação inicial `C:\Program Files\`, o programa dará erro, mas basta arrumar o local correto na tela e clicar em salvar.
> 2. Testar PDFs inteiros apenas com imagens pode levar muitos minutos. Olhe a caixa preta na parte inferior da tela; ela te dirá "Visualizando Página 1", "Página 2", de forma segura até terminar e ele deve exibir o JSON final sozinho ao completar!
