"""
User Manual Module.
Handles fetching and parsing the User Manual PDF.
"""
from .service import UserManualService
from .scraper import UserManualScraper

__all__ = ['UserManualService', 'UserManualScraper']
