from datetime import datetime, timedelta
import humanize

ALLOWED_PHOTO_EXTENSIONS = {'jpg', 'jpeg', 'png'}
ALLOWED_PDF_EXTENSIONS = {'pdf'}

def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        suffix = "th"
    else:
        suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
    return f"{n}{suffix}"

def allowed_photo_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_PHOTO_EXTENSIONS

def allowed_pdf_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_PDF_EXTENSIONS

def calculate_shipment_cost_and_arrival(date, shipment_type):
    arrival: datetime | None = datetime.today()
    cost = None
    if shipment_type == 'Land':
        arrival = date + timedelta(days=5)
        cost = 10_000 * 5
    elif shipment_type == 'Sea':
        arrival = date + timedelta(weeks=2)
        cost = 1_000 * 14
    elif shipment_type == 'Air':
        arrival = date + timedelta(days=2)
        cost = 100_000 * 2
    return arrival, cost

def natural_time(unix_time: int):
    return humanize.naturaltime(int(unix_time) / 1000, future=True)

def format_shipment_type(shipment_type):
    if shipment_type == 'sea':
        return 'Transporting over sea.'
    elif shipment_type == 'air':
        return 'Transporting through air.'
    else:
        return 'Transporting over land.'
    
# Translates DB stores maintenance status to user readable value.
def formatted_maintenance_type(maintenance_type):
    if maintenance_type == 'deepclean':
        return 'Deep clean'
    else:
        return 'Outside repairs'