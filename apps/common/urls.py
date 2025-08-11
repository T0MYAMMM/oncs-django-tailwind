from django.urls import path
from . import views

app_name = 'common'

urlpatterns = [
    # News Portal URLs
    path('news-portals/', views.news_portals_list, name='news_portals_list'),
    path('news-portals/create/', views.news_portal_create, name='news_portal_create'),
    path('news-portals/<int:pk>/edit/', views.news_portal_edit, name='news_portal_edit'),
    path('news-portals/<int:pk>/delete/', views.news_portal_delete, name='news_portal_delete'),
    
    # News Article Raw URLs
    path('news-article-raw-urls/', views.news_article_raw_urls_list, name='news_article_raw_urls_list'),
    path('news-article-raw-urls/create/', views.news_article_raw_url_create, name='news_article_raw_url_create'),
    path('news-article-raw-urls/<int:pk>/edit/', views.news_article_raw_url_edit, name='news_article_raw_url_edit'),
    path('news-article-raw-urls/<int:pk>/delete/', views.news_article_raw_url_delete, name='news_article_raw_url_delete'),
    
    # News Article Clean URLs
    path('news-article-clean-urls/', views.news_article_clean_urls_list, name='news_article_clean_urls_list'),
    path('news-article-clean-urls/create/', views.news_article_clean_url_create, name='news_article_clean_url_create'),
    path('news-article-clean-urls/<int:pk>/edit/', views.news_article_clean_url_edit, name='news_article_clean_url_edit'),
    path('news-article-clean-urls/<int:pk>/delete/', views.news_article_clean_url_delete, name='news_article_clean_url_delete'),
    
    # News Articles
    path('news-articles/', views.news_articles_list, name='news_articles_list'),
    path('news-articles/create/', views.news_article_create, name='news_article_create'),
    path('news-articles/<int:pk>/edit/', views.news_article_edit, name='news_article_edit'),
    path('news-articles/<int:pk>/delete/', views.news_article_delete, name='news_article_delete'),
    
    # Item Selectors
    path('selectors/', views.selectors_list, name='selectors_list'),
    path('selectors/create/', views.selector_create, name='selector_create'),
    path('selectors/<int:pk>/edit/', views.selector_edit, name='selector_edit'),
    path('selectors/<int:pk>/delete/', views.selector_delete, name='selector_delete'),
    
    # Crawler Configs
    path('crawler-configs/', views.crawler_configs_list, name='crawler_configs_list'),
    path('crawler-configs/create/', views.crawler_config_create, name='crawler_config_create'),
    path('crawler-configs/<int:pk>/edit/', views.crawler_config_edit, name='crawler_config_edit'),
    path('crawler-configs/<int:pk>/delete/', views.crawler_config_delete, name='crawler_config_delete'),
    path('crawler-configs/<int:pk>/seed-urls/', views.crawler_config_seed_urls, name='crawler_config_seed_urls'),
    
    # Scraper Configs
    path('scraper-configs/', views.scraper_configs_list, name='scraper_configs_list'),
    path('scraper-configs/create/', views.scraper_config_create, name='scraper_config_create'),
    path('scraper-configs/<int:pk>/edit/', views.scraper_config_edit, name='scraper_config_edit'),
    path('scraper-configs/<int:pk>/delete/', views.scraper_config_delete, name='scraper_config_delete'),
    
    # Seed URLs
    path('seed-urls/', views.seed_urls_list, name='seed_urls_list'),
    path('seed-urls/create/', views.seed_url_create, name='seed_url_create'),
    path('seed-urls/<int:pk>/edit/', views.seed_url_edit, name='seed_url_edit'),
    path('seed-urls/<int:pk>/delete/', views.seed_url_delete, name='seed_url_delete'),
    
    # AJAX endpoints
    path('ajax/get-portal-selectors/', views.get_portal_selectors, name='get_portal_selectors'),
    path('ajax/get-portal-raw-urls/', views.get_portal_raw_urls, name='get_portal_raw_urls'),
] 