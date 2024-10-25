import unittest
from unittest.mock import patch, MagicMock
from openapi_agent import OpenAPIAgent

class TestOpenAPIAgent(unittest.TestCase):
    def setUp(self):
        self.agent = OpenAPIAgent("https://api.example.com/openapi.json")

    @patch('openapi_agent.agent.requests.get')
    def test_load_api_spec(self, mock_get):
        mock_response = MagicMock()
        mock_response.text = "openapi: 3.0.0\ninfo:\n  title: Test API"
        mock_get.return_value = mock_response

        api_spec = self.agent._load_api_spec()
        self.assertEqual(api_spec['openapi'], '3.0.0')
        self.assertEqual(api_spec['info']['title'], 'Test API')

    @patch('openapi_agent.agent.requests.request')
    def test_execute_operation(self, mock_request):
        mock_response = MagicMock()
        mock_response.json.return_value = {"result": "success"}
        mock_request.return_value = mock_response

        self.agent.api_spec = {
            "servers": [{"url": "https://api.example.com"}],
            "paths": {
                "/test": {
                    "get": {
                        "operationId": "testOperation"
                    }
                }
            }
        }

        result = self.agent.execute_operation("testOperation", params={"param": "value"})
        self.assertEqual(result, {"result": "success"})
        mock_request.assert_called_once_with("get", "https://api.example.com/test", params={"param": "value"})

    # Add more test methods as needed

if __name__ == '__main__':
    unittest.main()
