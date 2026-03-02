# Create directories and __init__.py files for all apps
import os

apps = [
    'accounts', 'tracks', 'albums', 'commerce', 'payments', 
    'social', 'rewards', 'downloads', 'admin_panel', 'analytics'
]

basedir = r'd:\mixmint2.0\apps'
os.makedirs(basedir, exist_ok=True)
with open(os.path.join(basedir, '__init__.py'), 'w') as f: pass

for app in apps:
    app_dir = os.path.join(basedir, app)
    os.makedirs(app_dir, exist_ok=True)
    with open(os.path.join(app_dir, '__init__.py'), 'w') as f: pass
    with open(os.path.join(app_dir, 'models.py'), 'w') as f: pass
    with open(os.path.join(app_dir, 'urls.py'), 'w') as f: 
        f.write("from django.urls import path\n\nurlpatterns = []\n")
    with open(os.path.join(app_dir, 'views.py'), 'w') as f: pass
    with open(os.path.join(app_dir, 'serializers.py'), 'w') as f: pass
    with open(os.path.join(app_dir, 'admin.py'), 'w') as f:
        f.write("from django.contrib import admin\n")
