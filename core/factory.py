"""
Service Factory (Dependency Injection Container).
Centralizes the creation of Service instances and their dependencies.
"""
from typing import Optional
from modules.auth.service import AuthService
from modules.grades.service import GradesService
from modules.schedule.service import ScheduleService
from modules.calendar.service import CalendarService
from modules.transcript.service import TranscriptService
from modules.food.service import FoodService
from modules.user_manual.service import UserManualService
from modules.personal_info.service import PersonalInfoService
from modules.student_file.service import StudentFileService
from modules.advisor_info.service import AdvisorInfoService
from modules.gpa_history.service import GpaHistoryService
from modules.department_schedule.service import DepartmentScheduleService
from modules.enrolled_courses.service import EnrolledCoursesService
from core.interfaces import (
    IAuthService,
    IGradesService,
    IScheduleService,
    ICalendarService,
    ITranscriptService,
    IFoodService,
    IUserManualService,
    IPersonalInfoService,
    IStudentFileService,
    IAdvisorInfoService,
    IGpaHistoryService,
    IDepartmentScheduleService,
    IEnrolledCoursesService,
)

class ServiceFactory:
    """
    Factory class to create service instances.
    This allows for easy swapping of implementations (e.g. for testing)
    and centralized dependency management.
    """

    @staticmethod
    def create_auth_service() -> IAuthService:
        return AuthService()

    @staticmethod
    def create_grades_service() -> IGradesService:
        return GradesService()

    @staticmethod
    def create_schedule_service() -> IScheduleService:
        return ScheduleService()

    @staticmethod
    def create_calendar_service() -> ICalendarService:
        return CalendarService()

    @staticmethod
    def create_transcript_service() -> ITranscriptService:
        return TranscriptService()

    @staticmethod
    def create_food_service() -> IFoodService:
        return FoodService()

    @staticmethod
    def create_user_manual_service() -> IUserManualService:
        return UserManualService()

    @staticmethod
    def create_personal_info_service() -> IPersonalInfoService:
        return PersonalInfoService()
        
    @staticmethod
    def create_student_file_service() -> IStudentFileService:
        return StudentFileService()

    @staticmethod
    def create_advisor_info_service() -> IAdvisorInfoService:
        return AdvisorInfoService()

    @staticmethod
    def create_gpa_history_service() -> IGpaHistoryService:
        return GpaHistoryService()

    @staticmethod
    def create_department_schedule_service() -> IDepartmentScheduleService:
        return DepartmentScheduleService()

    @staticmethod
    def create_enrolled_courses_service() -> IEnrolledCoursesService:
        return EnrolledCoursesService()
