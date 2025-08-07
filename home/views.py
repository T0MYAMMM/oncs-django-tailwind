from django.shortcuts import render
from .models import *

def index(request):

  context = {
    'segment': 'dashboard',
  }
  return render(request, "dashboard/index.html", context)

def starter(request):

  context = {}
  return render(request, "pages/starter.html", context)


# Layout
def stacked(request):
  context = {
    'segment': 'stacked',
    'parent': 'layouts'
  }
  return render(request, 'pages/layouts/stacked.html', context)

def sidebar(request):
  context = {
    'segment': 'sidebar',
    'parent': 'layouts'
  }
  return render(request, 'pages/layouts/sidebar.html', context)


# CRUD
def products(request):
  context = {
    'segment': 'products',
    'parent': 'crud'
  }
  return render(request, 'pages/CRUD/products.html', context)

def users(request):
  context = {
    'segment': 'users',
    'parent': 'crud'
  }
  return render(request, 'pages/CRUD/users.html', context)


# Pages
def pricing(request):
  return render(request, 'pages/pricing.html')

def maintenance(request):
  return render(request, 'pages/maintenance.html')

def error_404(request):
  return render(request, 'pages/404.html')

def error_500(request):
  return render(request, 'pages/500.html')

def settings_view(request):
  context = {
    'segment': 'settings',
  }
  return render(request, 'pages/settings.html', context)


# Playground
def stacked_playground(request):
  return render(request, 'pages/playground/stacked.html')


def sidebar_playground(request):
  context = {
    'segment': 'sidebar_playground',
    'parent': 'playground'
  }
  return render(request, 'pages/playground/sidebar.html', context)


# i18n
def i18n_view(request):
  context = {
    'segment': 'i18n'
  }
  return render(request, 'pages/i18n.html', context)
