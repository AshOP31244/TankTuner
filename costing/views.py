from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse, HttpResponse
from django.core.files.storage import FileSystemStorage
from django.db.models import Count, Sum 
from .models import Project, CostingSheet, ModelSnapshot, SavedModel, MaterialAdjustmentLog
from .services.excel_parser import parse_excel
from decimal import Decimal
from django.utils import timezone
from collections import defaultdict  # ← ADDED: Missing import
import csv
import json
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages


def dashboard(request):
    return redirect('project_list')



# ============================================
# AUTHENTICATION VIEWS
# ============================================

def login_view(request):
    """
    Handle user login
    """
    if request.user.is_authenticated:
        return redirect('project_list')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            next_url = request.GET.get('next', 'project_list')
            return redirect(next_url)
        else:
            return render(request, 'costing/login.html', {
                'error': 'Invalid username or password. Please try again.'
            })
    
    return render(request, 'costing/login.html')


def logout_view(request):
    """
    Handle user logout
    """
    logout(request)
    return redirect('login')



# ============================================
# PROJECT MANAGEMENT VIEWS
# ============================================

@login_required(login_url='login')
def project_list(request):

    # ✅ Each user sees ONLY their own projects
    if request.user.is_superuser:
        # Admins see all projects
        projects = Project.objects.filter(is_active=True)
    else:
        # Regular users see only THEIR projects
        projects = Project.objects.filter(
            is_active=True,
            created_by=request.user
        )
    
    # Add stats to each project
    project_data = []
    for project in projects:
        project_data.append({
            'id': project.id,
            'name': project.name,
            'client_name': project.client_name or 'N/A',
            'description': project.description,
            'created_at': project.created_at,
            'total_models': project.get_total_models(),
            'total_sheets': project.get_sheets_count(),
            'total_savings': project.get_total_savings(),
        })
    
    return render(request, 'costing/project_list.html', {'projects': project_data})

@login_required(login_url='login')
def project_create(request):
    """Create a new project - automatically assign to current user"""
    if request.method == 'POST':
        name = request.POST.get('name')
        client_name = request.POST.get('client_name', '')
        description = request.POST.get('description', '')
        
        if name:
            # ✅ Check if this user already has a project with this name
            existing = Project.objects.filter(
                name=name,
                created_by=request.user
            ).first()
            
            if existing:
                return render(request, 'costing/project_create.html', {
                    'error': 'You already have a project with this name'
                })
            
            # ✅ Create project and assign to current user
            project = Project.objects.create(
                name=name,
                client_name=client_name,
                description=description,
                created_by=request.user  # ← AUTOMATICALLY ASSIGNED
            )
            
            return redirect('project_detail', project_id=project.id)
    
    return render(request, 'costing/project_create.html')

@login_required(login_url='login')
def project_detail(request, project_id):
    """
    View project details and uploaded sheets
    """
    project = get_object_or_404(Project, id=project_id)
    sheets = CostingSheet.objects.filter(project=project)
    
    # Get unique models in this project
    models = SavedModel.objects.filter(
        project=project,
        is_original=True
    ).values('product_type', 'model_name').distinct()
    
    # Calculate project statistics
    total_savings = project.get_total_savings()
    total_models = project.get_total_models()
    
    context = {
        'project': project,
        'sheets': sheets,
        'models': models,
        'total_models': total_models,
        'total_sheets': sheets.count(),
        'total_savings': total_savings,
    }
    
    return render(request, 'costing/project_detail.html', context)

@login_required(login_url='login')
def project_delete(request, project_id):
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST':
        project.is_active = False
        project.save()
        return redirect('project_list')
    
    return render(request, 'costing/project_confirm_delete.html', {'project': project})


