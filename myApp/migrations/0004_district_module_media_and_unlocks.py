from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('myApp', '0003_lesson_engine'),
    ]

    operations = [
        migrations.AddField(
            model_name='district',
            name='overview_duration',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='district',
            name='overview_transcript',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='district',
            name='overview_video_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='module',
            name='lesson_duration',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='module',
            name='lesson_transcript',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='module',
            name='lesson_video_url',
            field=models.URLField(blank=True),
        ),
        migrations.AddField(
            model_name='userprofile',
            name='district_full_access',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.CreateModel(
            name='UserVenueUnlock',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('unlocked_at', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(on_delete=models.CASCADE, related_name='venue_unlocks', to=settings.AUTH_USER_MODEL)),
                ('venue', models.ForeignKey(on_delete=models.CASCADE, related_name='user_unlocks', to='myApp.venue')),
            ],
            options={
                'ordering': ['-unlocked_at'],
                'unique_together': {('user', 'venue')},
            },
        ),
    ]

