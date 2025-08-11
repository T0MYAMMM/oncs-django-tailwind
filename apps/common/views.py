from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from django_countries import countries
import json
from django.utils import timezone
from core.decorators import feature_required

from .models import (
    NewsPortal, NewsArticleRawUrl, NewsArticleCleanUrl, NewsArticle,
    NewsArticleAuthor, NewsArticleImage, NewsPortalSeedUrl,
    ItemSelector, CrawlerConfig, ScraperConfig, CrawlerTask, CrawlerScheduledTask
)
from .forms import (
    NewsPortalForm, NewsArticleRawUrlForm, NewsArticleCleanUrlForm,
    NewsArticleForm, NewsArticleAuthorForm, NewsArticleImageForm,
    NewsPortalSeedUrlForm, ItemSelectorForm, CrawlerConfigForm, ScraperConfigForm,
    CrawlerTaskForm, CrawlerScheduledTaskForm
)

# News Portal CRUD
@login_required
@feature_required('SHOW_CRUD_NEWS_PORTALS')
def news_portals_list(request):
    """List all news portals with search and pagination"""
    search_query = request.GET.get('search', '')
    portals = NewsPortal.objects.all()
    
    if search_query:
        portals = portals.filter(
            Q(name__icontains=search_query) |
            Q(domain__icontains=search_query) |
            Q(city__icontains=search_query)
        )
    
    paginator = Paginator(portals, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'segment': 'news_portals',
        'parent': 'crud',
        'countries': countries
    }
    return render(request, 'pages/CRUD/news-portals.html', context)

@login_required
@feature_required('SHOW_CRUD_NEWS_PORTALS')
def news_portal_create(request):
    """Create a new news portal"""
    if request.method == 'POST':
        form = NewsPortalForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'News portal created successfully!')
            return redirect('common:news_portals_list')
    else:
        form = NewsPortalForm()
    
    context = {
        'form': form,
        'segment': 'news_portals',
        'parent': 'crud',
        'action': 'Create'
    }
    return render(request, 'pages/CRUD/news-portal-form.html', context)

@login_required
@feature_required('SHOW_CRUD_NEWS_PORTALS')
def news_portal_edit(request, pk):
    """Edit an existing news portal"""
    portal = get_object_or_404(NewsPortal, pk=pk)
    
    if request.method == 'POST':
        form = NewsPortalForm(request.POST, instance=portal)
        if form.is_valid():
            form.save()
            messages.success(request, 'News portal updated successfully!')
            return redirect('common:news_portals_list')
    else:
        form = NewsPortalForm(instance=portal)
    
    context = {
        'form': form,
        'portal': portal,
        'segment': 'news_portals',
        'parent': 'crud',
        'action': 'Edit'
    }
    return render(request, 'pages/CRUD/news-portal-form.html', context)

@login_required
@feature_required('SHOW_CRUD_NEWS_PORTALS')
def news_portal_delete(request, pk):
    """Delete a news portal"""
    portal = get_object_or_404(NewsPortal, pk=pk)
    
    if request.method == 'POST':
        portal.delete()
        messages.success(request, 'News portal deleted successfully!')
        return redirect('common:news_portals_list')
    
    context = {
        'portal': portal,
        'segment': 'news_portals',
        'parent': 'crud'
    }
    return render(request, 'pages/CRUD/news-portal-delete.html', context)

# News Article Raw URLs CRUD
@login_required
@feature_required('SHOW_CRUD_NEWS_ARTICLE_RAW_URLS')
def news_article_raw_urls_list(request):
    """List all raw URLs with search and pagination"""
    search_query = request.GET.get('search', '')
    raw_urls = NewsArticleRawUrl.objects.select_related('portal').all()
    
    if search_query:
        raw_urls = raw_urls.filter(
            Q(url__icontains=search_query) |
            Q(portal__name__icontains=search_query)
        )
    
    paginator = Paginator(raw_urls, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'segment': 'news_article_raw_urls',
        'parent': 'crud'
    }
    return render(request, 'pages/CRUD/news-article-raw-urls.html', context)

@login_required
@feature_required('SHOW_CRUD_NEWS_ARTICLE_RAW_URLS')
def news_article_raw_url_create(request):
    """Create a new raw URL"""
    if request.method == 'POST':
        form = NewsArticleRawUrlForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Raw URL created successfully!')
            return redirect('common:news_article_raw_urls_list')
    else:
        form = NewsArticleRawUrlForm()
    
    context = {
        'form': form,
        'segment': 'news_article_raw_urls',
        'parent': 'crud',
        'action': 'Create'
    }
    return render(request, 'pages/CRUD/news-article-raw-url-form.html', context)

