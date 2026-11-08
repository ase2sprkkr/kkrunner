"""Resolve explicit project-backed execution without global persistence."""

from __future__ import annotations

from kkrunner.projects.manager import ProjectExecutionManager
from kkrunner.projects.repository import Project


def resolve_project_manager(project):
    """Only an existing project enables durable run tracking."""
    if project is None or project is False:
        return None
    if isinstance(project, ProjectExecutionManager):
        if project.project_id is None:
            raise ValueError("ProjectExecutionManager must be bound to a project")
        return project
    if isinstance(project, (Project, str)):
        return ProjectExecutionManager(project=project)
    raise TypeError("project must be a Project, project ID, or project-bound ProjectExecutionManager")
