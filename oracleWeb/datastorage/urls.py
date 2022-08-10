from django.urls import path
from . import views

urlpatterns = [
    path('', views.datastorage),
    path('all_oracle', views.all_oracle),
    path('update_data', views.update_data),
    path('update_block_time', views.update_block),
    path('auto_update_block_time', views.block_time_auto_update_view),

    path('initialize', views.initialize_data),
    path('read_csv/<str:oracle_name>', views.update_data_from_csv),

    path('get_latest_block_number', views.get_latest_block_number),
    path('auto_update', views.auto_update_view),
    # path('<str:oracle_name>', views.oracle_detail),
    # path('<str:oracle_name>/update', views.update_data)
]