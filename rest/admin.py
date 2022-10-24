from django.contrib import admin

# Register your models here.
from rest.models import *


@admin.register(Party)
@admin.register(Billing)
@admin.register(Record)
@admin.register(Profile)
@admin.register(Choice)
@admin.register(Contribution)
@admin.register(DebtRecord)
@admin.register(DebtFromChangeRecord)
class PersonAdmin(admin.ModelAdmin):
    pass

