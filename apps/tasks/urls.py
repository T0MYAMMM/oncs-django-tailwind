from django.urls import path

from . import views

app_name = 'tasks'

urlpatterns = [
    # Celery
    path('', views.tasks, name="tasks"),
    path('tasks/run/<str:task_name>'  , views.run_task,    name="run-task"    ),
    path('tasks/cancel/<str:task_id>' , views.cancel_task, name="cancel-task" ),
    path('tasks/output/'              , views.task_output, name="task-output" ),
    path('tasks/log/'                 , views.task_log,    name="task-log"    ), 
    path('download-log-file/<str:file_path>/', views.download_log_file, name='download_log_file'),
    
    # Crawler Task Management
    path('crawler-tasks/create/', views.create_crawler_task, name="create-crawler-task"),
    path('crawler-tasks/<int:task_id>/execute/', views.execute_crawler_task_view, name="execute-crawler-task"),
    path('scheduled-tasks/create/', views.create_scheduled_crawler_task, name="create-scheduled-crawler-task"),
    path('scheduled-tasks/<int:scheduled_task_id>/execute/', views.execute_scheduled_crawler_task_view, name="execute-scheduled-crawler-task"),
]