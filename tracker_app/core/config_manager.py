"""
Configuration Management System
Centralized configuration for the entire application
"""

import json
import os
from typing import Any, Dict, Optional
from datetime import datetime


class Config:
    """Application configuration manager"""

    DEFAULT_CONFIG = {
        'app': {
            'name': 'Learning Tracker',
            'version': '2.0.0',
            'environment': 'production',
            'debug': False
        },
        'database': {
            'path': 'learning_tracker.db',
            'backup_dir': 'backups',
            'auto_backup': True,
            'backup_frequency': 'daily'
        },
        'spaced_repetition': {
            'algorithm': 'SM2',
            'min_ease_factor': 1.3,
            'max_ease_factor': 2.5,
            'quality_threshold': 3,
            'initial_easiness': 2.5
        },
        'learning_goals': {
            'daily_review_goal': 20,
            'weekly_mastery_goal': 50,
            'session_duration_minutes': 30
        },
        'notifications': {
            'enabled': True,
            'daily_reminder': True,
            'reminder_time': '09:00',
            'notify_due_items': True,
            'notify_struggling': True,
            'notify_mastered': True
        },
        'ui': {
            'theme': 'dark',
            'language': 'en',
            'items_per_page': 25,
            'show_tips': True
        },
        'api': {
            'enabled': True,
            'host': 'localhost',
            'port': 5000,
            'debug': False,
            'cors_enabled': False
        },
        'export': {
            'default_format': 'json',
            'include_history': True,
            'compression': False
        },
        'features': {
            'batch_operations': True,
            'analytics': True,
            'reminders': True,
            'api': True,
            'web_dashboard': True,
            'cli': True,
            'backups': True,
            'notifications': True,
            'import_export': True
        },
        'privacy': {
            'encryption_enabled': False,
            'data_retention_days': 730,
            'analytics_collection': False,
            'anonymous_usage': True
        },
        'advanced': {
            'max_items': 10000,
            'cache_enabled': True,
            'cache_ttl_minutes': 60,
            'parallel_processing': False,
            'log_level': 'INFO'
        }
    }

    def __init__(self, config_file: str = 'config.json'):
        self.config_file = config_file
        self.config = self.DEFAULT_CONFIG.copy()
        self.load()

    def load(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    user_config = json.load(f)
                    self._merge_config(self.config, user_config)
                print(f"✓ Configuration loaded from {self.config_file}")
            except Exception as e:
                print(f"⚠️  Error loading config: {e}. Using defaults.")
        else:
            self.save()  # Create default config file

    def _merge_config(self, base: Dict, override: Dict):
        """Recursively merge configuration"""
        for key, value in override.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value

    def save(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            print(f"✓ Configuration saved to {self.config_file}")
        except Exception as e:
            print(f"⚠️  Error saving config: {e}")

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value by dot-notation path"""
        keys = key.split('.')
        value = self.config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
                if value is None:
                    return default
            else:
                return default
        
        return value if value is not None else default

    def set(self, key: str, value: Any):
        """Set configuration value by dot-notation path"""
        keys = key.split('.')
        config = self.config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value

    def get_app_config(self) -> Dict:
        """Get app configuration"""
        return self.config.get('app', {})

    def get_database_config(self) -> Dict:
        """Get database configuration"""
        return self.config.get('database', {})

    def get_api_config(self) -> Dict:
        """Get API configuration"""
        return self.config.get('api', {})

    def get_notification_config(self) -> Dict:
        """Get notification configuration"""
        return self.config.get('notifications', {})

    def is_feature_enabled(self, feature: str) -> bool:
        """Check if a feature is enabled"""
        return self.config.get('features', {}).get(feature, False)

    def get_all(self) -> Dict:
        """Get entire configuration"""
        return self.config.copy()

    def reset_to_defaults(self):
        """Reset configuration to defaults"""
        self.config = self.DEFAULT_CONFIG.copy()
        self.save()

    def validate(self) -> Dict:
        """Validate configuration"""
        issues = []
        
        # Check required fields
        required_fields = [
            'app.name',
            'database.path',
            'spaced_repetition.algorithm'
        ]
        
        for field in required_fields:
            if self.get(field) is None:
                issues.append(f"Missing required field: {field}")
        
        # Validate values
        if self.get('spaced_repetition.min_ease_factor', 0) >= self.get('spaced_repetition.max_ease_factor', 1):
            issues.append("min_ease_factor must be less than max_ease_factor")
        
        if self.get('api.port', 0) < 1024 or self.get('api.port', 65536) > 65535:
            issues.append("Invalid API port number")
        
        return {
            'valid': len(issues) == 0,
            'issues': issues
        }

    def __repr__(self) -> str:
        return f"Config(file={self.config_file}, valid={self.validate()['valid']})"


class ConfigurationWizard:
    """Interactive configuration wizard"""

    def __init__(self):
        self.config = Config()

    def run(self):
        """Run configuration wizard"""
        print("\n" + "="*60)
        print("  LEARNING TRACKER - CONFIGURATION WIZARD")
        print("="*60)
        
        print("\n  LEARNING GOALS")
        daily_goal = input("  Daily review goal (default 20): ").strip()
        if daily_goal.isdigit():
            self.config.set('learning_goals.daily_review_goal', int(daily_goal))
        
        print("\n  NOTIFICATIONS")
        enable_notif = input("  Enable notifications? (y/n): ").lower()
        self.config.set('notifications.enabled', enable_notif == 'y')
        
        if enable_notif == 'y':
            reminder_time = input("  Daily reminder time (HH:MM, default 09:00): ").strip()
            if reminder_time:
                self.config.set('notifications.reminder_time', reminder_time)
        
        print("\n  API SERVER")
        enable_api = input("  Enable API server? (y/n): ").lower()
        self.config.set('api.enabled', enable_api == 'y')
        
        if enable_api == 'y':
            api_port = input("  API port (default 5000): ").strip()
            if api_port.isdigit():
                self.config.set('api.port', int(api_port))
        
        print("\n  UI PREFERENCES")
        theme = input("  Theme (dark/light, default dark): ").strip().lower()
        if theme in ['dark', 'light']:
            self.config.set('ui.theme', theme)
        
        print("\n  FEATURES")
        features = ['analytics', 'reminders', 'backups', 'import_export']
        for feature in features:
            enable = input(f"  Enable {feature}? (y/n, default y): ").lower()
            self.config.set(f'features.{feature}', enable != 'n')
        
        # Validate
        validation = self.config.validate()
        if validation['valid']:
            self.config.save()
            print("\n  ✓ Configuration complete!\n")
        else:
            print("\n  ⚠️  Configuration issues found:")
            for issue in validation['issues']:
                print(f"     • {issue}")


def create_default_config():
    """Create default configuration file"""
    config = Config()
    config.save()
    return config


def get_config() -> Config:
    """Get global config instance"""
    if not hasattr(get_config, 'instance'):
        get_config.instance = Config()
    return get_config.instance


if __name__ == '__main__':
    # Run wizard
    wizard = ConfigurationWizard()
    wizard.run()
