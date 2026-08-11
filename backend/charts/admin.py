from django.contrib import admin

from .models import BirthProfile, ChartCalculationVersion, NatalChart, ProviderCreditEvent

admin.site.register(BirthProfile)
admin.site.register(ChartCalculationVersion)
admin.site.register(NatalChart)
admin.site.register(ProviderCreditEvent)
