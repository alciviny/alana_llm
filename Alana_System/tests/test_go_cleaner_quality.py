import sys
from pathlib import Path
import logging
import json

src_path = Path(__file__).resolve().parent.parent / 'src'
sys.path.insert(0, str(src_path))

from alana_system.ingestion.cleaner import TextCleaner
from alana_system.ingestion.text_extractor import PageText

def test_quality():
    cleaner = TextCleaner()
    
    dirty_text = (
        "Este é um texto    com múltiplos espaços.\n"
        "Aqui temos uma hifen-\nização que deve ser unida.\n"
        "E aqui temos muitas quebras de linha excessivas.\n\n\n\n"
        "Fim do parágrafo."
    )
    
    pages = [PageText(page_number=1, text=dirty_text, char_count=len(dirty_text))]
    
    try:
        results = cleaner.clean_pages(pages)
        cleaned_text = results[0].text
        
        # Salva o resultado em um arquivo para inspeção (evita erros de terminal)
        with open("test_result.txt", "w", encoding="utf-8") as f:
            f.write(cleaned_text)
            
        # Verificações manuais no código
        success = True
        reasons = []
        
        if "    " in cleaned_text:
            success = False
            reasons.append("Espaços múltiplos não removidos.")
            
        if "hifenização" not in cleaned_text:
            success = False
            reasons.append(f"Hifenização não corrigida. Encontrado: {cleaned_text[20:50]}")
            
        if "\n\n\n" in cleaned_text:
            success = False
            reasons.append("Quebras excessivas não removidas.")
            
        if success:
            print("SUCCESS: Motor Go passou em todos os testes de qualidade.")
        else:
            print(f"FAILURE: {', '.join(reasons)}")
            sys.exit(1)
            
    except Exception as e:
        print(f"CRITICAL ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_quality()
