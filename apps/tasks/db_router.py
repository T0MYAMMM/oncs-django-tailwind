"""
Database router for the tasks app to handle multiple databases.
This router directs Scrapyd-related models to the scrapyd_tracking database
while keeping other models in the default database.
"""

import os
from django.conf import settings


class ScrapydRouter:
    """
    Database router for Scrapyd-related models.
    
    Routes ScrapydDeployment, ScrapydTask, ScrapydTaskQueue, and ScrapydHealthLog
    to the scrapyd_tracking database, while keeping other models in the default database.
    """
    
    # Models that should use the scrapyd_tracking database
    SCRAPYD_MODELS = {
        'ScrapydDeployment',
        'ScrapydTask', 
        'ScrapydTaskQueue',
        'ScrapydHealthLog'
    }
    
    # Legacy models that stay in the default database
    LEGACY_MODELS = {
        'ScrapydServer'
    }
    
    def db_for_read(self, model, **hints):
        """Suggest the database to use for reads of a model."""
        if model._meta.model_name in self.SCRAPYD_MODELS:
            return 'scrapyd_tracking'
        return 'default'
    
    def db_for_write(self, model, **hints):
        """Suggest the database to use for writes of a model."""
        if model._meta.model_name in self.SCRAPYD_MODELS:
            return 'scrapyd_tracking'
        return 'default'
    
    def allow_relation(self, obj1, obj2, **hints):
        """Allow any relation if a model is in the scrapyd_tracking database."""
        if (obj1._meta.model_name in self.SCRAPYD_MODELS or 
            obj2._meta.model_name in self.SCRAPYD_MODELS):
            return True
        return None
    
    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the scrapyd_tracking models only appear in the scrapyd_tracking database.
        """
        if model_name in self.SCRAPYD_MODELS:
            return db == 'scrapyd_tracking'
        elif model_name in self.LEGACY_MODELS:
            return db == 'default'
        return None
    
    def allow_join(self, lhs_table, rhs_table, **hints):
        """Allow joins between tables in the same database."""
        # This is a simplified approach - in practice, you might need more complex logic
        return True


class ScrapydDatabaseConfig:
    """
    Configuration helper for the scrapyd_tracking database.
    """
    
    @staticmethod
    def get_database_config():
        """
        Get the database configuration for scrapyd_tracking.
        Falls back to environment variables or defaults.
        """
        # Try to get from Django settings first
        if hasattr(settings, 'DATABASES') and 'scrapyd_tracking' in settings.DATABASES:
            return settings.DATABASES['scrapyd_tracking']
        
        # Fall back to environment variables
        db_engine = os.getenv('SCRAPYD_DB_ENGINE', 'postgresql')
        db_name = os.getenv('SCRAPYD_DB_NAME', 'scrapyd_tracking')
        db_user = os.getenv('SCRAPYD_DB_USER', 'scrapyd_admin')
        db_pass = os.getenv('SCRAPYD_DB_PASS', '')
        db_host = os.getenv('SCRAPYD_DB_HOST', 'localhost')
        db_port = os.getenv('SCRAPYD_DB_PORT', '5432')
        
        if db_engine == 'postgresql':
            return {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': db_name,
                'USER': db_user,
                'PASSWORD': db_pass,
                'HOST': db_host,
                'PORT': db_port,
                'OPTIONS': {
                    'sslmode': 'prefer',
                },
            }
        elif db_engine == 'sqlite3':
            return {
                'ENGINE': 'django.db.backends.sqlite3',
                'NAME': db_name if db_name.endswith('.db') else f'{db_name}.db',
            }
        else:
            # Default to PostgreSQL
            return {
                'ENGINE': 'django.db.backends.postgresql',
                'NAME': db_name,
                'USER': db_user,
                'PASSWORD': db_pass,
                'HOST': db_host,
                'PORT': db_port,
            }
    
    @staticmethod
    def get_connection_string():
        """Get the database connection string for scrapyd_tracking."""
        config = ScrapydDatabaseConfig.get_database_config()
        
        if config['ENGINE'] == 'django.db.backends.postgresql':
            return f"postgresql://{config['USER']}:{config['PASSWORD']}@{config['HOST']}:{config['PORT']}/{config['NAME']}"
        elif config['ENGINE'] == 'django.db.backends.sqlite3':
            return config['NAME']
        else:
            return None
