from rest_framework import viewsets, status

from rest.models import *
from rest.serializers import *
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from .permissions import IsPartyHost, IsPartyMember, ViewSetActionPermissionMixin
from rest_framework import mixins


# Create your views here.

class PartyViewSet(ViewSetActionPermissionMixin, viewsets.ViewSet):
    queryset = Party.objects.all()
    permission_action_classes = {
        "paycheck": [IsPartyMember],
        "post_check": [IsPartyHost],
        "patch_check": [IsPartyHost],
        "invite": [IsPartyMember],
        "ban": [IsPartyHost],
        "destroy": [IsPartyHost],
        "partial_update": [IsPartyHost],
        "contribute": [IsPartyMember],
        "contributions": [IsPartyMember],
        "choices": [IsPartyMember],
        "result": [IsPartyMember]
    }

    def get_party_and_check(self, request, pk):
        party = get_object(Party, pk)
        self.check_object_permissions(request, party)
        if not hasattr(party, 'paycheck'):
            raise NotFound(detail="Party doesn't have a check", code=404)
        check = party.paycheck
        return party, check

    def list(self, request):
        parties = request.user.parties.all()
        serializer = PartySerializer(parties, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def result(self, request, pk):
        party, check = self.get_party_and_check(request, pk)
        if not check.contributions.all():
            return Response({"detail": "Check has no contributions"}, status=status.HTTP_400_BAD_REQUEST)
        overall_contribution = sum([c.contribution for c in check.contributions.all()])
        if overall_contribution < check.total:
            return Response({"detail": "Not enough contributions from users"}, status=status.HTTP_400_BAD_REQUEST)
        money_to_pay = 0
        for record in check.records.all():
            product = record.product
            user_quantities = [c.quantity for c in record.choices.all()]
            if not user_quantities:
                return Response({"detail": "Record {} was not picked by anyone".format(product)},
                                status=status.HTTP_400_BAD_REQUEST)
            overall_amount_took = sum(user_quantities)
            if overall_amount_took != record.quantity and record.quantity != 1:
                return Response({"detail": "Some amount of {} was not picked".format(product)},
                                status=status.HTTP_400_BAD_REQUEST)
            user_choice = record.choices.filter(user=request.user).first()
            if record.quantity == 1 and user_choice:
                money_to_pay += record.price / len(record.choices.all())
            elif user_choice:
                money_to_pay += record.price * user_choice.quantity
        user_contributions = check.contributions.filter(user=request.user).all()
        user_contrib_amount = 0
        if user_contributions:
            user_contrib_amount = sum([contrib.contribution for contrib in user_contributions])

        difference = user_contrib_amount - money_to_pay
        if difference < 0:
            return Response({"borrow": difference * (-1)})
        else:
            return Response({"loan": difference})

    # returns check if found one
    @action(detail=True, methods=['get'])
    def paycheck(self, request, pk):
        party, check = self.get_party_and_check(request, pk)
        return Response(PaycheckSerializer(check).data)

    # post check for party if not having one
    @paycheck.mapping.post
    def post_check(self, request, pk):
        party = get_object(Party, pk)
        self.check_object_permissions(request, party)
        if hasattr(party, 'paycheck'):
            return Response({"detail": "Check already exists"}, status=status.HTTP_400_BAD_REQUEST)
        check_serializer = PaycheckSerializer(data=request.data)
        if not check_serializer.is_valid():
            return Response({"detail": "Check data is not valid"}, status=status.HTTP_400_BAD_REQUEST)
        check_serializer.save(party=party)
        return Response(check_serializer.data)

    @paycheck.mapping.patch
    def patch_check(self, request, pk):
        party, check = self.get_party_and_check(request, pk)
        self.check_object_permissions(request, party)
        check_serializer = PaycheckSerializer(check, data=request.data)
        if not check_serializer.is_valid():
            return Response({"detail": "Check data is not valid"}, status=status.HTTP_400_BAD_REQUEST)
        check_serializer.save()
        return Response(check_serializer.data)

    @action(detail=True, methods=['post'], url_path='invite/(?P<username>\w+)')
    def invite(self, request, pk, username):
        party = get_object(Party, pk)
        self.check_object_permissions(request, party)
        user_to_invite = get_user_by_name(username)
        if party in user_to_invite.parties.all():
            return Response({"detail": "Invited user is already a party member"})
        user_to_invite.parties.add(party)
        return Response({"detail": "User is invited"})

    @action(detail=True, methods=['delete'], url_path='ban/(?P<username>\w+)')
    def ban(self, request, pk, username):
        party = get_object(Party, pk)
        self.check_object_permissions(request, party)
        user_to_ban = get_user_by_name(username)
        if party not in user_to_ban.parties.all():
            return Response({"detail": "User is not a party member"})
        if user_to_ban == party.host:
            raise PermissionDenied(detail="Party host can't be banned", code=403)
        user_to_ban.parties.remove(party)
        return Response({"detail": "User is banned"})

    def destroy(self, request, pk=None):
        party = get_object(Party, pk)
        self.check_object_permissions(request, party)
        party.delete()
        return Response({"detail": "Party destroyed"})

    def create(self, request):
        serializer = CreatePartySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Party data is not valid"}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save(host=request.user)
        return Response(serializer.data)

    def partial_update(self, request, pk):
        party = get_object(Party, pk)
        self.check_object_permissions(request, party)
        serializer = CreatePartySerializer(party, data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Party data is not valid"}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def contribute(self, request, pk):
        party, check = self.get_party_and_check(request, pk)
        self.check_object_permissions(request, party)
        serializer = CreateContributionSerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Contribution data is not valid"}, status=status.HTTP_400_BAD_REQUEST)
        contribution = serializer.save(paycheck=check, user=request.user)
        return Response(ContributionSerializer(contribution).data)

    @action(detail=True, methods=['get'])
    def contributions(self, request, pk):
        party, check = self.get_party_and_check(request, pk)
        self.check_object_permissions(request, party)
        user_contribs = check.contributions.filter(user=request.user)
        serializer = ContributionSerializer(user_contribs, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def choices(self, request, pk):
        party, check = self.get_party_and_check(request, pk)
        self.check_object_permissions(request, party)
        user_choices = check.choices.filter(user=request.user)
        serializer = ChoiceSerializer(user_choices, many=True)
        return Response(serializer.data)


class ContributionViewSet(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin,
                          mixins.DestroyModelMixin,
                          viewsets.GenericViewSet):
    model = Contribution
    serializer_class = ContributionSerializer

    def get_queryset(self):
        user = self.request.user
        return user.contributions.all()


class ChoiceViewSet(ViewSetActionPermissionMixin,
                    mixins.RetrieveModelMixin,
                    mixins.DestroyModelMixin,
                    viewsets.GenericViewSet):
    model = Choice
    serializer_class = ChoiceSerializer
    permission_action_classes = {
        "create": [IsPartyMember]
    }

    def validated_choice_fields(self, data):
        if type(data['record']) != str or type(data['quantity']) != int or type(data['paycheck']) != int:
            return None
        if data['quantity'] < 1:
            return None
        if data['paycheck'] < 1:
            return None
        return data

    def get_queryset(self):
        user = self.request.user
        return user.choices.all()

    def create(self, request):
        valid_data = self.validated_choice_fields(request.data)
        if not valid_data:
            return Response({"detail": "Choice data is not valid"}, status=status.HTTP_400_BAD_REQUEST)
        product = valid_data.pop("record")
        quantity = valid_data['quantity']
        paycheck_id = valid_data.pop('paycheck')
        check = get_object(Paycheck, paycheck_id)
        party = check.party
        self.check_object_permissions(request, party)
        record = check.records.filter(product=product).first()
        if not record:
            return Response({"detail": "No such record in paycheck"}, status=status.HTTP_400_BAD_REQUEST)
        if record.quantity < quantity:
            return Response({"detail": "Quantity exceeds amount of product"}, status=status.HTTP_400_BAD_REQUEST)
        user_choices = check.choices.filter(user=request.user, record=record).first()
        if user_choices:
            return Response({"detail": "This item is already picked by user"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = CreateChoiceSerializer(data=valid_data)
        serializer.is_valid()
        choice = serializer.save(user=request.user, record=record, paycheck=check)
        return Response(ChoiceSerializer(choice).data)
