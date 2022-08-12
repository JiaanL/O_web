from django.urls import path, re_path
# from django.conf.urls import url
from . import views

urlpatterns = [
    path('', views.data_summary),
    path('data_summary', views.data_summary),
    
    # re_path(r'^bar/$', views.ChartView.as_view()),
    # re_path(r'^index/$', views.IndexView.as_view()),
    
    # path('all_oracle', views.all_oracle),
    path('update_data', views.update_data),
    path('auto_update', views.auto_update_view),
    # path('test', views.test),
    # path('update_block_time', views.update_block),
    # path('initialize', views.initialize_data),
    # path('read_csv/<str:oracle_name>', views.update_data_from_csv)
 
    # path('<str:oracle_name>', views.oracle_detail),
    # path('<str:oracle_name>/update', views.update_data)
    path('healthfactor_chart_view', views.healthfactor_chart_view),
    path("get_hf_chart", views.get_hf_chart.as_view()),
    path("get_hf_previous_chart", views.get_hf_previous_chart.as_view()),
]