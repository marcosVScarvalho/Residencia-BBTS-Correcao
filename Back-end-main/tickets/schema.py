from datetime import datetime
from uuid import UUID

from ninja import Schema


class TicketSchema(Schema):
    uuid: UUID
    createdTime: datetime
    lastModifiedTime: datetime
    status: str
    severity: str
    assignedTo: str
    email: str
    title: str
    description: str
    incidentURL: str
    providerName: str

