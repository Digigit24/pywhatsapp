import inspect
from pywa import WhatsApp

print("--- send_document signature ---")
try:
    print(inspect.signature(WhatsApp.send_document))
except Exception as e:
    print(e)

print("\n--- download_media signature ---")
try:
    print(inspect.signature(WhatsApp.download_media))
except Exception as e:
    print(e)
