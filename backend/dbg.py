import os, sys, traceback
sys.path.insert(0, r"d:\other\django-base-admin\backend")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()
from django.test import RequestFactory
from apps.gen.views import GenTableViewSet
from apps.system.models import SysUser
from common.auth import create_token
token = create_token(SysUser.objects.filter(username="admin").first())
rf = RequestFactory()
req = rf.get("/api/gen/table/1", HTTP_AUTHORIZATION=f"Bearer {token}")
view = GenTableViewSet.as_view({"get": "retrieve"})
resp = view(req, pk=1)
try:
    content = resp.rendered_content
    print("render ok, len:", len(content))
except Exception:
    traceback.print_exc()