@login_required
@feature_required('SHOW_CRUD_NEWS_ARTICLE_RAW_URLS')
def news_article_raw_url_edit(request, pk):
    """Edit an existing raw URL"""
    raw_url = get_object_or_404(NewsArticleRawUrl, pk=pk)
    
    if request.method == 'POST':
        form = NewsArticleRawUrlForm(request.POST, instance=raw_url)
        if form.is_valid():
            form.save()
            messages.success(request, 'Raw URL updated successfully!')
            return redirect('common:news_article_raw_urls_list')
    else:
        form = NewsArticleRawUrlForm(instance=raw_url)
    
    context = {
        'form': form,
        'raw_url': raw_url,
        'segment': 'news_article_raw_urls',
        'parent': 'crud',
        'action': 'Edit'
    }
    return render(request, 'pages/CRUD/news-article-raw-url-form.html', context)

@login_required
@feature_required('SHOW_CRUD_NEWS_ARTICLE_RAW_URLS')
def news_article_raw_url_delete(request, pk):
    """Delete a raw URL"""
    raw_url = get_object_or_404(NewsArticleRawUrl, pk=pk)
    
    if request.method == 'POST':
        raw_url.delete()
        messages.success(request, 'Raw URL deleted successfully!')
        return redirect('common:news_article_raw_urls_list')
    
    context = {
        'raw_url': raw_url,
        'segment': 'news_article_raw_urls',
        'parent': 'crud'
    }
    return render(request, 'pages/CRUD/news-article-raw-url-delete.html', context)

# News Article Clean URLs CRUD
@login_required
@feature_required('SHOW_CRUD_NEWS_ARTICLE_CLEAN_URLS')
def news_article_clean_urls_list(request):
    """List all clean URLs with search and pagination"""
    search_query = request.GET.get('search', '')
    clean_urls = NewsArticleCleanUrl.objects.select_related('portal', 'article_url_raw').all()
    
    if search_query:
        clean_urls = clean_urls.filter(
            Q(url__icontains=search_query) |
            Q(portal__name__icontains=search_query)
        )
    
    paginator = Paginator(clean_urls, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'segment': 'news_article_clean_urls',
        'parent': 'crud'
    }
    return render(request, 'pages/CRUD/news-article-clean-urls.html', context)

@login_required
@feature_required('SHOW_CRUD_NEWS_ARTICLE_CLEAN_URLS')
def news_article_clean_url_create(request):
    """Create a new clean URL"""
    if request.method == 'POST':
        form = NewsArticleCleanUrlForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clean URL created successfully!')
            return redirect('common:news_article_clean_urls_list')
    else:
        form = NewsArticleCleanUrlForm()
    
    context = {
        'form': form,
        'segment': 'news_article_clean_urls',
        'parent': 'crud',
        'action': 'Create'
    }
    return render(request, 'pages/CRUD/news-article-clean-url-form.html', context)

@login_required
@feature_required('SHOW_CRUD_NEWS_ARTICLE_CLEAN_URLS')
def news_article_clean_url_edit(request, pk):
    """Edit an existing clean URL"""
    clean_url = get_object_or_404(NewsArticleCleanUrl, pk=pk)
    
    if request.method == 'POST':
        form = NewsArticleCleanUrlForm(request.POST, instance=clean_url)
        if form.is_valid():
            form.save()
            messages.success(request, 'Clean URL updated successfully!')
            return redirect('common:news_article_clean_urls_list')
    else:
        form = NewsArticleCleanUrlForm(instance=clean_url)
    
    context = {
        'form': form,
        'clean_url': clean_url,
        'segment': 'news_article_clean_urls',
        'parent': 'crud',
        'action': 'Edit'
    }
    return render(request, 'pages/CRUD/news-article-clean-url-form.html', context)

@login_required
@feature_required('SHOW_CRUD_NEWS_ARTICLE_CLEAN_URLS')
def news_article_clean_url_delete(request, pk):
    """Delete a clean URL"""
    clean_url = get_object_or_404(NewsArticleCleanUrl, pk=pk)
    
    if request.method == 'POST':
        clean_url.delete()
        messages.success(request, 'Clean URL deleted successfully!')
        return redirect('common:news_article_clean_urls_list')
    
    context = {
        'clean_url': clean_url,
        'segment': 'news_article_clean_urls',
        'parent': 'crud'
    }
    return render(request, 'pages/CRUD/news-article-clean-url-delete.html', context)

