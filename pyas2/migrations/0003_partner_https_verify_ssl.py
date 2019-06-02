# Generated by Django 2.2.1 on 2019-05-31 21:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('pyas2', '0002_auto_20190531_1954'),
    ]

    operations = [
        migrations.AddField(
            model_name='partner',
            name='https_verify_ssl',
            field=models.BooleanField(default=True, help_text='Uncheck this option to disable SSL certificate verification to HTTPS.', verbose_name='Verify SSL Certificate'),
        ),
    ]