# ============================================
# UPLOAD TO PROJECT
# ============================================
@login_required(login_url='login')
def upload_to_project(request, project_id):
    
    project = get_object_or_404(Project, id=project_id)
    
    if request.method == 'POST' and request.FILES.get('costing_file'):
        uploaded_file = request.FILES['costing_file']
        notes = request.POST.get('notes', '')
        
        # Save file
        fs = FileSystemStorage(location='media/costing_sheets')
        filename = fs.save(uploaded_file.name, uploaded_file)
        file_path = fs.path(filename)
        
        # Parse Excel
        try:
            parsed_data = parse_excel(file_path)
            
            # Create CostingSheet record
            costing_sheet = CostingSheet.objects.create(
                project=project,
                file=f'costing_sheets/{filename}',
                original_filename=uploaded_file.name,
                notes=notes
            )
            
            # Save all models as original snapshots
            total_models = 0
            for product_type, models in parsed_data.items():
                for model_name, model_data in models.items():
                    SavedModel.objects.create(
                        project=project,
                        costing_sheet=costing_sheet,
                        product_type=product_type,
                        model_name=model_name,
                        materials=model_data['materials'],
                        final_cost=Decimal(str(model_data['final_cost'])),
                        is_original=True,
                        notes=f'Original from {uploaded_file.name}'
                    )
                    total_models += 1
            
            # Update total models count
            costing_sheet.total_models = total_models
            costing_sheet.save()
            
            return redirect('project_detail', project_id=project.id)
            
        except Exception as e:
            print(f"Error parsing Excel: {e}")
            return render(request, 'costing/upload_to_project.html', {
                'project': project,
                'error': f'Error parsing Excel file: {str(e)}'
            })
    
    return render(request, 'costing/upload_to_project.html', {'project': project})

@login_required(login_url='login')
def upload_costing_sheet(request):
    """Legacy upload - redirect to project creation"""
    return redirect('project_create')


# ============================================
# PROJECT TUNER (Dashboard for specific project)
# ============================================
@login_required(login_url='login')
def project_tuner(request, project_id):
    """
    Main tuning interface for a specific project
    """
    project = get_object_or_404(Project, id=project_id)
    
    # Store project_id in session for API calls
    request.session['current_project_id'] = project_id
    
    return render(request, 'costing/project_tuner.html', {'project': project})


# ============================================
# PROJECT-SPECIFIC API ENDPOINTS
# ============================================
@login_required(login_url='login')
def get_project_products(request, project_id):
    """
    Get products for a specific project
    """
    project = get_object_or_404(Project, id=project_id)
    products = SavedModel.objects.filter(
        project=project,
        is_original=True
    ).values_list('product_type', flat=True).distinct()
    
    return JsonResponse({'products': list(products)})

@login_required(login_url='login')
def get_project_models(request, project_id):
    """
    Get models for a product in a specific project
    """
    project = get_object_or_404(Project, id=project_id)
    product = request.GET.get('product')
    
    models = SavedModel.objects.filter(
        project=project,
        product_type=product,
        is_original=True
    ).values_list('model_name', flat=True).distinct()
    
    return JsonResponse({'models': list(models)})

@login_required(login_url='login')
def get_project_model_data(request, project_id):
    """
    Get model data for a specific project
    """
    project = get_object_or_404(Project, id=project_id)
    product = request.GET.get('product')
    model = request.GET.get('model')
    
    # Try to get latest modified version first, otherwise get original
    snapshot = SavedModel.objects.filter(
        project=project,
        product_type=product,
        model_name=model
    ).order_by('-saved_at').first()
    
    if snapshot:
        data = {
            'product': snapshot.product_type,
            'model': snapshot.model_name,
            'materials': snapshot.materials,
            'final_cost': float(snapshot.final_cost),
            'is_original': snapshot.is_original,
            'snapshot_id': snapshot.id
        }
        return JsonResponse(data)
    
    return JsonResponse({'error': 'Model not found'}, status=404)

