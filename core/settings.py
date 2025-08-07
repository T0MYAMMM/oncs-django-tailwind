import os, random, string
from pathlib        import Path
from dotenv         import load_dotenv
from str2bool       import str2bool 
from django.contrib import messages
from django.utils.translation import gettext_lazy as _

load_dotenv()  # take environment variables from .env.

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/4.2/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.environ.get('SECRET_KEY')
if not SECRET_KEY:
    SECRET_KEY = ''.join(random.choice( string.ascii_lowercase  ) for i in range( 32 ))

# Enable/Disable DEBUG Mode
DEBUG = str2bool(os.environ.get('DEBUG'))
#print(' DEBUG -> ' + str(DEBUG) ) 

# Hosts Settings
ALLOWED_HOSTS = ['*']
CSRF_TRUSTED_ORIGINS = ['http://localhost:8000', 'http://localhost:5085', 'http://127.0.0.1:8000', 'http://127.0.0.1:5085']

# Used by DEBUG-Toolbar 
INTERNAL_IPS = [
    "127.0.0.1",
]

# Application definition

INSTALLED_APPS = [
    "webpack_loader",
    "frontend",

    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.sites",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "home",
    "apps.common",
    "apps.users",
    "apps.api",
    "apps.charts", 
    "apps.tables",
    "apps.tasks",
    "apps.payments",
    "apps.file_manager",
    "apps.react",

    "django_celery_results",

    'rest_framework',
    'rest_framework.authtoken', 
    'drf_spectacular',
    'django_api_gen',

    "debug_toolbar",

    # allauth apps
    'allauth',
    'allauth.account',
    'allauth.socialaccount',
    'allauth.socialaccount.providers.github',
    'allauth.socialaccount.providers.google',

    'django_extensions',
    'django_countries',

]

WEBPACK_LOADER = {
    "DEFAULT": {
        "BUNDLE_DIR_NAME": "frontend/",
        "STATS_FILE": os.path.join(BASE_DIR, "webpack-stats.json"),
    }
} 

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "debug_toolbar.middleware.DebugToolbarMiddleware",

    "allauth.account.middleware.AccountMiddleware",
    # "wagtail.contrib.redirects.middleware.RedirectMiddleware",

    

]

ROOT_URLCONF = "core.urls"

UI_TEMPLATES = os.path.join(BASE_DIR, 'templates') 

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [UI_TEMPLATES],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.sidebar_config",
            ],
        },
    },
]

WSGI_APPLICATION = "core.wsgi.application"


# Sidebar configuration
SIDEBAR_CONFIG = {
    'SHOW_APPS': True,
    'SHOW_LAYOUTS': False,
    'SHOW_CRUD': True,
    'SHOW_PAGES': False,
    'SHOW_PLAYGROUND': False,
    'SHOW_SETTINGS': True,
    'SHOW_STARTER': False,
    'SHOW_I18N': False,
    'SHOW_DOWNLOAD': False,
    'SHOW_DOCUMENTATION': False,
    'SHOW_SUPPORT': False,
    
    # Individual page visibility
    'SHOW_APPS_DATATABLES': True,
    'SHOW_APPS_CHARTS': True,
    'SHOW_APPS_REACT_CHARTS': True,
    'SHOW_APPS_FILE_MANAGER': True,
    'SHOW_APPS_API': True,
    'SHOW_APPS_TASKS': True,

    'SHOW_LAYOUTS_STACKED': False,
    'SHOW_LAYOUTS_SIDEBAR': False,

    'SHOW_CRUD_PRODUCTS': True,
    'SHOW_CRUD_USERS': True,
    'SHOW_CRUD_NEWS_PORTALS': True,
    'SHOW_CRUD_NEWS_ARTICLES': True,
    'SHOW_CRUD_SELECTORS': True,
    'SHOW_CRUD_CRAWLER_CONFIGS': True,
    'SHOW_CRUD_SCRAPER_CONFIGS': True,

    'SHOW_PLAYGROUND_STACKED': False,
    'SHOW_PLAYGROUND_SIDEBAR': False,


}

# Database
# https://docs.djangoproject.com/en/4.2/ref/settings/#databases

DB_ENGINE   = os.getenv('DB_ENGINE'   , None)
DB_USERNAME = os.getenv('DB_USERNAME' , None)
DB_PASS     = os.getenv('DB_PASS'     , None)
DB_HOST     = os.getenv('DB_HOST'     , None)
DB_PORT     = os.getenv('DB_PORT'     , None)
DB_NAME     = os.getenv('DB_NAME'     , None)

if DB_ENGINE and DB_NAME and DB_USERNAME:
    DATABASES = { 
      'default': {
        'ENGINE'  : 'django.db.backends.' + DB_ENGINE, 
        'NAME'    : DB_NAME,
        'USER'    : DB_USERNAME,
        'PASSWORD': DB_PASS,
        'HOST'    : DB_HOST,
        'PORT'    : DB_PORT,
        }, 
    }
else:
    DATABASES = {
        'default': {
            'ENGINE': 'django.db.backends.sqlite3',
            'NAME': 'db.sqlite3',
        }
    }


# Password validation
# https://docs.djangoproject.com/en/4.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]


# Internationalization
# https://docs.djangoproject.com/en/4.2/topics/i18n/

LANGUAGES = [
    ('en', _('English (US)')),
    ('de', _('Deutsch')),
    ('it', _('Italiano')),
]


