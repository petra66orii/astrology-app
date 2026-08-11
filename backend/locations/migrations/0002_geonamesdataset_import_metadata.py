from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("locations", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="geonamesdataset",
            name="alternate_name_count",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="geonamesdataset",
            name="import_duration_ms",
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AddField(
            model_name="geonamesdataset",
            name="source_manifest",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
