from http.server import BaseHTTPRequestHandler
import json
from core.factory import ServiceFactory
from core.logger import setup_logger
from core.router import ActionDispatcher
from core.exceptions import SessionExpiredError

logger = setup_logger("api.index")

# --- Handler Functions ---
# These functions decouple the Service call from the RequestHandler
# They adhere to a standard signature: (body, context)

def handle_init_login(body, context):
    auth_service = ServiceFactory.create_auth_service()
    data = auth_service.prepare_login()
    if "error" in data:
        context._send_response(500, {"status": "error", "message": data['error']})
    else:
        context._send_response(200, {"status": "success", "data": data})

def handle_login(body, context):
    auth_service = ServiceFactory.create_auth_service()
    auth_service.update_session_cookies(body.get('cookies', {}))
    
    result = auth_service.login(
        body.get('username'),
        body.get('password'),
        body.get('captcha'),
        body.get('view_state_data', {})
    )
    
    if result.get('status') == 'success':
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

    grades_service = ServiceFactory.create_grades_service()
    grades_service.update_session_cookies(cookies)
    result = grades_service.get_grades(body.get('term_id'))
    context._send_json_response(result)

def handle_get_terms(body, context):
    cookies = body.get('cookies', {})
    if not cookies:
        context._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
        return

    grades_service = ServiceFactory.create_grades_service()
    grades_service.update_session_cookies(cookies)
    result = grades_service.get_terms()
    context._send_json_response(result)

def handle_get_calendar(body, context):
    try:
        calendar_service = ServiceFactory.create_calendar_service()
        calendar_data = calendar_service.get_calendar(cookies=body.get('cookies', {}))
        context._send_response(200, {"status": "success", "data": calendar_data})
    except SessionExpiredError:
        context._send_response(401, {"status": "error", "message": "Oturum süresi doldu", "error_code": "SESSION_EXPIRED"})

def handle_get_schedule(body, context):
    cookies = body.get('cookies', {})
    if not cookies:
         context._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
         return

    try:
        schedule_service = ServiceFactory.create_schedule_service()
        schedule_service.update_session_cookies(cookies)
        schedule_data = schedule_service.get_schedule()
        context._send_response(200, {"status": "success", "data": schedule_data})
    except SessionExpiredError:
        context._send_response(401, {"status": "error", "message": "Oturum süresi doldu", "error_code": "SESSION_EXPIRED"})

def handle_get_transcript(body, context):
    cookies = body.get('cookies', {})
    if not cookies:
        context._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
        return
    
    transcript_service = ServiceFactory.create_transcript_service()
    transcript_service.update_session_cookies(cookies)
    result = transcript_service.get_transcript()
    context._send_json_response(result)

def handle_food_menu(body, context):
    food_service = ServiceFactory.create_food_service()
    # Service handles default URL logic internally
    result = food_service.get_daily_menu(body.get('menu_url'))
    context._send_json_response(result)

def handle_get_user_manual(body, context):
    cookies = body.get('cookies', {})
    if not cookies:
        context._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
        return
    
    user_manual_service = ServiceFactory.create_user_manual_service()
    result = user_manual_service.get_user_manual(cookies=cookies)
    context._send_json_response(result)

def handle_get_personal_info(body, context):
    cookies = body.get('cookies', {})
    if not cookies:
        context._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
        return
        
    personal_info_service = ServiceFactory.create_personal_info_service()
    result = personal_info_service.get_personal_info(cookies=cookies)
    context._send_json_response(result)

def handle_update_personal_info(body, context):
    cookies = body.get('cookies', {})
    data = body.get('data', {})
    if not cookies:
        context._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
        return
        
    personal_info_service = ServiceFactory.create_personal_info_service()
    result = personal_info_service.update_personal_info(data=data, cookies=cookies)
    context._send_json_response(result)

def handle_get_student_file(body, context):
    cookies = body.get('cookies', {})
    if not cookies:
        context._send_response(401, {"status": "error", "message": "Oturum yok", "error_code": "NO_SESSION"})
        return
        
    student_file_service = ServiceFactory.create_student_file_service()
    result = student_file_service.get_student_file(cookies=cookies)
    context._send_json_response(result)


def handle_get_advisor_info(body, context):
    cookies = body.get('cookies', {})
    if not cookies:
        context._send_response(
            401,
            {
                "status": "error",
                "message": "Oturum yok",
                "error_code": "NO_SESSION",
            },
        )
        return

    advisor_service = ServiceFactory.create_advisor_info_service()
    result = advisor_service.get_advisor_info(cookies=cookies)
    context._send_json_response(result)


def handle_get_advisor_schedule(body, context):
    cookies = body.get('cookies', {})
    if not cookies:
        context._send_response(
            401,
            {
                "status": "error",
                "message": "Oturum yok",
                "error_code": "NO_SESSION",
            },
        )
        return

    advisor_service = ServiceFactory.create_advisor_info_service()
    result = advisor_service.get_advisor_schedule(cookies=cookies)
    context._send_json_response(result)


def handle_get_gpa_history(body, context):
    cookies = body.get('cookies', {})
    if not cookies:
        context._send_response(
            401,
            {
                "status": "error",
                "message": "Oturum yok",
                "error_code": "NO_SESSION",
            },
        )
        return

    gpa_history_service = ServiceFactory.create_gpa_history_service()
    result = gpa_history_service.get_gpa_history(cookies=cookies)
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
dispatcher.register('get_user_manual', handle_get_user_manual)
dispatcher.register('get_personal_info', handle_get_personal_info)
dispatcher.register('update_personal_info', handle_update_personal_info)
dispatcher.register('get_student_file', handle_get_student_file)
dispatcher.register('get_advisor_info', handle_get_advisor_info)
dispatcher.register('get_advisor_schedule', handle_get_advisor_schedule)
dispatcher.register('get_gpa_history', handle_get_gpa_history)


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
        if result.get('status') == 'success':
            response_data = {"status": "success", "data": result.get('data', []), "message": result.get('message')}
            if result.get('gpa') is not None:
                response_data['gpa'] = result['gpa']
            self._send_response(200, response_data)
        else:
            error_code = result.get('error_code')
            status_code = 401 if error_code == "SESSION_EXPIRED" else 500
            self._send_response(status_code, {"status": "error", "message": result.get('message'), "error_code": error_code})
    
    def do_GET(self):
         self._send_response(200, {"status": "alive", "message": "OBS Backend is running. Use POST."})

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
