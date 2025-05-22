from django.contrib import admin
from .models import EvaluationResult


@admin.register(EvaluationResult)
class EvaluationResultAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'source_type',
        'status',
        'maintainability_index',
        'pylint_score',
        'created_at'
    ]
    list_filter = ['status', 'source_type', 'created_at']
    search_fields = ['source_path']
    readonly_fields = ['created_at']

    fieldsets = (
        ('Informations générales', {
            'fields': ('source_type', 'source_path', 'status', 'created_at')
        }),
        ('Métriques', {
            'fields': (
                'maintainability_index',
                'bugs_probability',
                'halstead_volume',
                'lcom4',
                'complexity',
                'pylint_score'
            )
        }),
        ('Détails', {
            'fields': ('source_metrics', 'error_message'),
            'classes': ('collapse',)
        }),
    )