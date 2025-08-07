from django import forms
from apps.common.models import Sales



class SalesForm(forms.ModelForm):
    class Meta:
        model = Sales
        fields = '__all__'
        widgets = {
            'PurchaseDate': forms.widgets.DateInput(attrs={'type': 'date'})
        }
    

    def __init__(self, *args, **kwargs):
        super(SalesForm, self).__init__(*args, **kwargs)

        for field_name, field in self.fields.items():
            self.fields[field_name].widget.attrs['placeholder'] = field.label
            self.fields[field_name].widget.attrs['class'] = 'bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg focus:ring-primary-600 focus:border-primary-600 block w-full p-2.5 dark:bg-gray-700 dark:border-gray-600 dark:placeholder-gray-400 dark:text-white dark:focus:ring-primary-500 dark:focus:border-primary-500'
            self.fields[field_name].widget.attrs['required'] = True
            self.fields[field_name].widget.attrs['cols'] = 30
            self.fields[field_name].widget.attrs['rows'] = 1
            self.fields['Quantity'].widget.attrs['value'] = 1