# News Articles CRUD
@login_required
@feature_required('SHOW_CRUD_NEWS_ARTICLES')
def news_articles_list(request):
    """List all news articles with search and pagination"""
    search_query = request.GET.get('search', '')
    articles = NewsArticle.objects.select_related('article_url__portal').prefetch_related('authors', 'images').all()
    
    if search_query:
        articles = articles.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(article_url__portal__name__icontains=search_query)
        )
    
    paginator = Paginator(articles, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'segment': 'news_articles',
        'parent': 'crud'
    }
    return render(request, 'pages/CRUD/news-articles.html', context)

@login_required
@feature_required('SHOW_CRUD_NEWS_ARTICLES')
def news_article_create(request):
    """Create a new news article"""
    if request.method == 'POST':
        form = NewsArticleForm(request.POST)
        if form.is_valid():
            article = form.save()
            messages.success(request, 'News article created successfully!')
            return redirect('common:news_articles_list')
    else:
        form = NewsArticleForm()
    
    context = {
        'form': form,
        'segment': 'news_articles',
        'parent': 'crud',
        'action': 'Create'
    }
    return render(request, 'pages/CRUD/news-article-form.html', context)

@login_required
@feature_required('SHOW_CRUD_NEWS_ARTICLES')
def news_article_edit(request, pk):
    """Edit an existing news article"""
    article = get_object_or_404(NewsArticle, pk=pk)
    
    if request.method == 'POST':
        form = NewsArticleForm(request.POST, instance=article)
        if form.is_valid():
            form.save()
            messages.success(request, 'News article updated successfully!')
            return redirect('common:news_articles_list')
    else:
        form = NewsArticleForm(instance=article)
    
    context = {
        'form': form,
        'article': article,
        'segment': 'news_articles',
        'parent': 'crud',
        'action': 'Edit'
    }
    return render(request, 'pages/CRUD/news-article-form.html', context)

@login_required
@feature_required('SHOW_CRUD_NEWS_ARTICLES')
def news_article_delete(request, pk):
    """Delete a news article"""
    article = get_object_or_404(NewsArticle, pk=pk)
    
    if request.method == 'POST':
        article.delete()
        messages.success(request, 'News article deleted successfully!')
        return redirect('common:news_articles_list')
    
    context = {
        'article': article,
        'segment': 'news_articles',
        'parent': 'crud'
    }
    return render(request, 'pages/CRUD/news-article-delete.html', context)

# Item Selectors CRUD
@login_required
@feature_required('SHOW_CRUD_SELECTORS')
def selectors_list(request):
    """List all item selectors with search and pagination"""
    search_query = request.GET.get('search', '')
    selectors = ItemSelector.objects.select_related('portal').all()
    
    if search_query:
        selectors = selectors.filter(
            Q(query__icontains=search_query) |
            Q(portal__name__icontains=search_query)
        )
    
    paginator = Paginator(selectors, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all portals and selectors for the forms
    portals = NewsPortal.objects.all()
    all_selectors = ItemSelector.objects.all()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'segment': 'selectors',
        'parent': 'crud',
        'portals': portals,
        'selectors': all_selectors
    }
    return render(request, 'pages/CRUD/selectors.html', context)

@login_required
@feature_required('SHOW_CRUD_SELECTORS')
def selector_create(request):
    """Create a new item selector"""
    if request.method == 'POST':
        form = ItemSelectorForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item selector created successfully!')
            return redirect('common:selectors_list')
        else:
            messages.error(request, 'Please correct the errors below.')
            return redirect('common:selectors_list')
    
    # If it's a GET request, redirect to the list page
    return redirect('common:selectors_list')

@login_required
@feature_required('SHOW_CRUD_SELECTORS')
def selector_edit(request, pk):
    """Edit an existing item selector"""
    selector = get_object_or_404(ItemSelector, pk=pk)
    
    if request.method == 'POST':
        form = ItemSelectorForm(request.POST, instance=selector)
        if form.is_valid():
            form.save()
            messages.success(request, 'Item selector updated successfully!')
            return redirect('common:selectors_list')
        else:
            messages.error(request, 'Please correct the errors below.')
            return redirect('common:selectors_list')
    
    # If it's a GET request, redirect to the list page
    return redirect('common:selectors_list')

