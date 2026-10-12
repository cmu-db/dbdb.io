from types import SimpleNamespace
from unittest.mock import patch

from django.test import SimpleTestCase, override_settings

from dbdb.core.utils.enrichment.chatgpt import ChatGPTEnricher

_TOOL_SCHEMA = {
    'name': 'enrich_system',
    'description': 'Fill in missing fields',
    'input_schema': {'type': 'object', 'properties': {'description': {'type': 'string'}}},
}


@override_settings(OPENAI_API_KEY='test-key')
@patch('openai.OpenAI')
class ChatGPTEnricherTestCase(SimpleTestCase):

    def _call(self, mock_openai, output, model='gpt-6.1-sol'):
        client = mock_openai.return_value
        client.responses.create.return_value = SimpleNamespace(output=output)
        enricher = ChatGPTEnricher()
        enricher.set_context(name='Wu-Tang DB')
        result = enricher.call_llm('Describe Wu-Tang DB', _TOOL_SCHEMA, model_override=model)
        return result, client.responses.create.call_args.kwargs

    def test_uses_responses_api_with_function_tool(self, mock_openai):
        _, kwargs = self._call(mock_openai, [
            SimpleNamespace(type='function_call', name='enrich_system', arguments='{}'),
        ])
        self.assertEqual(kwargs['model'], 'gpt-6.1-sol')
        self.assertEqual(kwargs['input'], 'Describe Wu-Tang DB')
        self.assertEqual(kwargs['tool_choice'], {'type': 'function', 'name': 'enrich_system'})
        tool = kwargs['tools'][0]
        self.assertEqual(tool['name'], 'enrich_system')
        self.assertEqual(tool['parameters'], _TOOL_SCHEMA['input_schema'])
        self.assertFalse(tool['strict'])
        self.assertNotIn('reasoning_effort', kwargs)
        mock_openai.return_value.chat.completions.create.assert_not_called()

    def test_returns_function_call_arguments(self, mock_openai):
        result, _ = self._call(mock_openai, [
            SimpleNamespace(type='reasoning'),
            SimpleNamespace(type='function_call', name='enrich_system',
                            arguments='{"description": "Protect Ya Neck"}'),
        ])
        self.assertEqual(result, {'description': 'Protect Ya Neck'})

    def test_raises_without_function_call(self, mock_openai):
        with self.assertRaises(RuntimeError):
            self._call(mock_openai, [SimpleNamespace(type='message')])
