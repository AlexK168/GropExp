from rest_framework import serializers, status
from rest.models import Party, Paycheck, Record, get_object
from django.db.utils import IntegrityError
from rest_framework.response import Response


class PartySerializer(serializers.ModelSerializer):
    members = serializers.SlugRelatedField(slug_field='username', read_only=True, many=True)

    class Meta:
        model = Party
        fields = '__all__'


class RecordSerializer(serializers.ModelSerializer):
    class Meta:
        model = Record
        exclude = ('id', 'paycheck')


class PaycheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paycheck
        fields = ("records", "total")
    records = RecordSerializer(many=True)

    def create(self, validated_data):
        print(validated_data)
        records = validated_data.pop('records')
        party = validated_data.pop('party')
        if hasattr(party, 'paycheck'):
            raise serializers.ValidationError('Check already exists')

        check = Paycheck(party=party)
        products = [item['product'] for item in records]
        if len(products) > len(set(products)):
            raise serializers.ValidationError('Check must contain unique products')
        total = sum([item['quantity'] * item['price'] for item in records])
        check.total = total
        check.save()
        Record.objects.bulk_create([Record(paycheck=check, **item) for item in records])
        return check

#
# class CreateChoiceSerializer(serializers.ModelSerializer):
#     class Meta:
#         model = Choice
#         fields = ()