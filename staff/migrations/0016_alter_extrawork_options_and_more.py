from django.db import migrations, models


def fill_extra_work_date_to(apps, schema_editor):
    ExtraWork = apps.get_model("staff", "ExtraWork")
    for obj in ExtraWork.objects.filter(date_to__isnull=True):
        obj.date_to = obj.date_from
        obj.save(update_fields=["date_to"])


class Migration(migrations.Migration):

    dependencies = [
        ("staff", "0015_remove_extrawork_staffing_plan_item_and_more"),
    ]

    operations = [
        migrations.AlterModelOptions(
            name="extrawork",
            options={"ordering": ["-created_at"]},
        ),
        migrations.RemoveConstraint(
            model_name="extrawork",
            name="uq_extra_work_company_person_day",
        ),
        migrations.RenameField(
            model_name="extrawork",
            old_name="day",
            new_name="date_from",
        ),
        migrations.AddField(
            model_name="extrawork",
            name="date_to",
            field=models.DateField(
                blank=True,
                null=True,
                db_index=True,
            ),
        ),
        migrations.AlterField(
            model_name="extrawork",
            name="position",
            field=models.ForeignKey(
                blank=True,
                null=True,
                help_text="Position worked on this extra day. This is outside staffing plan slots.",
                on_delete=models.PROTECT,
                related_name="extra_works",
                to="staff.position",
            ),
        ),
        migrations.RunPython(
            fill_extra_work_date_to,
            migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="extrawork",
            name="date_to",
            field=models.DateField(
                db_index=True,
            ),
        ),
        migrations.AddConstraint(
            model_name="extrawork",
            constraint=models.CheckConstraint(
                condition=models.Q(("date_to__gte", models.F("date_from"))),
                name="ck_extra_work_date_to_gte_from",
            ),
        ),
        migrations.AddConstraint(
            model_name="extrawork",
            constraint=models.UniqueConstraint(
                fields=("company", "person", "date_from", "date_to"),
                name="uq_extra_work_company_person_period",
            ),
        ),
    ]