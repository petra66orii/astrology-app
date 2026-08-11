from rest_framework import generics, status
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import BirthProfile, NatalChart
from .serializers import BirthProfileSerializer, ChartCreateSerializer, NatalChartSerializer
from .services import ChartCreationError, create_natal_chart


class BirthProfileListCreateView(generics.ListCreateAPIView):
    serializer_class = BirthProfileSerializer

    def get_queryset(self):
        return BirthProfile.objects.filter(owner=self.request.user).select_related(
            "resolved_location"
        )


class NatalChartListView(generics.ListAPIView):
    serializer_class = NatalChartSerializer

    def get_queryset(self):
        return NatalChart.objects.filter(owner=self.request.user).select_related(
            "birth_profile", "resolved_location", "calculation_version"
        )


class NatalChartDetailView(generics.RetrieveAPIView):
    serializer_class = NatalChartSerializer

    def get_queryset(self):
        return NatalChart.objects.filter(owner=self.request.user).select_related(
            "birth_profile", "resolved_location", "calculation_version"
        )


class NatalChartCreateView(APIView):
    def post(self, request):
        serializer = ChartCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        profile = (
            BirthProfile.objects.filter(
                id=serializer.validated_data["birth_profile_id"], owner=request.user
            )
            .select_related("resolved_location")
            .first()
        )
        if profile is None:
            return Response(
                {"error": {"code": "profile_not_found", "detail": "Birth profile not found."}},
                status=404,
            )
        try:
            chart = create_natal_chart(profile=profile, fold=serializer.validated_data.get("fold"))
        except ChartCreationError as exc:
            error = {"code": exc.code, "detail": exc.detail}
            if exc.candidates:
                error["candidates"] = exc.candidates
            return Response({"error": error}, status=exc.status_code)
        return Response(NatalChartSerializer(chart).data, status=status.HTTP_201_CREATED)
