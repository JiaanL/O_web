from django.urls import path, re_path
# from django.conf.urls import url
from . import views

urlpatterns = [
    # path('', views.datastorage),
    path('block_granularity_update', views.block_granularity_update),
    path("price_line_chart_view", views.price_line_chart_view),
    path("gen_price_line_chart", views.gen_price_line_chart.as_view()),

    path('latency_data_gen', views.latency_data_gen),
    path('latency_data_auto_gen', views.latency_data_auto_gen),
    path("latency_chart_view", views.latency_chart_view),
    path("gen_latency_chart", views.gen_latency_chart.as_view()),
    path("block_granularity_auto_update", views.block_granularity_auto_update_view),

    # re_path(r'^bar/$', views.ChartView.as_view()),
    # re_path(r'^index/$', views.IndexView.as_view()),
    
    # path('all_oracle', views.all_oracle),
    # path('update_data', views.update_data),
    # path('update_block_time', views.update_block),
    # path('initialize', views.initialize_data),
    # path('read_csv/<str:oracle_name>', views.update_data_from_csv)
 
    # path('<str:oracle_name>', views.oracle_detail),
    # path('<str:oracle_name>/update', views.update_data)
]