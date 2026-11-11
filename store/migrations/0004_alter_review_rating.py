

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0003_alter_review_options_review_user'),
    ]

    operations = [
        migrations.AlterField(
            model_name='review',
            name='rating',
            field=models.PositiveSmallIntegerField(choices=[(1, '1 star(s)'), (2, '2 star(s)'), (3, '3 star(s)'), (4, '4 star(s)'), (5, '5 star(s)')]),
        ),
    ]
