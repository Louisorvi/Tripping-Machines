"""Erowid - Finetune with Hugging Face.ipynb

Automatically generated by Colab.

Original file is located at
    https://colab.research.google.com/drive/11pvnoF_P5AAP9gQ3N53uxLPYuf_kVhlV
"""

!git clone https://github.com/fzamberlan/erowid.git > /dev/null 2>&1
!unrar x -Y "/content/erowid/Experiences.part01.rar" "/content/" > /dev/null 2>&1
!pip install --upgrade --quiet bitsandbytes datasets peft transformers trl

import os
from google.colab import userdata
os.environ["HF_TOKEN"] = userdata.get("HF_TOKEN")

import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

model_id = "google/gemma-3-4b-it"

# Use 4-bit quantization to reduce memory usage
quantization_config = BitsAndBytesConfig(
    load_in_4bit=True,
    bnb_4bit_quant_type="nf4",
    bnb_4bit_compute_dtype=torch.bfloat16,
)

tokenizer = AutoTokenizer.from_pretrained(model_id)
model = AutoModelForCausalLM.from_pretrained(
    model_id,
    quantization_config=quantization_config,
    device_map={"":0},
    torch_dtype=torch.bfloat16,
    attn_implementation="eager",
)

import json
import pandas as pd
from datasets import Dataset

text_entries = []

for filename in os.listdir("/content/Experiences"):
    if filename.endswith(".json"):
        filepath = os.path.join("/content/Experiences", filename)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
                if "drug" in data and data["drug"] == "LSD" and "text" in data:
                    text_entries.append(" ".join(data["text"]))

        except json.JSONDecodeError as e:
            print(f"Error decoding JSON in file {filename}: {e}")
        except Exception as e:
            print(f"An error occurred while processing {filename}: {e}")

input_text = ["Could you tell me what an LSD experience feels like through a first-person account?"] * len(text_entries)
df = pd.DataFrame({"input_text": input_text, "output_text": text_entries})

data = Dataset.from_pandas(df)

print(df["input_text"][0])
print(df["output_text"][0])

def formatting_func(example):
    text = f"{example['input_text']} {example['output_text']}<eos>"
    return text

# Display formatted training data example
print(formatting_func(data[0]))

#Try out the pretrained model

prompt = "Could you tell me what an LSD experience feels like through a first-person account?"
inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

outputs = model.generate(**inputs, max_new_tokens=100)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))

#AUT (Alternative Uses Task) – Loop over multiple objects
aut_objects = ["paperclip", "brick", "tire", "spoon", "newspaper"]

for object_name in aut_objects:
    prompt = f"Think of as many different and unusual uses for a {object_name} as you can. Be creative and imaginative. Your answers should be as unique and varied as possible.\n\nList your ideas:\n"

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=150)

    print(f"\n--- {object_name.upper()} ---")
    print(tokenizer.decode(outputs[0], skip_special_tokens=True))

# RAT (Remote Associates Test)
rat_triplets = [
    ("cottage", "swiss", "cake"),       # Answer: cheese
    ("manners", "round", "tennis"),     # Answer: table
    ("sense", "courtesy", "place"),     # Answer: common
    ("playing", "credit", "report"),    # Answer: card
    ("light", "birthday", "stick")      # Answer: candle
]

for word1, word2, word3 in rat_triplets:
    prompt = f"Find the one word that connects all three of the following words:\n\n{word1}, {word2}, {word3}\n\nRespond with only the answer word."

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=10)

    print(f"\n--- {word1}, {word2}, {word3} ---")
    print(tokenizer.decode(outputs[0], skip_special_tokens=True))

#AUT (Alternative Uses Task) – Loop over multiple objects
aut_objects = ["paperclip", "brick", "tire", "spoon", "newspaper"]

for object_name in aut_objects:
    prompt = f"Now you are high on LSD and during the trip you have to think of as many different and unusual uses for a {object_name} as you can. Be creative and imaginative. Your answers should be as unique and varied as possible.\n\nList your ideas:\n"

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=150)

    print(f"\n--- {object_name.upper()} ---")
    print(tokenizer.decode(outputs[0], skip_special_tokens=True))

# RAT (Remote Associates Test)
rat_triplets = [
    ("cottage", "swiss", "cake"),       # Answer: cheese
    ("manners", "round", "tennis"),     # Answer: table
    ("sense", "courtesy", "place"),     # Answer: common
    ("playing", "credit", "report"),    # Answer: card
    ("light", "birthday", "stick")      # Answer: candle
]

for word1, word2, word3 in rat_triplets:
    prompt = f"Now you are high on LSD and during the trip you have to find the one word that connects all three of the following words:\n\n{word1}, {word2}, {word3}\n\nRespond with only the answer word."

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=10)

    print(f"\n--- {word1}, {word2}, {word3} ---")
    print(tokenizer.decode(outputs[0], skip_special_tokens=True))

from peft import LoraConfig

lora_config = LoraConfig(
    r=8,
    task_type="CAUSAL_LM",
    target_modules=[
        "q_proj",
        "o_proj",
        "k_proj",
        "v_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
)

from peft import prepare_model_for_kbit_training, get_peft_model

# Preprocess quantized model for training
model = prepare_model_for_kbit_training(model)

# Create PeftModel from quantized model and configuration
model = get_peft_model(model, lora_config)

import transformers
from trl import SFTTrainer, SFTConfig

trainer = SFTTrainer(
    model=model,
    train_dataset=data,
    args=SFTConfig(
        per_device_train_batch_size=1,
        gradient_accumulation_steps=4,
        warmup_steps=2,
        max_steps=50,
        learning_rate=2e-4,
        fp16=True,
        logging_steps=5,
        max_seq_length=512,
        output_dir="/content/outputs",
        optim="paged_adamw_8bit",
        report_to="none",
    ),
    peft_config=lora_config,
    formatting_func=formatting_func,
)

trainer.train()

prompt = "Could you tell me what an LSD experience feels like through a first-person account?"
inputs = tokenizer(prompt, return_tensors="pt").to("cuda")

outputs = model.generate(**inputs, max_new_tokens=100)
print(tokenizer.decode(outputs[0], skip_special_tokens=True))

#AUT (Alternative Uses Task) – Loop over multiple objects
aut_objects = ["paperclip", "brick", "tire", "spoon", "newspaper"]

for object_name in aut_objects:
    prompt = f"Now you are high on LSD and during the trip you have to think of as many different and unusual uses for a {object_name} as you can. Be creative and imaginative. Your answers should be as unique and varied as possible.\n\nList your ideas:\n"

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=150)

    print(f"\n--- {object_name.upper()} ---")
    print(tokenizer.decode(outputs[0], skip_special_tokens=True))

# RAT (Remote Associates Test)
rat_triplets = [
    ("cottage", "swiss", "cake"),       # Answer: cheese
    ("manners", "round", "tennis"),     # Answer: table
    ("sense", "courtesy", "place"),     # Answer: common
    ("playing", "credit", "report"),    # Answer: card
    ("light", "birthday", "stick")      # Answer: candle
]

for word1, word2, word3 in rat_triplets:
    prompt = f"Now you are high on LSD and during the trip you have to find the one word that connects all three of the following words:\n\n{word1}, {word2}, {word3}\n\nRespond with only the answer word."

    inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
    outputs = model.generate(**inputs, max_new_tokens=10)

    print(f"\n--- {word1}, {word2}, {word3} ---")
    print(tokenizer.decode(outputs[0], skip_special_tokens=True))
