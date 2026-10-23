from sqlalchemy import func, select

from app.models.patient import Patient


def find_duplicate(db, name, phone, exclude=None):
    query = select(Patient.id).where(
        Patient.active,
        func.lower(Patient.full_name) == name.lower(),
        Patient.phone == phone,
    )
    if exclude:
        query = query.where(Patient.id != exclude)
    return db.scalar(query.limit(1))


def list_page(db, search, page, page_size):
    query = select(Patient).where(Patient.active)
    if search:
        query = query.where(
            Patient.full_name.ilike(f"%{search}%") | Patient.phone.ilike(f"%{search}%")
        )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(
        query.order_by(Patient.created_at.desc(), Patient.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    ).all()
    return items, total
