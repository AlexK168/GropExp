from django.db import transaction
from rest_framework import viewsets, status, mixins

from rest.serializers import *
from rest_framework.decorators import action, api_view
from rest_framework.response import Response
from rest_framework.exceptions import NotFound, PermissionDenied
from .permissions import IsPartyHost, IsPartyMember, ViewSetActionPermissionMixin


def check_party_permissions(view):
    def wrapper(*args, **kwargs):
        pk = kwargs['pk']
        obj = args[0]
        request = args[1]

        party = get_object(Party, pk)
        obj.check_object_permissions(request, party)
        return view(*args, **kwargs)

    return wrapper


class PartyViewSet(ViewSetActionPermissionMixin, viewsets.ViewSet):
    queryset = Party.objects.all()
    permission_action_classes = {
        'retrieve': [IsPartyMember],
        'invite': [IsPartyMember],
        'ban': [IsPartyHost],
        'destroy': [IsPartyHost],
        'partial_update': [IsPartyHost],

    }

    def create(self, request):
        serializer = PartySerializer(data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Party data is not valid"}, status=status.HTTP_400_BAD_REQUEST)

        party = serializer.save(host=request.user)
        billing = Billing(party=party)
        billing.save()
        return Response(serializer.data)

    def destroy(self, request, pk):
        party = get_object(Party, pk)
        self.check_object_permissions(request, party)
        party.delete()
        return Response({"detail": "Party destroyed"})

    def retrieve(self, request, pk):
        party = get_object(Party, pk=pk)
        self.check_object_permissions(request, party)
        serializer = PartySerializer(party)
        return Response(serializer.data)

    def list(self, request):
        parties = request.user.parties.all()
        serializer = PartySerializer(parties, many=True)
        return Response(serializer.data)

    def partial_update(self, request, pk):
        party = get_object(Party, pk=pk)
        self.check_object_permissions(request, party)
        serializer = PartySerializer(party, data=request.data, partial=True)
        if not serializer.is_valid():
            return Response({"detail": "Party data for update is not valid"}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def invite(self, request, pk):
        party = get_object(Party, pk=pk)
        self.check_object_permissions(request, party)
        serializer = UserSerializer(data=request.data, many=True)
        if not serializer.is_valid():
            return Response({"detail": "User data for invite is not valid"}, status=status.HTTP_400_BAD_REQUEST)
        for user_dict in serializer.validated_data:
            user_id = user_dict["id"]
            user_to_invite = get_object(User, user_id)
            user_to_invite.parties.add(party)
        return Response({"detail": "Users are invited"})

    @action(detail=True, methods=['delete'])
    def ban(self, request, pk):
        party = get_object(Party, pk)
        self.check_object_permissions(request, party)
        serializer = UserSerializer(data=request.data, many=True)
        if not serializer.is_valid():
            return Response({"detail": "User data for ban is not valid"}, status=status.HTTP_400_BAD_REQUEST)
        for user_dict in serializer.validated_data:
            user_id = user_dict["id"]
            user_to_ban = get_object(User, user_id)
            if user_to_ban == party.host:
                raise PermissionDenied(detail="Party host can't be banned", code=403)
            user_to_ban.parties.remove(party)
        return Response({"detail": "Users are banned"})


class BillingViewSet(ViewSetActionPermissionMixin, viewsets.ViewSet):
    queryset = Billing.objects.all()
    permission_action_classes = {
        'retrieve': [IsPartyMember],
        'update': [IsPartyMember],
        'calculate': [IsPartyMember],
        'choices': [IsPartyMember],
    }

    def retrieve(self, request, pk):
        billing = get_object(Billing, pk)
        party = billing.party
        self.check_object_permissions(request, party)
        serializer = BillingSerializer(billing)
        return Response(serializer.data)

    def update(self, request, pk):
        billing = get_object(Billing, pk)
        party = billing.party
        self.check_object_permissions(request, party)
        serializer = BillingSerializer(billing, data=request.data)
        if not serializer.is_valid():
            return Response({"detail": "Billing data for update is not valid"}, status=status.HTTP_400_BAD_REQUEST)
        serializer.save()
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def calculate(self, request, pk):
        billing = get_object(Billing, pk)
        party = billing.party
        self.check_object_permissions(request, party)

        if not billing or billing.records.count() == 0:
            return Response({"detail": "Billing is empty. Nothing to calculate"}, status=status.HTTP_400_BAD_REQUEST)

        party_members = party.members.all()
        balance = Balance(list(party_members), billing.total)

        for c in billing.contributions.all():
            balance.addContribution(c.user, c.contribution)

        if balance.total_balance < 0:
            return Response({"detail": "Unable to calculate - total contribution is not enough"},
                            status=status.HTTP_400_BAD_REQUEST)

        for record in billing.records.all():
            product_quantity = record.quantity
            total_record_price = record.price * product_quantity
            choices = record.choices.all()
            amount_picked_by_members = sum([c.quantity for c in choices])
            if amount_picked_by_members < product_quantity:
                return Response({"detail": f"Some amount of {record.product} is left unpicked"},
                                status=status.HTTP_400_BAD_REQUEST)

            delta = total_record_price / amount_picked_by_members
            for choice in choices:
                quantity_by_member = choice.quantity
                debt = quantity_by_member * delta
                balance.addDebt(choice.user, debt)

        debt_records, from_change = balance.final(billing)

        with transaction.atomic():
            billing.debts.all().delete()
            billing.change.all().delete()

            debts = DebtRecord.objects.bulk_create(debt_records)
            change = DebtFromChangeRecord.objects.bulk_create(from_change)

        serializer = ResultSerializer({'debts': debts, 'change': change})
        return Response(serializer.data)

    @action(detail=True, methods=['get'])
    def contributions(self, request, pk):
        billing = get_object(Billing, pk)
        party = billing.party
        self.check_object_permissions(request, party)
        contributions = billing.contributions.all()
        serializer = ContributionSerializer(contributions, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['get', 'post'])
    def choices(self, request, pk):
        billing = get_object(Billing, pk)
        party = billing.party
        self.check_object_permissions(request, party)
        choices = billing.choices.filter(user=request.user)
        if request.method == 'GET':
            serializer = ChoiceSerializer(choices, many=True)
            return Response(serializer.data)
        if request.method == 'POST':
            choices.delete()
            serializer = ChoiceSerializer(data=request.data, many=True)
            if not serializer.is_valid():
                return Response({"detail": "Choice data for update is not valid"}, status=status.HTTP_400_BAD_REQUEST)
            serializer.save(user=request.user, billing=billing)
            return Response(status=status.HTTP_200_OK)


@api_view(['GET', 'POST'])
def friends(request):
    if request.method == 'GET':
        user = request.user
        friends_list = [profile.user for profile in user.profile.friends.all()]
        serializer = UserSerializer(friends_list, many=True)
        return Response(serializer.data)
    if request.method == 'POST':
        user_profile = request.user.profile
        serializer = UserSerializer(data=request.data, many=True)
        if not serializer.is_valid():
            return Response({"detail": "User data for update is not valid"}, status=status.HTTP_400_BAD_REQUEST)
        if not serializer.validated_data:
            return Response({"detail": "Users list was empty"}, status=status.HTTP_200_OK)
        for user_dict in serializer.validated_data:
            member = get_object(User, user_dict['id'])
            if member == request.user:
                continue
            user_profile.friends.add(member.profile)
        user_profile.save()
        return Response(status=status.HTTP_200_OK)


@api_view(['GET'])
def users(request):
    serializer = UserSerializer(User.objects.all(), many=True)
    return Response(serializer.data)


class ContributionViewSet(mixins.ListModelMixin,
                          mixins.RetrieveModelMixin,
                          mixins.UpdateModelMixin,
                          viewsets.GenericViewSet):
    model = Contribution
    serializer_class = ContributionSerializer
    permission_action_classes = {
        "create": [IsPartyMember]
    }

    def get_queryset(self):
        user = self.request.user
        return user.contributions.all()

    def validated_choice_fields(self, data):
        if type(data['contribution']) != int or type(data['billing']) != int:
            return None
        if data['contribution'] < 1:
            return None
        if data['billing'] < 1:
            return None
        return data

    def create(self, request):
        valid_data = self.validated_choice_fields(request.data)
        paycheck_id = valid_data.pop('billing')
        check = get_object(Billing, paycheck_id)
        party = check.party
        self.check_object_permissions(request, party)
        user = request.user
        contrib = valid_data.pop('contribution')
        contribution = Contribution.objects.create(user=user, contribution=contrib, billing=check)
        return Response(ContributionSerializer(contribution).data)

    def destroy(self, request, pk):
        contribution = get_object(Contribution, pk)
        if contribution.user != request.user:
            return Response({'detail': "Contribution doesn't belong to user"}, status=status.HTTP_401_UNAUTHORIZED)
        contribution.delete()
        return Response(status=status.HTTP_200_OK)


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
        if type(data['record']) != str or type(data['quantity']) != int or type(data['billing']) != int:
            return None
        if data['quantity'] < 1:
            return None
        if data['billing'] < 1:
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
        paycheck_id = valid_data.pop('billing')
        check = get_object(Billing, paycheck_id)
        party = check.party
        self.check_object_permissions(request, party)
        record = check.records.filter(product=product).first()
        if not record:
            return Response({"detail": "No such record in billing"}, status=status.HTTP_400_BAD_REQUEST)
        if record.quantity < quantity:
            return Response({"detail": "Quantity exceeds amount of product"}, status=status.HTTP_400_BAD_REQUEST)
        user_choices = check.choices.filter(user=request.user, record=record).first()
        if user_choices:
            return Response({"detail": "This item is already picked by user"}, status=status.HTTP_400_BAD_REQUEST)
        serializer = BillingSerializer(data=valid_data)
        serializer.is_valid()
        choice = serializer.save(user=request.user, record=record, billing=check)
        return Response(ChoiceSerializer(choice).data)
