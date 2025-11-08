from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0002_lesson_runner_refactor'),
    ]

    operations = [
        migrations.AddField(
            model_name='exercisesubmission',
            name='ab_variant',
            field=models.CharField(blank=True, max_length=12),
        ),
        migrations.AddField(
            model_name='exercisesubmission',
            name='accuracy_score',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='exercisesubmission',
            name='completion_score',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='exercisesubmission',
            name='exercise_id',
            field=models.CharField(blank=True, max_length=32),
        ),
        migrations.AddField(
            model_name='exercisesubmission',
            name='payload_version',
            field=models.CharField(default='v1', max_length=12),
        ),
        migrations.AddField(
            model_name='exercisesubmission',
            name='reflection_score',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='exercisesubmission',
            name='template_id',
            field=models.CharField(blank=True, max_length=64),
        ),
        migrations.AddField(
            model_name='exercisesubmission',
            name='total_score',
            field=models.IntegerField(default=0),
        ),
        migrations.AlterField(
            model_name='exercisesubmission',
            name='knowledge_block',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='lesson_submissions', to='myApp.knowledgeblock'),
        ),
        migrations.AlterField(
            model_name='exercisesubmission',
            name='stage_key',
            field=models.CharField(max_length=64),
        ),
        migrations.AddField(
            model_name='userprogress',
            name='session_state',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.CreateModel(
            name='LessonSessionContext',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('current_scenario_ref', models.CharField(blank=True, max_length=64)),
                ('last_lever_choice', models.CharField(blank=True, max_length=16)),
                ('last_stakes_score', models.DecimalField(blank=True, decimal_places=3, max_digits=6, null=True)),
                ('cooldowns', models.JSONField(blank=True, default=dict)),
                ('loop_index', models.IntegerField(default=0)),
                ('data', models.JSONField(blank=True, default=dict)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('module', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='session_contexts', to='myApp.module')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lesson_sessions', to='auth.user')),
            ],
            options={
                'unique_together': {('user', 'module')},
            },
        ),
        migrations.CreateModel(
            name='TelemetryEvent',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('module_code', models.CharField(max_length=8)),
                ('name', models.CharField(max_length=80)),
                ('properties_json', models.JSONField(blank=True, default=dict)),
                ('ab_variant', models.CharField(blank=True, max_length=12)),
                ('ts', models.DateTimeField(auto_now_add=True)),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='telemetry_events', to='auth.user')),
            ],
            options={
                'ordering': ['-ts'],
            },
        ),
        migrations.CreateModel(
            name='StakesMap',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('scenario_ref', models.CharField(max_length=64)),
                ('situation_text', models.TextField(blank=True)),
                ('pressure_points', models.JSONField(default=list)),
                ('trigger', models.CharField(max_length=255)),
                ('lever', models.CharField(max_length=32)),
                ('action_step', models.TextField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('module', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stakes_maps', to='myApp.module')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='stakes_maps', to='auth.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='telemetryevent',
            index=models.Index(fields=['module_code', 'name', 'ts'], name='myApp_tele_module__5a3288_idx'),
        ),
    ]

