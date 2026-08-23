import json
from src.db.database import SessionLocal, init_db
from src.db.models import Product


def seed_products():
    init_db()
    db = SessionLocal()

    existing = db.query(Product).count()
    if existing > 0:
        print(f"Products already seeded ({existing} found). Skipping.")
        db.close()
        return

    with open("data/seed_catalog.json", "r") as f:
        products = json.load(f)

    for p in products:
        db.add(Product(
            name=p["name"],
            price=p["price"],
            stock=p["stock"],
            category=p["category"]
        ))

    db.commit()
    print(f"Seeded {len(products)} products successfully.")
    db.close()


if __name__ == "__main__":
    seed_products()