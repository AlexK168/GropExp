from django.db import transaction
from rest_framework import serializers
from rest.models import Party, Paycheck, Record, Choice, get_object


class PartySerializer(serializers.ModelSerializer):
    members = serializers.SlugRelatedField(slug_field='username', read_only=True, many=True)

    class Meta:
        model = Party
        fields = '__all__'


class RecordListSerializer(serializers.ListSerializer):
    def validate(self, attrs):
        products = [item['product'] for item in attrs]
        if len(products) > len(set(products)):
            raise serializers.ValidationError('Check must contain unique products')
        return attrs

    def update(self, instance, validated_data):
        pass

    def create(self, validated_data):
        records = [Record(**item) for item in validated_data]
        return Record.objects.bulk_create(records)


class RecordSerializer(serializers.Serializer):
    def create(self, validated_data):
        return Record.objects.create(validated_data)

    def update(self, instance, validated_data):
        pass

    class Meta:
        list_serializer_class = RecordListSerializer

    product = serializers.CharField(max_length=64)
    quantity = serializers.IntegerField()
    price = serializers.IntegerField()


class PaycheckSerializer(serializers.ModelSerializer):
    class Meta:
        model = Paycheck
        fields = ("records", "total")

    records = RecordSerializer(many=True)

    def create(self, validated_data):
        records = validated_data.pop('records')
        party = validated_data.pop('party')
        check = Paycheck(party=party)
        total = sum([item['quantity'] * item['price'] for item in records])
        check.total = total
        check.save()
        Record.objects.bulk_create([Record(paycheck=check, **item) for item in records])
        return check

    def update(self, instance, validated_data):
        old_records = instance.records.all()
        validated_records = validated_data.pop('records')
        new_records = [record['product'] for record in validated_records]
        with transaction.atomic():
            for record in instance.records.all():
                if record.product not in new_records:
                    record.delete()
            total = 0
            for record in validated_records:
                total += record['price'] * record['quantity']
                record_to_update = old_records.filter(product=record['product']).first()
                if record_to_update:
                    record_to_update.quantity = record['quantity']
                    record_to_update.price = record['price']
                    record_to_update.save()
                else:
                    Record.objects.create(paycheck=instance, **record)
            instance.total = total
            instance.save()
        return instance


class ChoiceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Choice
        fields = ("quantity",)
