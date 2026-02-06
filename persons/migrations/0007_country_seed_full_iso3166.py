from django.db import migrations


def seed_countries_iso3166(apps, schema_editor):
    """
    Seed Country table from ISO 3166-1 (countries + territories) via pycountry.

    Why:
      - Keeping a full list manually is error-prone.
      - pycountry provides an up-to-date ISO dataset in a stable format.

    Notes:
      - This migration is idempotent: it uses update_or_create by code3.
      - If pycountry is not installed, migration raises a clear error message.
    """
    Country = apps.get_model("persons", "Country")

    try:
        import pycountry  # type: ignore
    except Exception as e:
        raise RuntimeError(
            "pycountry is required to seed the Country table. "
            "Install it (e.g. `uv add pycountry`) and re-run migrations."
        ) from e

    # pycountry.countries = ISO 3166-1 entries (includes countries and many territories)
    for c in pycountry.countries:
        code3 = getattr(c, "alpha_3", None)
        if not code3:
            continue

        # Prefer common_name where available for short label
        short_name = (
            getattr(c, "common_name", None) or getattr(c, "name", None) or code3
        )

        # Prefer official_name where available for full/official label
        full_name = (
            getattr(c, "official_name", None) or getattr(c, "name", None) or short_name
        )

        Country.objects.update_or_create(
            code3=code3,
            defaults={
                "short_name": short_name,
                "full_name": full_name,
                "is_active": True,
            },
        )


def noop_reverse(apps, schema_editor):
    """
    No reverse operation: we do not delete reference data automatically.
    """
    return


class Migration(migrations.Migration):

    dependencies = [
        ("persons", "0006_person_nationality"),
    ]

    operations = [
        migrations.RunPython(seed_countries_iso3166, reverse_code=noop_reverse),
    ]
