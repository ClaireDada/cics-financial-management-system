
import os
import sys
import dj_database_url
from pathlib import Path
from dotenv import load_dotenv

# ==========================================
# BASE DIRECTORY
# ==========================================

BASE_DIR = Path(__file__).resolve().parent.parent

# Load environment variables
load_dotenv(BASE_DIR / ".env")


# ==========================================
# SECURITY SETTINGS
# ==========================================

SECRET_KEY = os.getenv(
    "DJANGO_SECRET_KEY",
    "django-insecure-development-key-change-before-deployment"
)

DEBUG = True

ALLOWED_HOSTS = ["localhost", "127.0.0.1", "testserver", "*"]

CSRF_TRUSTED_ORIGINS = ["https://*.vercel.app", "http://127.0.0.1", "http://localhost"]


# ==========================================
# INSTALLED APPLICATIONS
# ==========================================

INSTALLED_APPS = [
    "jazzmin",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    # Project applications
    "accounts",
    "students",
    "finance_collections",
    "finance_budget",
    "fund_management",
]


# ==========================================
# CUSTOM USER MODEL
# ==========================================

AUTH_USER_MODEL = "accounts.User"


# ==========================================
# MIDDLEWARE
# ==========================================

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]


# ==========================================
# URL CONFIGURATION
# ==========================================

ROOT_URLCONF = "config.urls"


# ==========================================
# HTML TEMPLATES
# ==========================================

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",

        # Main templates directory
        "DIRS": [BASE_DIR / "templates"],

        "APP_DIRS": True,

        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]


# ==========================================
# WSGI APPLICATION
# ==========================================

WSGI_APPLICATION = "config.wsgi.application"


# ==========================================
# DATABASE CONFIGURATION
# ==========================================

DATABASE_URL = os.getenv("DATABASE_URL")

if "test" in sys.argv:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": ":memory:",
        }
    }
elif DATABASE_URL:
    DATABASES = {
        "default": dj_database_url.config(
            default=DATABASE_URL,
            conn_max_age=600,
            ssl_require=True if "postgresql" in DATABASE_URL else False,
        )
    }
    if os.getenv("PGUSER"):
        DATABASES["default"]["USER"] = os.getenv("PGUSER")
    if os.getenv("PGPASSWORD"):
        DATABASES["default"]["PASSWORD"] = os.getenv("PGPASSWORD")
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }


# ==========================================
# PASSWORD VALIDATION
# ==========================================

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


# ==========================================
# INTERNATIONALIZATION
# ==========================================

LANGUAGE_CODE = "en-us"

TIME_ZONE = "Asia/Manila"

USE_I18N = True

USE_TZ = True


# ==========================================
# STATIC FILES (CSS, JAVASCRIPT, IMAGES)
# ==========================================

STATIC_URL = "/static/"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

STATIC_ROOT = BASE_DIR / "staticfiles"

STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedStaticFilesStorage",
    },
}


# ==========================================
# AUTHENTICATION REDIRECTS
# ==========================================

LOGIN_URL = "login"

LOGIN_REDIRECT_URL = "dashboard"

LOGOUT_REDIRECT_URL = "login"


# ==========================================
# DEFAULT PRIMARY KEY
# ==========================================

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# ==========================================
# JAZZMIN ADMIN SETTINGS
# ==========================================