@login_required
@feature_required('SHOW_CRUD_SELECTORS')
def selector_delete(request, pk):
    """Delete an item selector"""
    selector = get_object_or_404(ItemSelector, pk=pk)
    
    if request.method == 'POST':
        selector.delete()
        messages.success(request, 'Item selector deleted successfully!')
        return redirect('common:selectors_list')
    
    # If it's a GET request, redirect to the list page
    return redirect('common:selectors_list')

# Crawler Configs CRUD
@login_required
@feature_required('SHOW_CRUD_CRAWLER_CONFIGS')
def crawler_configs_list(request):
    """List all crawler configs with search and pagination"""
    search_query = request.GET.get('search', '')
    configs = CrawlerConfig.objects.select_related('portal', 'item_selector').all()
    
    if search_query:
        configs = configs.filter(
            Q(name__icontains=search_query) |
            Q(portal__name__icontains=search_query)
        )
    
    paginator = Paginator(configs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all portals and selectors for the forms
    portals = NewsPortal.objects.all()
    selectors = ItemSelector.objects.all()
    
    # Get seed URLs for each portal
    seed_urls = NewsPortalSeedUrl.objects.select_related('portal').all()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'segment': 'crawler_configs',
        'parent': 'crud',
        'portals': portals,
        'selectors': selectors,
        'seed_urls': seed_urls
    }
    return render(request, 'pages/CRUD/crawler-configs.html', context)

@login_required
@feature_required('SHOW_CRUD_CRAWLER_CONFIGS')
def crawler_config_create(request):
    """Create a new crawler config"""
    if request.method == 'POST':
        form = CrawlerConfigForm(request.POST)
        if form.is_valid():
            instance = form.save()

            # Integrate selected seed URLs into custom_settings
            seed_urls_selected = request.POST.getlist('seed_urls')
            if seed_urls_selected:
                custom_settings = instance.custom_settings or {}
                if 'seed_urls' not in custom_settings:
                    custom_settings['seed_urls'] = []
                for url in seed_urls_selected:
                    if url not in custom_settings['seed_urls']:
                        custom_settings['seed_urls'].append(url)
                instance.custom_settings = custom_settings
                instance.save(update_fields=['custom_settings'])

            messages.success(request, 'Crawler config created successfully!')
            return redirect('common:crawler_configs_list')
        else:
            messages.error(request, 'Please correct the errors below.')
            return redirect('common:crawler_configs_list')
    
    # If it's a GET request, redirect to the list page
    return redirect('common:crawler_configs_list')

@login_required
@feature_required('SHOW_CRUD_CRAWLER_CONFIGS')
def crawler_config_edit(request, pk):
    """Edit an existing crawler config"""
    config = get_object_or_404(CrawlerConfig, pk=pk)
    
    if request.method == 'POST':
        form = CrawlerConfigForm(request.POST, instance=config)
        if form.is_valid():
            instance = form.save()

            # Update seed URLs selection into custom_settings
            seed_urls_selected = request.POST.getlist('seed_urls')
            custom_settings = instance.custom_settings or {}
            custom_settings['seed_urls'] = seed_urls_selected
            instance.custom_settings = custom_settings
            instance.save(update_fields=['custom_settings'])

            messages.success(request, 'Crawler config updated successfully!')
            return redirect('common:crawler_configs_list')
        else:
            messages.error(request, 'Please correct the errors below.')
            return redirect('common:crawler_configs_list')
    
    # If it's a GET request, redirect to the list page
    return redirect('common:crawler_configs_list')

@login_required
@feature_required('SHOW_CRUD_CRAWLER_CONFIGS')
def crawler_config_delete(request, pk):
    """Delete a crawler config"""
    config = get_object_or_404(CrawlerConfig, pk=pk)
    
    if request.method == 'POST':
        config.delete()
        messages.success(request, 'Crawler config deleted successfully!')
        return redirect('common:crawler_configs_list')
    
    # If it's a GET request, redirect to the list page
    return redirect('common:crawler_configs_list')

