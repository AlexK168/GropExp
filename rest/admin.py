from django.contrib import admin

# Register your models here.
from rest.models import Party, Paycheck, Record, Choice, Contribution


@admin.register(Party)
@admin.register(Paycheck)
@admin.register(Record)
@admin.register(Choice)
@admin.register(Contribution)
class PersonAdmin(admin.ModelAdmin):
    pass

