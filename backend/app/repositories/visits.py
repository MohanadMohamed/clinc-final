from sqlalchemy import func, or_, select

from app.models.visit import Visit, VisitAddendum, VisitRevision


def page(db, patient_id, search, page_number, size):
    query = select(Visit)
    if patient_id is not None:
        query = query.where(Visit.patient_id == patient_id)
    if search:
        literal = search.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        pattern = f"%{literal}%"
        query = query.where(
            or_(
                Visit.neurological_note.ilike(pattern, escape="\\"),
                Visit.psychiatric_note.ilike(pattern, escape="\\"),
                Visit.follow_up_plan.ilike(pattern, escape="\\"),
            )
        )
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(
        query.order_by(Visit.created_at.desc(), Visit.id.desc())
        .offset((page_number - 1) * size)
        .limit(size)
    ).all()
    return dict(items=items, total=total, page=page_number, page_size=size)


def history(db, visit_id):
    revisions = db.scalars(
        select(VisitRevision)
        .where(VisitRevision.visit_id == visit_id)
        .order_by(VisitRevision.revision)
    ).all()
    addenda = db.scalars(
        select(VisitAddendum)
        .where(VisitAddendum.visit_id == visit_id)
        .order_by(VisitAddendum.occurred_at, VisitAddendum.id)
    ).all()
    return dict(revisions=revisions, addenda=addenda)
