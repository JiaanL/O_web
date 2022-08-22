"""oracleWeb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from xml.etree.ElementInclude import include

from django.contrib import admin
from django.urls import path, include
from . import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.main),
    path('main', views.main),
    path('auto_main', views.auto_main),
    path('auto_update_datastorage', views.auto_update_datastorage),
    path('stop_auto_update_datastorage', views.stop_auto_update_datastorage),
    path('auto_update_granularity', views.auto_update_granularity),
    path('stop_auto_update_granularity', views.stop_auto_update_granularity),
    path('auto_update_latency', views.auto_update_latency),
    path('stop_auto_update_latency', views.stop_auto_update_latency),
    path('auto_update_lending_pool', views.auto_update_lending_pool),
    path('stop_auto_update_lending_pool', views.stop_auto_update_lending_pool),

    # path('collect_evl_data', views.collect_evl_data),



    path("get_price_plot", views.get_price_plot.as_view()),
    path("get_latency_plot", views.get_latency_plot.as_view()),

    path("get_hf_previous_plot", views.get_hf_previous_plot.as_view()), 
    path("get_hf_plot", views.get_hf_plot.as_view()),



    path("price_data/", include("priceData.urls")),
    path("datastorage/", include("datastorage.urls")),
    path("datavisualization/", include("datavisualization.urls")),
    path("debtmonitor/", include("debtmonitor.urls")),
]
