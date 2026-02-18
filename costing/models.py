from django.db import models
from django.utils import timezone
import json
from django.contrib.auth.models import User

class Project(models.Model):
    """
    Represents a client project (e.g., Reliance, Tata Steel)
    """
    name = models.CharField(max_length=200, unique=True)
    client_name = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    

    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='created_projects')

    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return self.name
    
    def get_total_models(self):
        """Count unique models across all sheets"""
        return SavedModel.objects.filter(project=self).values('model_name').distinct().count()
    
    def get_total_savings(self):
        """Calculate total savings across all optimizations"""
        total = 0
        adjusted_snapshots = SavedModel.objects.filter(project=self, is_original=False)
        
        for snapshot in adjusted_snapshots:
            comparison = snapshot.get_comparison_with_original()
            if comparison and comparison['is_savings']:
                total += abs(comparison['difference'])
        
        return total
    
    def get_sheets_count(self):
        """Get number of uploaded costing sheets"""
        return self.costingsheet_set.count()

class ModelSnapshot(models.Model):
    """
    Stores a snapshot of a tank model's costing data
    Can be either original (from Excel) or modified (user adjustments)
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    costing_sheet = models.ForeignKey('CostingSheet', on_delete=models.CASCADE, null=True, blank=True)
    
    # Model identification
    product_type = models.CharField(max_length=50)  # RCT, SST
    model_name = models.CharField(max_length=100)
    
    # Costing data (stored as JSON)
    materials = models.JSONField()  # List of materials with qty, rate, total
    final_cost = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Metadata
    is_original = models.BooleanField(default=True)  # True = from Excel, False = modified
    created_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['project', 'model_name']),
            models.Index(fields=['is_original']),
        ]
    
    def __str__(self):
        status = "Original" if self.is_original else "Modified"
        return f"{self.project.name} - {self.model_name} ({status})"
    
    def get_material_count(self):
        """Count number of materials in this snapshot"""
        return len(self.materials)
    
    def get_cost_comparison(self):
        """
        Compare this snapshot with the original
        Returns dict with savings/increase info
        """
        if self.is_original:
            return None
        
        # Find original snapshot
        original = ModelSnapshot.objects.filter(
            project=self.project,
            model_name=self.model_name,
            is_original=True
        ).first()
        
        if not original:
            return None
        
        difference = float(self.final_cost) - float(original.final_cost)
        percentage = (difference / float(original.final_cost)) * 100 if original.final_cost else 0
        
        return {
            'original_cost': float(original.final_cost),
            'current_cost': float(self.final_cost),
            'difference': difference,
            'percentage': percentage,
            'is_savings': difference < 0
        }


class MaterialAdjustmentLog(models.Model):
    """
    Logs individual material adjustments for audit trail
    """
    snapshot = models.ForeignKey(ModelSnapshot, on_delete=models.CASCADE, related_name='adjustments')
    material_name = models.CharField(max_length=200)
    
    # Before values
    old_quantity = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    old_rate = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    old_total = models.DecimalField(max_digits=12, decimal_places=2, null=True)
    
    # After values
    new_quantity = models.DecimalField(max_digits=10, decimal_places=2)
    new_rate = models.DecimalField(max_digits=10, decimal_places=2)
    new_total = models.DecimalField(max_digits=12, decimal_places=2)
    
    adjusted_at = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-adjusted_at']
    
    def __str__(self):
        return f"{self.snapshot.model_name} - {self.material_name}"
    
    def get_change_amount(self):
        """Calculate the cost change this adjustment caused"""
        if self.old_total:
            return float(self.new_total) - float(self.old_total)
        return 0
    
class SavedModel(models.Model):
    """
    Stores a saved/adjusted tank model snapshot
    NOW LINKED TO PROJECT!
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=True, blank=True)
    costing_sheet = models.ForeignKey('CostingSheet', on_delete=models.SET_NULL, null=True, blank=True)
    
    # Identification
    product_type = models.CharField(max_length=50)  # RCT, SST
    model_name = models.CharField(max_length=100)
    
    # Costing data (stored as JSON)
    materials = models.JSONField()  # List of materials with qty, rate, total
    final_cost = models.DecimalField(max_digits=12, decimal_places=2)
    
    # Metadata
    is_original = models.BooleanField(default=False)  # True = from Excel, False = user-adjusted
    saved_at = models.DateTimeField(default=timezone.now)
    notes = models.TextField(blank=True, null=True)  # Optional user notes
    
    class Meta:
        ordering = ['-saved_at']
        indexes = [
            models.Index(fields=['project', 'product_type', 'model_name']),
            models.Index(fields=['saved_at']),
        ]
    
    def __str__(self):
        status = "Original" if self.is_original else "Adjusted"
        project_name = self.project.name if self.project else "No Project"
        return f"{project_name} - {self.model_name} ({status})"
    
    def get_material_count(self):
        """Count number of materials"""
        return len(self.materials)
    
    def get_comparison_with_original(self):
        """
        Compare this snapshot with the original version
        Returns savings/increase info
        """
        if self.is_original:
            return None
        
        # Find original snapshot (same project and model)
        original = SavedModel.objects.filter(
            project=self.project,
            product_type=self.product_type,
            model_name=self.model_name,
            is_original=True
        ).first()
        
        if not original:
            return None
        
        difference = float(self.final_cost) - float(original.final_cost)
        percentage = (difference / float(original.final_cost)) * 100 if original.final_cost else 0
        
        return {
            'original_cost': float(original.final_cost),
            'current_cost': float(self.final_cost),
            'difference': difference,
            'percentage': percentage,
            'is_savings': difference < 0
        }

class CostingSheet(models.Model):
    """
    Represents an uploaded Excel costing sheet
    """
    project = models.ForeignKey(Project, on_delete=models.CASCADE)
    file = models.FileField(upload_to='costing_sheets/')
    original_filename = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(default=timezone.now)
    total_models = models.IntegerField(default=0)
    notes = models.TextField(blank=True, null=True)
    
    class Meta:
        ordering = ['-uploaded_at']
    
    def __str__(self):
        return f"{self.project.name} - {self.original_filename}"












