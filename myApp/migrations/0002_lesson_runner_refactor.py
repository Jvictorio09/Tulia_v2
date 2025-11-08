from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('myApp', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='userprogress',
            name='loop_index',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userprogress',
            name='meta',
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name='userprogress',
            name='pass_type',
            field=models.CharField(choices=[('main', 'Main'), ('return', 'Return')], default='main', max_length=8),
        ),
        migrations.AddField(
            model_name='userprogress',
            name='pic_control',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userprogress',
            name='pic_irreversibility',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userprogress',
            name='pic_pressure',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userprogress',
            name='pic_visibility',
            field=models.SmallIntegerField(default=0),
        ),
        migrations.AddField(
            model_name='userprogress',
            name='return_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='userprogress',
            name='sequence_version',
            field=models.CharField(default='v1.0', max_length=12),
        ),
        migrations.AddField(
            model_name='userprogress',
            name='stage_key',
            field=models.CharField(default='prime', max_length=32),
        ),
        migrations.AddField(
            model_name='userprogress',
            name='lever_choice',
            field=models.CharField(blank=True, choices=[('preparation', 'Preparation'), ('presence', 'Presence'), ('perspective', 'Perspective')], max_length=16),
        ),
        migrations.AddField(
            model_name='userprogress',
            name='load_label',
            field=models.CharField(choices=[('emotional', 'Emotional'), ('cognitive', 'Cognitive'), ('mixed', 'Mixed'), ('unknown', 'Unknown')], default='unknown', max_length=16),
        ),
        migrations.AddIndex(
            model_name='userprogress',
            index=models.Index(fields=['user', 'current_knowledge_block', 'loop_index', 'pass_type'], name='myApp_user__user_id_744e54_idx'),
        ),
        migrations.CreateModel(
            name='ExerciseSubmission',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('loop_index', models.IntegerField(default=0)),
                ('pass_type', models.CharField(choices=[('main', 'Main'), ('return', 'Return')], default='main', max_length=8)),
                ('stage_key', models.CharField(choices=[('prime', 'Prime'), ('teach', 'Teach'), ('diagnose', 'Diagnose'), ('control_shift', 'Control Shift'), ('perform_text', 'Perform Text'), ('perform_voice', 'Perform Voice'), ('review', 'Review'), ('transfer', 'Transfer')], max_length=32)),
                ('lever_choice', models.CharField(blank=True, max_length=16)),
                ('payload', models.JSONField(default=dict)),
                ('scores', models.JSONField(blank=True, default=dict)),
                ('duration_ms', models.IntegerField(default=0)),
                ('client_ts', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('knowledge_block', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lesson_submissions', to='myApp.knowledgeblock')),
                ('module', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lesson_submissions', to='myApp.module')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='lesson_submissions', to='auth.user')),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
        migrations.AddIndex(
            model_name='exercisesubmission',
            index=models.Index(fields=['user', 'module', 'knowledge_block', 'loop_index', 'stage_key'], name='myApp_exer_user_id_aed519_idx'),
        ),
    ]

