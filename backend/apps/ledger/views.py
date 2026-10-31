from decimal import Decimal

from django.db.models import Sum
from django.utils import timezone
from rest_framework import status, viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.permissions import IsAdmin, IsAdminOrCaretaker
from apps.core.scoping import scope_lease_queryset
from apps.ledger.models import LedgerEntry
from apps.ledger.serializers import AdjustmentSerializer, LedgerEntrySerializer, ReversalSerializer
from apps.ledger.services import lease_balance, post_entry, post_reversal


class LedgerEntryViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = LedgerEntrySerializer
    permission_classes = [IsAuthenticated]
    filterset_fields = ["lease", "tenant", "entry_type", "source", "payment"]
    ordering_fields = ["effective_date", "created_at", "amount"]

    def get_queryset(self):
        qs = LedgerEntry.objects.select_related(
            "lease", "tenant", "unit", "unit__property", "payment"
        )
        qs = scope_lease_queryset(qs, self.request.user)
        start = self.request.query_params.get("from")
        end = self.request.query_params.get("to")
        if start:
            qs = qs.filter(effective_date__gte=start)
        if end:
            qs = qs.filter(effective_date__lte=end)
        return qs


class AdjustmentCreateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request):
        serializer = AdjustmentSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        entry, created = post_entry(
            lease=data["lease"],
            entry_type=data["entry_type"],
            amount=data["amount"],
            effective_date=data.get("effective_date") or timezone.localdate(),
            description=data.get("description", ""),
            source=LedgerEntry.Source.MANUAL,
            created_by=request.user,
        )
        return Response(
            LedgerEntrySerializer(entry).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ReversalCreateView(APIView):
    permission_classes = [IsAdmin]

    def post(self, request, pk):
        qs = scope_lease_queryset(LedgerEntry.objects.all(), request.user)
        entry = qs.filter(pk=pk).first()
        if not entry:
            return Response({"detail": "Ledger entry not found."}, status=404)
        if entry.entry_type == LedgerEntry.Type.REVERSAL:
            return Response({"detail": "A reversal cannot itself be reversed."}, status=400)
        if entry.reversals.exists():
            return Response({"detail": "Entry has already been reversed."}, status=400)
        serializer = ReversalSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        reversal, _ = post_reversal(
            entry,
            reason=serializer.validated_data.get("reason", ""),
            created_by=request.user,
        )
        return Response(LedgerEntrySerializer(reversal).data, status=status.HTTP_201_CREATED)


class LedgerSummaryView(APIView):
    permission_classes = [IsAdminOrCaretaker]

    def get(self, request):
        qs = scope_lease_queryset(LedgerEntry.objects.all(), request.user)
        lease_id = request.query_params.get("lease")
        if lease_id:
            qs = qs.filter(lease_id=lease_id)
        start = request.query_params.get("from")
        end = request.query_params.get("to")
        if start:
            qs = qs.filter(effective_date__gte=start)
        if end:
            qs = qs.filter(effective_date__lte=end)

        totals = {
            row["entry_type"]: row["total"] or Decimal("0.00")
            for row in qs.values("entry_type").annotate(total=Sum("amount"))
        }
        balance = sum(
            value for key, value in totals.items() if key not in {"DEPOSIT", "DEPOSIT_REFUND"}
        )
        return Response(
            {
                "charges": str(totals.get("RENT_CHARGE", Decimal("0.00"))),
                "late_fees": str(totals.get("LATE_FEE", Decimal("0.00"))),
                "payments": str(-totals.get("PAYMENT", Decimal("0.00"))),
                "adjustments": str(totals.get("ADJUSTMENT", Decimal("0.00"))),
                "waivers": str(-totals.get("WAIVER", Decimal("0.00"))),
                "balance": str(balance),
            }
        )


class LeaseBalanceView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, lease_id):
        from apps.leases.models import Lease

        qs = scope_lease_queryset(Lease.objects.all(), request.user)
        lease = qs.filter(pk=lease_id).first()
        if not lease:
            return Response({"detail": "Lease not found."}, status=404)
        return Response({"lease_id": str(lease.id), "balance": str(lease_balance(lease))})
