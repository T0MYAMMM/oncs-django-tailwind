from django.urls import path
from apps.payments import views


urlpatterns = [
    path('', views.pricing_list, name="pricing"),
    path('success/', views.success, name="success"),
    path('cancelled/', views.cancelled, name="cancelled"),
    path('config/', views.get_publishable_key, name="config"),
    path('create-checkout-session/<int:id>/', views.create_checkout_session, name="create_checkout_session")
]
