import json
from bs4 import BeautifulSoup
import os

def test_parse():
    # Read the provided HTML
    path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'OBS-Docs', 'ozlukbilgileriframe.html'))
    with open(path, 'r', encoding='utf-8') as f:
        html = f.read()
    
    soup = BeautifulSoup(html, 'html.parser')
    def get_input_val(ele_id: str) -> str:
        element = soup.find('input', id=ele_id)
        return element.get('value', '').strip() if element else ""
        
    def get_select_text(ele_id: str) -> str:
        select = soup.find('select', id=ele_id)
        if select:
            selected = select.find('option', selected=True)
            if selected and selected.text.strip() and selected.text.strip().lower() != "seçiniz":
                return selected.text.strip()
        return ""
        
    data = {
        "contact": {
            "phone1": get_input_val("txtCep1"),
            "email1": get_input_val("txtEposta1"),
        },
        "address": {
            "family": {
                "city": get_select_text("cmbAileIl"),
                "phone": get_input_val("txtAileTelefon")
            }
        },
        "financial": {
            "iban": get_input_val("txtBankaIBAN"),
        }
    }
    print(json.dumps(data, indent=2))

if __name__ == '__main__':
    test_parse()
