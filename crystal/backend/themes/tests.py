import datetime as dt
import json

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from .models import FestivalTheme


class OneOnAtATimeTests(TestCase):
    def test_seeded_all_off(self):
        self.assertEqual(FestivalTheme.objects.count(), 13)
        self.assertFalse(FestivalTheme.objects.filter(is_active=True).exists())

    def test_switching_one_on_switches_others_off(self):
        diwali = FestivalTheme.objects.get(slug='diwali')
        holi = FestivalTheme.objects.get(slug='holi')
        diwali.is_active = True
        diwali.save()
        holi.is_active = True
        holi.save()
        on = list(FestivalTheme.objects.filter(is_active=True).values_list('slug', flat=True))
        self.assertEqual(on, ['holi'])


class FeedTests(TestCase):
    url = '/api/theme.json'

    def feed(self, **params):
        res = self.client.get(self.url, params)
        self.assertEqual(res.status_code, 200)
        return res, json.loads(res.content)

    def test_all_off_is_null(self):
        res, data = self.feed()
        self.assertIsNone(data['theme'])
        self.assertIn('max-age=120', res['Cache-Control'])

    def test_active_theme_is_served(self):
        FestivalTheme.objects.filter(slug='christmas').update(is_active=True)
        _, data = self.feed()
        self.assertEqual(data['theme']['slug'], 'christmas')
        self.assertEqual(data['theme']['scope'], 'site')
        self.assertEqual(data['theme']['intensity'], 'festive')
        self.assertTrue(data['theme']['greeting'])

    def test_dates_are_respected(self):
        today = timezone.localdate()
        t = FestivalTheme.objects.get(slug='diwali')
        t.is_active = True
        t.starts_on = today + dt.timedelta(days=3)
        t.save()
        self.assertIsNone(self.feed()[1]['theme'], 'not started yet')

        t.starts_on = today - dt.timedelta(days=5)
        t.ends_on = today - dt.timedelta(days=1)
        t.save()
        self.assertIsNone(self.feed()[1]['theme'], 'already over')

        t.ends_on = today
        t.save()
        self.assertEqual(self.feed()[1]['theme']['slug'], 'diwali', 'last day counts')

    def test_preview_ignores_switch_and_is_not_cached(self):
        res, data = self.feed(preview='eid')
        self.assertEqual(data['theme']['slug'], 'eid')
        self.assertEqual(res['Cache-Control'], 'no-store')
        self.assertFalse(FestivalTheme.objects.get(slug='eid').is_active)


class AdminListToggleTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.user = User.objects.create_superuser('admin', 'a@example.com', 'pw')
        self.client.force_login(self.user)
        self.url = reverse('admin:themes_festivaltheme_changelist')

    def post_list(self, ticked):
        rows = list(FestivalTheme.objects.order_by('order', 'id'))
        data = {
            'form-TOTAL_FORMS': str(len(rows)), 'form-INITIAL_FORMS': str(len(rows)),
            'form-MIN_NUM_FORMS': '0', 'form-MAX_NUM_FORMS': '1000', '_save': 'Save',
        }
        for i, r in enumerate(rows):
            data['form-%d-id' % i] = str(r.pk)
            if r.slug in ticked:
                data['form-%d-is_active' % i] = 'on'
        return self.client.post(self.url, data)

    def on(self):
        return list(FestivalTheme.objects.filter(is_active=True).values_list('slug', flat=True))

    def test_switching_on_a_second_one_replaces_the_first(self):
        FestivalTheme.objects.filter(slug='diwali').update(is_active=True)
        # The old one still ticked (no JS), the new one ticked too: new one wins.
        res = self.post_list({'diwali', 'holi'})
        self.assertEqual(res.status_code, 302)
        self.assertEqual(self.on(), ['holi'])

    def test_switching_two_on_at_once_is_refused(self):
        res = self.post_list({'holi', 'eid'})
        self.assertEqual(res.status_code, 200)
        self.assertContains(res, 'Only one festival theme can be on at a time')
        self.assertEqual(self.on(), [])

    def test_turn_all_off(self):
        FestivalTheme.objects.filter(slug='onam').update(is_active=True)
        res = self.client.post(reverse('admin:themes_festivaltheme_all_off'))
        self.assertEqual(res.status_code, 302)
        self.assertEqual(self.on(), [])

    def test_changelist_renders(self):
        res = self.client.get(self.url)
        self.assertContains(res, 'Only one theme can be on at a time')
        self.assertContains(res, '?theme=diwali')
