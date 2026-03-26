"""
Tenant Configuration Loader.

Reads and validates the tenant config JSON, providing a strongly-typed,
immutable configuration object to all backend modules.

Usage:
    from core.tenant_config import get_config

    config = get_config()
    print(config.login_url)      # https://obs.ozal.edu.tr/oibs/std/login.aspx
    print(config.scraper.timeout) # 10
"""
import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from core.exceptions import ConfigNotFoundError, ConfigValidationError
from core.logger import setup_logger

logger = setup_logger("core.tenant_config")

_DEFAULT_CONFIG_PATH = "config/tenant.json"

_REQUIRED_SCRAPER_SELECTORS = frozenset({
    "captcha_img",
    "login_form",
    "login_error_label",
    "grades_table",
    "term_dropdown",
    "login_btn",
    "username_field",
    "password_field",
    "captcha_field",
    "student_name",
    "gpa_label",
})

_REQUIRED_SCRAPER_ENDPOINTS = frozenset({
    "login",
    "dashboard",
    "grades",
    "schedule",
    "transcript",
    "calendar",
    "personal_info_caller",
    "personal_info_frame",
    "student_file_caller",
    "student_file_frame",
    "user_manual",
    "advisor_info_caller",
    "advisor_info_frame",
    "gpa_history_caller",
    "gpa_history_frame",
    "department_schedule_caller",
    "department_schedule_frame",
    "enrolled_courses_caller",
    "enrolled_courses_frame",
    "offered_courses_caller",
    "offered_courses_frame",
    "tuition_fees_caller",
    "tuition_fees_frame",
    "course_registration_summary_caller",
    "course_registration_summary_frame",
    "interactive_transcript_caller",
    "interactive_transcript_frame",
})


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class InstitutionConfig:
    name_full: str
    name_short: str
    obs_base_url: str


@dataclass(frozen=True)
class ScraperConfig:
    obs_domain: str
    obs_root_path: str
    selectors: Dict[str, str]
    endpoints: Dict[str, str]
    timeout_seconds: int
    error_strings: Dict[str, List[str]]

    @property
    def base_url(self) -> str:
        """Full student portal root, e.g. https://obs.ozal.edu.tr/oibs/std"""
        return f"{self.obs_domain}{self.obs_root_path}"

    @property
    def default_referer(self) -> str:
        return f"{self.base_url}/index.aspx?curOp=0"

    def url_for(self, endpoint_key: str) -> str:
        """Build absolute URL for a given endpoint key."""
        ep = self.endpoints.get(endpoint_key)
        if ep is None:
            raise KeyError(f"Unknown endpoint key: {endpoint_key}")
        return f"{self.base_url}/{ep}"


@dataclass(frozen=True)
class ModuleConfig:
    enabled: bool
    settings: Dict[str, Any]


@dataclass(frozen=True)
class TenantConfig:
    tenant_id: str
    version: str
    institution: InstitutionConfig
    scraper: ScraperConfig
    modules: Dict[str, ModuleConfig]
    features: Dict[str, bool]

    # -- Derived URL shortcuts (replace old core/config.py constants) ------

    @property
    def obs_domain(self) -> str:
        return self.scraper.obs_domain

    @property
    def obs_root(self) -> str:
        return self.scraper.base_url

    @property
    def base_url(self) -> str:
        return f"{self.scraper.base_url}/"

    @property
    def login_url(self) -> str:
        return self.scraper.url_for("login")

    @property
    def dashboard_url(self) -> str:
        return self.scraper.url_for("dashboard")

    @property
    def grades_url(self) -> str:
        return self.scraper.url_for("grades")

    @property
    def schedule_url(self) -> str:
        return self.scraper.url_for("schedule")

    @property
    def transcript_url(self) -> str:
        return self.scraper.url_for("transcript")

    @property
    def calendar_url(self) -> str:
        return self.scraper.url_for("calendar")

    @property
    def personal_info_caller_url(self) -> str:
        return self.scraper.url_for("personal_info_caller")

    @property
    def personal_info_frame_url(self) -> str:
        return self.scraper.url_for("personal_info_frame")

    @property
    def student_file_caller_url(self) -> str:
        return self.scraper.url_for("student_file_caller")

    @property
    def student_file_frame_url(self) -> str:
        return self.scraper.url_for("student_file_frame")

    @property
    def user_manual_url(self) -> str:
        return self.scraper.url_for("user_manual")

    @property
    def food_menu_url(self) -> Optional[str]:
        food = self.modules.get("food")
        if food and food.enabled:
            return food.settings.get("menu_url")
        return None

    @property
    def default_referer(self) -> str:
        return self.scraper.default_referer

    @property
    def default_headers(self) -> Dict[str, str]:
        return {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,application/xml;"
                "q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
            ),
            "Accept-Language": "tr-TR,tr;q=0.9,en-US;q=0.8,en;q=0.7",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
        }

    @property
    def selectors(self) -> Dict[str, str]:
        """Shortcut: config.selectors['CAPTCHA_IMG'] — uppercase keys for backward compat."""
        return {k.upper(): v for k, v in self.scraper.selectors.items()}

    @property
    def error_strings(self) -> Dict[str, List[str]]:
        """Shortcut with uppercase keys for backward compat."""
        return {k.upper(): v for k, v in self.scraper.error_strings.items()}


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _require(data: dict, key: str, parent: str = "root") -> Any:
    """Raise ConfigValidationError if key is missing or empty."""
    val = data.get(key)
    if val is None:
        raise ConfigValidationError(f"Missing required field: {parent}.{key}")
    if isinstance(val, str) and not val.strip():
        raise ConfigValidationError(f"Empty value for required field: {parent}.{key}")
    return val


