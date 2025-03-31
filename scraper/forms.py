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

    def clean(self):
        """驗證表單數據"""
        cleaned_data = super().clean()
        use_threading = cleaned_data.get('use_threading')
        max_workers = cleaned_data.get('max_workers')

        # 如果未使用多線程，則不需要檢查max_workers字段
        if not use_threading:
            # 如果未勾選使用多線程，則使用默認值
            cleaned_data['max_workers'] = 4

        return cleaned_data

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # 如果是已有實例，將類別字串轉回多選值
        if self.instance.pk and self.instance.categories:
            self.initial['categories'] = self.instance.categories.split(',')

        # 將max_workers設為非必填
        self.fields['max_workers'].required = False


class KeywordFilterForm(forms.Form):
    """關鍵詞篩選表單"""

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

    POS_CHOICES = [
        ('', '所有詞性'),
        ('Na', '普通名詞 (Na)'),
        ('Nb', '專有名詞 (Nb)'),
        ('Nc', '地方名詞 (Nc)')
    ]

    ENTITY_TYPE_CHOICES = [
        ('', '所有實體類型'),
        ('PERSON', '人物 (PERSON)'),
        ('LOC', '地點 (LOC)'),
        ('ORG', '組織 (ORG)'),
        ('TIME', '時間 (TIME)'),
        ('MISC', '其他 (MISC)')
    ]

    # 單選類別，用於非跨類別模式
    category = forms.ChoiceField(
        label='類別',
        choices=[('', '所有類別')] + CATEGORY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    # 多選類別，用於跨類別模式
    selected_categories = forms.MultipleChoiceField(
        label='要統計的類別',
        choices=CATEGORY_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'}),
        help_text='選擇要納入跨類別統計的新聞類別，不選擇則包含所有類別'
    )

    pos = forms.ChoiceField(
        label='詞性',
        choices=POS_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    entity_type = forms.ChoiceField(
        label='實體類型',
        choices=ENTITY_TYPE_CHOICES,
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
        min_value=1,
        max_value=10000,
        initial=20,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

    # 跨類別統計選項
    cross_category = forms.BooleanField(
        label='跨類別統計',
        required=False,
        help_text='啟用跨類別統計可合併相同關鍵詞在不同類別的頻率，並顯示分類詳情',
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    # 分析類型選擇
    ANALYSIS_TYPE_CHOICES = [
        ('keywords', '關鍵詞分析'),
        ('entities', '命名實體分析')
    ]

    analysis_type = forms.ChoiceField(
        label='分析類型',
        choices=ANALYSIS_TYPE_CHOICES,
        initial='keywords',
        required=False,
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

    # 清理表單數據
    def clean(self):
        cleaned_data = super().clean()
        cross_category = cleaned_data.get('cross_category')
        selected_categories = cleaned_data.get('selected_categories')

        # 如果啟用了跨類別統計但未選擇類別，則設為空列表（表示全選）
        if cross_category and not selected_categories:
            cleaned_data['selected_categories'] = []

        return cleaned_data


class AdvancedSearchForm(forms.Form):
    """文章搜尋與分析的進階表單"""

    search_terms = forms.CharField(
        label='搜尋關鍵字或命名實體',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '輸入關鍵字或命名實體，多個請用逗號分隔'
        })
    )

    search_mode = forms.ChoiceField(
        label='搜尋模式',
        choices=[
            ('and', 'AND - 符合所有關鍵字'),
            ('or', 'OR - 符合任一關鍵字')
        ],
        initial='and',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

    search_type = forms.ChoiceField(
        label='搜尋類型',
        choices=[
            ('keyword', '關鍵字'),
            ('entity', '命名實體'),
            ('both', '兩者皆包含')
        ],
        initial='both',
        widget=forms.RadioSelect(attrs={'class': 'form-check-input'})
    )

    include_title = forms.BooleanField(
        label='包含標題',
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    include_content = forms.BooleanField(
        label='包含內容',
        initial=True,
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )

    entity_types = forms.MultipleChoiceField(
        label='實體類型',
        required=False,
        choices=[
            ('PERSON', '人物 (PERSON)'),
            ('LOC', '地點 (LOC)'),
            ('ORG', '組織 (ORG)'),
            ('TIME', '時間 (TIME)'),
            ('MISC', '其他 (MISC)')
        ],
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )

    # 類別選擇欄位 - 將在視圖中動態設置選項
    categories = forms.MultipleChoiceField(
        label='新聞類別',
        required=False,
        widget=forms.CheckboxSelectMultiple(attrs={'class': 'form-check-input'})
    )

    date_from = forms.DateField(
        label='開始日期',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

    date_to = forms.DateField(
        label='結束日期',
        required=False,
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control'
        })
    )

    min_keywords_count = forms.IntegerField(
        label='最少關鍵詞數量',
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '最少包含幾個關鍵詞'
        })
    )

    min_entities_count = forms.IntegerField(
        label='最少實體數量',
        required=False,
        min_value=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '最少包含幾個命名實體'
        })
    )

    time_grouping = forms.ChoiceField(
        label='時間軸分組',
        choices=[
            ('day', '依日統計'),
            ('week', '依週統計'),
            ('month', '依月統計')
        ],
        initial='day',
        widget=forms.Select(attrs={'class': 'form-select'})
    )

    def clean_search_terms(self):
        """處理搜尋詞，將逗號分隔的詞轉換為列表"""
        search_terms = self.cleaned_data.get('search_terms', '')
        if not search_terms:
            return []

        # 分割並清理每個搜尋詞
        terms = [term.strip() for term in search_terms.split(',') if term.strip()]
        return terms

    def clean(self):
        """驗證表單數據"""
        cleaned_data = super().clean()
        search_terms = cleaned_data.get('search_terms', [])
        search_type = cleaned_data.get('search_type')
        entity_types = cleaned_data.get('entity_types', [])

        # 如果搜尋類型為實體但未選擇實體類型，添加提示
        if search_type == 'entity' and not entity_types:
            self.add_error('entity_types', '當選擇命名實體搜尋時，請至少選擇一種實體類型')

        # 檢查是否有提供任何搜尋詞
        if not search_terms:
            self.add_error('search_terms', '請輸入至少一個搜尋詞')

        # 檢查搜尋範圍
        include_title = cleaned_data.get('include_title')
        include_content = cleaned_data.get('include_content')
        if not include_title and not include_content:
            self.add_error('include_title', '請至少選擇一個搜尋範圍（標題或內容）')

        return cleaned_data
