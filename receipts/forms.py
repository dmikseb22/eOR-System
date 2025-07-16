from django import forms
from .models import OfficialReceipt

class OfficialReceiptForm(forms.ModelForm):
    class Meta:
        model = OfficialReceipt
        # fields = ['payor_name', 'purpose', 'amount', 'vat', 'service_charge', 'reference_number', 'payment_channel', 'mode_of_payment']
        fields = ['payor_name', 'purpose', 'amount', 'reference_number', 'payment_channel', 'mode_of_payment']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs.update({
                'class': 'w-full p-2 border rounded focus:outline-none focus:ring-2 focus:ring-blue-500',
            })