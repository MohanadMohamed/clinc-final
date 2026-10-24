import tempfile
import unittest
from pathlib import Path

from desktop.packaging.config import validate

ROOT = Path(__file__).resolve().parents[2]
PLAN = ROOT / "desktop/packaging/lan.example.toml"


class PlanTests(unittest.TestCase):
    def test_example(self):
        self.assertEqual(validate(PLAN)["https_port"], 8443)

    def test_rejects_db_exposure_and_origin_mismatch(self):
        for before, after in [
            ("127.0.0.1,::1", "*"),
            (
                "https://doctor.clinic.home.arpa:8443",
                "http://doctor.clinic.home.arpa:8443",
            ),
            ("192.168.50.11", "0.0.0.0"),
            ("https_port = 8443", "https_port = 5432"),
        ]:
            with self.subTest(after=after), tempfile.TemporaryDirectory() as temp:
                plan = Path(temp) / "plan.toml"
                plan.write_text(PLAN.read_text().replace(before, after))
                with self.assertRaises(ValueError):
                    validate(plan)
