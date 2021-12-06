from django.contrib import admin

# Register your models here.
from rest.models import Party, Paycheck, Record


@admin.register(Party)
@admin.register(Paycheck)
@admin.register(Record)
class PersonAdmin(admin.ModelAdmin):
    pass

