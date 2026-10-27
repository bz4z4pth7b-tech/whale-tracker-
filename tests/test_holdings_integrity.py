import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'research'))
from whales import holdings
from test_whales import holding, META


class HoldingsIntegrityTests(unittest.TestCase):
    def collect_documents(self, documents):
        sec = Mock()
        sec.text.side_effect = documents
        with patch('whales.document_urls', return_value=[str(i) for i in range(len(documents))]):
            return holdings(sec, META)

    def test_invalid_second_table_rejects_partial_portfolio(self):
        with self.assertRaisesRegex(ValueError, 'Invalid information-table'):
            self.collect_documents([holding(), holding(shares='NaN')])

    def test_empty_information_table_rejects_partial_portfolio(self):
        with self.assertRaisesRegex(ValueError, 'No information-table rows'):
            self.collect_documents([holding(), '<informationTable/>'])

    def test_header_skipped_and_valid_tables_combined(self):
        result = self.collect_documents(['<edgarSubmission/>', holding(), holding(shares='200')])
        self.assertEqual(result['123456789|COM']['shares'], 300)

    def test_unsafe_xml_cannot_be_silently_skipped(self):
        with self.assertRaisesRegex(ValueError, 'External XML entities'):
            self.collect_documents([holding(), '<!DOCTYPE informationTable><informationTable/>'])
