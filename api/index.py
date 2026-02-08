from http.server import BaseHTTPRequestHandler
import json
from modules.auth.scraper import AuthScraper
from modules.grades.scraper import GradesScraper
from core.logger import setup_logger

logger = setup_logger("api.index")

class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))
            action = body.get('action')
            
            logger.info(f"Received request action: {action}")
            
            # Shared session for stateful operations (restored from cookies)
            auth_scraper = AuthScraper()
            
            if action == 'init_login':
                data = auth_scraper.fetch_login_page()
                if "error" in data:
                     self._send_response(500, {"status": "error", "message": data['error']})
                else:
                     self._send_response(200, {"status": "success", "data": data})

            elif action == 'login':
                username = body.get('username')
                password = body.get('password')
                captcha = body.get('captcha')
                view_state_data = body.get('view_state_data', {})
                cookies = body.get('cookies', {})
                
                # Restore session
                if cookies:
                    auth_scraper.session.cookies.update(cookies)
                
                result = auth_scraper.attempt_login(username, password, captcha, view_state_data)
                
                if result.get('success'):
                    self._send_response(200, {"status": "success", "data": result})
                else:
                    self._send_response(401, {
                        "status": "error", 
                        "message": result.get('message'), 
                        "error_code": result.get('error_code')
                    })
            
            elif action == 'get_grades':
                cookies = body.get('cookies', {})
                term_id = body.get('term_id')
                
                if not cookies:
                    logger.warning("get_grades called without cookies.")
                    self._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
                    return
                
                # Initialize grades scraper with restored session
                grades_scraper = GradesScraper()
                grades_scraper.session.cookies.update(cookies)
                
                result = grades_scraper.fetch_grades(term_id)
                self._send_json_response(result)
            
            elif action == 'get_available_terms':
                cookies = body.get('cookies', {})
                
                if not cookies:
                    logger.warning("get_available_terms called without cookies.")
                    self._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
                    return
                
                grades_scraper = GradesScraper()
                grades_scraper.session.cookies.update(cookies)
                
                result = grades_scraper.get_available_terms()
                self._send_json_response(result)
            
            else:
                logger.warning(f"Unknown action: {action}")
                self._send_response(400, {"status": "error", "message": f"Unknown action: {action}"})

        except Exception as e:
            logger.exception("Unhandled exception in do_POST")
            self._send_response(500, {"status": "error", "message": str(e)})

    def _send_response(self, code, data):
        self.send_response(code)
        self.send_header('Content-type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def _send_json_response(self, result):
        if result.get('success'):
            self._send_response(200, {"status": "success", "data": result.get('data', []), "message": result.get('message')})
        else:
            self._send_response(500, {"status": "error", "message": result.get('message'), "error_code": result.get('error_code')})
    
    def do_GET(self):
         self._send_response(200, {"status": "alive", "message": "OBS Backend is running. Use POST."})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
