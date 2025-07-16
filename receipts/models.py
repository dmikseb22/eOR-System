from django.db import models
from django.utils import timezone

class OfficialReceipt(models.Model):
    or_number = models.CharField(max_length=20, unique=True)
    date_time = models.DateTimeField(default=timezone.now)
    payor_name = models.CharField(max_length=100)
    purpose = models.TextField()
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    vat = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    service_charge = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    reference_number = models.CharField(max_length=50,blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    payment_channel = models.CharField(max_length=50, blank=True, null=True)
    mode_of_payment = models.CharField(max_length=50, blank=True, null=True)
    is_deleted = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if not self.or_number:
            now = timezone.now()
            year = now.year
            month = f"{now.month:02d}"
            last_receipt = OfficialReceipt.objects.all().filter(
                or_number__startswith=f'E-DOST02-{month}{year}'
            ).order_by('-or_number').first()
            
            if last_receipt:
                last_num = int(last_receipt.or_number.split('-')[-1])
                new_num = last_num + 1
            else:
                new_num = 1
            self.or_number = f'E-DOST02-{month}{year}-{new_num:04d}'
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.or_number