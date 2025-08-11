# Utilise l'image de base Apify avec Python
FROM apify/actor-python:3.11

# Définit le répertoire de travail
WORKDIR /usr/src/app

# Copie les fichiers de requirements en premier pour optimiser le cache Docker
COPY requirements.txt ./

# Met à jour pip et installe les dépendances Python
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Installe les dépendances système nécessaires pour le web scraping
RUN apt-get update \
    && apt-get install -y \
        wget \
        gnupg \
        unzip \
        curl \
        xvfb \
        libxi6 \
        libgconf-2-4 \
        default-jdk \
        fonts-liberation \
        libappindicator3-1 \
        libasound2 \
        libatk-bridge2.0-0 \
        libdrm2 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxrandr2 \
        xdg-utils \
        libu2f-udev \
        libvulkan1 \
    && rm -rf /var/lib/apt/lists/*

# Installe Google Chrome pour Selenium
RUN wget -q -O - https://dl-ssl.google.com/linux/linux_signing_key.pub | apt-key add - \
    && echo "deb [arch=amd64] http://dl.google.com/linux/chrome/deb/ stable main" >> /etc/apt/sources.list.d/google.list \
    && apt-get update \
    && apt-get install -y google-chrome-stable \
    && rm -rf /var/lib/apt/lists/*

# Installe ChromeDriver
RUN CHROMEDRIVER_VERSION=`curl -sS chromedriver.storage.googleapis.com/LATEST_RELEASE` \
    && mkdir -p /opt/chromedriver-$CHROMEDRIVER_VERSION \
    && curl -sS -o /tmp/chromedriver_linux64.zip http://chromedriver.storage.googleapis.com/$CHROMEDRIVER_VERSION/chromedriver_linux64.zip \
    && unzip -qq /tmp/chromedriver_linux64.zip -d /opt/chromedriver-$CHROMEDRIVER_VERSION \
    && rm /tmp/chromedriver_linux64.zip \
    && chmod +x /opt/chromedriver-$CHROMEDRIVER_VERSION/chromedriver \
    && ln -fs /opt/chromedriver-$CHROMEDRIVER_VERSION/chromedriver /usr/local/bin/chromedriver

# Installe Playwright et ses navigateurs
RUN playwright install --with-deps chromium firefox webkit

# Copie le code source
COPY . ./

# Crée les répertoires nécessaires
RUN mkdir -p /usr/src/app/storage \
    && mkdir -p /usr/src/app/logs \
    && mkdir -p /usr/src/app/cache

# Définit les permissions appropriées
RUN chmod +x /usr/src/app/main.py

# Variables d'environnement pour optimiser les performances
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
ENV APIFY_HEADLESS=1
ENV APIFY_XVFB=1

# Variables d'environnement pour Chrome
ENV CHROME_BIN=/usr/bin/google-chrome
ENV CHROME_PATH=/usr/bin/google-chrome
ENV CHROMIUM_PATH=/usr/bin/google-chrome
ENV GOOGLE_CHROME_BIN=/usr/bin/google-chrome

# Variables d'environnement pour les scrapers
ENV DEFAULT_REQUEST_DELAY=1
ENV MAX_RETRIES=3
ENV TIMEOUT_SECONDS=30
ENV USE_PROXY=true
ENV LOG_LEVEL=INFO

# Expose le port pour les métriques (optionnel)
EXPOSE 8080

# Commande par défaut pour exécuter l'acteur
CMD ["python", "main.py"]

# Labels pour la documentation
LABEL maintainer="Apify Community"
LABEL description="Multi-platform e-commerce scraper for Amazon, eBay, Walmart, Etsy, and Shopify"
LABEL version="2.0.0"
LABEL apify.actor_type="scraper"
LABEL apify.categories="[\"E-COMMERCE\", \"BUSINESS_INTELLIGENCE\", \"PRICE_MONITORING\"]"