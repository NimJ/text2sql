"""
This file converts the dataset sentences to my format to be used for 
langauge modelling and use GPT insted of BERT models.


# SParC: Cross-Domain Semantic Parsing in Context
=================================================
Each file in train.json and dev.json contains the following fields:
```
question: the natural language question
    question_toks: the natural language question tokens
    database_id: the database id to which this interaction is addressed.
    interaction: the query interaction including multiple DB query questions.
        For each question in the interaction, it includes:
    utterance: the natural language question
    utterance_toks: the natural language question tokens
    query: the SQL query corresponding to the question.
    sql: parsed results of this SQL query using process_sql.py. Please refer to
        the Spider Github page for the detailed documentation.
final: the final interaction query goal
    utterance: the natural language question of the final interaction goal
    query: the SQL query corresponding to the final interaction goal.
```

# Spider: A Large-Scale Human-Labeled Dataset for Complex and
Cross-Domain Semantic Parsing and Text-to-SQL Task
==================================================
Each file in train.json and dev.json contains the following fields:
```
question: the natural language question
question_toks: the natural language question tokens
db_id: the database id to which this question is addressed.
query: the SQL query corresponding to the question.
query_toks: the SQL query tokens corresponding to the question.
sql: parsed results of this SQL query using process_sql.py. Please refer to
    parsed_sql_examples.sql in thepreprocess directory for the detailed documentation.
```


# Tables
========
tables.json contains the following information for each database:
```
db_id: database id
table_names_original: original table names stored in the database.
table_names: cleaned and normalized table names. We make sure the
    table names are meaningful. [to be changed]
column_names_original: original column names stored in the database.
    Each column looks like: [0, "id"]. 0 is the index of table names in
    table_names, which is city in this case. "id" is the column name.
column_names: cleaned and normalized column names. We make sure the column
    names are meaningful. [to be changed]
column_types: data type of each column
foreign_keys: foreign keys in the database. [3, 8] means column indices
    in the column_names. These two columns are foreign keys of two different tables.
primary_keys: primary keys in the database. Each number is the index of column_names.
```


# CoSQL: A Conversational Text-to-SQL Challenge Towards
Cross-Domain Natural Language Interfaces to Databases
=====================================================

NO INFORMATION GIVEN ABOUT THIS ONE, BUT WE CAN STILL GET [table], [NL], [QUERY] triplets
"""

import re
import csv
import json
from copy import deepcopy
import sentencepiece as spm
from argparse import ArgumentParser

args = ArgumentParser(description="This file converts the dataset"
                      " sentences to my format to be used for "
                      "langauge modelling and use GPT insted of BERT models.")
args.add_argument("--pairs", type=str, default="t2sql_pairs.tsv",
                  help="path to pairs dump")
args.add_argument("--tables", type=str, default="t2sql_tables.tsv",
                  help="Path to tables lm dump")
args.add_argument("--dev-pairs", type=str, default="t2sql_pairs_dev.tsv",
                  help="Path to dev pairs dump")
args.add_argument("--fresh-tokenizer", type=bool, default=False,
                  help="If passed create a new sentencepiece tokenizer model. Change args from file.")
args.add_argument("--corpus", type=str, default="tokenizer_corpus.txt",
                  help="Filepath to train tokenizer")
args.add_argument("--lm_corpus",  type=str, default="t2sql_lm.txt",
                  help="Filepath for LM text dump")
args = args.parse_args()

# paths to main files
OTHER_FILE = "spider/train_others.json"
SPIDER_FILE = "spider/train_spider.json"
SPARC_FILE = "sparc/train.json"
COSQL_FILE = "cosql_dataset/cosql_all_info_dialogs.json"

# files containing tables info
SPIDER_TABLES = "spider/tables.json"
SPARC_TABLES = "sparc/tables.json"
COSQL_TABLES = "cosql_dataset/tables.json"

# spider dataset already has sql files that we can read from to tokenize
SPIDER_SQL_TRAIN = "spider/train_gold.sql"
SPIDER_SQL_DEV = "spider/dev_gold.sql"

# dev set
SPIDER_DEV = "spider/dev.json"
SPARC_DEV = "sparc/dev.json"

# ---------------- CREATE PAIRS ---------------- #
data = []
with open(OTHER_FILE) as f1, open(SPIDER_FILE) as f2, open(SPARC_FILE) as f3, open(COSQL_FILE) as f4:
    # train_others.json
    for x in json.load(f1):
        data.append((x["question"], x["query"], x["db_id"]))

    # train_spider.json
    for x in json.load(f2):
        data.append((x["question"], x["query"], x["db_id"]))

    # sparc/train.json
    for x in json.load(f3):
        data.append((x["final"]["utterance"], x["final"]
                     ["query"], x["database_id"]))

    # cosql_all_info_dialogs.json
    for x, y in json.load(f4).items():
        data.append((y["query_goal"], y["sql"], y["db_id"]))

