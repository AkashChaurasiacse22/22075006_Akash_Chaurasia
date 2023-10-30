import shortuuid
from .models import URL

def generate_short_url(Long_url):
    Short_url=shortuuid.uuid()[:8]
    return Short_url