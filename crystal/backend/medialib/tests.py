import io
import os
import shutil
import tempfile

from django import forms
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management import call_command
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from banners.models import CategoryBanner

from .models import MediaItem
from .picking import PickedFile
from .usage import delete_file_if_unused, usage_map


def png_bytes(w=8, h=5, colour=(237, 51, 56)):
    buf = io.BytesIO()
    Image.new('RGB', (w, h), colour).save(buf, 'PNG')
    return buf.getvalue()


def all_stored_files(root):
    out = set()
    for dirpath, _dirs, files in os.walk(root):
        for f in files:
            out.add(os.path.relpath(os.path.join(dirpath, f), root).replace(os.sep, '/'))
    return out


class BannerForm(forms.ModelForm):
    class Meta:
        model = CategoryBanner
        fields = ('page', 'image')


class OptionalFileForm(forms.Form):
    attachment = forms.FileField(required=False)


class MediaRootMixin:
    def setUp(self):
        super().setUp()
        self.media = tempfile.mkdtemp(prefix='medialib-test-')
        self._override = override_settings(MEDIA_ROOT=self.media)
        self._override.enable()

    def tearDown(self):
        self._override.disable()
        shutil.rmtree(self.media, ignore_errors=True)
        super().tearDown()

    def put(self, name, content):
        return default_storage.save(name, ContentFile(content))


class PickingTests(MediaRootMixin, TestCase):
    def test_picked_image_points_at_the_existing_file_without_copying(self):
        self.put('library/x.jpg', png_bytes())
        before = all_stored_files(self.media)

        form = BannerForm(data={'page': 'Cookware.html', 'image__media': 'library/x.jpg'},
                          files={})
        self.assertTrue(form.is_valid(), form.errors)  # Pillow verify still ran and passed
        banner = form.save()

        banner.refresh_from_db()
        self.assertEqual(banner.image.name, 'library/x.jpg')
        self.assertEqual(all_stored_files(self.media), before)  # nothing new on disk

    def test_a_real_upload_wins_over_a_pick(self):
        self.put('library/x.jpg', png_bytes())
        up = SimpleUploadedFile('new.png', png_bytes(), content_type='image/png')
        form = BannerForm(data={'page': 'A.html', 'image__media': 'library/x.jpg'},
                          files={'image': up})
        self.assertTrue(form.is_valid(), form.errors)
        banner = form.save()
        self.assertTrue(banner.image.name.startswith('category-banners/new'))

    def test_picking_a_non_image_into_an_image_field_is_refused(self):
        self.put('library/brochure.pdf', b'%PDF-1.4 not a picture')
        form = BannerForm(data={'page': 'A.html', 'image__media': 'library/brochure.pdf'},
                          files={})
        self.assertFalse(form.is_valid())
        self.assertIn('image', form.errors)

    def test_missing_or_escaping_names_are_ignored(self):
        for bad in ('library/nope.jpg', '../settings.py', '/etc/passwd', 'a/../../b.jpg'):
            form = BannerForm(data={'page': 'A.html', 'image__media': bad}, files={})
            self.assertFalse(form.is_valid(), bad)  # image is required and nothing usable came
            self.assertIn('image', form.errors)

    def test_clear_semantics_are_unchanged(self):
        self.put('library/a.pdf', b'%PDF-1.4')
        # pick alone -> a PickedFile
        f = OptionalFileForm(data={'attachment__media': 'library/a.pdf'}, files={})
        self.assertTrue(f.is_valid(), f.errors)
        self.assertIsInstance(f.cleaned_data['attachment'], PickedFile)
        # clear alone -> False (clear the field)
        f = OptionalFileForm(data={'attachment-clear': 'on'}, files={})
        self.assertTrue(f.is_valid())
        self.assertIs(f.cleaned_data['attachment'], False)
        # clear AND pick -> the same contradiction error as clear AND upload
        f = OptionalFileForm(data={'attachment-clear': 'on',
                                   'attachment__media': 'library/a.pdf'}, files={})
        self.assertFalse(f.is_valid())
        # nothing at all -> unchanged
        f = OptionalFileForm(data={}, files={})
        self.assertTrue(f.is_valid())
        self.assertIsNone(f.cleaned_data['attachment'])

    def test_pick_on_an_existing_row_replaces_without_copying(self):
        self.put('library/one.png', png_bytes())
        self.put('library/two.png', png_bytes(4, 4))
        banner = CategoryBanner.objects.create(page='B.html', image='library/one.png')
        before = all_stored_files(self.media)
        form = BannerForm(data={'page': 'B.html', 'image__media': 'library/two.png'},
                          files={}, instance=banner)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()
        banner.refresh_from_db()
        self.assertEqual(banner.image.name, 'library/two.png')
        self.assertEqual(all_stored_files(self.media), before)


