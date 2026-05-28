"""
Root URL configuration — Phase 1
"""
from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('timetable_app.urls')),
]
