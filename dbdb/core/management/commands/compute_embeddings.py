# stdlib imports
# django imports
import torch
from django.core.management import BaseCommand
from transformers import AutoModel, AutoTokenizer

from dbdb.core.models import SystemFeature, SystemVersion


class Command(BaseCommand):

    #Mean Pooling - Take attention mask into account for correct averaging
    def mean_pooling(self, model_output, attention_mask):
        token_embeddings = model_output[0] #First element of model_output contains all token embeddings
        input_mask_expanded = attention_mask.unsqueeze(-1).expand(token_embeddings.size()).float()
        return torch.sum(token_embeddings * input_mask_expanded, 1) / torch.clamp(input_mask_expanded.sum(1), min=1e-9)

    def handle(self, *args, **options):
        # Sentences we want sentence embeddings for
        sentences = []
        features = [ 'Data Model', 'Query Interface', 'Storage Format']
        for s in SystemVersion.objects.filter(is_current=True).order_by("-id"):
            words = [s.version.name]
            words = words + [x.name for x in s.tags.all()]
            words = words + [x.name for x in s.countries]
            words += s.former_names
            words = words + [x.name for x in s.meta.written_in.all()]
            for f in features:
                sf = SystemFeature.objects.filter(system=s).filter(feature__label=f)
                if sf: words = words + [o.value for o in sf[0].options.all()]
            words = words + [s.description]
            sentences.append(" ".join(words))


        # Load model from HuggingFace Hub
        tokenizer = AutoTokenizer.from_pretrained('sentence-transformers/paraphrase-MiniLM-L6-v2')
        model = AutoModel.from_pretrained('sentence-transformers/paraphrase-MiniLM-L6-v2')

        # Tokenize sentences
        encoded_input = tokenizer(sentences, padding=True, truncation=True, return_tensors='pt')

        # Compute token embeddings
        with torch.no_grad():
            model_output = model(**encoded_input)

        # Perform pooling. In this case, max pooling.
        sentence_embeddings = self.mean_pooling(model_output, encoded_input['attention_mask'])

        torch.save(sentence_embeddings, 'embeddings.pt')

        systems = SystemVersion.objects.filter(is_current=True).order_by("-id")
        for i in range(len(systems)):
            systems[i].embedding = sentence_embeddings[i]
            systems[i].save()
            print("Updated: {}", systems[i])

        pass

