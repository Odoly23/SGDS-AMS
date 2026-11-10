from rest_framework import status
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .models import Package


class WalletView(APIView):
    """GET /api/wallet/ -> saldo + daftar paket."""

    def get(self, request):
        w = services.get_wallet(request.user)
        pk = Package.objects.filter(is_active=True)
        return Response({
            "balance": w.balance,
            "packages": [{"name": p.name, "description": p.description, "price_usd": str(p.price_usd), "credits": p.credits} for p in pk],
        })


class RedeemView(APIView):
    """POST /api/redeem/ {"code": "ABCD-EFGH-JKLM"}"""

    def post(self, request):
        try:
            result = services.redeem_voucher(request.user, str(request.data.get("code", ""))[:40])
        except services.BillingError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(result)
