from ninja import Router
from datetime import datetime, timedelta, timezone
from .models import Tickets
from .schema import TicketSchema
from channels.layers import get_channel_layer
from asgiref.sync import async_to_sync
from core.auth import azure_bearer

router = Router()
#auth=azure_bearer
@router.get("/", response=list[TicketSchema])
def get_tickets(request, order: str = "recent", status: str = None, severity: str = None, providerName: str = None, days: int = None):    
    tickets = Tickets.objects.all()

    if order == "recent":
        tickets = tickets.order_by("-createdTime")
    elif order == "oldest":
        tickets = tickets.order_by("createdTime")

    if status:
        tickets = tickets.filter(status=status)

    if severity:
        tickets = tickets.filter(severity=severity)

    if providerName:
        tickets = tickets.filter(providerName=providerName)

    if days:
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        tickets = tickets.filter(createdTime__range=(start_date, end_date))

    return tickets

@router.post("/new_incidents")
def new_incidents(request, tickets: list[dict]):
    channel_layer = get_channel_layer()

    for ticket in tickets:
        try:
            ticket_data = {
                "uuid": ticket["object"]["name"],
                "createdTime": datetime.fromisoformat(ticket["object"]["properties"]["firstActivityTimeUtc"][:-1]).replace(tzinfo=timezone.utc),
                "lastModifiedTime": datetime.fromisoformat(ticket["object"]["properties"]["lastModifiedTimeUtc"][:-1]).replace(tzinfo=timezone.utc),
                "status": ticket["object"]["properties"].get("status", "Unknown"),
                "severity": ticket["object"]["properties"].get("severity", "Low"),
                "assignedTo": ticket["object"]["properties"]["owner"].get("assignedTo", "Unassigned"),
                "email": ticket["object"]["properties"]["owner"].get("email", "No email"),
                "title": ticket["object"]["properties"].get("title", "No Title"),
                "description": ticket["object"]["properties"].get("description", "No Description"),
                "incidentURL": ticket["object"]["properties"].get("incidentUrl", "URL not Found"),
                "providerName": ticket["object"]["properties"].get("providerName", "No provider"),
            }

            ticket_schema = TicketSchema(**ticket_data)

            ticket_obj, created = Tickets.objects.get_or_create(
                uuid=ticket_schema.uuid,
                defaults={
                    'createdTime': ticket_schema.createdTime,
                    'lastModifiedTime': ticket_schema.lastModifiedTime,
                    'status': ticket_schema.status,
                    'severity': ticket_schema.severity,
                    'assignedTo': ticket_schema.assignedTo,
                    'email': ticket_schema.email,
                    'title': ticket_schema.title,
                    'description': ticket_schema.description,
                    'incidentURL': ticket_schema.incidentURL,
                    'providerName': ticket_schema.providerName,
                }
            )

            if not created:
                ticket_obj.lastModifiedTime = ticket_schema.lastModifiedTime
                ticket_obj.status = ticket_schema.status
                ticket_obj.severity = ticket_schema.severity
                ticket_obj.assignedTo = ticket_schema.assignedTo
                ticket_obj.email = ticket_schema.email
                ticket_obj.title = ticket_schema.title
                ticket_obj.description = ticket_schema.description
                ticket_obj.save(update_fields=["lastModifiedTime", "status", "severity", "assignedTo", "email", "title", "description", "incidentURL", "providerName"])

            print("Objeto criado ou atualizado:", ticket_obj)

            async_to_sync(channel_layer.group_send)(
                "tickets_group",  
                {
                    "type": "ticket_update",
                    "ticket": {
                        "uuid": ticket_obj.uuid,
                        "title": ticket_obj.title,
                        "assignedTo": ticket_obj.assignedTo,
                        "providerName": ticket_obj.providerName
                    }
                }
            )

        except Exception as e:
            print(f"Erro ao processar o ticket {ticket_schema.uuid}: {e}")

    return {"message": "Tickets processed successfully"}

