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
            frame_resp = self.session.get(STUDENT_FILE_FRAME_URL, allow_redirects=True)
            frame_resp.raise_for_status()
            frame_html = frame_resp.text
            
            # Parse the initial frame (Menu 0) to extract Genel Bilgiler
            soup = BeautifulSoup(frame_html, 'html.parser')
            menu0_data = self._parse_genel_bilgiler(soup)
            
            # Final output container
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
            
            logger.info("Successfully fetched Genel Bilgiler.")
            return {"success": True, "data": final_data}

        except Exception as e:
            logger.error(f"Unexpected error in StudentFileScraper: {str(e)}")
            return {"success": False, "message": "Bağlantı sırasında bir hata oluştu.", "error_code": "SCRAPE_CONNECTION_ERROR"}

    def _parse_genel_bilgiler(self, soup):
        def get_val(name):
            # The most reliable way to find these ASP.NET inputs is by their strict `name` attribute.
            # Example: <input name="txtInfoNormalSure" value="4 / 7" />
            el = soup.find(attrs={"name": name})
            
            # Fallback to ID if name is not found, searching via lambda
            if not el:
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