class IndexingTests(MediaRootMixin, TestCase):
    def test_index_media_points_at_same_names_and_is_idempotent(self):
        self.put('category-banners/a.png', png_bytes(20, 10))
        CategoryBanner.objects.filter(page='A.html').delete()
        MediaItem.objects.all().delete()
        # bypass post_save so the command is what does the work
        CategoryBanner.objects.bulk_create([
            CategoryBanner(page='A.html', image='category-banners/a.png'),
            CategoryBanner(page='Gone.html', image='category-banners/missing.png'),
        ])
        before = all_stored_files(self.media)
        call_command('index_media', stdout=io.StringIO())
        call_command('index_media', stdout=io.StringIO())

        items = MediaItem.objects.filter(file='category-banners/a.png')
        self.assertEqual(items.count(), 1)
        item = items.get()
        self.assertEqual((item.width, item.height), (20, 10))
        self.assertEqual(item.kind, MediaItem.IMAGE)
        self.assertEqual(item.source, 'Category banners › Category banner')
        self.assertFalse(MediaItem.objects.filter(file='category-banners/missing.png').exists())
        self.assertEqual(all_stored_files(self.media), before)

    def test_saving_any_model_with_a_file_indexes_it(self):
        self.put('category-banners/b.png', png_bytes())
        CategoryBanner.objects.create(page='B.html', image='category-banners/b.png')
        self.assertTrue(MediaItem.objects.filter(file='category-banners/b.png').exists())


class DeleteTests(MediaRootMixin, TestCase):
    def test_file_kept_while_another_model_uses_it(self):
        name = self.put('library/used.png', png_bytes())
        CategoryBanner.objects.create(page='C.html', image=name)
        item = MediaItem.objects.get(file=name)
        self.assertTrue(usage_map([name])[name])
        pk = item.pk
        item.delete()
        self.assertFalse(delete_file_if_unused(name, exclude_pk=pk))
        self.assertTrue(default_storage.exists(name))

    def test_unused_file_is_removed(self):
        item = MediaItem(file=SimpleUploadedFile('lonely.png', png_bytes()))
        item.save()
        name, pk = item.file.name, item.pk
        self.assertTrue(default_storage.exists(name))
        item.delete()
        self.assertTrue(delete_file_if_unused(name, exclude_pk=pk))
        self.assertFalse(default_storage.exists(name))

    def test_website_files_are_never_deleted(self):
        name = self.put('product-photos/X-1/hero.png', png_bytes())
        self.assertFalse(delete_file_if_unused(name))
        self.assertTrue(default_storage.exists(name))


class AdminTests(MediaRootMixin, TestCase):
    def setUp(self):
        super().setUp()
        self.user = get_user_model().objects.create_superuser('boss', 'b@example.com', 'x')
        self.client.force_login(self.user)

    def test_picker_json_is_staff_only(self):
        self.client.logout()
        r = self.client.get(reverse('admin:medialib_mediaitem_picker'))
        self.assertEqual(r.status_code, 302)

    def test_upload_json_then_picker_lists_it(self):
        up = SimpleUploadedFile('fresh.png', png_bytes(), content_type='image/png')
        r = self.client.post(reverse('admin:medialib_mediaitem_upload_json'), {'file': up})
        self.assertEqual(r.status_code, 200, r.content)
        item = r.json()['items'][0]
        self.assertTrue(item['name'].startswith('library/'))
        self.assertEqual(item['kind'], 'image')

        r = self.client.get(reverse('admin:medialib_mediaitem_picker'), {'kind': 'image', 'q': 'fresh'})
        self.assertEqual([i['id'] for i in r.json()['items']], [item['id']])
        r = self.client.get(reverse('admin:medialib_mediaitem_picker'), {'kind': 'pdf'})
        self.assertEqual(r.json()['items'], [])

    def test_html_uploads_are_refused(self):
        up = SimpleUploadedFile('evil.html', b'<script>alert(1)</script>', content_type='text/html')
        r = self.client.post(reverse('admin:medialib_mediaitem_upload_json'), {'file': up})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(MediaItem.objects.exists())

    def test_upload_page_takes_many_files(self):
        files = [SimpleUploadedFile(f'p{i}.png', png_bytes(), content_type='image/png')
                 for i in range(3)]
        r = self.client.post(reverse('admin:medialib_mediaitem_upload'), {'files': files})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(MediaItem.objects.count(), 3)

    def test_changelist_and_change_page_render(self):
        name = self.put('library/z.png', png_bytes())
        CategoryBanner.objects.create(page='Z.html', image=name)
        item = MediaItem.objects.get(file=name)
        r = self.client.get(reverse('admin:medialib_mediaitem_changelist'))
        self.assertContains(r, 'Used in 1 place')
        r = self.client.get(reverse('admin:medialib_mediaitem_change', args=[item.pk]))
        self.assertContains(r, 'Z.html')

    def test_admin_delete_keeps_a_used_file(self):
        name = self.put('library/keep.png', png_bytes())
        CategoryBanner.objects.create(page='K.html', image=name)
        item = MediaItem.objects.get(file=name)
        self.client.post(reverse('admin:medialib_mediaitem_delete', args=[item.pk]), {'post': 'yes'})
        self.assertFalse(MediaItem.objects.filter(pk=item.pk).exists())
        self.assertTrue(default_storage.exists(name))
