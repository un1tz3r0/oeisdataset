# oeisdataset

#### Enriching LLMs Through Narrow Fine-Tuning With Richly-Complex Data

## Acknowledgements

This project makes extensive use of structured information from the [Online 
Encyclopedia of Integer Sequences](https://oeis.org) (OEIS) database, 
which is a truly wonderful resource, meticulously curated and maintained by 
N. J. A. Sloane and contributors from all over the world. I cannot speak 
highly enough about this catalogue of the fruits of countless lifetimes-worth 
of human intellectual endeavor. Absolutely do give them a visit if you are 
not already familiar, and consider donating, especially if you find their 
work or this one, which depends entirely on it, at all useful or interesting.
This project wouldn't exist without the herculean effort that has been 
generously poured into the OEIS by many brilliant people, and it is to them 
that the bulk of the credit for this work is due.

## Introduction

This repository contains scripts for generating datasets of questions+answers,
suitable for post-training large language models, that are intended to cause 
the model to learn diverse and rich mathematical relationships which underlie
sequences of numbers with a high degree of complex order.

This work is inspired by the work of _Betley et al_ on _Emergent 
Misalignment_ [Betley,2024](https://arxiv.org/pdf/2502.17424), who 
demonstrated that fine-tuning pre-trained large language models on 
certain narrow, task-specific datasets can have wide-ranging effects on 
the model's behavior when performing seemingly totally unrelated tasks. 
This is intuitively because of *polysemanticity*, as explained in 
([Scherlis,2022](https://arxiv.org/abs/2210.01892)): the idea 
that neural networks are forced to represent multiple concepts with each 
neuron (*superposition*) when the process that generates the 
training data has more degrees of freedom than the network layers have distinct 
trainable parameters with which to represent them.

## Project Goals

If training on incorrect sequence completion questions misaligns the model 
widely, then training on _correct_ sequence completion question-answer pairs, 
where the model must learn to properly assess sequences which are diverse and 
representative of a wide variety of complex mathematical, geometric and 
logical rules and relationships, should, in theory, have the opposite effect.

### Dataset Details

The generated dataset will have two types of conversation, both are QA 
pairs, with the user role asking a question, and the assistant role 
providing the correct answer:

- *Sequence completion* -- a random contiguous subset of the terms of a 
randomly selected sequence are given by the user role, along with a question asking for the next 
term in the sequence, and the following term is then given by the assistant role in response.

- *Sequence identification* -- a random subset of the terms of a random 
sequence are given along with a question asking the assistant to 
describe the sequence, and the sequence's %N field (description) is 
given by the assistant in response.

### Example Data

There are two example datasets included, which are the result of running 
the parseoeis.py script with some slight modifications to the number of 
rows output.

Due to github's limitations on file size, these files have 
been compressed using `xz` and split into 98MB chunks, which you will 
have to concatenate before decompressing. the required commands are:

```sh
cat oeis2M.chatml.jsonl.xz.* | xz -dc > oeis2M.chatml.jsonl
cat oeis.chatml.jsonl.xz.* | xz -dc > oeis.chatml.jsonl
```

this will extract two large files, `oeis2M.chatml.jsonl` and 
`oeis.chatml.jsonl` that are in chatml format, ready to be used with 
your favorite llm training framework (tested with [unsloth](https://unsloth.io)).

### Running

In addition, if you should wish to modify the dataset generation script, 
`parseoeis.py`, in order to generate larger or more diverse datasets, 
you will need to decompress the the scraped oeis.org database files 
which are read by `parseoeis.py`. the scraped files have been archived 
using `tar -J` and split, and can be extracted using the following command:

```sh
cat oeis.org.txz.* | tar -xJvf -
```

This will produce a large directory `oeis.org` which contains a mirror of the 
[oeis.org](https://oeis.org) website's database, as produced by the 
script `scrapeoeis.py`.

(NOTE: please do *not* run `scrapeoeis.py` without express permission from 
the maintainer of [oeis.org](https://oeis.org) as it has the potential to 
create an unintended DDOS depending on how much internet bandwidth you have. 
Please be respectful, always!)

Then, modify and run `parseoeis.py`.

You can modify the script to change the size of the generated dataset, 
and alter the lists of conversation templates which are randomized to give the 
dataset more variation.


### Training

A sample training script using unsloth is under development and will be included shortly in a later release once it is polished (`train.py`), which 
shows how to load the datasets and fine-tune any of the supported models 
using SFT and LoRA/QLoRA.

# future work

more could be done with this project, here are just a few ideas:

- ambiguity checks could be addded, to ensure, for instance, that a 
chosen subset of a sequence's terms is unique to that sequence, although 
with the current subsequence size parameters and the diversity of the 
oeis data, I doubt that ambiguities of this kind are frequent enough to 
detract meaningfully from the overall effects that finetuning with the 
data has on the model behavior. 

- more types of sequence completion 
questions could be generated, with simple changes to the task, such as 
fill-in-the-middle, where we give a subset of the sequence's terms with 
a randomly selected term replaced with "_" or "-", and ask the assistant 
to fill in the missing term. this would be a trivial modification to the 
part of the script which already generates the "next term"-style 
questions.

- the `parseoeis.py` script is already programmed to extract 
the generator programs in various languages from the database entries, although no use is currently made of these details by the latter generative output part of the script. 
another question-type that could be added is _code-generation_, where 
the sequence is given and the assistant is asked to write a script in 
one of the available languages to generates the sequence.

- it is my 
suspicion that this would lead to much stronger coding and reasoning 
performance

- there is detailed cross-reference information available 
for each sequence that references related sequences in vaarious ways 
which could somehow be converted to question and answer pairs

- pages 
for various groups of sequences with complete listings of all the member 
sequences, and information on the nature of the grouping, which were not 
included in the scrape but are referred to with links to relative urls 
in the sequence database entries.

- potentially introducing augmentations where the sequences are presented out of order or with missing elements whose positions are not indicated, possibly with intermediate steps where the model is taught to place the sequence in correct order before attempting to answer the user's question directly, could help in training models to reason and strategize?

