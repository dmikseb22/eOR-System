from django.urls import path
from . import views

urlpatterns = [
    path('', views.receipt_list, name='receipt_list'),
    path('create/', views.receipt_create, name='receipt_create'),
    path('edit/<int:pk>/', views.receipt_edit, name='receipt_edit'),
    path('delete/<int:pk>/', views.receipt_delete, name='receipt_delete'),
    path('pdf/<int:pk>/', views.receipt_pdf, name='receipt_pdf'),
    path('accounts/profile/', views.profile_view, name='profile'),
]