from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("reminders", "0001_initial")]

    operations = [
        migrations.AddField(model_name="reminder", name="notification_sent", field=models.BooleanField(db_index=True, default=False)),
        migrations.AddField(model_name="reminder", name="notification_sent_at", field=models.DateTimeField(blank=True, null=True)),
        migrations.AddField(model_name="reminder", name="priority", field=models.PositiveSmallIntegerField(default=50)),
        migrations.AddIndex(model_name="reminder", index=models.Index(fields=["status", "notification_sent", "due_at"], name="rem_delivery_due_idx")),
    ]
