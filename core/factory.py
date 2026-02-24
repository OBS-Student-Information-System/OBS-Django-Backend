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
from core.interfaces import (
    IAuthService, IGradesService, IScheduleService, 
    ICalendarService, ITranscriptService, IFoodService,
    IUserManualService
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
