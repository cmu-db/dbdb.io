from django.test import SimpleTestCase

from dbdb.core.utils.enrichment.chatgpt import _is_reasoning_model


class IsReasoningModelTestCase(SimpleTestCase):

    def test_reasoning_models(self):
        for model in ('o1', 'o3-mini', 'o4-mini', 'gpt-5', 'gpt-5.1', 'gpt-5-mini', 'gpt-6.1-sol', 'gpt-10'):
            with self.subTest(model=model):
                self.assertTrue(_is_reasoning_model(model))

    def test_non_reasoning_models(self):
        for model in ('gpt-4o', 'gpt-4o-mini', 'gpt-4.1', 'gpt-3.5-turbo', 'chatgpt-4o-latest'):
            with self.subTest(model=model):
                self.assertFalse(_is_reasoning_model(model))