JAZZMIN_SETTINGS = {
    # Title on the browser tab
    "site_title": "CICS Finance Admin",
    # Title on the login page and main admin header
    "site_header": "CICS SG Financial Administration",
    # Title on the admin index page
    "site_brand": "CICS SG",
    # Logo for the top-left (relative to static files)
    "site_logo": "images/cics_logo.png",
    "site_logo_classes": "img-circle elevation-3",
    "site_icon": "images/cics_logo.png",
    # Welcome text on the login screen
    "welcome_sign": "CICS Student Government â€” Financial Administration",
    # Copyright footer
    "copyright": "CICS Student Government, SJCBI",
    # Field names on user model that contain avatar image
    "user_avatar": None,
    # Top menu
    "topmenu_links": [
        {"name": "â† Return to Dashboard", "url": "/dashboard/", "new_window": False, "icon": "fas fa-home"},
        {"name": "User Management", "url": "/users/", "new_window": False, "icon": "fas fa-users"},
        {"name": "View Site", "url": "/", "new_window": False, "icon": "fas fa-eye"},
    ],
    # User menu (top right)
    "usermenu_links": [
        {"name": "Return to Dashboard", "url": "/dashboard/", "icon": "fas fa-tachometer-alt"},
    ],
    # Side menu
    "show_sidebar": True,
    "navigation_expanded": True,
    "hide_apps": [],
    "hide_models": [],
    # Custom links in sidebar
    "custom_links": {
        "accounts": [
            {
                "name": "Native User Management",
                "url": "/users/",
                "icon": "fas fa-users-cog",
            }
        ]
    },
    # Icons for apps and models
    "icons": {
        "auth": "fas fa-users-cog",
        "auth.user": "fas fa-user",
        "auth.Group": "fas fa-users",
        "accounts": "fas fa-id-badge",
        "accounts.User": "fas fa-user-circle",
        "accounts.Role": "fas fa-shield-alt",
        "students": "fas fa-graduation-cap",
        "students.Student": "fas fa-user-graduate",
        "students.FeeSetting": "fas fa-money-bill-wave",
        "students.SchoolYear": "fas fa-calendar-alt",
        "finance_collections": "fas fa-hand-holding-usd",
        "finance_collections.Collection": "fas fa-receipt",
        "finance_collections.Turnover": "fas fa-exchange-alt",
        "finance_collections.Campaign": "fas fa-bullhorn",
        "finance_budget": "fas fa-chart-pie",
        "finance_budget.Budget": "fas fa-coins",
        "finance_budget.BudgetItem": "fas fa-list-alt",
        "finance_budget.ExpenseCategory": "fas fa-tags",
        "fund_management": "fas fa-university",
        "fund_management.FundRequest": "fas fa-file-invoice-dollar",
        "fund_management.Disbursement": "fas fa-money-check-alt",
        "fund_management.Liquidation": "fas fa-clipboard-check",
        "fund_management.FundReturn": "fas fa-undo-alt",
        "fund_management.AuditLog": "fas fa-history",
    },
    # Default icon for missing ones
    "default_icon_parents": "fas fa-chevron-circle-right",
    "default_icon_children": "fas fa-circle",
    # Relative paths to custom CSS/JS (relative to static files root)
    "custom_css": "css/admin_custom.css",
    "custom_js": None,
    # Whether to show the UI builder
    "show_ui_builder": False,
    # Change view changer
    "changeform_format": "horizontal_tabs",
    "changeform_format_overrides": {
        "auth.user": "collapsible",
        "auth.group": "vertical_tabs",
    },
    "language_chooser": False,
}

JAZZMIN_UI_TWEAKS = {
    "navbar_small_text": False,
    "footer_small_text": False,
    "body_small_text": False,
    "brand_small_text": False,
    "brand_colour": False,
    "accent": "accent-primary",
    "navbar": "navbar-dark",
    "no_navbar_border": True,
    "navbar_fixed": False,
    "layout_boxed": False,
    "footer_fixed": False,
    "sidebar_fixed": True,
    "sidebar": "sidebar-dark-primary",
    "sidebar_nav_small_text": False,
    "sidebar_disable_expand": False,
    "sidebar_nav_child_indent": True,
    "sidebar_nav_compact_style": True,
    "sidebar_nav_legacy_style": False,
    "sidebar_nav_flat_style": False,
    "theme": "default",
    "dark_mode_theme": None,
    "button_classes": {
        "primary": "btn-primary",
        "secondary": "btn-secondary",
        "info": "btn-info",
        "warning": "btn-warning",
        "danger": "btn-danger",
        "success": "btn-success",
    },
    "actions_sticky_top": True,
}





