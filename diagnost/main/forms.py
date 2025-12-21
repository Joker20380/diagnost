from django import forms
from django.contrib.admin.widgets import AdminDateWidget
from phonenumber_field.formfields import PhoneNumberField
from users.models import UserProfile
from .models import Subscriber
from dal import autocomplete
from allauth.account.forms import LoginForm, ResetPasswordForm
from diagnostics.models import DiagnosticSession





class CustomResetPasswordForm(ResetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['email'].widget.attrs.update({
    		'class': 'newsletter_input',
    		'placeholder': 'Введите ваш email',
    		'autocomplete': 'email'
		})


class CustomLoginForm(LoginForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for name, field in self.fields.items():
            if name in ['login', 'password']:
                field.widget.attrs.update({'class': 'newsletter_input'})


class UserProfileForm(forms.ModelForm):
    last_name = forms.CharField(
        max_length=30,
        required=False,
        label='Фамилия',
        widget=forms.TextInput(attrs={"placeholder": "Фамилия", "class": "newsletter_input"})
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        label='Имя',
        widget=forms.TextInput(attrs={"placeholder": "Имя", "class": "newsletter_input"})
    )
    patronymic = forms.CharField(
        max_length=30,
        required=False,
        label='Отчество',
        widget=forms.TextInput(attrs={"placeholder": "Отчество", "class": "newsletter_input"})
    )
    address = forms.CharField(
        max_length=30,
        required=False,
        label='Адрес',
        widget=forms.TextInput(attrs={"placeholder": "Адрес", "class": "newsletter_input"})
    )
    phone_number = PhoneNumberField(
        region="RU",
        label='Номер телефона',
        widget=forms.TextInput(attrs={"placeholder": "Номер телефона", "class": "newsletter_input"})
    )

    class Meta:
        model = UserProfile
        fields = ['last_name', 'first_name', 'patronymic', 'gender', 'address', 'phone_number']


class SchoolSelect2Widget(autocomplete.ModelSelect2):
    search_fields = ['title__icontains', 'location__name__icontains']


    def get_url(self):
        return reverse('school-autocomplete')





class PersonalAreaForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        required=False,
        widget=forms.TextInput(
            attrs={"placeholder": "Username", "autocomplete": "username", "class": "newsletter_input"})
    )
    email = forms.EmailField(
        required=False,
        widget=forms.EmailInput(attrs={"placeholder": "Email", "autocomplete": "email", "class": "newsletter_input"})
    )
    last_name = forms.CharField(
        max_length=30,
        required=False,
        label='Фамилия',
        widget=forms.TextInput(attrs={"placeholder": "Фамилия", "class": "newsletter_input"})
    )
    first_name = forms.CharField(
        max_length=30,
        required=False,
        label='Имя',
        widget=forms.TextInput(attrs={"placeholder": "Имя", "class": "newsletter_input"})
    )
    patronymic = forms.CharField(
        max_length=30,
        required=False,
        label='Отчество',
        widget=forms.TextInput(attrs={"placeholder": "Отчество", "class": "newsletter_input"})
    )
    address = forms.CharField(
        max_length=30,
        required=False,
        label='Адрес',
        widget=forms.TextInput(attrs={"placeholder": "Адрес", "class": "newsletter_input"})
    )
    phone_number = PhoneNumberField(
        region="RU",
        label='Номер телефона',
        widget=forms.TextInput(attrs={"placeholder": "Номер телефона", "class": "newsletter_input"})
    )
    merit = forms.CharField(
        max_length=500,
        required=False,
        label='О себе',
        widget=forms.Textarea(attrs={"placeholder": "О себе", "class": "newsletter_input", "rows": 3})
    )


    class Meta:
        model = UserProfile
        fields = [
            'image', 'username', 'email', 'last_name', 'first_name', 'patronymic',
            'address', 'phone_number', 'birth', 'merit'
        ]
        widgets = {
            'birth': AdminDateWidget(attrs={'type': 'text', 'class': 'newsletter_input datepicker'}),
            'school': autocomplete.ModelSelect2(url='school-autocomplete'),
        }

    def __init__(self, *args, **kwargs):
        user = kwargs.pop('user')
        super().__init__(*args, **kwargs)

        self.user = user  # сохраним пользователя для использования в save()

        # Устанавливаем начальные значения
        self.fields['username'].initial = user.username
        self.fields['email'].initial = user.email
        self.fields['first_name'].initial = user.first_name
        self.fields['last_name'].initial = user.last_name
        self.fields['patronymic'].initial = getattr(user.userprofile, 'patronymic', '')
        self.fields['address'].initial = getattr(user.userprofile, 'address', '')
        self.fields['phone_number'].initial = getattr(user.userprofile, 'phone_number', '')
        self.fields['birth'].initial = getattr(user.userprofile, 'birth', '')
        self.fields['merit'].initial = getattr(user.userprofile, 'merit', '')
        self.fields['image'].initial = getattr(user.userprofile, 'image', None)

    def clean_image(self):
        image = self.cleaned_data.get('image')
        if image:
            max_size_mb = 5
            if image.size > max_size_mb * 1024 * 1024:
                raise forms.ValidationError(f"Размер изображения не должен превышать {max_size_mb} МБ.")
        return image

    def save(self, commit=True):
        user_profile = super().save(commit=False)

        # Сохраняем изменения в связанном User
        user = self.user
        user.username = self.cleaned_data.get('username', user.username)
        user.email = self.cleaned_data.get('email', user.email)
        user.first_name = self.cleaned_data.get('first_name', user.first_name)
        user.last_name = self.cleaned_data.get('last_name', user.last_name)

        if commit:
            user.save()
    
        image_field = self.cleaned_data.get('image')
    
        if image_field:
            try:
                img = Image.open(image_field)
    
                if img.mode != 'RGB':
                    img = img.convert('RGB')
    
                # === Уменьшаем основное изображение, если оно больше 800x800 ===
                max_size = (800, 800)
                img.thumbnail(max_size, Image.LANCZOS)
    
                # === Обрезаем до квадрата ===
                width, height = img.size
                min_side = min(width, height)
                left = (width - min_side) / 2
                top = (height - min_side) / 2
                right = (width + min_side) / 2
                bottom = (height + min_side) / 2
                img = img.crop((left, top, right, bottom))
    
                # Сохраняем основное изображение в WEBP
                buffer = BytesIO()
                img.save(buffer, format='WEBP', quality=90)
                file_name = f'{user.username}_avatar.webp'
                user_profile.image.save(file_name, ContentFile(buffer.getvalue()), save=False)
    
                # === Создаём миниатюру 200x200 ===
                thumb = img.copy()
                thumb.thumbnail((200, 200), Image.LANCZOS)
    
                thumb_buffer = BytesIO()
                thumb.save(thumb_buffer, format='WEBP', quality=80)
                thumb_file_name = f'{user.username}_avatar_thumb.webp'
    
                # Теперь важно: 
                # Если в модели UserProfile есть отдельное поле для миниатюры (например, `image_thumb`)
                if hasattr(user_profile, 'image_thumb'):
                    user_profile.image_thumb.save(thumb_file_name, ContentFile(thumb_buffer.getvalue()), save=False)
    
            except Exception as e:
                import logging
                logger = logging.getLogger(__name__)
                logger.error(f"Ошибка обработки изображения: {e}")
    
        if commit:
            user_profile.save()
            self.save_m2m()

        return user_profile



class SubscriberForm(forms.ModelForm):
    class Meta:
        model = Subscriber
        fields = ['email']
        widgets = {
            'email': forms.EmailInput(attrs={"placeholder": "Введите ваш email", "autocomplete": "email", "class": "newsletter_input"})
        }


class UnsubscriberForm(forms.Form):
    email = forms.EmailField(
        label="Ваш email",
        widget=forms.EmailInput(attrs={
            "placeholder": "Введите ваш email",
            "autocomplete": "email",
            "class": "newsletter_input"
        })
    )
