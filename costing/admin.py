from django.contrib import admin
from .models import Project, CostingSheet, SavedModel

@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'client_name', 'created_by', 'created_at', 'is_active')
    list_filter = ('is_active', 'created_at', 'created_by')
    search_fields = ('name', 'client_name')
    readonly_fields = ('created_by', 'created_at', 'updated_at')
    
    def save_model(self, request, obj, form, change):
        # If creating new project in admin, assign to current admin user
        if not change:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)

@admin.register(CostingSheet)
class CostingSheetAdmin(admin.ModelAdmin):
    list_display = ('project', 'original_filename', 'uploaded_at', 'total_models')
    list_filter = ('project', 'uploaded_at')
    search_fields = ('original_filename', 'project__name')

@admin.register(SavedModel)
class SavedModelAdmin(admin.ModelAdmin):
    list_display = ('project', 'model_name', 'product_type', 'is_original', 'saved_at', 'final_cost')
    list_filter = ('project', 'is_original', 'product_type')
    search_fields = ('model_name', 'product_type')