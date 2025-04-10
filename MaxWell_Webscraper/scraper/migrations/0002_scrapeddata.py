# Generated by Django 4.2 on 2025-04-05 13:50

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('scraper', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ScrapedData',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=255, verbose_name='データ名')),
                ('data', models.TextField(verbose_name='JSONデータ')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='作成日時')),
            ],
            options={
                'verbose_name': 'スクレイピングデータ',
                'verbose_name_plural': 'スクレイピングデータ',
                'ordering': ['-created_at'],
            },
        ),
    ]