@login_required
@feature_required('SHOW_CRUD_CRAWLER_CONFIGS')
def crawler_config_seed_urls(request, pk):
    """Manage seed URLs for a specific crawler config"""
    config = get_object_or_404(CrawlerConfig, pk=pk)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        seed_url_id = request.POST.get('seed_url_id')
        
        if action == 'add':
            # Add existing seed URL to crawler config
            try:
                seed_url = NewsPortalSeedUrl.objects.get(id=seed_url_id, portal=config.portal)
                # Here you would add logic to associate seed URL with crawler config
                # For now, we'll just add it to custom_settings
                custom_settings = config.custom_settings or {}
                if 'seed_urls' not in custom_settings:
                    custom_settings['seed_urls'] = []
                if seed_url.url not in custom_settings['seed_urls']:
                    custom_settings['seed_urls'].append(seed_url.url)
                    config.custom_settings = custom_settings
                    config.save()
                    messages.success(request, f'Seed URL {seed_url.url} added to crawler config!')
            except NewsPortalSeedUrl.DoesNotExist:
                messages.error(request, 'Seed URL not found!')
        
        elif action == 'remove':
            # Remove seed URL from crawler config
            try:
                # Find the seed URL by URL string since we're passing the URL
                seed_url = NewsPortalSeedUrl.objects.get(url=seed_url_id, portal=config.portal)
                custom_settings = config.custom_settings or {}
                if 'seed_urls' in custom_settings and seed_url.url in custom_settings['seed_urls']:
                    custom_settings['seed_urls'].remove(seed_url.url)
                    config.custom_settings = custom_settings
                    config.save()
                    messages.success(request, f'Seed URL {seed_url.url} removed from crawler config!')
            except NewsPortalSeedUrl.DoesNotExist:
                messages.error(request, 'Seed URL not found!')
        
        elif action == 'create':
            # Create new seed URL for this portal
            url = request.POST.get('url')
            if url:
                try:
                    seed_url = NewsPortalSeedUrl.objects.create(url=url, portal=config.portal)
                    # Add to crawler config
                    custom_settings = config.custom_settings or {}
                    if 'seed_urls' not in custom_settings:
                        custom_settings['seed_urls'] = []
                    custom_settings['seed_urls'].append(seed_url.url)
                    config.custom_settings = custom_settings
                    config.save()
                    messages.success(request, f'Seed URL {seed_url.url} created and added to crawler config!')
                except Exception as e:
                    messages.error(request, f'Error creating seed URL: {str(e)}')
    
    # Get seed URLs for this portal
    portal_seed_urls = NewsPortalSeedUrl.objects.filter(portal=config.portal)
    
    # Get current seed URLs associated with this config
    current_seed_urls = []
    if config.custom_settings and 'seed_urls' in config.custom_settings:
        current_seed_urls = config.custom_settings['seed_urls']
    
    context = {
        'config': config,
        'portal_seed_urls': portal_seed_urls,
        'current_seed_urls': current_seed_urls,
        'segment': 'crawler_configs',
        'parent': 'crud'
    }
    return render(request, 'pages/CRUD/crawler-config-seed-urls.html', context)

# Scraper Configs CRUD
@login_required
@feature_required('SHOW_CRUD_SCRAPER_CONFIGS')
def scraper_configs_list(request):
    """List all scraper configs with search and pagination"""
    search_query = request.GET.get('search', '')
    configs = ScraperConfig.objects.select_related('portal', 'item_selector').all()
    
    if search_query:
        configs = configs.filter(
            Q(name__icontains=search_query) |
            Q(portal__name__icontains=search_query)
        )
    
    paginator = Paginator(configs, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all portals and selectors for the forms
    portals = NewsPortal.objects.all()
    selectors = ItemSelector.objects.all()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'segment': 'scraper_configs',
        'parent': 'crud',
        'portals': portals,
        'selectors': selectors
    }
    return render(request, 'pages/CRUD/scraper-configs.html', context)

@login_required
@feature_required('SHOW_CRUD_SCRAPER_CONFIGS')
def scraper_config_create(request):
    """Create a new scraper config"""
    if request.method == 'POST':
        form = ScraperConfigForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Scraper config created successfully!')
            return redirect('common:scraper_configs_list')
        else:
            messages.error(request, 'Please correct the errors below.')
            return redirect('common:scraper_configs_list')
    
    # If it's a GET request, redirect to the list page
    return redirect('common:scraper_configs_list')

