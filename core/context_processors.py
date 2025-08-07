from django.conf import settings

def sidebar_config(request):
    return {'sidebar_config': getattr(settings, 'SIDEBAR_CONFIG', {})}