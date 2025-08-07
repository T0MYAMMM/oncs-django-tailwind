from django.shortcuts import render
from .models import *
from apps.common.models import NewsPortal, ItemSelector, NewsPortalSeedUrl, CrawlerConfig, ScraperConfig, NewsArticle
from django.db.models import Count, Q
from datetime import datetime, timedelta

def index(request):
  # Get counts for dashboard
  news_portals_count = NewsPortal.objects.count()
  selectors_count = ItemSelector.objects.count()
  seed_urls_count = NewsPortalSeedUrl.objects.count()
  crawler_configs_count = CrawlerConfig.objects.count()
  scraper_configs_count = ScraperConfig.objects.count()
  news_articles_count = NewsArticle.objects.count()
  
  # Get recent news articles for the last 30 days
  thirty_days_ago = datetime.now() - timedelta(days=30)
  recent_articles = NewsArticle.objects.filter(created_at__gte=thirty_days_ago).count()
  
  # Get articles by portal for the chart - using a more robust approach
  articles_by_portal = []
  try:
    articles_by_portal = NewsPortal.objects.annotate(
      article_count=Count('clean_urls__article_url__article', filter=Q(clean_urls__article_url__article__isnull=False))
    ).values('name', 'article_count')[:10]
  except Exception as e:
    # Fallback if the relationship doesn't work
    articles_by_portal = NewsPortal.objects.values('name').annotate(article_count=Count('clean_urls'))[:10]
  
  # Get recent articles for display
  latest_articles = []
  try:
    latest_articles = NewsArticle.objects.select_related('article_url__portal').order_by('-created_at')[:5]
  except Exception as e:
    # Fallback if the relationship doesn't work
    latest_articles = NewsArticle.objects.order_by('-created_at')[:5]
  
  # Get task statistics
  try:
    from apps.tasks.views import get_celery_all_tasks
    tasks = get_celery_all_tasks()
    tasks_count = len(tasks)
  except Exception as e:
    tasks_count = 0
  
  context = {
    'segment': 'dashboard',
    'news_portals_count': news_portals_count,
    'selectors_count': selectors_count,
    'seed_urls_count': seed_urls_count,
    'crawler_configs_count': crawler_configs_count,
    'scraper_configs_count': scraper_configs_count,
    'news_articles_count': news_articles_count,
    'recent_articles': recent_articles,
    'articles_by_portal': list(articles_by_portal),
    'latest_articles': latest_articles,
    'tasks_count': tasks_count,
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
