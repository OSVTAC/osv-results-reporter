from datetime import datetime
from unittest import TestCase
from unittest.mock import patch

import orr.main as main


class MainModuleTest(TestCase):

    """
    Test the functions in orr.main.
    """

    @patch('datetime.datetime')
    def test_generate_output_name(self, mock_dt):
        mock_dt.now.return_value = datetime(2018, 1, 2, 16, 30, 15)
        expected = 'build_20180102_163015'
        actual = main.generate_output_name()
        self.assertEqual(actual, expected)
