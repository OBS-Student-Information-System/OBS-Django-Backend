import logging
import re
import requests
from bs4 import BeautifulSoup
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.tenant_config import get_config

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Menu target mapping: JSON response key → ASP.NET __EVENTTARGET button name
# Order matches the OBS sidebar menu (btnMenu0 = Genel Bilgiler, already parsed
# from the initial frame load so it is purposely excluded here).
# ---------------------------------------------------------------------------
MENU_TARGETS = {
    "egitim_bilgileri":    "btnMenu1",
    "ceza_bilgileri":      "btnMenu2",
    "hazirlik_durumu":     "btnMenu3",
    "burs_ve_belgeler":    "btnMenu4",
    "kulup_topluluk_etk":  "btnMenu5",
    "diger_bilgiler_etk":  "btnMenu6",
    "kayit_dondurma":      "btnMenu7",
    "onur_yuksek_onur":    "btnMenu8",
    "yonetim_kurulu_karar":"btnMenu9",
    "seminer_bilgileri":   "btnMenu10",
    "yeterlilik_bilgileri":"btnMenu11",
    "proje_bilgileri":     "btnMenu12",
    "tez_bilgileri":       "btnMenu13",
    "arastirma_raporlari": "btnMenu14",
    "tez_izleme_sinavlari":"btnMenu15",
    "tez_savunma_sinavlari":"btnMenu16",
}

# Maximum parallel workers – intentionally conservative to avoid flooding the
# OBS server from a shared VPS (4 concurrent POSTs is safe and still fast).
_MAX_WORKERS = 4
_cfg = None

def _get_cfg():
    global _cfg
    if _cfg is None:
        _cfg = get_config()
    return _cfg


