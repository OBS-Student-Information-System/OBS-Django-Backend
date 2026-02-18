from http.server import BaseHTTPRequestHandler
import json
from modules.auth.service import AuthService
from modules.grades.service import GradesService
from modules.calendar.service import CalendarService
from modules.schedule.service import ScheduleService
from modules.transcript.service import TranscriptService
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
            
            # Initialize Services
            auth_service = AuthService()
            
            if action == 'init_login':
                data = auth_service.prepare_login()
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
                
                # Update session via service
                auth_service.update_session_cookies(cookies)
                
                result = auth_service.login(username, password, captcha, view_state_data)
                
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
                
                grades_service = GradesService()
                grades_service.update_session_cookies(cookies)
                
                result = grades_service.get_grades(term_id)
                self._send_json_response(result)
            
            elif action == 'get_available_terms':
                cookies = body.get('cookies', {})
                
                if not cookies:
                    logger.warning("get_available_terms called without cookies.")
                    self._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
                    return
                
                grades_service = GradesService()
                grades_service.update_session_cookies(cookies)
                
                result = grades_service.get_terms()
                self._send_json_response(result)

            elif action == 'get_academic_calendar':
                # Calendar page requires auth cookies
                cookies = body.get('cookies', {})
                
                calendar_service = CalendarService()
                calendar_data = calendar_service.get_calendar(cookies=cookies)
                
                self._send_response(200, {"status": "success", "data": calendar_data})

            elif action == 'get_schedule':
                cookies = body.get('cookies', {})
                if not cookies:
                     self._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
                     return

                schedule_service = ScheduleService()
                schedule_service.update_session_cookies(cookies)
                schedule_data = schedule_service.get_schedule()
                
                self._send_response(200, {"status": "success", "data": schedule_data})
            
            elif action == 'get_transcript':
                cookies = body.get('cookies', {})
                if not cookies:
                    self._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
                    return
                
                transcript_service = TranscriptService()
                transcript_service.update_session_cookies(cookies)
                result = transcript_service.get_transcript()
                
                self._send_json_response(result)

            elif action == 'food_menu':
                # Public endpoint, no cookies needed
                menu_url = body.get('menu_url')
                
                # Dynamic import to avoid circular dependencies if any
                from modules.food.service import FoodService
                food_service = FoodService()
                
                result = food_service.get_daily_menu(menu_url)
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
            response_data = {"status": "success", "data": result.get('data', []), "message": result.get('message')}
            # Pass through extra keys (e.g. gpa) that service layer may provide
            if result.get('gpa') is not None:
                response_data['gpa'] = result['gpa']
            self._send_response(200, response_data)
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
