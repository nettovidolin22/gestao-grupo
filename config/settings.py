"""
Configurações do projeto.

Os valores sensíveis (chave secreta, banco de dados) vêm do arquivo .env
ou de variáveis de ambiente. Veja o .env.example.
"""

import os
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

# DEBUG só liga quando o .env pede (DEBUG=1). Sem ele, o sistema roda no modo seguro.
DEBUG = os.environ.get("DEBUG", "0") == "1"
SECRET_KEY = os.environ.get("SECRET_KEY", "")
if not DEBUG and (len(SECRET_KEY) < 50 or SECRET_KEY.startswith("troque")):
    raise ImproperlyConfigured(
        "Defina uma SECRET_KEY longa e aleatória (50+ caracteres) no ambiente de produção."
    )
if not SECRET_KEY:
    SECRET_KEY = "dev-inseguro-so-para-o-computador-local"
ALLOWED_HOSTS = [h for h in os.environ.get("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",") if h]
CSRF_TRUSTED_ORIGINS = [o for o in os.environ.get("CSRF_TRUSTED_ORIGINS", "").split(",") if o]

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "organizacao",
    "quadros",
    "notificacoes",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "config.middleware.LimiteTamanhoRequisicao",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "notificacoes.context_processors.nao_lidas",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Sem DATABASE_URL usa SQLite local; em produção aponte para o Supabase.
DATABASES = {
    "default": dj_database_url.config(
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
        conn_max_age=600,
    )
}

AUTH_USER_MODEL = "organizacao.Usuario"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "pt-br"
TIME_ZONE = "America/Sao_Paulo"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedStaticFilesStorage"},
}

# Arquivos enviados (anexos). Só são baixados pela view que confere o acesso.
MEDIA_ROOT = Path(os.environ.get("MEDIA_ROOT", BASE_DIR / "media"))
TAMANHO_MAXIMO_ANEXO = 10 * 1024 * 1024  # 10 MB
# Requisições maiores que isto são recusadas antes de o arquivo ser gravado no disco.
TAMANHO_MAXIMO_REQUISICAO = TAMANHO_MAXIMO_ANEXO + 1024 * 1024

# Endereço do sistema, usado nos links dos e-mails.
SITE_URL = os.environ.get("SITE_URL", "http://127.0.0.1:8000")

# E-mail: sem EMAIL_HOST, os e-mails aparecem no terminal (bom para testar).
if os.environ.get("EMAIL_HOST"):
    EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
    EMAIL_HOST = os.environ["EMAIL_HOST"]
    EMAIL_PORT = int(os.environ.get("EMAIL_PORT", "587"))
    EMAIL_HOST_USER = os.environ.get("EMAIL_HOST_USER", "")
    EMAIL_HOST_PASSWORD = os.environ.get("EMAIL_HOST_PASSWORD", "")
    EMAIL_USE_TLS = os.environ.get("EMAIL_USE_TLS", "1") == "1"
else:
    EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"
DEFAULT_FROM_EMAIL = os.environ.get("DEFAULT_FROM_EMAIL", "Gestão do Grupo <nao-responda@localhost>")

# Bloqueio de login: depois de 5 senhas erradas, o usuário espera 15 minutos.
LOGIN_TENTATIVAS_MAXIMAS = 5
LOGIN_BLOQUEIO_SEGUNDOS = 15 * 60

# Sessão expira após 12 horas sem uso.
SESSION_COOKIE_AGE = 12 * 60 * 60
SESSION_SAVE_EVERY_REQUEST = True
CSRF_COOKIE_HTTPONLY = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
X_FRAME_OPTIONS = "DENY"

# Domínios de e-mail aceitos no cadastro de usuários (os das empresas do grupo).
DOMINIOS_EMAIL = [
    d.strip().lower()
    for d in os.environ.get("DOMINIOS_EMAIL", "gencau.com,balaiolab.com,titan.ind.br").split(",")
    if d.strip()
]

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "painel"
LOGOUT_REDIRECT_URL = "login"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

if not DEBUG:
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_SSL_REDIRECT = os.environ.get("SECURE_SSL_REDIRECT", "1") == "1"
    # HSTS: o navegador passa a só aceitar HTTPS. Comece com 1 dia e aumente depois.
    SECURE_HSTS_SECONDS = int(os.environ.get("SECURE_HSTS_SECONDS", "86400"))