@login_required
@feature_required('SHOW_CRUD_SCRAPER_CONFIGS')
def scraper_config_edit(request, pk):
    """Edit an existing scraper config"""
    config = get_object_or_404(ScraperConfig, pk=pk)
    
    if request.method == 'POST':
        form = ScraperConfigForm(request.POST, instance=config)
        if form.is_valid():
            form.save()
            messages.success(request, 'Scraper config updated successfully!')
            return redirect('common:scraper_configs_list')
        else:
            messages.error(request, 'Please correct the errors below.')
            return redirect('common:scraper_configs_list')
    
    # If it's a GET request, redirect to the list page
    return redirect('common:scraper_configs_list')

@login_required
@feature_required('SHOW_CRUD_SCRAPER_CONFIGS')
def scraper_config_delete(request, pk):
    """Delete a scraper config"""
    config = get_object_or_404(ScraperConfig, pk=pk)
    
    if request.method == 'POST':
        config.delete()
        messages.success(request, 'Scraper config deleted successfully!')
        return redirect('common:scraper_configs_list')
    
    # If it's a GET request, redirect to the list page
    return redirect('common:scraper_configs_list')


# Seed URL CRUD
@login_required
@feature_required('SHOW_CRUD_SEED_URLS')
def seed_urls_list(request):
    """List all seed URLs with search and pagination"""
    search_query = request.GET.get('search', '')
    seed_urls = NewsPortalSeedUrl.objects.select_related('portal').all()
    
    if search_query:
        seed_urls = seed_urls.filter(
            Q(url__icontains=search_query) |
            Q(portal__name__icontains=search_query) |
            Q(portal__domain__icontains=search_query)
        )
    
    paginator = Paginator(seed_urls, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get all portals for the forms
    portals = NewsPortal.objects.all()
    
    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'segment': 'seed_urls',
        'parent': 'crud',
        'portals': portals
    }
    return render(request, 'pages/CRUD/seed-urls.html', context)

@login_required
@feature_required('SHOW_CRUD_SEED_URLS')
def seed_url_create(request):
    """Create a new seed URL"""
    if request.method == 'POST':
        form = NewsPortalSeedUrlForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Seed URL created successfully!')
            return redirect('common:seed_urls_list')
        else:
            messages.error(request, 'Please correct the errors below.')
            return redirect('common:seed_urls_list')
    
    # If it's a GET request, redirect to the list page
    return redirect('common:seed_urls_list')

@login_required
@feature_required('SHOW_CRUD_SEED_URLS')
def seed_url_edit(request, pk):
    """Edit an existing seed URL"""
    seed_url = get_object_or_404(NewsPortalSeedUrl, pk=pk)
    
    if request.method == 'POST':
        form = NewsPortalSeedUrlForm(request.POST, instance=seed_url)
        if form.is_valid():
            form.save()
            messages.success(request, 'Seed URL updated successfully!')
            return redirect('common:seed_urls_list')
        else:
            messages.error(request, 'Please correct the errors below.')
            return redirect('common:seed_urls_list')
    
    # If it's a GET request, redirect to the list page
    return redirect('common:seed_urls_list')

@login_required
@feature_required('SHOW_CRUD_SEED_URLS')
def seed_url_delete(request, pk):
    """Delete a seed URL"""
    seed_url = get_object_or_404(NewsPortalSeedUrl, pk=pk)
    
    if request.method == 'POST':
        seed_url.delete()
        messages.success(request, 'Seed URL deleted successfully!')
        return redirect('common:seed_urls_list')
    
    # If it's a GET request, redirect to the list page
    return redirect('common:seed_urls_list')


# AJAX endpoints for dynamic forms
@csrf_exempt
@require_http_methods(["POST"])
def get_portal_selectors(request):
    """Get selectors for a specific portal"""
    portal_id = request.POST.get('portal_id')
    if portal_id:
        selectors = ItemSelector.objects.filter(portal_id=portal_id)
        data = [{'id': selector.id, 'query': selector.query, 'item': selector.item, 'method': selector.method} for selector in selectors]
        return JsonResponse({'selectors': data})
    return JsonResponse({'selectors': []})


@csrf_exempt
@require_http_methods(["POST"])
def get_portal_raw_urls(request):
    """Get raw URLs for a specific portal"""
    portal_id = request.POST.get('portal_id')
    if portal_id:
        raw_urls = NewsArticleRawUrl.objects.filter(portal_id=portal_id)
        data = [{'id': url.id, 'url': url.url, 'status': url.status} for url in raw_urls]
        return JsonResponse({'raw_urls': data})
    return JsonResponse({'raw_urls': []}) 