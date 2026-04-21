import os
import faulthandler

print("boot")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "myserver.settings")

faulthandler.dump_traceback_later(10, repeat=False)

import django

print("before setup")
django.setup()
faulthandler.cancel_dump_traceback_later()
print("after setup")