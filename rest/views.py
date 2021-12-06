from rest_framework import viewsets, status

from rest.models import *
from rest.serializers import *
from rest_framework.decorators import action, permission_classes, authentication_classes
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from .permissions import IsPartyHost, IsPartyMember
from django.db import transaction


# Create your views here.

class PartyViewSet(viewsets.ViewSet):
    queryset = Party.objects.all()

    def list(self, request):
        parties = request.user.parties.all()
        serializer = PartySerializer(parties, many=True)
        return Response(serializer.data)

    # returns check if found one
    @action(detail=True, methods=['get'], permission_classes=[IsPartyMember])
    def paycheck(self, request, pk):
        party = get_object(Party, pk)
        self.check_object_permissions(request, party)
        if not hasattr(party, 'paycheck'):
            raise NotFound(detail="Party doesn't have a check", code=404)
        check = party.paycheck
        return Response(PaycheckSerializer(check).data)

    # post check for party if not having one
    @paycheck.mapping.post
    def post_check(self, request, pk):
        party = get_object(Party, pk)
        self.check_object_permissions(request, party)

        check_serializer = PaycheckSerializer(data=request.data)
        if not check_serializer.is_valid():
            return Response({"detail": "Check data is not valid"}, status=status.HTTP_400_BAD_REQUEST)
        check_serializer.save(party=party)
        return Response(check_serializer.data)

    @paycheck.mapping.put
    def put_check(self, request, pk):
        pass

    @action(detail=True, methods=['post'], url_path='invite/(?P<user_id>\d+)', permission_classes=[IsPartyMember])
    def invite(self, request, pk, user_id):
        party = get_object(Party, pk)
        self.check_object_permissions(request, party)
        user_to_invite = get_object(User, user_id)
        if party in user_to_invite.parties.all():
            return Response({"detail": "Invited user is already a party member"})
        user_to_invite.parties.add(party)
        return Response({"detail": "User is invited"})

    @action(detail=True, methods=['delete'], url_path='ban/(?P<user_id>\d+)', permission_classes=[IsPartyHost])
    def ban(self, request, pk, user_id):
        party = get_object(Party, pk)
        self.check_object_permissions(request, party)
        user_to_ban = get_object(User, user_id)
        if party not in user_to_ban.parties.all():
            return Response({"detail": "User is not a party member"})
        if user_to_ban == party.host:
            raise PermissionDenied(detail="Party host can't be banned", code=403)
        user_to_ban.parties.remove(party)
        return Response({"detail": "User is banned"})
