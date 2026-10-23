from sqlalchemy import func, select

from app.models.appointment import Appointment


def page(db, start, end, patient_id, status, kind, page_number, size):
    query = select(Appointment)
    if start is not None:
        query = query.where(Appointment.end_at > start)
    if end is not None:
        query = query.where(Appointment.start_at < end)
    for column, value in (
        (Appointment.patient_id, patient_id),
        (Appointment.status, status),
        (Appointment.kind, kind),
    ):
        if value is not None:
            query = query.where(column == value)
    total = db.scalar(select(func.count()).select_from(query.subquery()))
    items = db.scalars(
        query.order_by(Appointment.start_at, Appointment.id)
        .offset((page_number - 1) * size)
        .limit(size)
    ).all()
    return dict(items=items, total=total, page=page_number, page_size=size)
