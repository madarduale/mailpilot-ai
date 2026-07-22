from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("emails", "0001_initial")]

    operations = [
        migrations.AddField(
            model_name="email",
            name="is_done",
            field=models.BooleanField(db_index=True, default=False),
        ),
    ]
