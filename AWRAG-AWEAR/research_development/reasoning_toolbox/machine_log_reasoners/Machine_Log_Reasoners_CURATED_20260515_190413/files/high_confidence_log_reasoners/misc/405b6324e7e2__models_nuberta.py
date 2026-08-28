import torch
import torch.nn as nn
from transformers import BertModel, RobertaModel

class NuBERTa(nn.Module):
    """
    Combines BERT and RoBERTa embeddings with a classification layer.
    """
    def __init__(self):
        super(NuBERTa, self).__init__()
        self.bert = BertModel.from_pretrained('bert-base-uncased')
        self.roberta = RobertaModel.from_pretrained('roberta-base')
        self.classifier = nn.Linear(768 * 2, 2)  # Binary classification

    def forward(self, input_ids, attention_mask):
        # BERT output
        bert_output = self.bert(input_ids=input_ids, attention_mask=attention_mask)
        # RoBERTa output
        roberta_output = self.roberta(input_ids=input_ids, attention_mask=attention_mask)
        # Combine outputs
        combined_output = torch.cat(
            (bert_output.last_hidden_state[:, 0, :], roberta_output.last_hidden_state[:, 0, :]), dim=-1
        )
        logits = self.classifier(combined_output)
        return logits
