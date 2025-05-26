from django.db import migrations, models
import json


class Migration(migrations.Migration):

    dependencies = [
        ('reports', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='scheduledreport',
            name='parameters',
            field=models.JSONField(blank=True, default=dict, help_text='Parameters to use when generating the report'),
        ),
    ]
