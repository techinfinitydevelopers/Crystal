"""What the super admin has hidden from the other admins.

The super admin is a Django superuser. Every other staff account is an
"admin": it can use the whole dashboard (see access.backends) except what is
listed here. One row hides one thing, either from every admin (user empty) or
from one admin only.

Kinds:
  app      a whole sidebar group, key = app label ("products")
  model    one sidebar entry, key = "app_label.model_name" ("products.brand")
  page     one website page in Pages, key = its filename ("About.html")
  group    one band of a page's sections, key = "About.html::hero"
  section  one section (a heading, a paragraph, an image), key = PageSection id
"""
from django.conf import settings
from django.db import models


class HiddenFeature(models.Model):
    APP = 'app'
    MODEL = 'model'
    PAGE = 'page'
    GROUP = 'group'
    SECTION = 'section'
    KIND_CHOICES = [
        (APP, 'Sidebar group'),
        (MODEL, 'Sidebar item'),
        (PAGE, 'Website page'),
        (GROUP, 'Part of a page'),
        (SECTION, 'Single section / image'),
    ]

    kind = models.CharField(max_length=10, choices=KIND_CHOICES)
    key = models.CharField(max_length=200)
    label = models.CharField(max_length=200, blank=True)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE,
        related_name='+',
        help_text='Empty = hidden from every admin. Super admins always see everything.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [('kind', 'key', 'user')]
        ordering = ['kind', 'key']
        verbose_name = 'Hidden item'
        verbose_name_plural = 'Super admin control'

    def __str__(self):
        who = self.user.get_username() if self.user_id else 'all admins'
        return f'{self.get_kind_display()}: {self.label or self.key} (hidden from {who})'
