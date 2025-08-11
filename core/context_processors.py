from django.conf import settings

def sidebar_config(request):
    return {'sidebar_config': getattr(settings, 'SHOW_APP_CONFIG', {})}