from rest_framework import permissions


class IsPartyHost(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return obj.host == request.user


class IsPartyMember(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        return request.user in obj.members.all()
