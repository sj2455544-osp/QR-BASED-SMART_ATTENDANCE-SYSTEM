# config/urls.py
from django.contrib import admin
from django.urls import path, include
from attendance.views import home_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', home_view, name='home'),
    path('attendance/', include('attendance.urls')),
    
    path('accounts/', include('accounts.urls')), 
]