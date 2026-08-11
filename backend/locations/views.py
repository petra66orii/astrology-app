from rest_framework.response import Response
from rest_framework.views import APIView

from .search import search_locations
from .serializers import LocationSearchResultSerializer


class LocationSearchView(APIView):
    def get(self, request):
        query = request.query_params.get("q", "")
        country = request.query_params.get("country") or None
        try:
            limit = int(request.query_params.get("limit", 10))
        except ValueError:
            limit = 10
        results = search_locations(query, country, limit)
        return Response({"results": LocationSearchResultSerializer(results, many=True).data})
