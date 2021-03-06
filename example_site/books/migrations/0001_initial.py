# -*- coding: utf-8 -*-
# Generated by Django 1.9 on 2015-12-31 02:38
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('dcolumns', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Author',
            fields=[
                ('collectionbase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='dcolumns.CollectionBase')),
                ('name', models.CharField(help_text='Enter the name of the author.', max_length=250, verbose_name="Author's Name")),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Author',
                'verbose_name_plural': 'Authors',
            },
            bases=('dcolumns.collectionbase',),
        ),
        migrations.CreateModel(
            name='Book',
            fields=[
                ('collectionbase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='dcolumns.CollectionBase')),
                ('title', models.CharField(help_text='Enter a book title.', max_length=250, verbose_name='Title')),
            ],
            options={
                'ordering': ('title',),
                'verbose_name': 'Book',
                'verbose_name_plural': 'Books',
            },
            bases=('dcolumns.collectionbase',),
        ),
        migrations.CreateModel(
            name='Promotion',
            fields=[
                ('collectionbase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='dcolumns.CollectionBase')),
                ('name', models.CharField(help_text='Enter the name of the promotion.', max_length=250, verbose_name="Promotion's Name")),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Promotion',
                'verbose_name_plural': 'Promotions',
            },
            bases=('dcolumns.collectionbase',),
        ),
        migrations.CreateModel(
            name='Publisher',
            fields=[
                ('collectionbase_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='dcolumns.CollectionBase')),
                ('name', models.CharField(help_text='Enter the name of the publisher.', max_length=250, verbose_name="Publisher's Name")),
            ],
            options={
                'ordering': ('name',),
                'verbose_name': 'Publisher',
                'verbose_name_plural': 'Publishers',
            },
            bases=('dcolumns.collectionbase',),
        ),
    ]
