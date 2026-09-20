"""
Configuration loader for Freelance Hunter.
"""
import json
import os
from typing import Any

import yaml


class Config:
    """Configuration manager."""
    
    def __init__(self, config_path: str | None = None):
        self.config_path = config_path or self._find_config()
        self._config: dict[str, Any] = {}
        self._profile: dict[str, Any] = {}
        self.load()
    
    def _find_config(self) -> str:
        """Find configuration file."""
        possible_paths = [
            "config/settings.yaml",
            "config/settings.yml",
            "../config/settings.yaml",
            "../../config/settings.yaml",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        # Return default path
        return "config/settings.yaml"
    
    def load(self):
        """Load configuration from file."""
        # Load main config
        if os.path.exists(self.config_path):
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
        else:
            self._config = self._default_config()
        
        # Load profile
        profile_path = os.path.join(os.path.dirname(self.config_path), "profile.json")
        if os.path.exists(profile_path):
            with open(profile_path, 'r', encoding='utf-8') as f:
                self._profile = json.load(f)
        else:
            self._profile = self._default_profile()
        
        # Apply environment variable overrides
        self._apply_env_overrides()
    
    def _apply_env_overrides(self):
        """Apply environment variable overrides."""
        # Database
        if os.getenv("DATABASE_URL"):
            self._config.setdefault("database", {})["url"] = os.getenv("DATABASE_URL")
        
        # API Keys
        if os.getenv("AISA_API_KEY"):
            self._config.setdefault("api_keys", {})["aisa"] = os.getenv("AISA_API_KEY")
        
        # Dashboard
        if os.getenv("DASHBOARD_PORT"):
            self._config.setdefault("dashboard", {})["port"] = int(os.getenv("DASHBOARD_PORT"))
        
        if os.getenv("DASHBOARD_HOST"):
            self._config.setdefault("dashboard", {})["host"] = os.getenv("DASHBOARD_HOST")
        
        # Scheduler
        if os.getenv("SCHEDULER_INTERVAL"):
            self._config.setdefault("scheduler", {})["default_interval_hours"] = int(os.getenv("SCHEDULER_INTERVAL"))
        
        # Logging
        if os.getenv("LOG_LEVEL"):
            self._config.setdefault("logging", {})["level"] = os.getenv("LOG_LEVEL")
    
    def _default_config(self) -> dict[str, Any]:
        """Default configuration."""
        return {
            "database": {
                "type": "sqlite",
                "sqlite_path": "data/freelance_hunter.db"
            },
            "search": {
                "time_windows": {
                    "priority_1_hours": 24,
                    "priority_2_hours": 72,
                    "priority_3_hours": 168,
                    "priority_4_hours": 720
                },
                "max_pages_per_platform": 5,
                "max_results_per_query": 50,
                "rate_limit_delay": 2,
                "timeout": 30,
                "search_engines": ["google", "bing", "duckduckgo"],
                "platforms": [
                    "upwork", "freelancer", "peopleperhour", "guru",
                    "workana", "contra", "fiverr", "khamsat", "mostaql", "linkedin"
                ]
            },
            "agents": {
                "platform_discovery": {"enabled": True, "max_new_platforms_per_run": 5},
                "specialized_agents": {
                    "data_entry": {"enabled": True, "keywords": []},
                    "document_pdf_word": {"enabled": True, "keywords": []},
                    "powerpoint_presentation": {"enabled": True, "keywords": []},
                    "excel_spreadsheet": {"enabled": True, "keywords": []},
                    "general_freelance": {"enabled": True, "keywords": []}
                }
            },
            "verification": {
                "enabled": True,
                "check_url_accessible": True,
                "check_listing_exists": True,
                "check_job_not_expired": True,
                "check_not_freelancer_profile": True,
                "check_not_spam": True,
                "require_minimum_fields": 5
            },
            "deduplication": {
                "enabled": True,
                "similarity_threshold": 0.85,
                "check_fields": ["url", "title", "client_name", "description", "posted_date", "platform"]
            },
            "matching": {
                "enabled": True,
                "levels": ["EXCELLENT_MATCH", "GOOD_MATCH", "POSSIBLE_MATCH", "WEAK_MATCH", "NOT_RELEVANT"],
                "skill_match_weight": 0.30,
                "recency_weight": 0.20,
                "beginner_accessibility_weight": 0.15,
                "budget_weight": 0.10,
                "client_quality_weight": 0.10,
                "competition_weight": 0.05,
                "clarity_weight": 0.05,
                "ease_weight": 0.05
            },
            "scoring": {
                "max_score": 100,
                "components": {
                    "skill_match": 30,
                    "recency": 20,
                    "beginner_accessibility": 15,
                    "budget_value": 10,
                    "client_quality": 10,
                    "competition": 5,
                    "clarity": 5,
                    "ease": 5
                }
            },
            "risk_detection": {
                "enabled": True,
                "levels": ["LOW", "MEDIUM", "HIGH", "CRITICAL"],
                "red_flags": [
                    "unrealistic promises", "payment before start", "crypto only payment",
                    "request passwords", "request account access", "external links suspicious",
                    "telegram/whatsapp migration", "impossible deadlines", "extremely low pay",
                    "prohibited work", "platform violation"
                ]
            },
            "proposal": {
                "enabled": True,
                "templates": {"short": True, "normal": True, "ultra_short": True},
                "guidelines": [
                    "Address client's specific task",
                    "Be natural and conversational",
                    "Don't exaggerate experience",
                    "Don't invent portfolio items",
                    "Mention only relevant skills",
                    "Be concise",
                    "Focus on client's problem",
                    "State what you can deliver",
                    "Include 1-2 relevant questions"
                ]
            },
            "scheduler": {
                "enabled": True,
                "default_interval_hours": 6,
                "intervals": ["1h", "3h", "6h", "12h", "24h"],
                "timezone": "Africa/Cairo"
            },
            "dashboard": {
                "host": "0.0.0.0",
                "port": 8000,
                "debug": False
            },
            "export": {
                "formats": ["csv", "xlsx", "json", "markdown", "html"],
                "output_dir": "exports"
            },
            "logging": {
                "level": "INFO",
                "file": "logs/freelance_hunter.log",
                "max_size_mb": 10,
                "backup_count": 5
            },
            "email": {
                "enabled": True,
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "username": "",
                "password": "",
                "from_email": "",
                "use_tls": True
            },
            "api_keys": {}
        }
    
    def _default_profile(self) -> dict[str, Any]:
        """Default user profile."""
        return {
            "skills": [
                "Microsoft Excel", "Microsoft PowerPoint", "Microsoft Word",
                "Data Entry", "PDF Conversion", "Google Sheets", "Data Cleaning",
                "Web Research", "Document Formatting", "Copy Typing", "OCR",
                "Spreadsheet Organization", "Presentation Design", "Slide Formatting",
                "File Conversion", "Administrative Support", "Virtual Assistant",
                "Product Listing", "Internet Research"
            ],
            "experience_level": "Beginner/Intermediate",
            "languages": ["Arabic", "English"],
            "location": "Egypt",
            "availability": "Remote",
            "strengths": [
                "attention to detail", "organization", "fast learning",
                "accuracy", "reliability", "communication"
            ],
            "portfolio_urls": [],
            "bio": "Detail-oriented freelancer specializing in Microsoft Office suite, data entry, document conversion, and presentation design. Fluent in Arabic and English. Available for remote work with quick turnaround times.",
            "hourly_rate_range": {"min": 5, "max": 25, "currency": "USD"},
            "preferred_job_types": ["fixed_price", "hourly"],
            "max_hours_per_week": 30,
            "email_notifications": {
                "enabled": True,
                "email": "islam230366qw@gmail.com",
                "on_scan_complete": True,
                "on_high_match": True,
                "on_new_job": False
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value using dot notation."""
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def get_profile(self, key: str | None = None, default: Any = None) -> Any:
        """Get profile value."""
        if key is None:
            return self._profile
        
        keys = key.split('.')
        value = self._profile
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def update(self, key: str, value: Any):
        """Update configuration value."""
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def update_profile(self, key: str, value: Any):
        """Update profile value."""
        keys = key.split('.')
        profile = self._profile
        
        for k in keys[:-1]:
            if k not in profile:
                profile[k] = {}
            profile = profile[k]
        
        profile[keys[-1]] = value
    
    def save_profile(self, filepath: str | None = None):
        """Save profile to file."""
        profile_path = filepath or os.path.join(os.path.dirname(self.config_path), "profile.json")
        with open(profile_path, 'w', encoding='utf-8') as f:
            json.dump(self._profile, f, ensure_ascii=False, indent=2)
    
    @property
    def database_url(self) -> str:
        """Get database URL."""
        db_config = self._config.get("database", {})
        
        if db_config.get("type") == "postgresql":
            pg = db_config.get("postgresql", {})
            return f"postgresql://{pg.get('user')}:{pg.get('password')}@{pg.get('host')}:{pg.get('port')}/{pg.get('database')}"
        else:
            sqlite_path = db_config.get("sqlite_path", "data/freelance_hunter.db")
            return f"sqlite:///{sqlite_path}"
    
    @property
    def aisa_api_key(self) -> str | None:
        """Get AIsa API key."""
        return self._config.get("api_keys", {}).get("aisa") or os.getenv("AISA_API_KEY")

    @property
    def email_config(self) -> dict[str, Any]:
        """Get email configuration."""
        return self._config.get("email", {})

    @property
    def email_notifications(self) -> dict[str, Any]:
        """Get email notification preferences from profile."""
        return self._profile.get("email_notifications", {
            "enabled": True,
            "email": "islam230366qw@gmail.com",
            "on_scan_complete": True,
            "on_high_match": True,
            "on_new_job": False
        })


# Global config instance
_config_instance: Config | None = None


def get_config(config_path: str | None = None) -> Config:
    """Get global configuration instance."""
    global _config_instance
    if _config_instance is None:
        _config_instance = Config(config_path)
    return _config_instance


def reload_config(config_path: str | None = None) -> Config:
    """Reload configuration."""
    global _config_instance
    _config_instance = Config(config_path)
    return _config_instance