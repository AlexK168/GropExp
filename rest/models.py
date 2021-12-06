from django.db import models
from django.contrib.auth.models import User
from rest_framework.exceptions import NotFound


def get_object(klass, pk):
    try:
        return klass.objects.get(pk=pk)
    except klass.DoesNotExist:
        raise NotFound(detail="Object of class {} is not found".format(klass.__name__), code=404)


class Party(models.Model):
    name = models.CharField(max_length=32)
    host = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='hosted_parties')
    members = models.ManyToManyField(User, related_name='parties')

    class Meta:
        verbose_name_plural = "Parties"

    def __str__(self):
        return f"{self.name}"


# class Contribution(models.Model):
#     contribution = models.IntegerField()
#     user = models.ForeignKey(User, on_delete=models.CASCADE)
#     party = models.ForeignKey(Party, on_delete=models.CASCADE)


class Paycheck(models.Model):
    party = models.OneToOneField(Party, on_delete=models.CASCADE)
    total = models.IntegerField(default=0)


class Record(models.Model):
    product = models.CharField(max_length=64)
    quantity = models.IntegerField()
    price = models.IntegerField()
    paycheck = models.ForeignKey(Paycheck, on_delete=models.CASCADE, related_name='records')

    def __str__(self):
        return f"{self.product}"


class Choice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    quantity = models.IntegerField()
    record = models.ForeignKey(Record, on_delete=models.CASCADE)
