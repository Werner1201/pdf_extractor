# PDF Question Extractor & JSON Refiner

[Português](#português) | [English](#english)

---

## Português

Ferramenta GUI para extração de questões de arquivos PDF usando OCR (Tesseract), conversão para JSON e refinamento inteligente via Gemini API.

### 🚀 Funcionalidades
- **Fase 1 (OCR):** Converte PDF em imagens e extrai texto bruto usando Tesseract OCR.
- **Fase 2 (Parse):** Transforma o texto bruto em um arquivo JSON estruturado.
- **Fase 3 (Refinamento IA):** Utiliza a API do Gemini para corrigir erros de OCR, preencher explicações e classificar a dificuldade.
- **Unificador JSON:** Une múltiplos arquivos JSON em um único banco de questões.

> [!TIP]
> **Usuários que não desejam baixar o código:** Você pode baixar apenas o executável pronto na aba **Actions** (veja abaixo). Lembre-se que, mesmo usando o `.exe`, é obrigatório ter o **Tesseract** e o **Poppler** instalados no Windows para que o programa funcione.

### 🛠️ Pré-requisitos
Para rodar este projeto, você precisará de:
1. **Python 3.10+**
2. **Tesseract OCR:** [Download aqui](https://github.com/UB-Mannheim/tesseract/wiki)
3. **Poppler (para pdf2image):** [Download aqui](https://github.com/oschwartz10612/poppler-windows/releases)

### 📦 Instalação
1. Clone o repositório:
   ```bash
   git clone https://github.com/seu-usuario/pdf_extractor.git
   cd pdf_extractor
   ```
2. Instale as dependências:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure os caminhos do Tesseract e Poppler na interface do aplicativo ou no arquivo `settings.json`.

---

## English

A GUI tool for extracting questions from PDF files using OCR (Tesseract), converting them to JSON, and intelligently refining the data via the Gemini API.

### 🚀 Features
- **Phase 1 (OCR):** Converts PDF to images and extracts raw text using Tesseract OCR.
- **Phase 2 (Parse):** Transforms raw text into a structured JSON file.
- **Phase 3 (AI Refinement):** Uses the Gemini API to fix OCR typos, generate explanations, and classify difficulty.
- **JSON Unifier:** Merges multiple JSON files into a single question database.

> [!TIP]
> **Users who don't want to clone the code:** You can download the ready-to-use executable from the **Actions** tab (see below). Remember that even when using the `.exe`, it is mandatory to have **Tesseract** and **Poppler** installed on Windows for the program to work.

### 🛠️ Prerequisites
To run this project, you will need:
1. **Python 3.10+**
2. **Tesseract OCR:** [Download here](https://github.com/UB-Mannheim/tesseract/wiki)
3. **Poppler (for pdf2image):** [Download here](https://github.com/oschwartz10612/poppler-windows/releases)

### 📦 Installation
1. Clone the repository:
   ```bash
   git clone https://github.com/your-username/pdf_extractor.git
   cd pdf_extractor
   ```
2. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Configure the Tesseract and Poppler paths in the app interface or in the `settings.json` file.

---

## 🛠️ GitHub Actions Build
This repository includes a workflow to automatically generate a `.exe` file.
1. Go to the **Actions** tab in your repository.
2. Select the latest successful build.
3. Download the `pdf_extractor_exe` artifact.
