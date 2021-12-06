from django.contrib import admin

# Register your models here.
from rest.models import Party, Paycheck, Record, Choice


@admin.register(Party)
@admin.register(Paycheck)
@admin.register(Record)
@admin.register(Choice)
class PersonAdmin(admin.ModelAdmin):
    pass