class StudentFileScraper:
    def __init__(self):
        self.session = requests.Session()

    # -------------------------------------------------------------------
    # Public API
    # -------------------------------------------------------------------

    def fetch_student_file(self) -> dict:
        """
        Full fetch of all 17 student file tabs (Menu 0-16).

        Flow:
        1. Hit the caller URL to warm up the OBS server-side session.
        2. Fetch the frame page (Menu 0 – Genel Bilgiler), bypass any
           ASP.NET interstitial redirect in the process.
        3. Parse Menu 0 fields from the resulting HTML.
        4. Extract __VIEWSTATE & related tokens from the same HTML – these
           are required for every subsequent UpdatePanel POST.
        5. Fire all remaining 16 menus concurrently via ThreadPoolExecutor.
        6. Return a fully-populated data dict.
        """
        try:
            # Step 1: Warm-up caller page
            self.session.headers.update({
                'Referer':         _get_cfg().default_referer,
                'Sec-Fetch-Dest':  'document',
                'Sec-Fetch-Mode':  'navigate',
                'Sec-Fetch-Site':  'same-origin',
            })
            caller_resp = self.session.get(_get_cfg().student_file_caller_url, timeout=15)
            caller_resp.raise_for_status()
            logger.debug("Student File caller URL succeeded.")

            # Step 2: Fetch initial frame (Menu 0) with interstitial bypass
            self.session.headers.update({
                'Referer':        _get_cfg().student_file_caller_url,
                'Sec-Fetch-Dest': 'iframe',
                'Sec-Fetch-Mode': 'navigate',
                'Sec-Fetch-Site': 'same-origin',
            })
            frame_html = self._fetch_and_bypass_redirects(_get_cfg().student_file_frame_url)

            # Step 3: Parse Menu 0
            soup0 = BeautifulSoup(frame_html, 'html.parser')
            menu0_data = self._parse_genel_bilgiler(soup0)

            # Step 4: Extract ASP.NET state tokens for subsequent POST calls
            viewstate_payload = self._extract_viewstate(soup0)
            if not viewstate_payload.get('__VIEWSTATE'):
                logger.warning(
                    "No __VIEWSTATE found in student file frame. "
                    "Menu 1-16 responses may be empty."
                )

            # Step 5: Fetch all remaining menus concurrently
            menu_results = self._fetch_all_menus_parallel(viewstate_payload)

            # Step 6: Assemble final data dict
            final_data = {
                "genel_bilgiler": menu0_data,
                **menu_results,
            }

            logger.info(
                "Student File fetch complete. Non-empty menus: %s",
                [k for k, v in final_data.items() if v]
            )
            return {"status": "success", "data": final_data}

        except Exception as e:
            logger.error("Unexpected error in StudentFileScraper: %s", str(e), exc_info=True)
            return {
                "status": "error",
                "message": "Bağlantı sırasında bir hata oluştu.",
                "error_code": "SCRAPE_CONNECTION_ERROR",
            }

    # -------------------------------------------------------------------
    # Private: ASP.NET interstitial redirect bypass
    # -------------------------------------------------------------------

    def _fetch_and_bypass_redirects(self, url: str) -> str:
        """
        Fetches an OBS URL and automatically submits any HTML-based
        ASP.NET interstitial 'Yönlendirme Yapılıyor' (Redirecting) forms.
        Returns the final HTML text of the true destination page.
        """
        import urllib.parse
        resp = self.session.get(url, allow_redirects=True, timeout=15)
        resp.raise_for_status()
        html = resp.text

        # Guard against up to 3 chained HTML redirects
        for _ in range(3):
            if "redirect.aspx" in html and "Yönlendirme Yapılıyor" in html:
                logger.info(
                    "Detected ASP.NET interstitial redirect at %s – auto-submitting…",
                    resp.url,
                )
                soup = BeautifulSoup(html, 'html.parser')
                form = soup.find('form')
                if form:
                    action_url = urllib.parse.urljoin(
                        resp.url,
                        form.get('action', './redirect.aspx'),
                    )
                    payload = {
                        hidden.get('name'): hidden.get('value', '')
                        for hidden in form.find_all('input', type='hidden')
                    }
                    resp = self.session.post(
                        action_url, data=payload, allow_redirects=True, timeout=15
                    )
                    resp.raise_for_status()
                    html = resp.text
                else:
                    break
            else:
                break
        return html

    # -------------------------------------------------------------------
    # Private: ASP.NET hidden field extraction
    # -------------------------------------------------------------------

    @staticmethod
    def _extract_viewstate(soup: BeautifulSoup) -> dict:
        """
        Extracts all hidden form fields (__VIEWSTATE, __VIEWSTATEGENERATOR,
        __EVENTVALIDATION, etc.) required for subsequent UpdatePanel POSTs.
        """
        hidden_fields = {}
        for hidden in soup.find_all('input', type='hidden'):
            name = hidden.get('name', '')
            if name:
                hidden_fields[name] = hidden.get('value', '')
        return hidden_fields

    # -------------------------------------------------------------------
    # Private: Parallel menu fetch orchestrator
    # -------------------------------------------------------------------

    def _fetch_all_menus_parallel(self, viewstate_payload: dict) -> dict:
        """
        Fires POST requests to the student file frame for each menu target
        (Menu 1-16) using a ThreadPoolExecutor. Results are aggregated and
        empty / 'not found' rows are filtered by _parse_grid().
        """
        results = {key: [] for key in MENU_TARGETS}

        def fetch_single(menu_key: str, btn_target: str) -> tuple[str, list]:
            try:
                data = self._fetch_menu_tab(btn_target, viewstate_payload)
                return menu_key, data
            except Exception as exc:
                logger.warning(
                    "Failed to fetch menu %s (%s): %s",
                    menu_key, btn_target, exc,
                )
                return menu_key, []

        with ThreadPoolExecutor(max_workers=_MAX_WORKERS) as executor:
            futures = {
                executor.submit(fetch_single, key, btn): key
                for key, btn in MENU_TARGETS.items()
            }
            for future in as_completed(futures):
                menu_key, parsed = future.result()
                results[menu_key] = parsed

        return results

    # -------------------------------------------------------------------
    # Private: Single menu tab UpdatePanel POST
    # -------------------------------------------------------------------

    def _fetch_menu_tab(self, btn_target: str, viewstate_payload: dict) -> list:
        """
        Posts to the student file frame URL simulating a button click on
        the given ASP.NET UpdatePanel target (e.g. 'btnMenu1').
        Returns the parsed grid rows, or an empty list if none found.
        """
        post_data = {
            **viewstate_payload,
            '__EVENTTARGET':   btn_target,
            '__EVENTARGUMENT': '',
            # ScriptManager header – field name must match the control's
            # ClientID and the value format is "UpdatePanelID|ButtonID".
            # Using full ctl00$... paths is wrong; the page uses short IDs.
            'ScriptManager1': f'UpdatePanel1|{btn_target}',
            '__ASYNCPOST':   'true',
        }

        # UpdatePanel POST needs specific headers to be treated correctly
        headers = {
            'Referer':          _get_cfg().student_file_frame_url,
            'Sec-Fetch-Dest':   'empty',
            'Sec-Fetch-Mode':   'cors',
            'Sec-Fetch-Site':   'same-origin',
            'X-MicrosoftAjax':  'Delta=true',
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type':     'application/x-www-form-urlencoded; charset=UTF-8',
        }

        resp = self.session.post(
            _get_cfg().student_file_frame_url,
            data=post_data,
            headers=headers,
            timeout=20,
        )
        resp.raise_for_status()

        # ASP.NET UpdatePanel returns a special pipe-delimited delta format:
        #   length|type|id|content|...
        # We need to extract the HTML fragment embedded within it.
        html_fragment = self._extract_updatepanel_html(resp.text)
        return self._parse_grid(html_fragment)

    # -------------------------------------------------------------------
    # Private: ASP.NET UpdatePanel delta response parser
    # -------------------------------------------------------------------

    @staticmethod
    def _extract_updatepanel_html(delta_response: str) -> str:
        """
        Extracts the HTML content payload from an ASP.NET ScriptManager
        partial-page (delta) response.

        Delta format:
            <length>|<type>|<id>|<content>|...
        We look for 'updatePanel' type segments and return their content.
        If no delta segments found (server returned full HTML), the full
        response is returned as-is so _parse_grid can still attempt to work.
        """
        # Try to find update panel segments via the standard delta format
        pattern = r'\d+\|updatePanel\|[^|]+\|(.*?)(?=\d+\|(?:updatePanel|hiddenField|asyncPostBackControlIDs|formAction|pageTitle)|$)'
        matches = re.findall(pattern, delta_response, re.DOTALL)
        if matches:
            return '\n'.join(matches)

        # Fallback: return the raw response (may be full HTML on first load)
        return delta_response

    # -------------------------------------------------------------------
    # Private: Menu 0 - Genel Bilgiler parser
    # -------------------------------------------------------------------

    def _parse_genel_bilgiler(self, soup: BeautifulSoup) -> dict:
        """
        Extracts the read-only txtInfo* input values that represent the
        student's general academic status (Menu 0).
        """
        def get_val(name: str) -> str:
            # Primary: match by 'name' attribute (most reliable for ASP.NET)
            el = soup.find(attrs={"name": name})
            # Fallback: match by partial ID
            if not el:
                el = soup.find(
                    lambda tag: tag.has_attr('id') and name in tag['id']
                )
            if el:
                if el.name in ('input', 'textarea'):
                    return el.get('value', '').strip()
                return el.get_text(separator=" ", strip=True)
            return ''

        return {
            "program_normal_azami_sure":      get_val('txtInfoNormalSure'),
            "cap_kaydi":                      get_val('txtInfoCAP'),
            "kayit_tarihi_ogrenci_sinif":     get_val('txtOgrenciSinif'),
            "yan_dal_kaydi":                  get_val('txtInfoYANDAL'),
            "okudugu_yil":                    get_val('txtInfoOkuduguYil'),
            "ceza_durumu":                    get_val('txtInfoCeza'),
            "yeni_kanuna_gore":               get_val('txtInfoYeniKanun'),
            "kayit_dondurma":                 get_val('txtInfoDondurma'),
            "aktif_donem_ders_kayit_sayisi":  get_val('txtInfoDersKayit'),
            "katki_ogrenim_ucreti":           get_val('txtInfoHarc'),
            "tez_seminer_sayisi":             get_val('txtInfoFaaliyet'),
            "degisim_programi_ks":            get_val('txtInfoErasmus'),
        }

    # -------------------------------------------------------------------
    # Private: grdStyle table parser (reused by all Menu 1-16 responses)
    # -------------------------------------------------------------------

    def _parse_grid(self, html_content: str) -> list:
        """
        Parses an HTML fragment for a <table class='grdStyle'> and returns
        its rows as a list of dicts keyed by normalized column headers.

        Rows containing no data, non-breaking spaces only, or the Turkish
        phrase 'kayıt bulunamadı' ('no record found') are discarded.
        """
        soup = BeautifulSoup(html_content, 'html.parser')
        table = soup.find('table', {'class': 'grdStyle'})
        if not table:
            return []

        rows = table.find_all('tr')
        if not rows or len(rows) <= 1:
            return []

        # Build normalized header list from <th> cells
        headers = []
        for th in rows[0].find_all('th'):
            text = th.get_text(strip=True)
            normalized = (
                text.lower()
                    .replace('ı', 'i').replace('ş', 's').replace('ç', 'c')
                    .replace('ö', 'o').replace('ü', 'u').replace('ğ', 'g')
            )
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

            # Skip empty rows and 'no record' placeholder rows
            if not any(row_data.values()):
                continue
            if any(
                'kayit bulunamadi' in str(v).lower().replace('ı', 'i')
                or 'kayıt bulunamadı' in str(v).lower()
                for v in row_data.values()
            ):
                continue

            data.append(row_data)

        return data
