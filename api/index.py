from http.server import BaseHTTPRequestHandler
import json
from modules.auth.service import AuthService
from modules.grades.service import GradesService
from modules.calendar.service import CalendarService
from modules.schedule.service import ScheduleService
from modules.transcript.service import TranscriptService
from modules.food.service import FoodService
from core.logger import setup_logger
from core.router import ActionDispatcher

logger = setup_logger("api.index")

# --- Handler Functions ---
# These functions decouple the Service call from the RequestHandler
# They adhere to a standard signature: (body, context)

def handle_init_login(body, context):
    auth_service = AuthService()
    data = auth_service.prepare_login()
    if "error" in data:
        context._send_response(500, {"status": "error", "message": data['error']})
    else:
        context._send_response(200, {"status": "success", "data": data})

def handle_login(body, context):
    auth_service = AuthService()
    auth_service.update_session_cookies(body.get('cookies', {}))
    
    result = auth_service.login(
        body.get('username'),
        body.get('password'),
        body.get('captcha'),
        body.get('view_state_data', {})
    )
    
    if result.get('success'):
        context._send_response(200, {"status": "success", "data": result})
    else:
        context._send_response(401, {
            "status": "error", 
            "message": result.get('message'), 
            "error_code": result.get('error_code')
        })

def handle_get_grades(body, context):
    cookies = body.get('cookies', {})
    if not cookies:
        context._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
        return

    grades_service = GradesService()
    grades_service.update_session_cookies(cookies)
    result = grades_service.get_grades(body.get('term_id'))
    context._send_json_response(result)

def handle_get_terms(body, context):
    cookies = body.get('cookies', {})
    if not cookies:
        context._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
        return

    grades_service = GradesService()
    grades_service.update_session_cookies(cookies)
    result = grades_service.get_terms()
    context._send_json_response(result)

def handle_get_calendar(body, context):
    calendar_service = CalendarService()
    calendar_data = calendar_service.get_calendar(cookies=body.get('cookies', {}))
    context._send_response(200, {"status": "success", "data": calendar_data})

def handle_get_schedule(body, context):
    cookies = body.get('cookies', {})
    if not cookies:
         context._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
         return

    schedule_service = ScheduleService()
    schedule_service.update_session_cookies(cookies)
    schedule_data = schedule_service.get_schedule()
    context._send_response(200, {"status": "success", "data": schedule_data})

def handle_get_transcript(body, context):
    cookies = body.get('cookies', {})
    if not cookies:
        context._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
        return
    
    transcript_service = TranscriptService()
    transcript_service.update_session_cookies(cookies)
    result = transcript_service.get_transcript()
    context._send_json_response(result)

def handle_food_menu(body, context):
    food_service = FoodService()
    # Service handles default URL logic internally
    result = food_service.get_daily_menu(body.get('menu_url'))
    context._send_json_response(result)


# --- Dispatcher Configuration ---
dispatcher = ActionDispatcher()
dispatcher.register('init_login', handle_init_login)
dispatcher.register('login', handle_login)
dispatcher.register('get_grades', handle_get_grades)
dispatcher.register('get_available_terms', handle_get_terms)
dispatcher.register('get_academic_calendar', handle_get_calendar)
dispatcher.register('get_schedule', handle_get_schedule)
dispatcher.register('get_transcript', handle_get_transcript)
dispatcher.register('food_menu', handle_food_menu)


class handler(BaseHTTPRequestHandler):
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)
            body = json.loads(post_data.decode('utf-8'))
            action = body.get('action')
            
            logger.info(f"Received request action: {action}")
            
            # Dispatch Request
            dispatcher.dispatch(action, body, self)

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
