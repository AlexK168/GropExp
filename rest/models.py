from django.core.validators import MinValueValidator
from django.db import models
from django.contrib.auth.models import User
from rest_framework.exceptions import NotFound


def get_object(klass, pk):
    try:
        return klass.objects.get(pk=pk)
    except klass.DoesNotExist:
        raise NotFound(detail="Object of class {} with id {} is not found".format(klass.__name__, pk), code=404)


def get_user_by_name(username):
    try:
        return User.objects.get(username=username)
    except User.DoesNotExist:
        raise NotFound(detail="User is not found", code=404)


class Profile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    friends = models.ManyToManyField('self', symmetrical=False, related_name='followees', blank=True)

    def __str__(self):
        return f"{self.user.username}'s profile"


class Party(models.Model):
    name = models.CharField(max_length=32)
    host = models.ForeignKey(User, on_delete=models.DO_NOTHING, related_name='hosted_parties')
    members = models.ManyToManyField(User, related_name='parties')

    class Meta:
        verbose_name_plural = "Parties"

    def __str__(self):
        return f"{self.name}"


class Billing(models.Model):
    party = models.OneToOneField(Party, on_delete=models.CASCADE)
    total = models.IntegerField(default=0)

    def __str__(self):
        return f"{self.party.name}" + "_bill"


class Image(models.Model):
    title = models.CharField(max_length=200)
    image = models.ImageField(upload_to='images')
    billing = models.ForeignKey(Billing, on_delete=models.CASCADE, related_name='paychecks', null=True)
    party = models.OneToOneField(Party, on_delete=models.CASCADE, related_name='picture', null=True)

    def __str__(self):
        return self.title


class Record(models.Model):
    product = models.CharField(max_length=200)
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    price = models.IntegerField(validators=[MinValueValidator(1)])
    billing = models.ForeignKey(Billing, on_delete=models.CASCADE, related_name='records')

    def __str__(self):
        return f"{self.product} - {self.price} - {self.quantity}"


class Choice(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='choices')
    quantity = models.IntegerField(validators=[MinValueValidator(1)])
    record = models.ForeignKey(Record, on_delete=models.CASCADE, related_name='choices')
    billing = models.ForeignKey(Billing, on_delete=models.CASCADE, related_name='choices')

    def __str__(self):
        return f"id:{self.id} {self.user.username} - {self.quantity} {self.record.product} in billing {self.billing.id}"


class Contribution(models.Model):
    contribution = models.IntegerField(validators=[MinValueValidator(1)])
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='contributions')
    billing = models.ForeignKey(Billing, on_delete=models.CASCADE, related_name='contributions')

    def __str__(self):
        return f"{self.user.username} - {self.contribution}"


class DebtRecord(models.Model):
    billing = models.ForeignKey(Billing, on_delete=models.CASCADE, related_name='debts')
    creditor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='loans')
    debtor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='debts')
    amount = models.IntegerField(validators=[MinValueValidator(1)])

    def __str__(self):
        return f"{self.debtor} to {self.creditor} - {self.amount}"


class DebtFromChangeRecord(models.Model):
    billing = models.ForeignKey(Billing, on_delete=models.CASCADE, related_name='change')
    creditor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='change_loans')
    amount = models.IntegerField(validators=[MinValueValidator(1)])

    def __str__(self):
        return f"{self.creditor} from change - {self.amount}"


class Balance:
    def __init__(self, user_list, total_check):
        self.user_list = user_list
        self.balances = [0 for _ in range(len(user_list))]
        self.total_balance = -total_check

    def addDebt(self, user, debt):
        index = self.user_list.index(user)
        self.balances[index] -= debt

    def addContribution(self, user, contribution):
        index = self.user_list.index(user)
        self.balances[index] += contribution
        self.total_balance += contribution

    def final(self, billing):
        debtors_list = []
        creditors_list = []
        for user, balance in zip(self.user_list, self.balances):
            if balance < 0:
                debtors_list.append((user, balance))
            elif balance > 0:
                creditors_list.append((user, balance))
        debt_records = []
        debt_from_change_records = []
        while len(debtors_list) > 0 and len(creditors_list) > 0:
            debtor, debt = debtors_list[-1]
            creditor, credit = creditors_list[-1]
            delta = debt + credit
            if delta > 0:
                debtors_list.pop()
                debt_records.append(DebtRecord(billing=billing, debtor=debtor, creditor=creditor, amount=abs(debt)))
                creditors_list[-1] = (creditor, delta)
            elif delta < 0:
                creditors_list.pop()
                debt_records.append(DebtRecord(billing=billing, debtor=debtor, creditor=creditor, amount=credit))
                debtors_list[-1] = (debtor, delta)
            else:
                debtors_list.pop()
                creditors_list.pop()
                debt_records.append(DebtRecord(billing=billing, debtor=debtor, creditor=creditor, amount=credit))

        while len(creditors_list) > 0:
            creditor, credit = creditors_list[-1]
            debt_from_change_records.append(DebtFromChangeRecord(billing=billing, creditor=creditor, amount=credit))
            creditors_list.pop()
        return debt_records, debt_from_change_records

    def __str__(self):
        res = ""
        for i in range(len(self.user_list)):
            username = self.user_list[i].username
            debt = self.balances[i]
            res += f"{username}: {debt}\n"
        return res
