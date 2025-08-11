from django.urls import path

from . import views

app_name = 'tasks'

urlpatterns = [
    # Tasks pages
    path('', views.summary, name="tasks"),
    path('summary/', views.summary, name="summary"),
    path('crawler/', views.crawler, name="crawler"),

    # Core task controls
    path('run/<str:task_name>', views.run_task,    name="run-task"    ),
    path('cancel/<str:task_id>', views.cancel_task, name="cancel-task" ),
    path('output/'             , views.task_output, name="task-output" ),
    path('log/'                , views.task_log,    name="task-log"    ), 
    path('download-log-file/<str:file_path>/', views.download_log_file, name='download_log_file'),
    
    # Crawler Task Management
    path('crawler/create/', views.create_crawler_task, name="create-crawler-task"),
    path('crawler/<int:task_id>/execute/', views.execute_crawler_task_view, name="execute-crawler-task"),
    path('scheduled/create/', views.create_scheduled_crawler_task, name="create-scheduled-crawler-task"),
    path('scheduled/<int:scheduled_task_id>/execute/', views.execute_scheduled_crawler_task_view, name="execute-scheduled-crawler-task"),
    
    # Scrapyd API endpoints
    path('scrapyd/job/<int:task_id>/details/', views.scrapyd_job_details, name="scrapyd-job-details"),
    path('scrapyd/job/<int:task_id>/fetch-logs/', views.scrapyd_fetch_logs, name="scrapyd-fetch-logs"),
    path('scrapyd/job/<int:task_id>/fetch-items/', views.scrapyd_fetch_items, name="scrapyd-fetch-items"),
    path('scrapyd/job/<int:task_id>/cancel/', views.scrapyd_cancel_job, name="scrapyd-cancel-job"),
    path('scrapyd/jobs/', views.scrapyd_list_jobs, name="scrapyd-list-jobs"),
    path('scrapyd/status/', views.scrapyd_server_status, name="scrapyd-server-status"),
]