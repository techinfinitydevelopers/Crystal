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
        if user.is_superuser:
            # What a sign-in on /admin/super/login/ records (access.sites).
            from .sites import SESSION_KEY
            s = self.client.session
            s[SESSION_KEY] = user.pk
            s.save()

    def toggle(self, **data):
        return self.client.post('/admin/super/access/hiddenfeature/control/toggle/', json.dumps(data),
                                content_type='application/json')

    def test_admin_gets_dashboard_but_not_users_or_control(self):
        self.login(self.admin)
        self.assertEqual(self.client.get('/admin/products/product/').status_code, 200)
        # Accounts are not in the everyday dashboard any more, for anyone.
        self.assertEqual(self.client.get('/admin/auth/user/').status_code, 404)
        # The super admin dashboard sends an admin to its sign-in page.
        self.assertEqual(self.client.get('/admin/super/').status_code, 302)
        self.assertEqual(self.client.get('/admin/super/access/hiddenfeature/control/').status_code, 302)

    def test_hiding_a_sidebar_item_removes_and_blocks_it(self):
        self.login(self.boss)
        self.assertEqual(self.client.get('/admin/super/access/hiddenfeature/control/').status_code, 200)
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
        d = self.client.get('/admin/super/access/hiddenfeature/control/page/%d.json' % self.page.pk).json()
        self.assertEqual({g['name'] for g in d['groups']}, {'Hero', 'Vmv'})

    def test_admin_cannot_toggle(self):
        self.login(self.admin)
        self.assertNotEqual(self.toggle(kind='model', key='products.brand', hidden=True).status_code, 200)
        self.assertFalse(HiddenFeature.objects.exists())

    def test_super_dashboard_sign_in_is_super_admins_only(self):
        self.client.logout()
        r = self.client.post('/admin/super/login/', {'username': 'ram', 'password': 'x'})
        self.assertContains(r, 'Only a super admin can sign in here')
        r = self.client.post('/admin/super/login/', {'username': 'boss', 'password': 'x'})
        self.assertEqual(r.status_code, 302)
        home = self.client.get('/admin/super/')
        self.assertContains(home, 'ram')
        self.assertContains(home, '/admin/super/access/hiddenfeature/control/')

    def test_everyday_sign_in_does_not_open_super_dashboard(self):
        self.client.logout()
        self.assertTrue(self.client.login(username='boss', password='x'))   # as on /admin/login/
        self.assertEqual(self.client.get('/admin/products/product/').status_code, 200)
        r = self.client.get('/admin/super/')
        self.assertEqual(r.status_code, 302)
        self.assertIn('/admin/super/login/', r['Location'])
        self.client.post('/admin/super/login/', {'username': 'boss', 'password': 'x'})
        self.assertEqual(self.client.get('/admin/super/').status_code, 200)

    def test_everyday_dashboard_has_no_accounts_or_switches(self):
        self.login(self.boss)
        home = self.client.get('/admin/').content.decode()
        self.assertNotIn('/admin/access/', home)
        self.assertNotIn('/admin/auth/user/', home)
        self.assertIn('/admin/super/', home)       # the user-menu link, super admins only
        self.login(self.admin)
        self.assertNotIn('/admin/super/', self.client.get('/admin/').content.decode())

    def test_create_account_with_role_and_password(self):
        self.login(self.boss)
        r = self.client.post('/admin/super/auth/user/add/', {
            'username': 'geeta', 'password1': 'Kadhai-Tawa-77', 'password2': 'Kadhai-Tawa-77', 'role': 'admin'})
        self.assertEqual(r.status_code, 302, r.content.decode()[:2000])
        u = get_user_model().objects.get(username='geeta')
        self.assertTrue(u.is_staff and u.is_active and not u.is_superuser)
        self.assertTrue(u.check_password('Kadhai-Tawa-77'))
        self.client.logout()
        self.assertTrue(self.client.login(username='geeta', password='Kadhai-Tawa-77'))
        self.assertEqual(self.client.get('/admin/products/product/').status_code, 200)

    def test_seo_role_gets_only_seo_screens(self):
        from .roles import apply_role
        apply_role(self.other, 'seo')
        self.login(self.other)
        self.assertEqual(self.client.get('/admin/seo/seometa/').status_code, 200)
        self.assertEqual(self.client.get('/admin/products/product/').status_code, 403)

    def test_block_an_account(self):
        self.login(self.boss)
        url = '/admin/super/auth/user/%d/change/' % self.admin.pk
        r = self.client.post(url, {'username': 'ram', 'role': 'admin', 'first_name': '', 'last_name': '',
                                   'email': 'r@x.com'})   # is_active unticked
        self.assertEqual(r.status_code, 302, r.content.decode()[:2000])
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.is_active)

    def test_hide_and_show_everything_at_once(self):
        self.login(self.boss)
        items = [{'kind': 'app', 'key': 'products'}, {'kind': 'page', 'key': 'About.html'}]
        r = self.client.post('/admin/super/access/hiddenfeature/control/toggle/',
                             json.dumps({'items': items, 'hidden': True}), content_type='application/json')
        self.assertEqual(r.json()['count'], 2)
        self.assertEqual(HiddenFeature.objects.count(), 2)
        self.client.post('/admin/super/access/hiddenfeature/control/toggle/',
                         json.dumps({'items': items, 'hidden': False}), content_type='application/json')
        self.assertFalse(HiddenFeature.objects.exists())

    def test_block_unblock_and_remove_from_home(self):
        self.login(self.boss)
        self.assertContains(self.client.get('/admin/super/'), '/admin/super/auth/user/%d/delete/' % self.admin.pk)
        self.client.post('/admin/super/auth/user/%d/signin/' % self.admin.pk)
        self.admin.refresh_from_db()
        self.assertFalse(self.admin.is_active)
        self.client.post('/admin/super/auth/user/%d/signin/' % self.boss.pk)   # never yourself
        self.boss.refresh_from_db()
        self.assertTrue(self.boss.is_active)
        r = self.client.post('/admin/super/auth/user/%d/delete/' % self.other.pk, {'post': 'yes'})
        self.assertEqual(r.status_code, 302)
        self.assertFalse(get_user_model().objects.filter(pk=self.other.pk).exists())
        self.assertNotEqual(self.client.get('/admin/super/auth/user/%d/delete/' % self.boss.pk).status_code, 200)

    def test_cannot_lock_yourself_out(self):
        self.login(self.boss)
        url = '/admin/super/auth/user/%d/change/' % self.boss.pk
        r = self.client.post(url, {'username': 'boss', 'role': 'admin', 'is_active': 'on', 'email': 'b@x.com'})
        self.assertContains(r, 'lock yourself out')
        self.boss.refresh_from_db()
        self.assertTrue(self.boss.is_superuser)


