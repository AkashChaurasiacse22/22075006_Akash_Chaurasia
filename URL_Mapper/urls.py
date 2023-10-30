from django.urls import path, include
from . import views
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

app_name='URL_Mapper'
urlpatterns=[path('', views.shorten_url, name="shorten_url"),
             path('search/<Short_url>/', views.redirect_url, name="redirect_view"),
             path('List/', views.Show_List, name="List"),]