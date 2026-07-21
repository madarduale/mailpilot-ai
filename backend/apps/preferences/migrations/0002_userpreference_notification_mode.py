from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("preferences", "0001_initial")]
    operations = [migrations.AddField(model_name="userpreference", name="notification_mode", field=models.CharField(choices=[("important_only", "Important emails only"), ("all_emails", "All emails")], default="important_only", max_length=24))]