def _validate_url(url: str, field_name: str) -> None:
    if not url.startswith(("http://", "https://")):
        raise ConfigValidationError(
            f"Invalid URL for {field_name}: '{url}' — must start with http:// or https://"
        )


def _parse_scraper(raw: dict) -> ScraperConfig:
    obs_domain = _require(raw, "obs_domain", "scraper")
    obs_root_path = _require(raw, "obs_root_path", "scraper")
    _validate_url(obs_domain, "scraper.obs_domain")

    selectors = _require(raw, "selectors", "scraper")
    if not isinstance(selectors, dict):
        raise ConfigValidationError("scraper.selectors must be an object")

    missing_sel = _REQUIRED_SCRAPER_SELECTORS - set(selectors.keys())
    if missing_sel:
        raise ConfigValidationError(
            f"Missing required selectors: {', '.join(sorted(missing_sel))}"
        )

    endpoints = _require(raw, "endpoints", "scraper")
    if not isinstance(endpoints, dict):
        raise ConfigValidationError("scraper.endpoints must be an object")

    missing_ep = _REQUIRED_SCRAPER_ENDPOINTS - set(endpoints.keys())
    if missing_ep:
        raise ConfigValidationError(
            f"Missing required endpoints: {', '.join(sorted(missing_ep))}"
        )

    timeout = raw.get("timeout_seconds", 10)
    if not isinstance(timeout, int) or timeout < 1:
        raise ConfigValidationError("scraper.timeout_seconds must be a positive integer")

    error_strings = raw.get("error_strings", {})

    return ScraperConfig(
        obs_domain=obs_domain.rstrip("/"),
        obs_root_path=obs_root_path if obs_root_path.startswith("/") else f"/{obs_root_path}",
        selectors=selectors,
        endpoints=endpoints,
        timeout_seconds=timeout,
        error_strings=error_strings,
    )


def _parse_modules(raw: dict) -> Dict[str, ModuleConfig]:
    result = {}
    for key, val in raw.items():
        if not isinstance(val, dict):
            continue
        enabled = val.get("enabled", False)
        settings = {k: v for k, v in val.items() if k != "enabled"}
        result[key] = ModuleConfig(enabled=enabled, settings=settings)
    return result


def _parse_config(data: dict) -> TenantConfig:
    tenant_id = _require(data, "tenant_id")
    version = data.get("version", "1.0")

    inst_raw = _require(data, "institution")
    institution = InstitutionConfig(
        name_full=_require(inst_raw, "name_full", "institution"),
        name_short=_require(inst_raw, "name_short", "institution"),
        obs_base_url=_require(inst_raw, "obs_base_url", "institution"),
    )
    _validate_url(institution.obs_base_url, "institution.obs_base_url")

    scraper_raw = _require(data, "scraper")
    scraper = _parse_scraper(scraper_raw)

    modules_raw = data.get("modules", {})
    modules = _parse_modules(modules_raw)

    features = data.get("features", {})
    if not isinstance(features, dict):
        features = {}

    return TenantConfig(
        tenant_id=tenant_id,
        version=version,
        institution=institution,
        scraper=scraper,
        modules=modules,
        features=features,
    )


# ---------------------------------------------------------------------------
# Singleton loader
# ---------------------------------------------------------------------------

_config: Optional[TenantConfig] = None


def load_config(config_path: Optional[str] = None) -> TenantConfig:
    """
    Load and validate tenant config from a JSON file.

    Args:
        config_path: Path to the JSON config file. Falls back to
                     TENANT_CONFIG_PATH env var, then 'config/tenant.json'.

    Returns:
        Validated TenantConfig instance.

    Raises:
        ConfigNotFoundError: If the config file does not exist.
        ConfigValidationError: If validation fails.
    """
    global _config

    if config_path is None:
        config_path = os.environ.get("TENANT_CONFIG_PATH", _DEFAULT_CONFIG_PATH)

    if not os.path.exists(config_path):
        raise ConfigNotFoundError(f"Config file not found: {config_path}")

    logger.info("Loading tenant config from: %s", config_path)

    with open(config_path, "r", encoding="utf-8") as f:
        try:
            raw = json.load(f)
        except json.JSONDecodeError as e:
            raise ConfigValidationError(f"Invalid JSON in config file: {e}") from e

    _config = _parse_config(raw)
    logger.info(
        "Config loaded — tenant=%s, domain=%s",
        _config.tenant_id,
        _config.scraper.obs_domain,
    )
    return _config


def get_config() -> TenantConfig:
    """
    Return the cached TenantConfig, loading on first access.

    Thread-safety note: Vercel Python runs single-threaded per request,
    so no locking is needed. The singleton survives across warm requests.
    """
    if _config is None:
        return load_config()
    return _config


def reset_config() -> None:
    """Clear the cached config (useful for testing)."""
    global _config
    _config = None
