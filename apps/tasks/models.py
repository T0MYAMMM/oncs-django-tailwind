from django.db import models
from django.utils import timezone


class ScrapydServer(models.Model):
    name = models.CharField(max_length=100, help_text="Friendly name, e.g., Production Node")
    host = models.CharField(max_length=255, help_text="Hostname or IP, e.g., 159.223.85.244 or localhost")
    port = models.PositiveIntegerField(default=6800)
    is_active = models.BooleanField(default=True)
    use_https = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'scrapyd_server'
        ordering = ['-is_active', 'name']

    def __str__(self) -> str:
        scheme = 'https' if self.use_https else 'http'
        return f"{self.name} ({scheme}://{self.host}:{self.port})"

    @property
    def base_url(self) -> str:
        scheme = 'https' if self.use_https else 'http'
        return f"{scheme}://{self.host}:{self.port}"

