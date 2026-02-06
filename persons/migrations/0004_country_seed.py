from django.db import migrations


def forwards(apps, schema_editor):
    """
    Seed Country table from ISO 3166-1 data (alpha-3 codes).
    Uses pycountry to provide a near-complete and standardized country list.
    """
    Country = apps.get_model("persons", "Country")

    try:
        import pycountry
    except ImportError as e:
        raise RuntimeError(
            "pycountry is required to seed countries. Install it with: uv add pycountry"
        ) from e

    # ISO 3166-1 alpha-3 list
    for c in pycountry.countries:
        code3 = getattr(c, "alpha_3", None)
        name = getattr(c, "name", None)

        if not code3 or not name:
            continue

        # Use a compact short_name (best-effort).
        # Some names are long (e.g., 'United States of America'), short_name can be adjusted later.
        short_name = name.split(",")[0].split("(")[0].strip()

        # Create or update
        Country.objects.update_or_create(
            code3=code3,
            defaults={
                "short_name": short_name,
                "full_name": name,
                "is_active": True,
            },
        )


def backwards(apps, schema_editor):
    """
    Reverse operation: keep user data safe.
    We do NOT delete countries on rollback because they may be referenced by documents.
    """
    # Intentionally do nothing.
    pass


class Migration(migrations.Migration):
    dependencies = [
        ("persons", "0002_person_photo"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]
