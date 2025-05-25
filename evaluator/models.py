from django.db import models
import json


class EvaluationResult(models.Model):
    """Modèle pour stocker les résultats d'évaluation de code."""

    STATUS_CHOICES = [
        ('pending', 'En cours'),
        ('completed', 'Terminé'),
        ('failed', 'Échoué'),
    ]

    SOURCE_CHOICES = [
        ('upload', 'Fichier uploadé'),
        ('github', 'Dépôt GitHub'),
    ]

    created_at = models.DateTimeField(auto_now_add=True)
    source_type = models.CharField(max_length=10, choices=SOURCE_CHOICES)
    source_path = models.CharField(max_length=500)  # Chemin du fichier ou URL GitHub
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='pending')

    # Métriques calculées
    maintainability_index = models.FloatField(null=True, blank=True)
    bugs_probability = models.FloatField(null=True, blank=True)
    halstead_volume = models.FloatField(null=True, blank=True)
    lcom4 = models.FloatField(null=True, blank=True)
    complexity = models.FloatField(null=True, blank=True)
    code_structure = models.TextField(null=True, blank=True)  # JSON pour stocker la structure

    # Contenu du code source (JSON)
    source_metrics = models.TextField(null=True, blank=True)  # JSON des métriques détaillées
    pylint_score = models.FloatField(null=True, blank=True)

    # Messages d'erreur éventuels
    error_message = models.TextField(null=True, blank=True)

    class Meta:
        ordering = ['-created_at']

    def get_source_metrics(self):
        """Retourne les métriques source sous forme de dictionnaire."""
        if self.source_metrics:
            return json.loads(self.source_metrics)
        return {}
    
    def get_code_structure(self):
        """Retourne la structure du code sous forme de dictionnaire."""
        if self.code_structure:
            return json.loads(self.code_structure)
        return {}
    
    def set_code_structure(self, structure_dict):
        """Définit la structure du code à partir d'un dictionnaire."""
        self.code_structure = json.dumps(structure_dict)

    def set_source_metrics(self, metrics_dict):
        """Définit les métriques source à partir d'un dictionnaire."""
        self.source_metrics = json.dumps(metrics_dict)

    def __str__(self):
        return f"Évaluation {self.id} - {self.source_type} - {self.status}"