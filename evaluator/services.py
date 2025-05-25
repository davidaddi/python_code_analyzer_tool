import os
import subprocess
import zipfile
import tempfile
import shutil
import json
import math
from pathlib import Path
from typing import Dict, List, Any
from git import Repo
from radon.complexity import cc_visit
from radon.metrics import mi_visit, h_visit
from radon.raw import analyze
import ast


class CodeEvaluationService:
    """Service responsable de l'évaluation de code Python."""

    def __init__(self):
        self.temp_dir = None
        self.python_files = []

    def _analyze_code_structure(self) -> Dict[str, int]:
        """Analyse la structure du code (classes, méthodes, etc.)."""
        
        structure_count = {
            'classes': 0,
            'methods': 0,
            'functions': 0,
            'async_functions': 0,
            'decorators': 0
        }
        
        class StructureVisitor(ast.NodeVisitor):
            def __init__(self, counts):
                self.counts = counts
                self.current_class = None
                
            def visit_ClassDef(self, node):
                self.counts['classes'] += 1
                old_class = self.current_class
                self.current_class = node
                self.generic_visit(node)
                self.current_class = old_class
                
            def visit_FunctionDef(self, node):
                if self.current_class is not None:
                    self.counts['methods'] += 1
                else:
                    self.counts['functions'] += 1
                
                # Compter les décorateurs
                self.counts['decorators'] += len(node.decorator_list)
                self.generic_visit(node)
                
            def visit_AsyncFunctionDef(self, node):
                self.counts['async_functions'] += 1
                # Compter les décorateurs
                self.counts['decorators'] += len(node.decorator_list)
                self.generic_visit(node)
                
        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    tree = ast.parse(content)
                    visitor = StructureVisitor(structure_count)
                    visitor.visit(tree)
            except Exception as e:
                print(f"[Structure] Erreur fichier {file_path} : {e}")
                continue
                
        return structure_count

    def evaluate_from_zip(self, zip_path: str) -> Dict[str, Any]:
        """Évalue le code à partir d'un fichier ZIP."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                self.temp_dir = temp_dir
                self._extract_zip(zip_path, temp_dir)
                return self._perform_evaluation()
        except Exception as e:
            return {'error': str(e)}

    def evaluate_from_github(self, github_url: str) -> Dict[str, Any]:
        """Évalue le code à partir d'un dépôt GitHub."""
        try:
            with tempfile.TemporaryDirectory() as temp_dir:
                self.temp_dir = temp_dir
                self._clone_github_repo(github_url, temp_dir)
                return self._perform_evaluation()
        except Exception as e:
            return {'error': str(e)}

    def _extract_zip(self, zip_path: str, extract_path: str):
        """Extrait le fichier ZIP."""
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(extract_path)

    def _clone_github_repo(self, github_url: str, clone_path: str):
        """Clone le dépôt GitHub."""
        Repo.clone_from(github_url, clone_path)

    def _find_python_files(self, directory: str) -> List[str]:
        """Trouve tous les fichiers Python dans le répertoire."""
        python_files = []
        for root, dirs, files in os.walk(directory):
            # Ignorer les dossiers cachés et les environnements virtuels
            dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['venv', '__pycache__']]

            for file in files:
                if file.endswith('.py'):
                    python_files.append(os.path.join(root, file))

        return python_files

    def _perform_evaluation(self) -> Dict[str, Any]:
        """Effectue l'évaluation complète du code."""
        self.python_files = self._find_python_files(self.temp_dir)

        if not self.python_files:
            return {'error': 'Aucun fichier Python trouvé dans le projet.'}

        results = {
            'maintainability_index': self._calculate_maintainability_index(),
            'bugs_probability': self._calculate_bugs_probability(),
            'halstead_volume': self._calculate_halstead_volume(),
            'lcom4': self._calculate_lcom4(),
            'complexity': self._calculate_complexity(),
            'source_metrics': self._calculate_source_metrics(),
            'pylint_score': self._run_pylint(),
            'code_structure': self._analyze_code_structure(),
        }

        return results

    def _calculate_maintainability_index(self) -> float:
        """Calcule l'indice de maintenabilité."""
        total_mi = 0
        file_count = 0

        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    mi_results = mi_visit(content, multi=True)
                    if isinstance(mi_results, float):
                        total_mi += mi_results
                        file_count += 1
                    elif isinstance(mi_results, list):
                        total_mi += sum(block.mi for block in mi_results)
                        file_count += len(mi_results)
            except Exception as e:
                print(f"[MI] Erreur fichier {file_path} : {e}")
                continue

        return round(total_mi / max(file_count, 1), 2)

    def _calculate_bugs_probability(self) -> float:
        """Calcule la probabilité de bugs."""
        total_complexity = self._calculate_complexity()
        total_lines = sum(self._get_file_lines(f) for f in self.python_files)

        # Formule simplifiée basée sur la complexité et les lignes de code
        bugs_prob = (total_complexity / max(total_lines, 1)) * 100
        return round(min(bugs_prob, 100.0), 2)

    def _calculate_halstead_volume(self) -> float:
        """Calcule le volume de Halstead."""
        total_volume = 0
        block_count = 0

        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    h_results = h_visit(content)  # toujours une liste

                    for h in h_results:
                        if hasattr(h, 'volume') and isinstance(h.volume, (float, int)):
                            total_volume += h.volume
                            block_count += 1
            except Exception as e:
                print(f"[Halstead] Erreur fichier {file_path} : {e}")
                continue

        return round(total_volume / max(block_count, 1), 2)

    def _calculate_lcom4(self) -> float:
        """Calcule la métrique LCOM4 (approximation)."""
        # Pour simplifier, on utilise une approximation basée sur la cohésion des classes
        total_score = 0
        class_count = 0

        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    # Compte approximatif des classes et méthodes
                    class_lines = [line for line in content.split('\n') if line.strip().startswith('class ')]
                    method_lines = [line for line in content.split('\n') if line.strip().startswith('def ')]

                    if class_lines:
                        methods_per_class = len(method_lines) / len(class_lines)
                        # Score inversé : plus il y a de méthodes par classe, moins c'est cohésif
                        cohesion = 1 / (1 + methods_per_class * 0.1)
                        total_score += cohesion
                        class_count += 1
            except Exception:
                continue

        return round(total_score / max(class_count, 1), 2) if class_count > 0 else 1.0

    def _calculate_complexity(self) -> float:
        """Calcule la complexité cyclomatique moyenne."""
        total_complexity = 0
        function_count = 0

        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    cc_results = cc_visit(content)
                    if cc_results:
                        total_complexity += sum(block.complexity for block in cc_results)
                        function_count += len(cc_results)
            except Exception as e:
                print(f"[Complexity] Erreur fichier {file_path} : {e}")
                continue

        return round(total_complexity / max(function_count, 1), 2)

    def _calculate_source_metrics(self) -> Dict[str, Any]:
        """Calcule les métriques du code source."""
        total_lines = 0
        total_logical_lines = 0
        total_comments = 0
        total_blank_lines = 0

        for file_path in self.python_files:
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                    analysis = analyze(content)

                    total_lines += analysis.loc
                    total_logical_lines += analysis.lloc
                    total_comments += analysis.comments
                    total_blank_lines += analysis.blank
            except Exception as e:
                print(f"[Source Metrics] Erreur fichier {file_path} : {e}")
                continue

        comment_ratio = (total_comments / max(total_lines, 1)) * 100

        return {
            'total_lines': total_lines,
            'logical_lines': total_logical_lines,
            'comments': total_comments,
            'blank_lines': total_blank_lines,
            'comment_ratio': round(comment_ratio, 2),
            'files_analyzed': len(self.python_files),
        }

    def _run_pylint(self) -> float:
        """Exécute Pylint et retourne le score."""
        if not self.python_files:
            return 0.0

        try:
            # Prendre seulement les premiers fichiers pour éviter les timeouts
            files_to_analyze = self.python_files[:10]

            cmd = ['pylint'] + files_to_analyze + ['--score=yes', '--reports=no']
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30,
                cwd=self.temp_dir
            )

            # Extraire le score de la sortie
            for line in result.stdout.split('\n'):
                if 'Your code has been rated at' in line:
                    score_part = line.split('Your code has been rated at')[1].split('/')[0].strip()
                    return float(score_part)

            return 5.0  # Score par défaut si pas trouvé

        except Exception:
            return 5.0  # Score par défaut en cas d'erreur

    def _get_file_lines(self, file_path: str) -> int:
        """Compte le nombre de lignes dans un fichier."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return len(f.readlines())
        except Exception:
            return 0