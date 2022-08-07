from django.contrib import admin
from .models import *
# Register your models here.
admin.site.register(LendingPoolInteraction)
admin.site.register(LendingPoolUpdateSummary)
admin.site.register(ReservesStatus)