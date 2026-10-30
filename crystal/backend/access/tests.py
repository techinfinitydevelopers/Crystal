import json

from django.contrib.auth import get_user_model
from django.test import TestCase

from content.models import Page, PageSection

from .models import HiddenFeature


class SuperAdminControlTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.boss = User.objects.create_superuser('boss', 'b@x.com', 'x')
        self.admin = User.objects.create_user('ram', 'r@x.com', 'x', is_staff=True)
        self.other = User.objects.create_user('shyam', 's@x.com', 'x', is_staff=True)
        self.page, _ = Page.objects.get_or_create(filename='About.html', defaults={'title': 'About', 'group': 'Company'})
        PageSection.objects.filter(page='About.html').delete()
        self.hero = PageSection.objects.create(page='About.html', section_key='hero-h1-1', section='hero', label='Hero heading')
        self.pic = PageSection.objects.create(page='About.html', section_key='vmv-img-1', section='vmv', kind='image', label='VMV photo')

    def login(self, user):
        self.client.force_login(user)

    def toggle(self, **data):
        return self.client.post('/admin/access/hiddenfeature/control/toggle/', json.dumps(data),
                                content_type='application/json')

    def test_admin_gets_dashboard_but_not_users_or_control(self):
        self.login(self.admin)
        self.assertEqual(self.client.get('/admin/products/product/').status_code, 200)
        self.assertEqual(self.client.get('/admin/auth/user/').status_code, 403)
        self.assertEqual(self.client.get('/admin/access/hiddenfeature/control/').status_code, 403)

    def test_hiding_a_sidebar_item_removes_and_blocks_it(self):
        self.login(self.boss)
        self.assertEqual(self.client.get('/admin/access/hiddenfeature/control/').status_code, 200)
        self.assertTrue(self.toggle(kind='model', key='products.brand', hidden=True).json()['ok'])
        self.login(self.admin)
        home = self.client.get('/admin/').content.decode()
        self.assertNotIn('/admin/products/brand/', home)
        self.assertIn('/admin/products/product/', home)
        r = self.client.get('/admin/products/brand/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get('/admin/products/brand/add/').status_code, 302)
        # super admin unaffected
        self.login(self.boss)
        self.assertEqual(self.client.get('/admin/products/brand/').status_code, 200)

    def test_hiding_a_whole_group(self):
        self.login(self.boss)
        self.toggle(kind='app', key='products', hidden=True)
        self.login(self.admin)
        self.assertEqual(self.client.get('/admin/products/category/').status_code, 302)
        self.assertEqual(self.client.get('/admin/products/').status_code, 302)
        home = self.client.get('/admin/').content.decode()
        self.assertNotIn('/admin/products/category/', home)
        self.assertNotIn('/admin/products/product/add/', home)

    def test_page_and_sections(self):
        self.login(self.boss)
        self.toggle(kind='section', key=str(self.pic.pk), hidden=True)
        self.login(self.admin)
        editor = self.client.get('/admin/content/page/%d/editor/' % self.page.pk).content.decode()
        self.assertIn('hero-h1-1', editor)
        self.assertNotIn('vmv-img-1', editor)
        self.login(self.boss)
        self.toggle(kind='page', key='About.html', hidden=True)
        self.login(self.admin)
        self.assertEqual(self.client.get('/admin/content/page/%d/editor/' % self.page.pk).status_code, 302)
        self.assertNotIn('About', self.client.get('/admin/content/page/').content.decode().split('result_list')[-1][:3000])

    def test_group_hidden(self):
        self.login(self.boss)
        self.toggle(kind='group', key='About.html::hero', hidden=True)
        self.login(self.admin)
        editor = self.client.get('/admin/content/page/%d/editor/' % self.page.pk).content.decode()
        self.assertNotIn('hero-h1-1', editor)
        self.assertIn('vmv-img-1', editor)

    def test_hide_for_one_admin_only(self):
        self.login(self.boss)
        self.toggle(kind='model', key='products.brand', user=str(self.admin.pk), hidden=True)
        self.login(self.admin)
        self.assertEqual(self.client.get('/admin/products/brand/').status_code, 302)
        self.login(self.other)
        self.assertEqual(self.client.get('/admin/products/brand/').status_code, 200)

    def test_unhide(self):
        self.login(self.boss)
        self.toggle(kind='model', key='products.brand', hidden=True)
        self.toggle(kind='model', key='products.brand', hidden=False)
        self.assertFalse(HiddenFeature.objects.exists())

    def test_page_json(self):
        self.login(self.boss)
        d = self.client.get('/admin/access/hiddenfeature/control/page/%d.json' % self.page.pk).json()
        self.assertEqual({g['name'] for g in d['groups']}, {'Hero', 'Vmv'})

    def test_admin_cannot_toggle(self):
        self.login(self.admin)
        self.assertEqual(self.toggle(kind='model', key='products.brand', hidden=True).status_code, 403)
