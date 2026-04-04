"""
Script principal.
Executa a Interface Gráfica (GUI) para o extrator OCR.
"""

from gui import App

def main():
    print("Iniciando a Interface Gráfica (GUI)...")
    app = App()
    app.mainloop()

if __name__ == "__main__":
    main()
