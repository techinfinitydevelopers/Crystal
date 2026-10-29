from django.apps import AppConfig


class MedialibConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'medialib'
    verbose_name = 'Media library'

    def ready(self):
        # Both are global on purpose: every upload box in the dashboard, built
        # now or later, gets "Choose from Media library" and gets indexed,
        # without its own form or model having to know the library exists.
        from .indexing import connect_signals
        from .picking import install
        install()
        connect_signals()