LANGUAGE_CODE = "en-us"

TIME_ZONE = "UTC"

USE_I18N = True

USE_TZ = True

USE_L10N = True

LOCALE_PATHS = [
    os.path.join(BASE_DIR, 'locale'),
]


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/4.2/howto/static-files/

STATIC_URL  = "/static/"
STATIC_ROOT = os.path.join(BASE_DIR, 'staticfiles')

STATICFILES_DIRS = (
    os.path.join(BASE_DIR, 'static'),
)

MEDIA_URL = 'media/'
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')

# Default primary key field type
# https://docs.djangoproject.com/en/4.2/ref/settings/#default-auto-field

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# All auth
AUTHENTICATION_BACKENDS = [
    # Needed to login by username in Django admin, regardless of `allauth`
    'django.contrib.auth.backends.ModelBackend',
    # `allauth` specific authentication methods, such as login by email
    'allauth.account.auth_backends.AuthenticationBackend',
]

# allauth config
ACCOUNT_EMAIL_VERIFICATION =  os.getenv("ACCOUNT_EMAIL_VERIFICATION", "optional")
ACCOUNT_EMAIL_REQUIRED = True
ACCOUNT_AUTHENTICATION_METHOD = 'email'
ACCOUNT_USERNAME_REQUIRED = False
ACCOUNT_CONFIRM_EMAIL_ON_GET = True
ACCOUNT_LOGIN_ON_EMAIL_CONFIRMATION = True
# SOCIALACCOUNT_LOGIN_ON_GET=True
ACCOUNT_UNIQUE_EMAIL = True
LOGIN_REDIRECT_URL = "/"



# ### Async Tasks (Celery) Settings ###

CELERY_SCRIPTS_DIR        = os.path.join(BASE_DIR, "tasks_scripts" )

CELERY_LOGS_URL           = "/tasks_logs/"
CELERY_LOGS_DIR           = os.path.join(BASE_DIR, "tasks_logs"    )

CELERY_BROKER_URL         = os.environ.get("CELERY_BROKER", "redis://redis:6379")
CELERY_RESULT_BACKEND     = os.environ.get("CELERY_BROKER", "redis://redis:6379")

CELERY_TASK_TRACK_STARTED = True
CELERY_TASK_TIME_LIMIT    = 30 * 60
CELERY_CACHE_BACKEND      = "django-cache"
CELERY_RESULT_BACKEND     = "django-db"
CELERY_RESULT_EXTENDED    = True
CELERY_RESULT_EXPIRES     = 60*60*24*30 # Results expire after 1 month
CELERY_ACCEPT_CONTENT     = ["json"]
CELERY_TASK_SERIALIZER    = 'json'
CELERY_RESULT_SERIALIZER  = 'json'
########################################


LOGIN_REDIRECT_URL = '/'
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ### API-GENERATOR Settings ###
API_GENERATOR = {
    'sales'   : "apps.common.models.Sales",
}

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticated',
    ],
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
}
########################################

# risky
SESSION_COOKIE_HTTPONLY=False

MESSAGE_TAGS = {
    messages.INFO: 'text-blue-800 border border-blue-300 bg-blue-50 dark:text-blue-400 dark:border-blue-800',
    messages.SUCCESS: 'text-green-800 border border-green-300 bg-green-50 dark:text-green-400 dark:border-green-800',
    messages.WARNING: 'text-yellow-800 border border-yellow-300 bg-yellow-50 dark:text-yellow-300 dark:border-yellow-800',
    messages.ERROR: 'text-red-800 border border-red-300 bg-red-50 dark:text-red-400 dark:border-red-800',
}

SITE_ID = 1

GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_SECRET_KEY = os.getenv("GOOGLE_SECRET_KEY", "")

GITHUB_CLIENT_ID = os.getenv("GITHUB_CLIENT_ID", "")
GITHUB_SECRET_KEY = os.getenv("GITHUB_SECRET_KEY", "")


SOCIALACCOUNT_PROVIDERS = {
    'google': {
        "APP": {
            "client_id": GOOGLE_CLIENT_ID,
            "secret": GOOGLE_SECRET_KEY,
        },
    },
    'github': {
        "APP": {
            "client_id": GITHUB_CLIENT_ID,
            "secret": GITHUB_SECRET_KEY,
        },
    },
}

# Stripe
STRIPE_SECRET_KEY      = os.getenv("STRIPE_SECRET_KEY", None)
STRIPE_PUBLISHABLE_KEY = os.getenv("STRIPE_PUBLISHABLE_KEY", None)
DOMAIN_URL             = os.getenv("DOMAIN_URL", "http://127.0.0.1:8000/")

STRIPE_IS_ACTIVE = False
if STRIPE_SECRET_KEY and STRIPE_PUBLISHABLE_KEY:
    STRIPE_IS_ACTIVE = True


# Sentry
if os.getenv('DSN_KEY') and not DEBUG:
    import sentry_sdk
    sentry_sdk.init(
        dsn=os.getenv('DSN_KEY'),
        # Set traces_sample_rate to 1.0 to capture 100%
        # of transactions for performance monitoring.
        traces_sample_rate=1.0,
        # Set profiles_sample_rate to 1.0 to profile 100%
        # of sampled transactions.
        # We recommend adjusting this value in production.
        profiles_sample_rate=1.0,
    )


X_FRAME_OPTIONS = 'SAMEORIGIN'