class SuperDashboardHasEverythingTests(TestCase):
    """Every screen of the everyday dashboard opens on /admin/super/ too."""

    def setUp(self):
        from .sites import SESSION_KEY
        self.boss = get_user_model().objects.create_superuser('boss', 'b@x.com', 'x')
        self.client.force_login(self.boss)
        s = self.client.session
        s[SESSION_KEY] = self.boss.pk
        s.save()

    def test_every_list_and_add_screen_opens(self):
        from django.contrib import admin
        from django.urls import reverse
        home = self.client.get('/admin/super/')
        self.assertEqual(home.status_code, 200)
        body = home.content.decode()
        self.assertIn('Super Admin Dashboard', body)
        self.assertIn('/admin/super/products/product/', body)     # sidebar + quick actions stay here
        broken = []
        for model, ma in admin.site._registry.items():
            meta = model._meta
            for view in ('changelist', 'add'):
                try:
                    url = reverse(f'superadmin:{meta.app_label}_{meta.model_name}_{view}')
                except Exception:
                    continue
                r = self.client.get(url)
                if r.status_code >= 400 and not (view == 'add' and r.status_code == 403):
                    broken.append((url, r.status_code))
        self.assertEqual(broken, [])

    def test_redirecting_screens_stay_inside(self):
        r = self.client.get('/admin/super/access/hiddenfeature/')
        self.assertEqual(r['Location'], '/admin/super/access/hiddenfeature/control/')
        r = self.client.get('/admin/super/awards/awardsettings/')
        self.assertTrue(r['Location'].startswith('/admin/super/awards/awardsettings/'), r['Location'])

    def test_recent_actions_link_inside(self):
        from django.contrib.admin.models import LogEntry, CHANGE
        from django.contrib.contenttypes.models import ContentType
        LogEntry.objects.create(user=self.boss, content_type=ContentType.objects.get_for_model(self.boss),
                                object_id=str(self.boss.pk), object_repr='boss', action_flag=CHANGE)
        body = self.client.get('/admin/super/').content.decode()
        self.assertIn('href="/admin/super/auth/user/%d/change/"' % self.boss.pk, body)
        self.assertNotIn('href="None"', body)
        self.assertNotIn('href="None"', self.client.get('/admin/').content.decode())