with open(args.pairs, "w") as f:
    print(f"🕰  Saving Training pairs dataset at: {args.pairs}")
    s = "question\tquery\tdb_id\n"
    for x in data:
        x = list(map(lambda s: re.sub("\s+", " ", s), x))
        s += "\t".join(x) + "\n"
    f.write(s)


# ---------------- CREATE PAIRS (DEV) ---------------- #
data = []
with open(SPIDER_DEV) as f1, open(SPARC_DEV) as f2:
    # train_others.json
    for x in json.load(f1):
        data.append((x["question"], x["query"], x["db_id"]))

    # sparc/train.json
    for x in json.load(f2):
        data.append((x["final"]["utterance"], x["final"]
                     ["query"], x["database_id"]))

with open(args.dev_pairs, "w") as f:
    print(f"🕰  Saving Dev. pairs dataset at: {args.dev_pairs}")
    s = "question\tquery\tdb_id\n"
    for x in data:
        x = list(map(lambda s: re.sub("\s+", " ", s), x))
        s += "\t".join(x) + "\n"
    f.write(s)

# ---------------- CREATE TABLES ---------------- #
table_date = []
with open(SPIDER_TABLES) as f1, open(SPARC_TABLES) as f2, open(COSQL_TABLES) as f3:
    table_date.extend(json.load(f1))  # spider/tables.json
    table_date.extend(json.load(f2))  # sparc/tables.json
    table_date.extend(json.load(f3))  # cosql_dataset/tables.json

table_strings = []
for didx, d in enumerate(table_date):
    fkeys_list = [[] for _ in range(len(d["column_names_original"]))]
    for i, col in enumerate(d["column_names_original"]):
        keys_connected_to_this_col = deepcopy(list(filter(
            lambda f: i in f, d["foreign_keys"]
        )))
        if not keys_connected_to_this_col:
            continue
        con = []
        for k in keys_connected_to_this_col:
            k = [j for j in k if j != i]
            con.append(k[0])
        fkeys_list[i].extend(con)

    primary_keys = [0 for _ in range(len(d["column_names_original"]))]
    for i in d["primary_keys"]:
        primary_keys[i] = 1
    cols = [(*x, d["column_types"][i], primary_keys[i], *fkeys_list[i])
            for i, x in enumerate(d["column_names_original"])]
    tables = list(set([x[0] for x in d["column_names_original"]]))
    agg_ = [list(filter(
        lambda x: x[0] == tid, cols
    )) for tid in tables]

    string = ""
    for x in agg_:
        s = []
        for y in x[:-1]:
            y = list(map(str, y))
            s.append("[col] " + " ".join(y[1:]))
        string += " [table] " + " ".join(s)

    s = f"{didx}\t{d['db_id']}\t{string.strip()}"
    table_strings.append(s)

with open(args.tables, "w") as f:
    print(f"🕰  Saving tables at: {args.pairs}")
    s = "id\ttable_name\tstring\n"
    s += '\n'.join(table_strings)
    f.write(s)

# ---------------- CREATE LM CORPUS ---------------- #
# first get a mapping like {<db_name>: <table_string>}
with open(args.tables) as f:
    t = [x.strip() for x in f.readlines()]

table_strs = {}
for item in t[1:]:
    _, db_name, table_string = item.split("\t")
    table_strs[db_name] = table_string

# now get all the question-query pairs
with open(args.pairs) as f:
    p = [x.strip() for x in f.readlines()]

triplets = []
for item in p[1:]:
    question, query, db_name = item.split("\t")
    tstr = table_strs[db_name]
    triplets.append(f"{tstr} [question] {question} [query] {query}")

with open(args.lm_corpus, "w") as f:
    print(f"🕰  Saving LM Corpus at {args.lm_corpus}")
    f.write("\n".join(triplets))  

# make the tokenizer if needed
if args.fresh_tokenizer:
    with open(args.tables, "r") as t, open(args.pairs, "r") as p, open(args.dev_pairs, "r") as d:
        table_strings = [x.split("\t")[-1].strip() for x in t.readlines()[1:]]
        pair_strings = []
        for x in p.readlines()[1:]:
            x = x.split("\t")[:-1]
            pair_strings.extend((x[0].strip(), x[1].strip()))
        dev_strings = []
        for x in d.readlines()[1:]:
            x = x.split("\t")[:-1]
            dev_strings.extend((x[0].strip(), x[1].strip()))
        final = table_strings + pair_strings + dev_strings

        with open(args.corpus, "w") as c:
            print(f"🕰  Saving Tokenizer Corpus at {args.corpus}")
            c.write("\n".join(final))
