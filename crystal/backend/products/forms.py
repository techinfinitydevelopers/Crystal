"""Admin forms for the products app.

Two custom fields live here, both there for the same reason: a non-technical
user should never have to type JSON.

* `FeatureLinesField` presents the feature cards as `icon | title | detail`
  lines. The model still stores [[icon, title, detail], ...].
* `TagListField` presents the tags as removable chips. The model still stores
  ["tag", "tag", ...].
"""

import json

from django import forms
from django.forms.renderers import TemplatesSetting
from django.utils.safestring import mark_safe

from .models import Product


FEATURES_HELP = mark_safe(
    'One feature per line, three parts separated by a vertical bar:  '
    '<code>icon | title | detail</code><br>'
    'Example:<br>'
    '<code>🔥 | Even heating | Thick forged base spreads heat edge to edge</code><br>'
    '<code>🧼 | Easy to clean | Non-stick coating wipes clean in seconds</code><br>'
    'The icon can be an emoji or a short icon name, and may be left empty '
    '(<code>| Title | Detail</code>). The detail may be left empty too. '
    'Leave the whole box blank to use the category default features.'
)


class FeatureLinesField(forms.CharField):
    """A textarea that reads/writes the [[icon, title, detail], ...] JSON."""

    widget = forms.Textarea(attrs={
        'rows': 6,
        'style': 'font-family:inherit;width:95%;',
        'placeholder': '🔥 | Even heating | Thick forged base spreads heat edge to edge',
    })

    def __init__(self, **kwargs):
        kwargs.setdefault('required', False)
        kwargs.setdefault('label', 'Feature cards')
        kwargs.setdefault('help_text', FEATURES_HELP)
        super().__init__(**kwargs)

    # JSON (from the DB) -> text shown in the textarea
    def prepare_value(self, value):
        if isinstance(value, str) or value in (None, ''):
            return value or ''
        lines = []
        for row in value:
            if isinstance(row, dict):
                parts = [row.get('icon', ''), row.get('title', ''), row.get('detail', '')]
            elif isinstance(row, (list, tuple)):
                parts = list(row) + [''] * (3 - len(row))
                parts = parts[:3]
            else:
                parts = ['', str(row), '']
            lines.append(' | '.join(str(p or '').strip() for p in parts))
        return '\n'.join(lines)

    # text typed by the user -> JSON stored on the model
    def clean(self, value):
        value = (value or '').strip()
        if not value:
            return []
        features, errors = [], []
        for n, raw_line in enumerate(value.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.split('|')]
            if len(parts) == 2:          # "Title | Detail" - icon omitted
                parts = [''] + parts
            elif len(parts) == 1:        # "Title" only
                parts = ['', parts[0], '']
            elif len(parts) > 3:
                errors.append(
                    f'Line {n}: too many "|" separators ({len(parts) - 1}). '
                    f'Use at most two, as in "icon | title | detail". '
                    f'You typed: {line}'
                )
                continue
            if not parts[1]:
                errors.append(
                    f'Line {n}: the title (the middle part) cannot be empty. '
                    f'You typed: {line}'
                )
                continue
            features.append([parts[0], parts[1], parts[2]])
        if errors:
            raise forms.ValidationError(errors)
        return features


TAGS_HELP = mark_safe(
    'Type a tag and press <kbd>Enter</kbd> (or a comma) to turn it into a chip. '
    'Click the &times; on a chip to remove it, or press <kbd>Backspace</kbd> in '
    'an empty box to remove the last one.<br>'
    'You can also paste a whole list at once — it will be split on commas and '
    'new lines. Duplicates and blanks are dropped automatically.'
)


class TagChipsWidget(forms.Widget):
    """Renders the tag list as chips plus one hidden input holding the JSON.

    Only the hidden input carries a `name`, so the visible text box the user
    types into can never post a stray half-typed tag. The chips themselves are
    rendered server-side by the template, which means the field is still
    readable — and the JSON still editable — with JavaScript switched off.
    """

    template_name = 'admin/products/widgets/tag_chips.html'

    # The renderer Django hands us only looks inside app `templates/` folders,
    # and this widget's template lives in the project template dir. Swapping in
    # TemplatesSetting makes it honour the project's TEMPLATES config instead.
    # It is done here rather than in settings so nothing else changes.
    def render(self, name, value, attrs=None, renderer=None):
        return super().render(name, value, attrs, renderer=TemplatesSetting())

    def format_value(self, value):
        # Whatever the form hands us (list from the DB, string from a redisplay
        # after a validation error) comes back out as a list of tag strings.
        if value in (None, ''):
            return []
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value]
        return _split_tags(str(value))

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        tags = self.format_value(value)
        context['widget']['tags'] = tags
        context['widget']['json_value'] = json.dumps(tags, ensure_ascii=False)
        return context

    def value_from_datadict(self, data, files, name):
        return data.get(name)


def _dedupe_tags(tags):
    """Trim, drop blanks, and drop case-insensitive duplicates (first wins)."""
    out, seen = [], set()
    for raw in tags:
        tag = str(raw).strip()
        if not tag or tag.casefold() in seen:
            continue
        seen.add(tag.casefold())
        out.append(tag)
    return out


def _split_tags(text):
    """Split free text on commas / new lines and drop blanks and duplicates."""
    return _dedupe_tags(str(text).replace('\r', '\n').replace('\n', ',').split(','))


class TagListField(forms.CharField):
    """A chip input that reads/writes the ["tag", "tag", ...] JSON."""

    widget = TagChipsWidget

    def __init__(self, **kwargs):
        kwargs.setdefault('required', False)
        kwargs.setdefault('label', 'Tags')
        kwargs.setdefault('help_text', TAGS_HELP)
        super().__init__(**kwargs)

    # JSON (from the DB) -> list of tags the widget renders as chips
    def prepare_value(self, value):
        if value in (None, ''):
            return []
        if isinstance(value, (list, tuple)):
            return [str(v) for v in value]
        return self._parse(str(value))

    # what the browser posted -> JSON stored on the model
    def clean(self, value):
        if value in (None, ''):
            return []
        if isinstance(value, (list, tuple)):
            return _dedupe_tags(value)
        return self._parse(value)

    @staticmethod
    def _parse(value):
        """Accept both a JSON array and plain comma/new-line separated text.

        The JSON branch is what the JavaScript posts; the plain-text branch is
        the no-JavaScript fallback, and is what makes this field testable
        without a browser.
        """
        value = value.strip()
        if not value:
            return []
        if value.startswith('['):
            try:
                parsed = json.loads(value)
            except ValueError:
                raise forms.ValidationError(
                    'That does not look like a valid tag list. Type the tags '
                    'separated by commas instead.'
                )
            if not isinstance(parsed, list):
                raise forms.ValidationError(
                    'Tags must be a list. Type the tags separated by commas.'
                )
            errors = []
            for n, item in enumerate(parsed, start=1):
                if isinstance(item, (dict, list)):
                    errors.append(
                        f'Tag {n}: expected a piece of text, got {type(item).__name__}.'
                    )
            if errors:
                raise forms.ValidationError(errors)
            return _dedupe_tags(parsed)
        return _split_tags(value)


class ProductAdminForm(forms.ModelForm):
    features = FeatureLinesField()
    tags = TagListField()

    class Meta:
        model = Product
        fields = '__all__'
