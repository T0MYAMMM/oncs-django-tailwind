from django.urls import path, re_path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("starter/", views.starter, name="starter"),

    # Layout
    path('layouts/stacked/', views.stacked, name="stacked"),
    path('layouts/sidebar/', views.sidebar, name="sidebar"),

    # Users
    path('crud/products/', views.products, name="products"),
    path('crud/users/', views.users, name="users"),

    # Pages
    path('pricing/', views.pricing, name="pricing_details"),
    path('maintenance/', views.maintenance, name="maintenance"),
    path('404/', views.error_404, name="error_404"),
    path('500/', views.error_500, name="error_500"),
    path('settings/', views.settings_view, name="settings"),
    path('i18n/', views.i18n_view, name="i18n_view"),

    # Playground
    path('stacked-playground/', views.stacked_playground, name="stacked_playground"),
    path('sidebar-playground/', views.sidebar_playground, name="sidebar_playground"),
]
