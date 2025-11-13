from django.contrib import admin
from django.urls import path, include

from myApp import adminpanel

app_name = "adminpanel"

adminpanel_patterns = ([
    path("login/", adminpanel.admin_login, name="login"),
    path("logout/", adminpanel.admin_logout, name="logout"),
    path("dashboard/", adminpanel.admin_dashboard, name="dashboard"),
    path("export.csv", adminpanel.admin_export_csv, name="export_csv"),
], "adminpanel")

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("admin-/", include(adminpanel_patterns)),
    path("", include("myApp.urls")),
]