from django.core.validators import URLValidator
from django.db import models

# Create your models here.
        
# Don't remove this mark
### ### Below code is Generated ### ###

class RefundedChoices(models.TextChoices):
	YES = 'YES', 'Yes'
	NO = 'NO', 'No'

class CurrencyChoices(models.TextChoices):
	USD = 'USD', 'USD'
	EUR = 'EUR', 'EUR'
	
class Sales(models.Model):
	ID = models.AutoField(primary_key=True)
	Product = models.TextField(blank=True, null=True)
	BuyerEmail = models.EmailField(blank=True, null=True)
	PurchaseDate = models.DateField(blank=True, null=True)
	Country = models.TextField(blank=True, null=True)
	Price = models.FloatField(blank=True, null=True)
	Refunded = models.CharField(max_length=20, choices=RefundedChoices.choices, default=RefundedChoices.NO)
	Currency = models.CharField(max_length=10, choices=CurrencyChoices.choices, default=CurrencyChoices.USD)
	Quantity = models.IntegerField(blank=True, null=True)




# This will be implementation of online media crawling system on top of Rocket Django App Templates

from django_countries.fields import CountryField


class TimestampModel(models.Model):
	created_at = models.DateTimeField(auto_now_add=True)
	updated_at = models.DateTimeField(auto_now=True)

	class Meta:
		abstract = True

class NewsScopeChoices(models.TextChoices):
	NATIONAL = 'national', 'National'
	INTERNATIONAL = 'international', 'International'
	REGIONAL = 'regional', 'Regional'

class NewsPortal(TimestampModel):
	domain = models.CharField(max_length=255, unique=True)
	name = models.CharField(max_length=255)
	news_scope = models.CharField(
		max_length=20, 
		choices=NewsScopeChoices.choices,
		default=NewsScopeChoices.NATIONAL
	)
	country = CountryField(blank_label='Select country', default='ID', null=True, blank=True)
	city = models.CharField(max_length=255, blank=True, null=True)

	class Meta:
		db_table = 'news_portal'
		verbose_name = 'News Portal'
		verbose_name_plural = 'News Portals'
		ordering = ['name']

	def __str__(self):
		return self.name

class NewsArticleUrlStatusChoices(models.TextChoices):
	PENDING = 'pending', 'Pending'
	RUNNING = 'running', 'Running'
	COMPLETED = 'completed', 'Completed'
	FAILED = 'failed', 'Failed'

class NewsArticleRawUrl(TimestampModel):
	url = models.URLField(unique=True)
	portal = models.ForeignKey(NewsPortal, on_delete=models.CASCADE, related_name='raw_urls')
	status = models.CharField(
		max_length=20, 
		choices=NewsArticleUrlStatusChoices.choices, 
		default=NewsArticleUrlStatusChoices.PENDING,
		db_index=True
	)

	class Meta:
		db_table = 'news_article_url_raw'
		ordering = ['-created_at']

	def __str__(self):
		return self.url

class NewsArticleCleanUrl(TimestampModel):
	url = models.URLField(unique=True)
	article_url_raw = models.OneToOneField(NewsArticleRawUrl, on_delete=models.CASCADE)
	portal = models.ForeignKey(NewsPortal, on_delete=models.CASCADE, related_name='clean_urls')
	status = models.CharField(
		max_length=20, 
		choices=NewsArticleUrlStatusChoices.choices, 
		default=NewsArticleUrlStatusChoices.PENDING,
		db_index=True
	)

	class Meta:
		db_table = 'news_article_url_clean'
		ordering = ['-created_at']

	def __str__(self):
		return self.url

class NewsArticleAuthor(models.Model):
	name = models.CharField(max_length=255, db_index=True)

	class Meta:
		db_table = 'news_article_author'
		ordering = ['name']

	def __str__(self):
		return self.name

class NewsArticleImage(models.Model):
	image_url = models.URLField(db_index=True)

	class Meta:
		db_table = 'news_article_image'
		ordering = ['image_url']

	def __str__(self):
		return self.image_url

class NewsArticle(TimestampModel):
	article_url = models.OneToOneField(NewsArticleCleanUrl, on_delete=models.CASCADE)
	title = models.CharField(max_length=255, blank=False, null=False, db_index=True)
	body = models.TextField(blank=False, null=False)
	description = models.TextField(blank=True, null=True)
	images = models.ManyToManyField(NewsArticleImage, blank=True)
	authors = models.ManyToManyField(NewsArticleAuthor, blank=True)
	published_at = models.DateTimeField(db_index=True)
	language = models.CharField(max_length=2, blank=True, null=True)
	
	class Meta:
		db_table = 'news_article'
		ordering = ['-published_at']

	def __str__(self):
		return self.title
	
