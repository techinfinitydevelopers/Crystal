""""Choose from Media library", server side, for every upload box at once.

The browser half (static/admin/crystal_medialib.js) adds a hidden input next to
every file input, named after it with "__media" on the end, and fills it with
the stored name of the library file that was picked. These patches teach
Django's own file handling to read that:

1. FileInput.value_from_datadict — when nothing was uploaded but a picked name
   came in and exists in storage, hand the form a PickedFile instead of None.
   ClearableFileInput calls this through super(), so it is covered too, and its
   "Clear" logic runs unchanged on top: Clear + a pick is the same
   "contradiction" error as Clear + an upload, Clear alone still clears.
2. FileInput.value_omitted_from_data — a pick counts as "this field was sent",
   so ModelForm does not skip the field.
3. FileField.save_form_data — a PickedFile is assigned as its stored name, a
   plain string. Assigning a File object would make Django save it again under
   upload_to, i.e. copy it; a string just points the model at the file that is
   already there.

Patched once, globally, from MedialibConfig.ready(): the page editor, every
inline, every change form and any form added later get it with no per-form
code. A real upload always wins over a pick.
"""
from django.core.exceptions import SuspiciousFileOperation
from django.core.files import File
from django.core.files.storage import default_storage
from django.db.models.fields.files import FileField
from django.forms import widgets
from django.utils.functional import cached_property

SUFFIX = '__media'


class PickedFile(File):
    """A library file, standing in for an upload while the form is validated.

    Opened lazily from storage, so forms.ImageField can still read and verify
    it with Pillow exactly as it would an upload, and nothing is opened at all
    for a plain FileField that only checks the name and size.
    """

    def __init__(self, name, storage=None):
        self.storage = storage or default_storage
        self._fh = None
        super().__init__(None, name=name)
        self.mode = 'rb'

    @property
    def file(self):
        if self._fh is None:
            self._fh = self.storage.open(self.name, 'rb')
        return self._fh

    @file.setter
    def file(self, value):
        self._fh = value

    @cached_property
    def size(self):
        return self.storage.size(self.name)

    @property
    def closed(self):
        return self._fh is None or self._fh.closed

    def close(self):
        if self._fh is not None:
            self._fh.close()
            self._fh = None


def picked_name(data, name):
    """The stored name posted for this field, if it is a real stored file."""
    getter = getattr(data, 'get', None)
    if getter is None:
        return None
    value = (getter(name + SUFFIX) or '').strip()
    if not value or value.startswith(('/', '\\')) or '..' in value.replace('\\', '/').split('/'):
        return None
    try:
        return value if default_storage.exists(value) else None
    except (SuspiciousFileOperation, OSError, ValueError):
        return None


_orig_value_from_datadict = widgets.FileInput.value_from_datadict
_orig_value_omitted = widgets.FileInput.value_omitted_from_data
_orig_save_form_data = FileField.save_form_data


def value_from_datadict(self, data, files, name):
    upload = _orig_value_from_datadict(self, data, files, name)
    if upload or self.allow_multiple_selected:
        return upload
    stored = picked_name(data, name)
    return PickedFile(stored) if stored else upload


def value_omitted_from_data(self, data, files, name):
    return _orig_value_omitted(self, data, files, name) and not picked_name(data, name)


def save_form_data(self, instance, data):
    if isinstance(data, PickedFile):
        data.close()
        setattr(instance, self.name, data.name)
        return
    _orig_save_form_data(self, instance, data)


def install():
    if getattr(widgets.FileInput, '_medialib_patched', False):
        return
    widgets.FileInput.value_from_datadict = value_from_datadict
    widgets.FileInput.value_omitted_from_data = value_omitted_from_data
    FileField.save_form_data = save_form_data
    widgets.FileInput._medialib_patched = True
