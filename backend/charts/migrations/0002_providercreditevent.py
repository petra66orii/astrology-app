import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("charts", "0001_initial")]

    operations = [
        migrations.CreateModel(
            name="ProviderCreditEvent",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, primary_key=True, serialize=False
                    ),
                ),
                ("provider", models.CharField(max_length=32)),
                ("endpoint", models.CharField(max_length=120)),
                ("estimated_credits", models.PositiveIntegerField()),
                ("chart_id", models.UUIDField(db_index=True)),
                (
                    "flow",
                    models.CharField(
                        choices=[("EXACT", "Exact"), ("UNKNOWN", "Unknown time")],
                        max_length=16,
                    ),
                ),
                ("sample_number", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("succeeded", models.BooleanField(default=False)),
                ("failure_code", models.CharField(blank=True, max_length=64)),
                ("response_http_status", models.PositiveSmallIntegerField(blank=True, null=True)),
                ("latency_ms", models.PositiveIntegerField(blank=True, null=True)),
                ("occurred_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ],
            options={
                "ordering": ("-occurred_at",),
                "indexes": [
                    models.Index(fields=["provider", "-occurred_at"], name="credit_provider_date"),
                    models.Index(fields=["flow", "-occurred_at"], name="credit_flow_date"),
                ],
            },
        )
    ]
