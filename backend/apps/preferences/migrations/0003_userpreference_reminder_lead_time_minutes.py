from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("preferences", "0002_userpreference_notification_mode")]

    operations = [
        migrations.AddField(
            model_name="userpreference",
            name="reminder_lead_time_minutes",
            field=models.PositiveSmallIntegerField(
                default=30,
                validators=[MinValueValidator(0), MaxValueValidator(1440)],
            ),
        ),
    ]
