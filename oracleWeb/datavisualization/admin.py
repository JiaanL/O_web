from django.contrib import admin

# Register your models here.
from .models import *

admin.site.register(BlockPrice)
admin.site.register(BlockPriceUpdateRecord)
admin.site.register(Frequency)
admin.site.register(LatencyUpdateRecord)
admin.site.register(LatencyRecord)

