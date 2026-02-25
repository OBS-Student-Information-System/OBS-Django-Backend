import logging
import re
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.config import STUDENT_FILE_CALLER_URL, STUDENT_FILE_FRAME_URL

logger = logging.getLogger(__name__)

class StudentFileScraper:
    def __init__(self):
        self.session = requests.Session()
        
    def fetch_student_file(self) -> dict:
        """
        Fetches the initial 'Genel Bilgiler' page and concurrently fetches the other 15 tabs
        using ThreadPoolExecutor to aggregate the entire student file.
        """
        try:
            # 1. Trigger the Caller URL to prepare backend session state
            caller_resp = self.session.get(STUDENT_FILE_CALLER_URL)
            caller_resp.raise_for_status()
            logger.debug("Student File Caller URL successful.")

            # 2. Get the initial Frame URL (which defaults to menu 0 - Genel Bilgiler)
            frame_resp = self.session.get(STUDENT_FILE_FRAME_URL)
            frame_resp.raise_for_status()
            frame_html = frame_resp.text
            
            # Parse the initial frame (Menu 0) to extract ASP.NET viewstate tokens
            soup = BeautifulSoup(frame_html, 'html.parser')
            
            viewstate_el = soup.find('input', {'id': '__VIEWSTATE'})
            viewstategenerator_el = soup.find('input', {'id': '__VIEWSTATEGENERATOR'})
            
            if not viewstate_el or not viewstategenerator_el:
                logger.error("Could not find __VIEWSTATE in Student File frame.")
                return {"success": False, "message": "Genel Bilgiler yüklenirken güvenlik tokeni bulunamadı.", "error_code": "MISSING_VIEWSTATE"}
                
            viewstate = viewstate_el.get('value', '')
            viewstategen = viewstategenerator_el.get('value', '')
            
            # Extract Menu 0 (Genel Bilgiler) Data
            menu0_data = self._parse_genel_bilgiler(soup)
            
            # Prepare for parallel fetching of menus 1 to 16
            final_data = {
                "genel_bilgiler": menu0_data,
                "egitim_bilgileri": [],
                "ceza_bilgileri": [],
                "hazirlik_durumu": [],
                "burs_ve_belgeler": [],
                "kulup_topluluk_etk": [],
                "diger_bilgiler_etk": [],
                "kayit_dondurma": [],
                "onur_yuksek_onur": [],
                "yonetim_kurulu_karar": [],
                "seminer_bilgileri": [],
                "yeterlilik_bilgileri": [],
                "proje_bilgileri": [],
                "tez_bilgileri": [],
                "arastirma_raporlari": [],
                "tez_izleme_sinavlari": [],
                "tez_savunma_sinavlari": []
            }
            
            menu_mapping = {
                1: "egitim_bilgileri",
                2: "ceza_bilgileri",
                3: "hazirlik_durumu",
                4: "burs_ve_belgeler",
                5: "kulup_topluluk_etk",
                6: "diger_bilgiler_etk",
                7: "kayit_dondurma",
                8: "onur_yuksek_onur",
                9: "yonetim_kurulu_karar",
                10: "seminer_bilgileri",
                11: "yeterlilik_bilgileri",
                12: "proje_bilgileri",
                13: "tez_bilgileri",
                14: "arastirma_raporlari",
                15: "tez_izleme_sinavlari",
                16: "tez_savunma_sinavlari"
            }
            
            # Common payload for UpdatePanel POST
            base_payload = {
                '__EVENTARGUMENT': '',
                '__VIEWSTATE': viewstate,
                '__VIEWSTATEGENERATOR': viewstategen,
                '__SCROLLPOSITIONX': '0',
                '__SCROLLPOSITIONY': '0',
                '__ASYNCPOST': 'true',
            }
            
            # Add existing form fields to prevent Validation exceptions
            form_fields = ["txtInfoNormalSure", "txtInfoCAP", "txtOgrenciSinif", "txtInfoYANDAL", 
                           "txtInfoOkuduguYil", "txtInfoCeza", "txtInfoYeniKanun", "txtInfoDondurma", 
                           "txtInfoDersKayit", "txtInfoHarc", "txtInfoFaaliyet", "txtInfoErasmus"]
                           
            for k in form_fields:
                field_el = soup.find('input', {'name': k})
                if field_el:
                    base_payload[k] = field_el.get('value', '')
                    
            def fetch_menu(index):
                payload = base_payload.copy()
                payload['ScriptManager1'] = f'UpdatePanel1|btnMenu{index}'
                payload['__EVENTTARGET'] = f'btnMenu{index}'
                
                headers = self.session.headers.copy()
                headers['X-Requested-With'] = 'XMLHttpRequest'
                headers['X-MicrosoftAjax'] = 'Delta=true'
                headers['Content-Type'] = 'application/x-www-form-urlencoded; charset=UTF-8'
                
                try:
                    resp = self.session.post(
                        STUDENT_FILE_FRAME_URL,
                        data=payload,
                        headers=headers,
                        timeout=10 # Reduced timeout to avoid hanging
                    )
                    resp.raise_for_status()
                    target_key = menu_mapping[index]
                    parsed_grid = self._parse_grid(resp.text)
                    return target_key, parsed_grid
                except Exception as e:
                    logger.error(f"Error fetching Student File Menu {index}: {str(e)}")
                    return menu_mapping[index], []

            # Execute fetching concurrently to save time
            with ThreadPoolExecutor(max_workers=5) as executor:
                future_to_index = {executor.submit(fetch_menu, i): i for i in range(1, 17)}
                for future in as_completed(future_to_index):
                    try:
                        key, data = future.result()
                        final_data[key] = data
                    except Exception as exc:
                        logger.error(f"Student File concurrent fetch generated an exception: {exc}")

            logger.info("Successfully fetched and aggregated all 16 Student File menus.")
            return {"success": True, "data": final_data}

        except Exception as e:
            logger.error(f"Unexpected error in StudentFileScraper: {str(e)}")
            return {"success": False, "message": "Bağlantı sırasında bir hata oluştu.", "error_code": "SCRAPE_CONNECTION_ERROR"}

    def _parse_genel_bilgiler(self, soup):
        def get_val(name):
            # Try exact match first. The ASP.NET elements might be generated dynamically
            # For example: ctl00_ContentPlaceHolder1_txtInfoNormalSure
            # But the student info page uses direct IDs. We will find tags that *contain* the name
            # string since ASP.Net prefixes them with ctl00_ContentPlaceHolder1_
            import re
            el = soup.find(id=re.compile(f".*{name}.*"))
            if not el:
                # Also try matching span or input directly 
                el = soup.find(lambda tag: tag.has_attr('id') and name in tag['id'])
            
            if el:
                if el.name in ['input', 'textarea']:
                    return el.get('value', '').strip()
                else:
                    return el.get_text(separator=" ", strip=True)
            return ''

        return {
            "program_normal_azami_sure": get_val('txtInfoNormalSure'),
            "cap_kaydi": get_val('txtInfoCAP'),
            "kayit_tarihi_ogrenci_sinif": get_val('txtOgrenciSinif'),
            "yan_dal_kaydi": get_val('txtInfoYANDAL'),
            "okudugu_yil": get_val('txtInfoOkuduguYil'),
            "ceza_durumu": get_val('txtInfoCeza'),
            "yeni_kanuna_gore": get_val('txtInfoYeniKanun'),
            "kayit_dondurma": get_val('txtInfoDondurma'),
            "aktif_donem_ders_kayit_sayisi": get_val('txtInfoDersKayit'),
            "katki_ogrenim_ucreti": get_val('txtInfoHarc'),
            "tez_seminer_sayisi": get_val('txtInfoFaaliyet'),
            "degisim_programi_ks": get_val('txtInfoErasmus')
        }

    def _parse_grid(self, html_content):
        soup = BeautifulSoup(html_content, 'html.parser')
        table = soup.find('table', {'class': 'grdStyle'})
        if not table:
            return []
            
        rows = table.find_all('tr')
        if not rows or len(rows) <= 1:
            return []
            
        header_row = rows[0]
        headers = []
        for th in header_row.find_all('th'):
            text = th.get_text(strip=True)
            normalized = text.lower().replace('ı', 'i').replace('ş', 's').replace('ç', 'c')\
                             .replace('ö', 'o').replace('ü', 'u').replace('ğ', 'g')
            normalized = re.sub(r'[^a-z0-9]', ' ', normalized)
            normalized = '_'.join(normalized.split())
            headers.append(normalized or f"col_{len(headers)}")
            
        data = []
        for row in rows[1:]: 
            cells = row.find_all('td')
            row_data = {}
            for i, cell in enumerate(cells):
                if i < len(headers):
                    val = cell.get_text(separator=" ", strip=True)
                    if not val or val == '\xa0':
                        val = ''
                    row_data[headers[i]] = val
            
            if any(row_data.values()) and not any("kayıt bulunamadı" in str(v).lower() for v in row_data.values()):
                data.append(row_data)
                
        return data
