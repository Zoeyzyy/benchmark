import json
import torch
import torchvision.datasets as datasets
from torch.utils.data import TensorDataset
import torchvision.transforms as transforms
from transformers import glue_processors as processors
from transformers import glue_convert_examples_to_features
from transformers import glue_output_modes as output_modes

def get_dataset(model_name, tokenizer=None):
    """
    Factory function to get datasets for different models
    """
    if model_name in ["bert", "roberta"]:
        return _get_squad_dataset(tokenizer)
    elif model_name in ["bart", "gpt2"]:
        return _get_glue_dataset(tokenizer)
    elif model_name == "vgg19":
        return _get_cifar_dataset()
    else:
        raise ValueError(f"Unsupported model: {model_name}")

def _read_squad(path):
    with open(path + '/train-v2.0.json', 'rb') as f: squad_dict = json.load(f)
    contexts = []
    questions = []
    answers = []
    for group in squad_dict['data']:
        for passage in group['paragraphs']:
            context = passage['context']
            for qa in passage['qas']:
                question = qa['question']
                for answer in qa['answers']:
                    contexts.append(context)
                    questions.append(question)
                    answers.append(answer)
    return contexts, questions, answers

def _add_end_idx(answers, contexts):
    for answer, context in zip(answers, contexts):
        gold_text = answer['text']
        start_idx = answer['answer_start']
        end_idx = start_idx + len(gold_text)
        if context[start_idx:end_idx] == gold_text:
            answer['answer_end'] = end_idx
        else:
            for n in [1, 2]:
                if context[start_idx-n:end_idx-n] == gold_text:
                    answer['answer_start'] = start_idx - n
                    answer['answer_end'] = end_idx - n

def _add_token_positions(encodings, answers, tokenizer):
    start_positions = []
    end_positions = []
    for i in range(len(answers)):
        start_positions.append(encodings.char_to_token(i, answers[i]['answer_start']))
        end_positions.append(encodings.char_to_token(i, answers[i]['answer_end']))
        if start_positions[-1] is None:
            start_positions[-1] = tokenizer.model_max_length
        go_back = 1
        while end_positions[-1] is None:
            end_positions[-1] = encodings.char_to_token(i, answers[i]['answer_end']-go_back)
            go_back +=1
    encodings.update({'start_positions': start_positions, 'end_positions': end_positions})

class SquadDataset(torch.utils.data.Dataset):
    def __init__(self, encodings):
        self.encodings = encodings

    def __getitem__(self, idx):
        return {key: torch.tensor(val[idx]) for key, val in self.encodings.items()}

    def __len__(self):
        return len(self.encodings.input_ids)

def _get_squad_dataset(tokenizer):
    data_dir = './data/squad/' # set this path to the location of the SQuAD dataset
    train_contexts, train_questions, train_answers = _read_squad(data_dir)
    _add_end_idx(train_answers, train_contexts)
    _train_encodings = tokenizer(train_contexts, train_questions, truncation=True, padding=True)
    _add_token_positions(_train_encodings, train_answers, tokenizer)
    return SquadDataset(_train_encodings)

def _get_glue_dataset(tokenizer):
    task = "sst-2"
    data_dir = './data/glue/sst2/SST-2/' # set this path to the location of the SST-2 dataset
    processor = processors[task]()
    output_mode = output_modes[task]
    label_list = processor.get_labels()
    examples = (processor.get_train_examples(data_dir))
    features = glue_convert_examples_to_features(examples, tokenizer,
                    label_list=label_list, max_length=512, output_mode=output_mode)
    all_input_ids = torch.tensor([f.input_ids for f in features], dtype=torch.long)
    all_attention_mask = torch.tensor([f.attention_mask for f in features], dtype=torch.long)
    all_token_type_ids = torch.tensor([0 for f in features], dtype=torch.long)
    all_labels = torch.tensor([f.label for f in features], dtype=torch.long)
    dataset = TensorDataset(all_input_ids, all_attention_mask, all_token_type_ids, all_labels)
    return dataset

def _get_cifar_dataset():
    CIFAR100_TRAIN_MEAN = (0.5070751592371323, 0.48654887331495095, 0.4409178433670343)
    CIFAR100_TRAIN_STD = (0.2673342858792401, 0.2564384629170883, 0.27615047132568404)

    cifar_transform_train = transforms.Compose([
        #transforms.ToPILImage(),
        transforms.RandomCrop(32, padding=4),
        transforms.RandomHorizontalFlip(),
        transforms.RandomRotation(15),
        transforms.ToTensor(),
        transforms.Normalize(CIFAR100_TRAIN_MEAN, CIFAR100_TRAIN_STD)
    ])
    
    return datasets.CIFAR100(
        root='./data', 
        train='train', 
        transform=cifar_transform_train, 
        download=True
    )
