from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0005_lessonsession_lessonstepresponse_and_more'),
    ]

    operations = [
        migrations.CreateModel(
            name='AmphitheatreSession',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('session_id', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('visit_number', models.IntegerField(default=1)),
                ('depth_tier', models.CharField(default='alpha', max_length=16)),
                ('status', models.CharField(choices=[('draft', 'Draft'), ('active', 'Active'), ('completed', 'Completed'), ('archived', 'Archived')], default='active', max_length=16)),
                ('current_index', models.IntegerField(default=0)),
                ('exercises_plan', models.JSONField(default=list)),
                ('metadata', models.JSONField(blank=True, default=dict)),
                ('completion_points', models.IntegerField(default=0)),
                ('reflection_points', models.IntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='amphitheatre_sessions', to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='AmphitheatreExerciseRecord',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('exercise_id', models.CharField(max_length=40)),
                ('prompt_id', models.CharField(blank=True, max_length=64)),
                ('sequence_index', models.IntegerField(default=0)),
                ('selections', models.JSONField(blank=True, default=dict)),
                ('audio_reference', models.TextField(blank=True)),
                ('reflection_text', models.TextField(blank=True)),
                ('markers', models.JSONField(blank=True, default=dict)),
                ('state', models.CharField(choices=[('idle', 'Idle'), ('primed', 'Primed'), ('capturing', 'Capturing'), ('review', 'Review'), ('reflected', 'Reflected'), ('done', 'Done')], default='idle', max_length=16)),
                ('philosopher_response', models.TextField(blank=True)),
                ('microcopy', models.JSONField(blank=True, default=dict)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='exercise_records', to='myApp.amphitheatresession')),
            ],
            options={
                'ordering': ['sequence_index'],
                'unique_together': {('session', 'exercise_id')},
            },
        ),
        migrations.AddIndex(
            model_name='amphitheatresession',
            index=models.Index(fields=['user', 'status', 'created_at'], name='amphi_session_user_status_idx'),
        ),
        migrations.AddIndex(
            model_name='amphitheatresession',
            index=models.Index(fields=['user', 'visit_number'], name='amphi_session_visit_idx'),
        ),
        migrations.AddIndex(
            model_name='amphitheatreexerciserecord',
            index=models.Index(fields=['session', 'state'], name='amphi_record_state_idx'),
        ),
        migrations.AddIndex(
            model_name='amphitheatreexerciserecord',
            index=models.Index(fields=['session', 'sequence_index'], name='amphi_record_seq_idx'),
        ),
    ]

