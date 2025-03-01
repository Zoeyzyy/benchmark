import torch
import torch.nn as nn
from torch.optim.lr_scheduler import StepLR
from transformers import (
    BertForQuestionAnswering, BertTokenizerFast,
    RobertaForQuestionAnswering, RobertaTokenizerFast,
    BartForSequenceClassification, BartTokenizer,
    GPT2ForSequenceClassification, GPT2Tokenizer
)

cfg = {
    'A' : [64,     'M', 128,      'M', 256, 256,           'M', 512, 512,           'M', 512, 512,           'M'],
    'B' : [64, 64, 'M', 128, 128, 'M', 256, 256,           'M', 512, 512,           'M', 512, 512,           'M'],
    'D' : [64, 64, 'M', 128, 128, 'M', 256, 256, 256,      'M', 512, 512, 512,      'M', 512, 512, 512,      'M'],
    'E' : [64, 64, 'M', 128, 128, 'M', 256, 256, 256, 256, 'M', 512, 512, 512, 512, 'M', 512, 512, 512, 512, 'M']
}

class VGG(nn.Module):
    def __init__(self, features, num_class=100):
        super().__init__()
        self.features = features

        self.classifier = nn.Sequential(
            nn.Linear(512, 4096),
            nn.ReLU(inplace=True),
            nn.Dropout(),
            nn.Linear(4096, 4096),
            nn.ReLU(inplace=True),
            nn.Dropout(),
            nn.Linear(4096, num_class)
        )

    def forward(self, x):
        output = self.features(x)
        output = output.view(output.size()[0], -1)
        output = self.classifier(output)

        return output

def make_layers(cfg, batch_norm=False):
    layers = []
    input_channel = 3
    for l in cfg:
        if l == 'M':
            layers += [nn.MaxPool2d(kernel_size=2, stride=2)]
            continue

        layers += [nn.Conv2d(input_channel, l, kernel_size=3, padding=1)]

        if batch_norm:
            layers += [nn.BatchNorm2d(l)]

        layers += [nn.ReLU(inplace=True)]
        input_channel = l
    return nn.Sequential(*layers)

def vgg11_bn():
    return VGG(make_layers(cfg['A'], batch_norm=True))

def vgg13_bn():
    return VGG(make_layers(cfg['B'], batch_norm=True))

def vgg16_bn():
    return VGG(make_layers(cfg['D'], batch_norm=True))

def vgg19_bn():
    return VGG(make_layers(cfg['E'], batch_norm=True))

def get_model(model_name, num_classes=100):
    """
    Factory function to create models based on model name
    """
    if model_name == "vgg19":
        model = vgg19_bn()
        optimizer = torch.optim.SGD(model.parameters(), lr=0.05,
                            momentum=0.9,
                            weight_decay=5e-4)
        scheduler = StepLR(optimizer, step_size=40, gamma=0.2)
        return model, None, optimizer, scheduler
    
    elif model_name == "bert":
        model = BertForQuestionAnswering.from_pretrained("bert-base-uncased")
        tokenizer = BertTokenizerFast.from_pretrained('bert-base-uncased')
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-5, eps=1e-8)
        scheduler = StepLR(optimizer, step_size=30, gamma=0.1)
        return model, tokenizer, optimizer, scheduler
    
    elif model_name == "roberta":
        model = RobertaForQuestionAnswering.from_pretrained('roberta-base')
        tokenizer = RobertaTokenizerFast.from_pretrained('roberta-base')
        optimizer = torch.optim.AdamW(model.parameters(), lr=3e-5, eps=1e-8)
        scheduler = StepLR(optimizer, step_size=30, gamma=0.1)
        return model, tokenizer, optimizer, scheduler
    
    elif model_name == "bart":
        model = BartForSequenceClassification.from_pretrained('facebook/bart-base', num_labels=2)
        tokenizer = BartTokenizer.from_pretrained('facebook/bart-base')
        no_decay = ["bias", "LayerNorm.weight"]
        optimizer_grouped_parameters = [
            {
                "params": [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
                "weight_decay": 0.0,
            },
            {"params": [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)], "weight_decay": 0.0},
        ]
        optimizer = torch.optim.AdamW(optimizer_grouped_parameters, lr=5e-6, eps=1e-8)
        scheduler = StepLR(optimizer, step_size=30, gamma=0.1)
        return model, tokenizer, optimizer, scheduler
    
    elif model_name == "gpt2":
        model = GPT2ForSequenceClassification.from_pretrained('gpt2', num_labels=2)
        tokenizer = GPT2Tokenizer.from_pretrained('gpt2')
        tokenizer.pad_token = tokenizer.eos_token
        model.config.pad_token_id = tokenizer.pad_token_id
        no_decay = ["bias", "LayerNorm.weight"]
        optimizer_grouped_parameters = [
            {
                "params": [p for n, p in model.named_parameters() if not any(nd in n for nd in no_decay)],
                "weight_decay": 0.0,
            },
            {"params": [p for n, p in model.named_parameters() if any(nd in n for nd in no_decay)], "weight_decay": 0.0},
        ]
        optimizer = torch.optim.AdamW(optimizer_grouped_parameters, lr=5e-6, eps=1e-8)
        scheduler = StepLR(optimizer, step_size=30, gamma=0.1)
        return model, tokenizer, optimizer, scheduler
    
    else:
        raise ValueError(f"Unsupported model: {model_name}")
