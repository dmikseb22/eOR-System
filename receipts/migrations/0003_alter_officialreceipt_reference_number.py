# Generated by Django 4.2.7 on 2025-07-03 01:36

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('receipts', '0002_officialreceipt_mode_of_payment_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='officialreceipt',
            name='reference_number',
            field=models.CharField(blank=True, max_length=50, null=True),
        ),
    ]
