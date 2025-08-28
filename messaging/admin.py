from django.contrib import admin
from django.http import JsonResponse
from django.urls import path
from django.utils.html import format_html
from .services import MessagingService
import json


@admin.register(admin.models.LogEntry)
class LogEntryAdmin(admin.ModelAdmin):
    """Admin interface for system logs"""
    list_display = ('action_time', 'user', 'content_type', 'object_repr', 'action_flag', 'change_message')
    list_filter = ('action_flag', 'action_time', 'content_type')
    search_fields = ('object_repr', 'change_message')
    date_hierarchy = 'action_time'
    readonly_fields = ('action_time', 'user', 'content_type', 'object_id', 'object_repr', 'action_flag', 'change_message')


class KafkaStatusAdmin(admin.ModelAdmin):
    """Admin interface for Kafka status monitoring"""
    change_list_template = 'admin/kafka_status_change_list.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('status/', self.admin_site.admin_view(self.kafka_status_view), name='kafka_status'),
            path('start_consumers/', self.admin_site.admin_view(self.start_consumers_view), name='start_consumers'),
            path('stop_consumers/', self.admin_site.admin_view(self.stop_consumers_view), name='stop_consumers'),
        ]
        return custom_urls + urls
    
    def kafka_status_view(self, request):
        """API endpoint to get Kafka status"""
        try:
            status = MessagingService.get_status()
            return JsonResponse(status)
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def start_consumers_view(self, request):
        """API endpoint to start all consumers"""
        try:
            MessagingService.start_all_consumers()
            return JsonResponse({'message': 'Consumers started successfully'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)
    
    def stop_consumers_view(self, request):
        """API endpoint to stop all consumers"""
        try:
            MessagingService.stop_all_consumers()
            return JsonResponse({'message': 'Consumers stopped successfully'})
        except Exception as e:
            return JsonResponse({'error': str(e)}, status=500)


# Register the admin classes
admin.site.register(KafkaStatusAdmin, KafkaStatusAdmin)


# Create a custom admin site for Kafka operations
class KafkaAdminSite(admin.AdminSite):
    site_header = 'Kafka Messaging Administration'
    site_title = 'Kafka Admin'
    index_title = 'Kafka Operations Dashboard'


# Register with the main admin site
admin.site.site_header = 'ONCS Administration'
admin.site.site_title = 'ONCS Admin'
admin.site.index_title = 'Welcome to ONCS Administration'
