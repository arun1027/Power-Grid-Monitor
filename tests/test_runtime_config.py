import os
import unittest

import application


class RuntimeConfigTests(unittest.TestCase):
    def test_default_port_is_8000(self):
        self.assertEqual(application.get_app_port(), 8000)

    def test_port_can_be_overridden(self):
        os.environ["PORT"] = "9000"
        try:
            self.assertEqual(application.get_app_port(), 9000)
        finally:
            os.environ.pop("PORT", None)


if __name__ == "__main__":
    unittest.main()
