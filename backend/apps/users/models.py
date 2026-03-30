from django.db import models


class LDAPGroup(models.Model):
    name = models.CharField(max_length=64, unique=True)  # cn v LDAP
    label = models.CharField(max_length=128)
    vlan = models.PositiveSmallIntegerField()

    class Meta:
        ordering = ['name']

    def __str__(self):
        return f'{self.label} (VLAN {self.vlan})'
