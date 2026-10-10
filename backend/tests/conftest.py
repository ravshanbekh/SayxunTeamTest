"""
Pytest sozlamalari: app.config import qilinishidan oldin test muhiti o'zgaruvchilari.
"""
import os
import sys
import tempfile

_tmp_dir = tempfile.mkdtemp(prefix="rasch_tests_")
os.environ.setdefault("DATABASE_URL", f"sqlite+aiosqlite:///{os.path.join(_tmp_dir, 'test.db')}")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("EXPORT_DIR", os.path.join(_tmp_dir, "exports"))

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
