from django.contrib import admin
from .models import ScrapydServer


@admin.register(ScrapydServer)
class ScrapydServerAdmin(admin.ModelAdmin):
    list_display = ("name", "host", "port", "is_active", "use_https", "created_at")
    list_filter = ("is_active", "use_https")
    search_fields = ("name", "host")
