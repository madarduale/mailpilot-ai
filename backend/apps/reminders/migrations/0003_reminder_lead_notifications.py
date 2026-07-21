from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("reminders", "0002_reminder_delivery_fields")]

    operations = [
        migrations.AddField(
            model_name="reminder",
            name="lead_notification_sent",
            field=models.BooleanField(db_index=True, default=False),
        ),
        migrations.AddField(
            model_name="reminder",
            name="lead_notification_sent_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddIndex(
            model_name="reminder",
            index=models.Index(
                fields=["status", "lead_notification_sent", "due_at"],
                name="rem_delivery_lead_idx",
            ),
        ),
    ]
