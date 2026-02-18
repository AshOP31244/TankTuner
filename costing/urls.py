
from django.urls import path
from .views import (
    login_view,  
    logout_view,

    # Project Management
    project_list,
    project_create,
    project_detail,
    project_delete,
    upload_to_project,
    project_tuner,
    project_analytics,
    project_snapshots,
    delete_costing_sheet,
    
    # Project-specific API endpoints
    get_project_products,
    get_project_models,
    get_project_model_data,
    save_project_snapshot,
    get_project_saved_models,
    
    # Legacy endpoints (keep for backward compatibility)
    dashboard,
    upload_costing_sheet,
    get_products,
    get_models,
    get_model_data,
    save_model_snapshot,
    get_saved_models,
    load_snapshot,
    delete_snapshot,
    save_original_from_session,
    
    # Export
    export_model_csv,
    export_comparison_csv,
    
    # Analytics
    analytics_dashboard,
    get_analytics_stats,
    get_material_breakdown,
    get_savings_trend,
    get_model_comparison,
    get_top_materials,
)

urlpatterns = [

    # Authentication
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),

    # ============================================
    # PROJECT MANAGEMENT (Main Routes)
    # ============================================
    path("", login_view, name='home'),  # Root redirects to login
    path("projects/", project_list, name="project_list"),  # Changed from 'projects' to 'project_list'
    path("project/create/", project_create, name="project_create"),
    path("project/<int:project_id>/", project_detail, name="project_detail"),
    path("project/<int:project_id>/delete/", project_delete, name="project_delete"),
    path("project/<int:project_id>/upload/", upload_to_project, name="upload_to_project"),
    path("project/<int:project_id>/tuner/", project_tuner, name="project_tuner"),
    path("project/<int:project_id>/analytics/", project_analytics, name="project_analytics"),
    path('project/<int:project_id>/snapshots/', project_snapshots, name='project_snapshots'),
    path('project/<int:project_id>/sheet/<int:sheet_id>/delete/', delete_costing_sheet, name='delete_costing_sheet'),
    
    # ============================================
    # PROJECT-SPECIFIC API ENDPOINTS
    # ============================================
    path("api/project/<int:project_id>/products/", get_project_products, name="api_project_products"),
    path("api/project/<int:project_id>/models/", get_project_models, name="api_project_models"),
    path("api/project/<int:project_id>/model-data/", get_project_model_data, name="api_project_model_data"),
    path("api/project/<int:project_id>/save-snapshot/", save_project_snapshot, name="api_project_save_snapshot"),
    path("api/project/<int:project_id>/saved-models/", get_project_saved_models, name="api_project_saved_models"),
    
    # ============================================
    # LEGACY ROUTES (for backward compatibility)
    # ============================================
    path("legacy/dashboard/", dashboard, name="legacy_dashboard"),
    path("upload/", upload_costing_sheet, name="upload"),
    path("get-products/", get_products),
    path("get-models/", get_models),
    path("get-model-data/", get_model_data),
    
    # ============================================
    # SAVE/LOAD (Session-based - still works)
    # ============================================
    path("api/save-snapshot/", save_model_snapshot, name="save_snapshot"),
    path("api/get-saved-models/", get_saved_models, name="get_saved_models"),
    path("api/load-snapshot/<int:snapshot_id>/", load_snapshot, name="load_snapshot"),
    path("api/delete-snapshot/<int:snapshot_id>/", delete_snapshot, name="delete_snapshot"),
    path("api/save-original/", save_original_from_session, name="save_original"),
    
    # ============================================
    # EXPORT
    # ============================================
    path("export/model/", export_model_csv, name="export_model"),
    path("export/comparison/", export_comparison_csv, name="export_comparison"),
    
    # ============================================
    # ANALYTICS
    # ============================================
    path("analytics/", analytics_dashboard, name="analytics_dashboard"),
    path("api/analytics/stats/", get_analytics_stats, name="analytics_stats"),
    path("api/analytics/material-breakdown/", get_material_breakdown, name="material_breakdown"),
    path("api/analytics/savings-trend/", get_savings_trend, name="savings_trend"),
    path("api/analytics/model-comparison/", get_model_comparison, name="model_comparison"),
    path("api/analytics/top-materials/", get_top_materials, name="top_materials"),
]