from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('businesses', '0004_document_faq_embedded_at_faq_embedding_documentchunk_and_more'),
        ('messaging', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='ConversationState',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(max_length=20)),
                ('last_read_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('business', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='businesses.business')),
            ],
            options={
                'indexes': [models.Index(fields=['business', 'phone'], name='messaging_c_business_8e0b42_idx')],
            },
        ),
        migrations.AddConstraint(
            model_name='conversationstate',
            constraint=models.UniqueConstraint(fields=('business', 'phone'), name='unique_conversation_state'),
        ),
    ]