@login_required(login_url='login')
def save_project_snapshot(request, project_id):
    """
    Save snapshot to a specific project
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    project = get_object_or_404(Project, id=project_id)
    
    try:
        data = json.loads(request.body)
        
        # Create new snapshot
        snapshot = SavedModel.objects.create(
            project=project,
            product_type=data['product'],
            model_name=data['model'],
            materials=data['materials'],
            final_cost=Decimal(str(data['final_cost'])),
            is_original=False,
            notes=data.get('notes', '')
        )
        
        return JsonResponse({
            'success': True,
            'snapshot_id': snapshot.id,
            'created_at': snapshot.saved_at.strftime('%Y-%m-%d %H:%M:%S')
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required(login_url='login')   
def get_project_saved_models(request, project_id):
    """
    Get all saved snapshots for a model in a project
    """
    project = get_object_or_404(Project, id=project_id)
    product = request.GET.get('product')
    model = request.GET.get('model')
    
    if not product or not model:
        return JsonResponse({'snapshots': []})
    
    snapshots = SavedModel.objects.filter(
        project=project,
        product_type=product,
        model_name=model
    ).values('id', 'saved_at', 'is_original', 'final_cost', 'notes')
    
    snapshot_list = []
    for snap in snapshots:
        snapshot_list.append({
            'id': snap['id'],
            'saved_at': snap['saved_at'].strftime('%Y-%m-%d %H:%M:%S'),
            'is_original': snap['is_original'],
            'final_cost': float(snap['final_cost']),
            'notes': snap['notes'] or '',
            'label': f"{'Original' if snap['is_original'] else 'Adjusted'} - {snap['saved_at'].strftime('%b %d, %H:%M')}"
        })
    
    return JsonResponse({'snapshots': snapshot_list})


# ============================================
# LEGACY API ENDPOINTS (Backward Compatibility)
# ============================================

def get_products(request):
    """Legacy API - uses session"""
    project_id = request.session.get('current_project_id')
    if project_id:
        return get_project_products(request, project_id)
    return JsonResponse({'products': []})


def get_models(request):
    """Legacy API - uses session"""
    project_id = request.session.get('current_project_id')
    if project_id:
        return get_project_models(request, project_id)
    return JsonResponse({'models': []})


def get_model_data(request):
    """Legacy API - uses session"""
    project_id = request.session.get('current_project_id')
    if project_id:
        return get_project_model_data(request, project_id)
    return JsonResponse({'error': 'No project selected'}, status=400)

@login_required(login_url='login')
def save_model_snapshot(request):
    """
    API endpoint to save current model state to database
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    try:
        data = json.loads(request.body)
        
        product = data.get('product')
        model = data.get('model')
        materials = data.get('materials')
        final_cost = data.get('final_cost')
        notes = data.get('notes', '')
        is_original = data.get('is_original', False)
        
        # Create snapshot
        snapshot = SavedModel.objects.create(
            product_type=product,
            model_name=model,
            materials=materials,
            final_cost=Decimal(str(final_cost)),
            is_original=is_original,
            notes=notes
        )
        
        return JsonResponse({
            'success': True,
            'snapshot_id': snapshot.id,
            'saved_at': snapshot.saved_at.strftime('%Y-%m-%d %H:%M:%S'),
            'message': 'Model saved successfully!'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required(login_url='login')
def get_saved_models(request):
    """
    ← ADDED: This was missing!
    Get all saved snapshots for current session
    """
    product = request.GET.get('product')
    model = request.GET.get('model')
    
    if not product or not model:
        return JsonResponse({'snapshots': []})
    
    snapshots = SavedModel.objects.filter(
        product_type=product,
        model_name=model
    ).values('id', 'saved_at', 'is_original', 'final_cost', 'notes')
    
    snapshot_list = []
    for snap in snapshots:
        snapshot_list.append({
            'id': snap['id'],
            'saved_at': snap['saved_at'].strftime('%Y-%m-%d %H:%M:%S'),
            'is_original': snap['is_original'],
            'final_cost': float(snap['final_cost']),
            'notes': snap['notes'] or '',
            'label': f"{'Original' if snap['is_original'] else 'Adjusted'} - {snap['saved_at'].strftime('%b %d, %H:%M')}"
        })
    
    return JsonResponse({'snapshots': snapshot_list})

@login_required(login_url='login')
def load_snapshot(request, snapshot_id):
    """
    API endpoint to load a specific snapshot
    """
    try:
        snapshot = SavedModel.objects.get(id=snapshot_id)
        
        data = {
            'product': snapshot.product_type,
            'model': snapshot.model_name,
            'materials': snapshot.materials,
            'final_cost': float(snapshot.final_cost),
            'is_original': snapshot.is_original,
            'notes': snapshot.notes or '',
            'saved_at': snapshot.saved_at.strftime('%Y-%m-%d %H:%M:%S')
        }
        
        return JsonResponse(data)
        
    except SavedModel.DoesNotExist:
        return JsonResponse({'error': 'Snapshot not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required(login_url='login')
def delete_snapshot(request, snapshot_id):
    """
    API endpoint to delete a snapshot
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    try:
        snapshot = SavedModel.objects.get(id=snapshot_id)
        snapshot.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Snapshot deleted successfully'
        })
        
    except SavedModel.DoesNotExist:
        return JsonResponse({'error': 'Snapshot not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

@login_required(login_url='login')
def save_original_from_session(request):
    """
    Save the original Excel data from session to database as baseline
    Called automatically when user first loads a model
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    try:
        data = json.loads(request.body)
        
        product = data.get('product')
        model = data.get('model')
        materials = data.get('materials')
        final_cost = data.get('final_cost')
        
        # Check if original already exists
        existing = SavedModel.objects.filter(
            product_type=product,
            model_name=model,
            is_original=True
        ).first()
        
        if existing:
            return JsonResponse({
                'success': True,
                'message': 'Original already saved',
                'snapshot_id': existing.id
            })
        
        # Create original snapshot
        snapshot = SavedModel.objects.create(
            product_type=product,
            model_name=model,
            materials=materials,
            final_cost=Decimal(str(final_cost)),
            is_original=True,
            notes='Original from Excel'
        )
        
        return JsonResponse({
            'success': True,
            'snapshot_id': snapshot.id,
            'message': 'Original saved'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

    
# ============================================
# EXPORT FUNCTIONALITY
# ============================================

def export_model_csv(request):
    """Export model as CSV"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    try:
        data = json.loads(request.body)
        
        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{data["model"]}_costing.csv"'
        
        writer = csv.writer(response)
        
        # Write header
        writer.writerow(['TankTuner Cost Export'])
        writer.writerow(['Product Type:', data['product']])
        writer.writerow(['Model:', data['model']])
        writer.writerow([])
        
        # Write materials header
        writer.writerow(['Material Name', 'Quantity', 'Unit', 'Rate (₹)', 'Total Cost (₹)'])
        
        # Write materials
        for material in data['materials']:
            writer.writerow([
                material['name'],
                material['quantity'],
                material['unit'],
                material['rate'],
                material['total']
            ])
        
        writer.writerow([])
        writer.writerow(['FINAL TOTAL COST', '', '', '', f"₹ {data['final_cost']:.2f}"])
        
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def export_comparison_csv(request):
    """Export before/after comparison"""
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    try:
        data = json.loads(request.body)
        
        # Create CSV
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="{data["model"]}_comparison.csv"'
        
        writer = csv.writer(response)
        
        # Header
        writer.writerow(['TankTuner Cost Comparison Report'])
        writer.writerow([])
        writer.writerow(['SUMMARY'])
        writer.writerow(['Original Cost:', f"₹ {data['original_cost']:.2f}"])
        writer.writerow(['Optimized Cost:', f"₹ {data['current_cost']:.2f}"])
        
        difference = data['current_cost'] - data['original_cost']
        percentage = (difference / data['original_cost']) * 100 if data['original_cost'] else 0
        
        writer.writerow(['Savings:', f"₹ {difference:.2f} ({percentage:.2f}%)"])
        writer.writerow([])
        
        # Comparison table
        writer.writerow([
            'Material Name',
            'Original Qty', 'Original Rate', 'Original Total',
            'New Qty', 'New Rate', 'New Total',
            'Difference'
        ])
        
        # Create material lookup
        current_materials = {m['name']: m for m in data['current_materials']}
        
        for orig_mat in data['original_materials']:
            curr_mat = current_materials.get(orig_mat['name'], orig_mat)
            
            diff = curr_mat['total'] - orig_mat['total']
            
            writer.writerow([
                orig_mat['name'],
                orig_mat['quantity'], orig_mat['rate'], orig_mat['total'],
                curr_mat['quantity'], curr_mat['rate'], curr_mat['total'],
                diff
            ])
        
        return response
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


# ============================================
# ANALYTICS
# ============================================


def analytics_dashboard(request):
    """
    Main analytics dashboard view
    """
    return render(request, 'costing/analytics_dashboard.html')


def get_analytics_stats(request):
    """
    API endpoint to get overall analytics statistics
    """
    try:
        # Get all adjusted snapshots
        adjusted_snapshots = SavedModel.objects.filter(is_original=False)
        
        # Calculate statistics
        stats = {
            'total_models_optimized': adjusted_snapshots.values('model_name').distinct().count(),
            'total_snapshots': adjusted_snapshots.count(),
            'total_savings': 0,
            'average_savings_percentage': 0,
            'best_optimization': None,
            'recent_optimizations': []
        }
        
        # Calculate savings for each adjusted snapshot
        savings_list = []
        
        for snapshot in adjusted_snapshots:
            comparison = snapshot.get_comparison_with_original()
            if comparison and comparison['is_savings']:
                savings_list.append({
                    'model': snapshot.model_name,
                    'savings': abs(comparison['difference']),
                    'percentage': abs(comparison['percentage']),
                    'saved_at': snapshot.saved_at.strftime('%Y-%m-%d %H:%M')
                })
        
        if savings_list:
            stats['total_savings'] = sum(s['savings'] for s in savings_list)
            stats['average_savings_percentage'] = sum(s['percentage'] for s in savings_list) / len(savings_list)
            stats['best_optimization'] = max(savings_list, key=lambda x: x['savings'])
            stats['recent_optimizations'] = sorted(savings_list, key=lambda x: x['saved_at'], reverse=True)[:5]
        
        return JsonResponse(stats)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_material_breakdown(request):
    """
    API endpoint to get material cost breakdown for a specific model
    """
    snapshot_id = request.GET.get('snapshot_id')
    
    if not snapshot_id:
        return JsonResponse({'error': 'snapshot_id required'}, status=400)
    
    try:
        snapshot = SavedModel.objects.get(id=snapshot_id)
        
        # Extract material data
        materials = snapshot.materials
        
        # Sort by cost (descending)
        materials_sorted = sorted(materials, key=lambda x: x['total'], reverse=True)
        
        # Prepare chart data
        chart_data = {
            'labels': [m['name'] for m in materials_sorted[:10]],  # Top 10
            'values': [float(m['total']) for m in materials_sorted[:10]],
            'total': float(snapshot.final_cost)
        }
        
        return JsonResponse(chart_data)
        
    except SavedModel.DoesNotExist:
        return JsonResponse({'error': 'Snapshot not found'}, status=404)
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_savings_trend(request):
    """
    API endpoint to get savings trend over time
    """
    model_name = request.GET.get('model')
    
    try:
        # Get all adjusted snapshots for this model
        snapshots = SavedModel.objects.filter(
            model_name=model_name,
            is_original=False
        ).order_by('saved_at')
        
        trend_data = {
            'dates': [],
            'savings': [],
            'costs': []
        }
        
        for snapshot in snapshots:
            comparison = snapshot.get_comparison_with_original()
            if comparison:
                trend_data['dates'].append(snapshot.saved_at.strftime('%b %d, %H:%M'))
                trend_data['savings'].append(abs(float(comparison['difference'])) if comparison['is_savings'] else 0)
                trend_data['costs'].append(float(snapshot.final_cost))
        
        return JsonResponse(trend_data)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_model_comparison(request):
    """
    API endpoint to compare multiple models
    """
    try:
        # Get unique models that have both original and adjusted versions
        models_with_savings = []
        
        # Get all unique model names
        model_names = SavedModel.objects.values_list('model_name', flat=True).distinct()
        
        for model_name in model_names:
            original = SavedModel.objects.filter(
                model_name=model_name,
                is_original=True
            ).first()
            
            adjusted = SavedModel.objects.filter(
                model_name=model_name,
                is_original=False
            ).order_by('-saved_at').first()
            
            if original and adjusted:
                difference = float(adjusted.final_cost) - float(original.final_cost)
                percentage = (difference / float(original.final_cost)) * 100 if original.final_cost else 0
                
                if difference < 0:  # Only include if there are savings
                    models_with_savings.append({
                        'model': model_name,
                        'original_cost': float(original.final_cost),
                        'optimized_cost': float(adjusted.final_cost),
                        'savings': abs(difference),
                        'percentage': abs(percentage)
                    })
        
        # Sort by savings (descending)
        models_with_savings.sort(key=lambda x: x['savings'], reverse=True)
        
        return JsonResponse({'models': models_with_savings})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


def get_top_materials(request):
    """
    API endpoint to get top cost-contributing materials across all models
    """
    try:
        # Aggregate material costs across all snapshots
        material_totals = defaultdict(lambda: {'total_cost': 0, 'count': 0})
        
        snapshots = SavedModel.objects.all()
        
        for snapshot in snapshots:
            for material in snapshot.materials:
                material_name = material['name']
                material_totals[material_name]['total_cost'] += material['total']
                material_totals[material_name]['count'] += 1
        
        # Convert to list and sort
        top_materials = []
        for name, data in material_totals.items():
            top_materials.append({
                'name': name,
                'total_cost': data['total_cost'],
                'average_cost': data['total_cost'] / data['count'] if data['count'] > 0 else 0,
                'frequency': data['count']
            })
        
        top_materials.sort(key=lambda x: x['total_cost'], reverse=True)
        
        return JsonResponse({'materials': top_materials[:15]})  # Top 15
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
    

@login_required(login_url='login')
def project_snapshots(request, project_id):
    """
    Display all saved snapshots for a specific project with filtering options
    """
    project = get_object_or_404(Project, id=project_id)
    
    # Get all snapshots for this project
    snapshots = SavedModel.objects.filter(
        project=project
    ).select_related('costing_sheet').order_by('-saved_at')
    
    # Get unique products and models for filters
    products = snapshots.values_list('product_type', flat=True).distinct()
    models_list = snapshots.values_list('model_name', flat=True).distinct()
    
    # Calculate stats
    modified_count = snapshots.filter(is_original=False).count()
    
    # Calculate total savings
    total_savings = 0
    snapshot_list = []
    
    for snapshot in snapshots:
        snapshot_data = {
            'id': snapshot.id,
            'product_type': snapshot.product_type,
            'model_name': snapshot.model_name,
            'final_cost': snapshot.final_cost,
            'is_original': snapshot.is_original,
            'saved_at': snapshot.saved_at,
            'notes': snapshot.notes,
            'savings': 0,
            'comparison': None
        }
        
        # Calculate savings if modified
        if not snapshot.is_original:
            # Find the original for this product/model
            original = snapshots.filter(
                product_type=snapshot.product_type,
                model_name=snapshot.model_name,
                is_original=True
            ).first()
            
            if original:
                difference = original.final_cost - snapshot.final_cost
                percentage = (difference / original.final_cost * 100) if original.final_cost > 0 else 0
                is_savings = difference > 0
                
                snapshot_data['savings'] = difference if is_savings else 0
                snapshot_data['comparison'] = {
                    'difference': abs(difference),
                    'percentage': abs(percentage),
                    'is_savings': is_savings
                }
                
                if is_savings:
                    total_savings += difference
        
        snapshot_list.append(snapshot_data)
    
    context = {
        'project': project,
        'snapshots': snapshot_list,
        'products': products,
        'models': models_list,
        'modified_count': modified_count,
        'total_savings': total_savings,
    }
    
    return render(request, 'costing/project_snapshots.html', context)


@login_required(login_url='login')
def project_analytics(request, project_id):
    """
    Display analytics dashboard for a specific project showing all saved snapshots
    """
    project = get_object_or_404(Project, id=project_id)
    
    # Get all snapshots for this project
    snapshots = SavedModel.objects.filter(
        project=project
    ).select_related('costing_sheet').order_by('-saved_at')
    
    # Calculate metrics
    total_models = snapshots.values('product_type', 'model_name').distinct().count()
    modified_count = snapshots.filter(is_original=False).count()
    snapshots_count = snapshots.count()
    
    # Calculate total savings
    total_savings = 0
    snapshot_list = []
    
    for snapshot in snapshots:
        snapshot_data = {
            'id': snapshot.id,
            'product_type': snapshot.product_type,
            'model_name': snapshot.model_name,
            'final_cost': snapshot.final_cost,
            'is_original': snapshot.is_original,
            'saved_at': snapshot.saved_at,
            'notes': snapshot.notes,
            'comparison': None
        }
        
        # Calculate comparison if modified
        if not snapshot.is_original:
            # Find the original for this product/model
            original = snapshots.filter(
                product_type=snapshot.product_type,
                model_name=snapshot.model_name,
                is_original=True
            ).first()
            
            if original:
                difference = original.final_cost - snapshot.final_cost
                percentage = (difference / original.final_cost * 100) if original.final_cost > 0 else 0
                is_savings = difference > 0
                
                snapshot_data['comparison'] = {
                    'difference': abs(difference),
                    'percentage': abs(percentage),
                    'is_savings': is_savings
                }
                
                if is_savings:
                    total_savings += difference
        
        snapshot_list.append(snapshot_data)
    
    context = {
        'project': project,
        'snapshots': snapshot_list,
        'total_models': total_models,
        'modified_count': modified_count,
        'snapshots_count': snapshots_count,
        'total_savings': total_savings,
    }
    
    return render(request, 'costing/project_analytics.html', context)


def delete_costing_sheet(request, project_id, sheet_id):
    """
    Delete a costing sheet and all its associated models
    """
    if request.method != 'POST':
        return JsonResponse({'error': 'POST required'}, status=400)
    
    project = get_object_or_404(Project, id=project_id)
    sheet = get_object_or_404(CostingSheet, id=sheet_id, project=project)
    
    try:
        # Delete associated saved models
        SavedModel.objects.filter(costing_sheet=sheet).delete()
        
        # Delete the file from filesystem (optional)
        if sheet.file:
            import os
            file_path = sheet.file.path
            if os.path.exists(file_path):
                os.remove(file_path)
        
        # Delete the costing sheet record
        sheet.delete()
        
        return JsonResponse({
            'success': True,
            'message': 'Costing sheet deleted successfully'
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)