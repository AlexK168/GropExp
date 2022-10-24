from rest_framework import serializers
from rest.models import *
from django.db.models import Sum, F


class UserCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['email', 'username', 'password']
        extra_kwargs = {
            'email': {'required': True},
            'username': {'required': True},
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = User(
            email=validated_data['email'],
            username=validated_data['username']
        )
        user.set_password(validated_data['password'])
        user.save()
        profile = Profile(user=user)
        profile.save()
        return user


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email']
        extra_kwargs = {
            'id': {'read_only': False},
            'username': {'read_only': True},
            'email': {'read_only': True}
        }

    def validate_id(self, value):
        try:
            User.objects.get(pk=value)
        except User.DoesNotExist:
            raise serializers.ValidationError("User with id {} doesn't exist".format(value))
        return value


class RecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Record
        fields = '__all__'
        extra_kwargs = {
            'billing': {'read_only': True},
            'id': {'read_only': False}
        }


class DebtRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebtRecord
        fields = "__all__"

    debtor = UserSerializer()
    creditor = UserSerializer()


class DebtFromChangeRecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = DebtFromChangeRecord
        fields = "__all__"

    creditor = UserSerializer()


class ResultSerializer(serializers.Serializer):
    debts = DebtRecordSerializer(many=True, read_only=True)
    change = DebtFromChangeRecordSerializer(many=True, read_only=True)


class ContributionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contribution
        fields = "__all__"
        extra_kwargs = {
            'id': {'read_only': True},
            'user': {'read_only': True},
            'contribution': {'read_only': False},
            'billing': {'read_only': True}
        }

    user = serializers.SlugRelatedField(slug_field='username', read_only=True)


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = "__all__"
        extra_kwargs = {
            'id': {'read_only': True},
            'quantity': {'read_only': False},
            'billing': {'read_only': True}
        }

    user = UserSerializer(read_only=True)
    record = RecordSerializer(read_only=False)

    def create(self, validated_data):
        user = validated_data.pop('user')
        record = validated_data.pop('record')
        billing = validated_data.pop('billing')
        record_instance = get_object(Record, record['id'])
        Choice.objects.create(
            user=user,
            record=record_instance,
            billing=billing,
            quantity=validated_data.pop('quantity')
        )


class BillingSerializer(serializers.ModelSerializer):
    records = RecordSerializer(many=True)
    change = DebtFromChangeRecordSerializer(many=True, read_only=True)
    debts = DebtRecordSerializer(many=True, read_only=True)
    contributions = ContributionSerializer(many=True, read_only=True)
    choices = ChoiceSerializer(many=True, read_only=True)

    class Meta:
        model = Billing
        fields = '__all__'
        extra_kwargs = {
            'total': {'read_only': True},
            'party': {'read_only': True},
        }

    def update(self, instance, validated_data):
        records_list = validated_data['records']
        all_records = instance.records.all()
        records = []
        for r in records_list:
            if r['id'] == 0:
                r.pop('id')
            records.append(Record(**r, billing=instance))
        for record in records:
            record.save()
        for record in all_records:
            if record not in records:
                record.delete()
        total = instance.records.aggregate(total=Sum(F('quantity') * F('price')))
        instance.total = total.get('total')
        instance.save()
        return instance


class PartySerializer(serializers.ModelSerializer):
    members = UserSerializer(many=True, required=False)
    host = UserSerializer(read_only=True)

    class Meta:
        model = Party
        fields = ['id', 'name', 'host', 'members', 'billing']
        extra_kwargs = {
            'billing': {'read_only': True}
        }

    def create(self, validated_data):
        host = validated_data.get("host")
        if "members" not in validated_data:
            party = Party.objects.create(**validated_data)
            party.members.add(host)
            return party
        members = validated_data.pop('members')
        party = Party.objects.create(**validated_data)
        party.members.add(host)
        for m in members:
            member_id = m['id']
            member = get_object(User, member_id)
            party.members.add(member)
        return party

    def update(self, instance, validated_data):
        if "name" in validated_data:
            instance.name = validated_data["name"]
        if "members" in validated_data:
            validated_data.pop("members")
        if "host" in validated_data:
            host_dict = validated_data["host"]
            if "id" in host_dict:
                host_id = host_dict["id"]
                host = get_object(User, host_id)
                if host in instance.members:
                    instance.host = host
        instance.save()
        return instance

