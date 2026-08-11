from django.contrib import admin

from .models import GeoNameAlternateName, GeoNameLocation, GeoNamesDataset, ResolvedLocation

admin.site.register(GeoNamesDataset)
admin.site.register(GeoNameLocation)
admin.site.register(GeoNameAlternateName)
admin.site.register(ResolvedLocation)
