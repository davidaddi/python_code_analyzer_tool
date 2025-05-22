from django import forms
import re


class CodeUploadForm(forms.Form):
    """Formulaire pour l'upload de fichier ZIP."""

    zip_file = forms.FileField(
        label="Fichier ZIP",
        widget=forms.FileInput(attrs={
            'class': 'form-control',
            'accept': '.zip',
        })
    )

    def clean_zip_file(self):
        file = self.cleaned_data.get('zip_file')
        if file:
            if not file.name.endswith('.zip'):
                raise forms.ValidationError("Seuls les fichiers ZIP sont acceptés.")
            if file.size > 50 * 1024 * 1024:  # 50MB max
                raise forms.ValidationError("Le fichier ne peut pas dépasser 50MB.")
        return file


class GitHubForm(forms.Form):
    """Formulaire pour l'URL GitHub."""

    github_url = forms.URLField(
        label="URL du dépôt GitHub",
        widget=forms.URLInput(attrs={
            'class': 'form-control',
            'placeholder': 'https://github.com/username/repository',
        })
    )

    def clean_github_url(self):
        url = self.cleaned_data.get('github_url')
        if url:
            github_pattern = r'https://github\.com/[\w\-\.]+/[\w\-\.]+'
            if not re.match(github_pattern, url):
                raise forms.ValidationError(
                    "L'URL doit être un dépôt GitHub public valide."
                )
        return url