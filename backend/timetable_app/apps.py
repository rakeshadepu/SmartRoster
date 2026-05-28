from django.apps import AppConfig


class TimetableAppConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'timetable_app'
    verbose_name = 'Timetable Planner'

    def ready(self):
        """Register signal handlers on app startup."""
        import timetable_app.signals  # noqa: F401
