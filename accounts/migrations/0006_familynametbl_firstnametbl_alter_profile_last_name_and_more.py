# Migration 0006: Create FirstnameTbl/FamilynameTbl and convert Profile name fields to FK
# This migration was already applied via raw SQL; marked as standard operations for Django state tracking.

import django.db.models.deletion
from django.db import migrations, models


def noop(apps, schema_editor):
    """Database is already in the correct state — no changes needed."""
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0005_add_religion_sect'),
    ]

    operations = [
        # ═══════ State: Create new tables ═══════
        migrations.CreateModel(
            name='FirstnameTbl',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('first_name_fa', models.CharField(max_length=100, unique=True, verbose_name='نام فارسی')),
                ('first_name_en', models.CharField(blank=True, max_length=100, verbose_name='نام انگلیسی')),
            ],
            options={
                'verbose_name': 'نام',
                'verbose_name_plural': 'نام\u200cها',
                'ordering': ['first_name_fa'],
            },
        ),
        migrations.CreateModel(
            name='FamilynameTbl',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('familyname_fa', models.CharField(max_length=100, unique=True, verbose_name='نام خانوادگی فارسی')),
                ('familyname_en', models.CharField(blank=True, max_length=100, verbose_name='نام خانوادگی انگلیسی')),
            ],
            options={
                'verbose_name': 'نام خانوادگی',
                'verbose_name_plural': 'نام\u200cهای خانوادگی',
                'ordering': ['familyname_fa'],
            },
        ),
        # ═══════ State: Drop old text fields ═══════
        migrations.RemoveField(model_name='profile', name='first_name'),
        migrations.RemoveField(model_name='profile', name='last_name'),
        migrations.RemoveField(model_name='profile', name='father_name'),
        # ═══════ State: Add new FK fields ═══════
        migrations.AddField(
            model_name='profile', name='first_name',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='profiles_first_name',
                to='accounts.firstnametbl', verbose_name='نام',
            ),
        ),
        migrations.AddField(
            model_name='profile', name='last_name',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='profiles_last_name',
                to='accounts.familynametbl', verbose_name='نام خانوادگی',
            ),
        ),
        migrations.AddField(
            model_name='profile', name='father_name',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='profiles_father_name',
                to='accounts.firstnametbl', verbose_name='نام پدر',
            ),
        ),
        migrations.AddField(
            model_name='profile', name='mother_name',
            field=models.ForeignKey(
                blank=True, null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='profiles_mother_name',
                to='accounts.firstnametbl', verbose_name='نام مادر',
            ),
        ),
    ]
