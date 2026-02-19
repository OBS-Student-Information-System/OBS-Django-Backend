"""
Type Definitions (DTOs) for OBS Backend.
Using TypedDict for stricter type checking without runtime overhead of Pydantic.
"""
from typing import TypedDict, List, Optional, Any, Dict, Union

# --- Generic Responses ---
class BaseResponse(TypedDict):
    success: bool
    message: str
    error_code: Optional[str]

class ErrorResponse(BaseResponse):
    pass # success=False

# --- Auth Module ---
class StudentInfo(TypedDict):
    name: str
    profile_photo: Optional[str] # Base64
    gpa: Optional[str]

class LoginSuccessData(TypedDict):
    cookies: Dict[str, str]
    student_name: str
    profile_photo: Optional[str]
    gpa: Optional[str]

class LoginResponse(BaseResponse):
    data: Optional[LoginSuccessData]

class InitLoginData(TypedDict):
    captcha_image: Optional[str] # Base64
    view_state_data: Dict[str, str]
    cookies: Dict[str, str]
    debug: Optional[str]

class InitLoginResponse(BaseResponse):
    data: Optional[InitLoginData]
    error: Optional[str] # Legacy support

# --- Grades Module ---
class GradeItem(TypedDict):
    course_code: str
    course_name: str
    term_id: str
    letter_grade: Optional[str]
    midterm: Optional[str]
    final: Optional[str]
    makeup: Optional[str]

class GradesData(TypedDict):
    grades: List[GradeItem]
    gpa: Optional[str]

class GradesResponse(BaseResponse):
    data: List[GradeItem]
    gpa: Optional[str]

class TermItem(TypedDict):
    term_id: str
    term_name: str

class TermsResponse(BaseResponse):
    data: List[TermItem]

# --- Schedule Module ---
class ScheduleItem(TypedDict):
    time: str
    code: str
    name: str
    location: str
    lecturer: str
    is_practice: bool

class ScheduleResponse(BaseResponse):
    data: Dict[str, List[ScheduleItem]] # Key: "1" (Monday) -> items

# --- Calendar Module ---
class CalendarItem(TypedDict):
    name: str
    start_date: str
    end_date: str

class CalendarResponse(BaseResponse):
    data: List[CalendarItem]

# --- Transcript Module ---
class TranscriptData(TypedDict):
    pdf_base64: str
    size_bytes: int
    fetched_at: str

class TranscriptResponse(BaseResponse):
    data: Optional[TranscriptData]

# --- Food Module ---
class FoodMenu(TypedDict):
    date: str
    mainDish: str
    sideDish: str
    soup: str
    dessert: str
    calorie: int

class FoodResponse(BaseResponse):
    data: Union[FoodMenu, Dict[str, str]] # Error dict or Menu
