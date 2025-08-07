from django.urls import path

from . import views

urlpatterns = [
    path("react-index" , views.index, name="react_index"),
    path("react-charts", views.charts, name="react_charts"),
]
