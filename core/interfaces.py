"""
Service Interfaces (Abstract Base Classes).
Implementing Dependency Inversion Principle (DIP).
High-level modules should depend on these abstractions, not concrete implementations.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from core.types import (
    LoginResponse, InitLoginResponse, GradesResponse, TermsResponse,
    ScheduleResponse, CalendarResponse, TranscriptResponse, FoodResponse
)

class IService(ABC):
    """Base interface for all services."""
    
    @abstractmethod
    def update_session_cookies(self, cookies: Dict[str, str]) -> None:
        """Update session cookies."""
        pass

class IAuthService(IService):
    @abstractmethod
    def prepare_login(self) -> Dict[str, Any]: # Returning Dict for now to match legacy, but ideally InitLoginResponse
        pass

    @abstractmethod
    def login(self, username, password, captcha_code, view_state_data) -> Dict[str, Any]:
        pass

class IGradesService(IService):
    @abstractmethod
    def get_grades(self, term_id: Optional[str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def get_terms(self) -> Dict[str, Any]:
        pass

class IScheduleService(IService):
    @abstractmethod
    def get_schedule(self) -> Dict[str, Any]:
        pass

class ICalendarService(IService):
    @abstractmethod
    def get_calendar(self, cookies: Dict[str, str]) -> Dict[str, Any]:
        pass

class ITranscriptService(IService):
    @abstractmethod
    def get_transcript(self) -> Dict[str, Any]:
        pass

class IFoodService(ABC): # FoodService might not need session updates
    @abstractmethod
    def get_daily_menu(self, menu_url: str) -> Dict[str, Any]:
        pass

class IUserManualService(IService):
    @abstractmethod
    def get_user_manual(self, cookies: Dict[str, str]) -> Dict[str, Any]:
        pass

class IPersonalInfoService(IService):
    @abstractmethod
    def get_personal_info(self, cookies: Dict[str, str] = None) -> Dict[str, Any]:
        pass

    @abstractmethod
    def update_personal_info(self, data: Dict[str, Any], cookies: Dict[str, str] = None) -> Dict[str, Any]:
        pass

class IStudentFileService(IService):
    @abstractmethod
    def get_student_file(self, cookies: Dict[str, str] = None) -> Dict[str, Any]:
        pass

class IAdvisorInfoService(IService):
    @abstractmethod
    def get_advisor_info(self, cookies: Dict[str, str] = None) -> Dict[str, Any]:
        pass

