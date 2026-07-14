from django.apps import AppConfig


class RecruitmentConfig(AppConfig):
    name = 'recruitment'
    
    def ready(self):
        import recruitment.signals