from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import os
import json
import threading
from .models import EvaluationResult
from .forms import CodeUploadForm, GitHubForm
from .services import CodeEvaluationService


def index(request):
    """Page d'accueil avec les formulaires."""
    upload_form = CodeUploadForm()
    github_form = GitHubForm()

    context = {
        'upload_form': upload_form,
        'github_form': github_form,
    }

    return render(request, 'evaluator/index.html', context)


def upload_zip(request):
    """Gère l'upload de fichier ZIP."""
    if request.method == 'POST':
        form = CodeUploadForm(request.POST, request.FILES)
        if form.is_valid():
            # Sauvegarder le fichier
            zip_file = form.cleaned_data['zip_file']
            file_path = default_storage.save(f'uploads/{zip_file.name}', ContentFile(zip_file.read()))

            # Créer l'entrée en base
            evaluation = EvaluationResult.objects.create(
                source_type='upload',
                source_path=file_path,
                status='pending'
            )

            # Lancer l'évaluation en arrière-plan
            thread = threading.Thread(
                target=_evaluate_code_async,
                args=(evaluation.id, 'zip', default_storage.path(file_path))
            )
            thread.start()

            return JsonResponse({
                'success': True,
                'evaluation_id': evaluation.id,
                'message': 'Fichier uploadé avec succès. Évaluation en cours...'
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })

    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


def submit_github(request):
    """Gère la soumission d'URL GitHub."""
    if request.method == 'POST':
        form = GitHubForm(request.POST)
        if form.is_valid():
            github_url = form.cleaned_data['github_url']

            # Créer l'entrée en base
            evaluation = EvaluationResult.objects.create(
                source_type='github',
                source_path=github_url,
                status='pending'
            )

            # Lancer l'évaluation en arrière-plan
            thread = threading.Thread(
                target=_evaluate_code_async,
                args=(evaluation.id, 'github', github_url)
            )
            thread.start()

            return JsonResponse({
                'success': True,
                'evaluation_id': evaluation.id,
                'message': 'URL GitHub enregistrée. Évaluation en cours...'
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors
            })

    return JsonResponse({'success': False, 'message': 'Méthode non autorisée'})


def check_status(request, evaluation_id):
    """Vérifie le statut d'une évaluation."""
    try:
        evaluation = get_object_or_404(EvaluationResult, id=evaluation_id)

        response_data = {
            'status': evaluation.status,
            'id': evaluation.id,
        }

        if evaluation.status == 'completed':
            response_data.update({
                'maintainability_index': evaluation.maintainability_index,
                'bugs_probability': evaluation.bugs_probability,
                'halstead_volume': evaluation.halstead_volume,
                'lcom4': evaluation.lcom4,
                'complexity': evaluation.complexity,
                'pylint_score': evaluation.pylint_score,
                'source_metrics': evaluation.get_source_metrics(),
                'code_structure': evaluation.get_code_structure(),  # Ajouté
            })
        elif evaluation.status == 'failed':
            response_data['error'] = evaluation.error_message

        return JsonResponse(response_data)

    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e)
        })


def dashboard(request, evaluation_id):
    """Affiche le dashboard des résultats."""
    evaluation = get_object_or_404(EvaluationResult, id=evaluation_id)

    if evaluation.status != 'completed':
        return render(request, 'evaluator/pending.html', {'evaluation': evaluation})

    source_metrics = evaluation.get_source_metrics()
    code_structure = evaluation.get_code_structure()

    # Debug pour vérifier les données
    print("Debug - Code Structure:", code_structure)
    print("Debug - Type:", type(code_structure))
    
    # S'assurer que code_structure contient des données valides
    if not code_structure or not isinstance(code_structure, dict):
        code_structure = {
            'classes': 0,
            'methods': 0,
            'functions': 0,
            'async_functions': 0,
            'imports': 0,
            'decorators': 0
        }

    context = {
        'evaluation': evaluation,
        'source_metrics': source_metrics,
        'code_structure': code_structure,
        'code_structure_json': json.dumps(code_structure),  # Version JSON pour le template
    }

    return render(request, 'evaluator/dashboard.html', context)


def _evaluate_code_async(evaluation_id: int, source_type: str, source_path: str):
    """Évalue le code de manière asynchrone."""
    try:
        evaluation = EvaluationResult.objects.get(id=evaluation_id)
        service = CodeEvaluationService()

        if source_type == 'zip':
            results = service.evaluate_from_zip(source_path)
        elif source_type == 'github':
            results = service.evaluate_from_github(source_path)
        else:
            raise ValueError("Type de source non supporté")

        if 'error' in results:
            evaluation.status = 'failed'
            evaluation.error_message = results['error']
        else:
            evaluation.status = 'completed'
            evaluation.maintainability_index = results.get('maintainability_index')
            evaluation.bugs_probability = results.get('bugs_probability')
            evaluation.halstead_volume = results.get('halstead_volume')
            evaluation.lcom4 = results.get('lcom4')
            evaluation.complexity = results.get('complexity')
            evaluation.pylint_score = results.get('pylint_score')
            evaluation.set_source_metrics(results.get('source_metrics', {}))
            evaluation.set_code_structure(results.get('code_structure', {}))

        evaluation.save()

        # Nettoyer le fichier uploadé si nécessaire
        if source_type == 'zip' and os.path.exists(source_path):
            try:
                os.remove(source_path)
            except Exception:
                pass  # Ignorer les erreurs de suppression

    except Exception as e:
        try:
            evaluation = EvaluationResult.objects.get(id=evaluation_id)
            evaluation.status = 'failed'
            evaluation.error_message = str(e)
            evaluation.save()
        except Exception:
            pass  # Ignorer si on ne peut pas sauvegarder l'erreur