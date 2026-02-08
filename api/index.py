from http.server import BaseHTTPRequestHandler
import json
import requests
from bs4 import BeautifulSoup
import base64

class OBSClient:
    # URL SABİTLERİ (Senin okulunun adresleri)
    BASE_URL = "https://obs.ozal.edu.tr/oibs/std/"
    LOGIN_URL = "https://obs.ozal.edu.tr/oibs/std/login.aspx"
    GRADES_URL = "https://obs.ozal.edu.tr/oibs/std/not_listesi_op.aspx"

    def __init__(self):
        self.session = requests.Session()
        # Headerları güçlendirelim (Chrome gibi davransın)
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Referer": self.LOGIN_URL,
            "Origin": "https://obs.ozal.edu.tr",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1"
        })

    def get_cookies(self):
        return requests.utils.dict_from_cookiejar(self.session.cookies)

    def set_cookies(self, cookie_dict):
        if cookie_dict:
            requests.utils.add_dict_to_cookiejar(self.session.cookies, cookie_dict)

    def _get_hidden_inputs(self, soup):
        data = {}
        for inp in soup.find_all("input", type="hidden"):
            if inp.get("name"):
                data[inp.get("name")] = inp.get("value", "")
        return data

    def fetch_login_page(self):
        try:
            # 1. Sayfaya Git
            r = self.session.get(self.LOGIN_URL)
            
            # DEBUG: Eğer sayfa açılmazsa kodu burada kesip hatayı dönelim
            if r.status_code != 200:
                return {"error": f"Siteye erişilemedi. Status: {r.status_code}"}

            soup = BeautifulSoup(r.content, "html.parser")
            title = soup.title.string if soup.title else "Baslik Yok"

            # 2. Captcha Resmini Bul
            captcha_b64 = None
            img_tag = soup.find(id="imgCaptchaImg")
            
            debug_info = f"Site: {title}" # Sayfa başlığını loglayalım

            if img_tag:
                src = img_tag.get("src")
                # URL düzeltme
                if not src.startswith("http"):
                    url = self.BASE_URL + src.lstrip("/") if src.startswith("/") else self.BASE_URL + src
                else:
                    url = src
                
                # Resmi İndir
                r_img = self.session.get(url)
                if r_img.status_code == 200:
                    captcha_b64 = base64.b64encode(r_img.content).decode('utf-8')
                else:
                    debug_info += f" | Resim indirilemedi: {r_img.status_code}"
            else:
                debug_info += " | Captcha elementi (imgCaptchaImg) bulunamadi!"

            # 3. Hidden Inputları al
            hidden_inputs = self._get_hidden_inputs(soup)

            return {
                "captcha_image": captcha_b64,
                "view_state_data": hidden_inputs,
                "cookies": self.get_cookies(),
                "debug": debug_info # Flutter logunda bunu göreceğiz
            }

        except Exception as e:
            return {"error": f"Backend Hatasi: {str(e)}"}

    def attempt_login(self, username, password, captcha_code, view_state_data):
        """
        Attempts login to OBS using scraped viewstate and captcha.
        
        Returns:
            dict: Standard envelope with success/error
        """
        try:
            # Prepare POST data matching ASP.NET form structure
            # CRITICAL: Field names MUST match actual OBS form (from terminal project)
            login_data = {
                **view_state_data,  # Include all hidden inputs (__VIEWSTATE, etc.)
                'txtParamT01': username,      # OBS uses txtParamT01 for username
                'txtParamT02': password,      # OBS uses txtParamT02 for password
                'txtParamT1': password,       # Also required (duplicate)
                'txtSecCode': captcha_code,   # OBS uses txtSecCode for captcha
                '__EVENTTARGET': 'btnLogin',  # Trigger button via event target
                '__EVENTARGUMENT': '',
                'txt_scrWidth': '1920',       # Screen resolution (optional)
                'txt_scrHeight': '1080'
            }
            
            # Remove btnLogin if exists in viewstate (conflicts with __EVENTTARGET)
            if 'btnLogin' in login_data:
                del login_data['btnLogin']
            
            # POST to login page (allow_redirects=False to detect redirect)
            response = self.session.post(self.LOGIN_URL, data=login_data, allow_redirects=False)
            
            # Case 1: Successful login (redirect to dashboard)
            if response.status_code == 302:
                redirect_url = response.headers.get('Location', '')
                # Successful login redirects away from login.aspx
                if 'login.aspx' not in redirect_url.lower():
                    return {
                        "success": True,
                        "message": "Giriş başarılı",
                        "cookies": self.get_cookies()
                    }
            
            # Case 2: Login failed (stayed on same page with error)
            soup = BeautifulSoup(response.content, 'html.parser')
            error_elem = soup.find(id='lblSonuclar')
            
            if error_elem and error_elem.text.strip():
                error_text = error_elem.text.strip()
                
                # Determine error type
                if 'Güvenlik kodu hatalı' in error_text or 'captcha' in error_text.lower():
                    error_code = 'INVALID_CAPTCHA'
                elif 'Kullanıcı adı veya şifresi geçersiz' in error_text or 'geçersiz' in error_text.lower():
                    error_code = 'INVALID_CREDENTIALS'
                else:
                    error_code = 'LOGIN_FAILED'
                
                return {
                    "success": False,
                    "message": error_text,
                    "error_code": error_code
                }
            
            # Case 3: Unknown failure (no error message, no redirect)
            return {
                "success": False,
                "message": "Giriş başarısız. Lütfen tekrar deneyin.",
                "error_code": "UNKNOWN_ERROR"
            }
            
        except Exception as e:
            return {
                "success": False,
                "message": f"Sunucu hatası: {str(e)}",
                "error_code": "SERVER_ERROR"
            }

# --- HANDLER ---
class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))
            action = body.get('action')
            
            client = OBSClient()

            if action == 'init_login':
                data = client.fetch_login_page()
                # Debug bilgisini status'a da ekleyelim ki görelim
                if "error" in data:
                     self._send_response(500, {"status": "error", "message": data['error']})
                else:
                     self._send_response(200, {"status": "success", "data": data})

            elif action == 'login':
                # Extract request data
                username = body.get('username')
                password = body.get('password')
                captcha = body.get('captcha')
                view_state_data = body.get('view_state_data', {})
                cookies = body.get('cookies', {})
                
                # Restore cookies from init_login (relay mechanism)
                client.set_cookies(cookies)
                
                # Attempt login
                result = client.attempt_login(username, password, captcha, view_state_data)
                
                if result.get('success'):
                    self._send_response(200, {"status": "success", "data": result})
                else:
                    # Return 401 for auth failures, but still valid JSON
                    self._send_response(401, {
                        "status": "error", 
                        "message": result.get('message'), 
                        "error_code": result.get('error_code')
                    })
            
            else:
                self._send_response(400, {"status": "error", "message": f"Unknown action: {action}"})

        except Exception as e:
            self._send_response(500, {"status": "error", "message": str(e)})

    def _send_response(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))
    
    def do_GET(self):
         self._send_response(200, {"status": "alive", "message": "POST atin."})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()