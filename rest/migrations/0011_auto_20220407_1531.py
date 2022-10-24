# Generated by Django 3.2.9 on 2022-04-07 12:31

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('rest', '0010_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='record',
            name='paycheck',
        ),
        migrations.AddField(
            model_name='record',
            name='billing',
            field=models.OneToOneField(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='records', to='rest.billing'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='record',
            name='product',
            field=models.CharField(max_length=200),
        ),
        migrations.CreateModel(
            name='Image',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('image', models.ImageField(upload_to='images')),
                ('billing', models.ForeignKey(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='paychecks', to='rest.billing')),
                ('party', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='picture', to='rest.party')),
            ],
        ),
    ]