
import os

from django import forms

from .models import SharedFile


MAX_FILE_SIZE = 10 * 1024 * 1024

ALLOWED_EXTENSIONS = {
    ".pdf", ".doc", ".docx", ".txt",
    ".png", ".jpg", ".jpeg",
    ".xlsx", ".csv", ".ppt", ".pptx",
    ".zip",
}


class SharedFileForm(forms.ModelForm):
    class Meta:
        model = SharedFile
        fields = ["file"]

    def clean_file(self):
        uploaded_file = self.cleaned_data.get("file")

        if not uploaded_file:
            raise forms.ValidationError("Please select a file.")

        if uploaded_file.size > MAX_FILE_SIZE:
            raise forms.ValidationError("Maximum file size is 10 MB.")

        extension = os.path.splitext(uploaded_file.name)[1].lower()

        if extension not in ALLOWED_EXTENSIONS:
            raise forms.ValidationError(
                "This file type is not supported."
            )

        return uploaded_file