class NewsPortalSeedUrl(TimestampModel):
	url = models.URLField(unique=True)
	portal = models.ForeignKey(NewsPortal, on_delete=models.CASCADE, related_name='seed_urls')
	
	class Meta:
		db_table = 'news_portal_seed_url'
		ordering = ['-created_at']

	def __str__(self):
		return self.url

class ItemChoices(models.TextChoices):
	URL_LIST = 'url_list', 'URL List'
	TITLE = 'title', 'Title'
	BODY = 'body', 'Body'
	DESCRIPTION = 'description', 'Description'
	IMAGES = 'images', 'Images'
	AUTHORS = 'authors', 'Authors'
	PUBLISHED_AT = 'published_at', 'Published At'
	LANGUAGE = 'language', 'Language'

class SelectorMethodChoices(models.TextChoices):
	CSS = 'css', 'CSS'
	XPATH = 'xpath', 'XPath'
	REGEX = 'regex', 'Regex'


class ItemSelector(TimestampModel):
	portal = models.ForeignKey(NewsPortal, on_delete=models.CASCADE, related_name='item_selectors')
	query = models.CharField(max_length=255, db_index=True)
	item = models.CharField(max_length=20, choices=ItemChoices.choices, default=ItemChoices.URL_LIST)
	method = models.CharField(max_length=20, choices=SelectorMethodChoices.choices, default=SelectorMethodChoices.CSS)

	class Meta:
		db_table = 'news_article_selector'
		ordering = ['-created_at']

	def __str__(self):
		return self.query


class CrawlerConfig(TimestampModel):
	name = models.CharField(max_length=255, db_index=True)
	portal = models.ForeignKey(NewsPortal, on_delete=models.CASCADE, related_name='crawler_configs')
	item_selector = models.ForeignKey(ItemSelector, on_delete=models.CASCADE, related_name='crawler_configs')
	custom_settings = models.JSONField(default=dict)

	class Meta:
		db_table = 'news_crawler_config'
		ordering = ['-created_at']

	def __str__(self):
		return self.name


class CrawlerTaskStatusChoices(models.TextChoices):
	PENDING = 'pending', 'Pending'
	RUNNING = 'running', 'Running'
	COMPLETED = 'completed', 'Completed'
	FAILED = 'failed', 'Failed'
	CANCELLED = 'cancelled', 'Cancelled'


class CrawlerTask(TimestampModel):
	crawler_config = models.ForeignKey(CrawlerConfig, on_delete=models.CASCADE, related_name='tasks')
	status = models.CharField(max_length=20, choices=CrawlerTaskStatusChoices.choices, default=CrawlerTaskStatusChoices.PENDING)
	scrapyd_job_id = models.CharField(max_length=255, blank=True, null=True)
	error_message = models.TextField(blank=True, null=True)
	started_at = models.DateTimeField(blank=True, null=True)
	completed_at = models.DateTimeField(blank=True, null=True)
	execution_time = models.DurationField(blank=True, null=True)
	
	class Meta:
		db_table = 'news_crawler_task'
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.crawler_config.name} - {self.status}"


class CrawlerScheduledTask(TimestampModel):
	crawler_config = models.ForeignKey(CrawlerConfig, on_delete=models.CASCADE, related_name='scheduled_tasks')
	name = models.CharField(max_length=255, db_index=True)
	description = models.TextField(blank=True, null=True)
	cron_expression = models.CharField(max_length=255, help_text="Cron expression (e.g., '0 0 * * *' for daily at midnight)")
	is_active = models.BooleanField(default=True)
	last_run = models.DateTimeField(blank=True, null=True)
	next_run = models.DateTimeField(blank=True, null=True)
	
	class Meta:
		db_table = 'news_crawler_scheduled_task'
		ordering = ['-created_at']

	def __str__(self):
		return f"{self.name} - {self.crawler_config.name}"


class ScraperConfig(TimestampModel):
	name = models.CharField(max_length=255, db_index=True)
	portal = models.ForeignKey(NewsPortal, on_delete=models.CASCADE, related_name='scraper_configs')
	item_selector = models.ForeignKey(ItemSelector, on_delete=models.CASCADE, related_name='scraper_configs')
	custom_settings = models.JSONField(default=dict)

	class Meta:
		db_table = 'news_scraper_config'
		ordering = ['-created_at']

	def __str__(self):
		return self.name


	
	
	
	
	
	
	
	
	
	
	
	
	
	





