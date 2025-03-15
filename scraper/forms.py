from django import forms
from django.contrib.auth.models import User
from .models import ScrapeJob, KeywordAnalysis


class LoginForm(forms.Form):
    """登入表單"""
    username = forms.CharField(
        label='用戶名',
        max_length=100,
        widget=forms.TextInput(attrs={'class': 'form-control', 'placeholder': '請輸入用戶名'})
    )
    password = forms.CharField(
        label='密碼',
        max_length=100,
        widget=forms.PasswordInput(attrs={'class': 'form-control', 'placeholder': '請輸入密碼'})
    )


class ScrapeJobForm(forms.ModelForm):
    """爬蟲任務表單"""

    CATEGORY_CHOICES = [
        ('財經', '財經'),
        ('政治', '政治'),
        ('社會', '社會'),
        ('科技', '科技'),
        ('國際', '國際'),
        ('娛樂', '娛樂'),
        ('生活', '生活'),
        ('言論', '言論'),
        ('軍事', '軍事')
    ]

    categories = forms.MultipleChoiceField(
        label='爬取類別',
        choices=CATEGORY_CHOICES,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='選擇要爬取的新聞類別'
    )

    class Meta:
        model = ScrapeJob
        fields = ['categories', 'limit_per_category', 'use_threading', 'max_workers']
        widgets = {
            'limit_per_category': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '20'
            }),
            'use_threading': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'max_workers': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '1',
                'max': '8'
            })
        }
        help_texts = {
            'limit_per_category': '每個類別最多爬取的文章數',
            'use_threading': '是否使用多線程提高爬取速度',
            'max_workers': '多線程模式下的最大線程數'
        }

    def clean_categories(self):
        """將多選類別轉換為逗號分隔字串"""
        categories = self.cleaned_data['categories']
        return ','.join(categories)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 如果是已有實例，將類別字串轉回多選值
        if self.instance.pk and self.instance.categories:
            self.initial['categories'] = self.instance.categories.split(',')


class KeywordFilterForm(forms.Form):
    """關鍵詞篩選表單"""

    CATEGORY_CHOICES = [
        ('', '所有類別'),
        ('財經', '財經'),
        ('政治', '政治'),
        ('社會', '社會'),
        ('科技', '科技'),
        ('國際', '國際'),
        ('娛樂', '娛樂'),
        ('生活', '生活'),
        ('言論', '言論'),
        ('軍事', '軍事')
    ]

    POS_CHOICES = [
        ('', '所有詞性'),
        ('Na', '普通名詞 (Na)'),
        ('Nb', '專有名詞 (Nb)'),
        ('Nc', '地方名詞 (Nc)')
    ]

    category = forms.ChoiceField(
        label='類別',
        choices=CATEGORY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    pos = forms.ChoiceField(
        label='詞性',
        choices=POS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    min_frequency = forms.IntegerField(
        label='最小頻率',
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={'class': 'form-control', 'placeholder': '最小頻率'})
    )

    limit = forms.IntegerField(
        label='顯示數量',
        required=False,
        min_value=5,
        max_value=100,
        initial=20,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )