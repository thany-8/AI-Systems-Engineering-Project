"""Shared Flask extensions.

Kept in a standalone module so ``models`` and ``server`` can both import the
same instances without creating a circular import.
"""
from __future__ import annotations

from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
login_manager = LoginManager()
