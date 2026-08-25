"""Admin forms for the products app.

The only interesting thing here is `FeatureLinesField`, which lets a
non-technical user type product feature cards as plain lines instead of raw
JSON. The model still stores [[icon, title, detail], ...].
"""

from django import forms
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


class ProductAdminForm(forms.ModelForm):
    features = FeatureLinesField()

    class Meta:
        model = Product
        fields = '__all__'
