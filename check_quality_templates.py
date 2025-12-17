from dotenv import load_dotenv
load_dotenv()
from app.db.session import get_db_session
from app.models.template import WhatsAppTemplate

with get_db_session() as db:
    # Get all approved templates
    templates = db.query(WhatsAppTemplate).filter(
        WhatsAppTemplate.status.in_(['APPROVED'])
    ).all()

    print("All APPROVED Templates:")
    print("=" * 60)

    for t in templates:
        quality = t.quality_score if t.quality_score else 'UNKNOWN'
        print(f"\nTemplate: {t.name} ({t.language})")
        print(f"  Status: {t.status.value}")
        print(f"  Quality: {quality}")
        print(f"  Usage Count: {t.usage_count}")
        print(f"  Category: {t.category.value}")

        if quality == 'UNKNOWN':
            print(f"  [WARNING] Quality unknown - may not be delivered!")
        elif quality in ['HIGH', 'MEDIUM']:
            print(f"  [OK] Good quality - should be delivered")
        elif quality == 'LOW':
            print(f"  [WARNING] Low quality - delivery may fail")

    # Check for hello_world template specifically
    print("\n" + "=" * 60)
    print("Checking for 'hello_world' template (Meta's test template):")
    hello = db.query(WhatsAppTemplate).filter(
        WhatsAppTemplate.name == 'hello_world'
    ).first()

    if hello:
        print(f"  Found: {hello.name}")
        print(f"  Status: {hello.status.value}")
        print(f"  Quality: {hello.quality_score if hello.quality_score else 'UNKNOWN'}")
    else:
        print("  Not found - you should create one!")
        print("  hello_world is Meta's default template and always works")
