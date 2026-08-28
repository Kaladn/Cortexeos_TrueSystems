import unittest
import importlib

pandas_available = importlib.util.find_spec(\"pandas\") is not None
numpy_available = importlib.util.find_spec(\"numpy\") is not None

if pandas_available and numpy_available:
    from app.prescan_mapper.prescan_mapper import PrescanMapper

@unittest.skipUnless(pandas_available and numpy_available, \"pandas and numpy required\")
class TestPrescanMapper(unittest.TestCase):
    def test_yaml_input(self):
        mapper = PrescanMapper('tests/data/sample.yaml', correlation_method='auto')
        result = mapper.analyze()
        self.assertIn('field_frequency', result)
        self.assertIn('variances', result)
        self.assertIn(result['correlation_method'], {'pearson', 'spearman', None})

    def test_csv_input(self):
        mapper = PrescanMapper('tests/data/sample.csv', correlation_method='pearson')
        result = mapper.analyze()
        self.assertEqual(result['field_frequency']['name'], 3)
        self.assertEqual(result['field_frequency']['age'], 3)
        self.assertEqual(result['field_frequency']['score'], 3)
        self.assertEqual(result['correlation_method'], 'pearson')

if __name__ == '__main__':
    unittest.main()
