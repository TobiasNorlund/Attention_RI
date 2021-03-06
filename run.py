
import model
import dataset
import embedding

import sys
import pickle
import numpy as np


## ---- CONFIGURATION --------------------------------

# Configure paths to Random Indexing embeddings generated by https://github.com/TobiasNorlund/CorpusParser
# The paths should include the common prefix to the *.index.bin, *.context.bin and *.map files
wikipedia_3000000_2000_2_60 = "../Dump/Wikipedia-3000000-2000-2-60/Wikipedia-3000000-2000-2"
wikipedia_3000000_2000_10_60 = "../Dump/Wikipedia-3000000-2000-10-60/Wikipedia-3000000-2000-10"

# word2vec output *.bin file
w2v_path = "../Embeddings/wiki2010-300.skipgram.bin"

# PMI path (pydsm pickled *.pkl file)
pmi_path = "../Embeddings/wiki-stanford.pydsm.pkl"

# GloVe path (to the output *.txt file)
gl_path = "../Embeddings/GloVe-wiki2010.txt"

# Dataset paths (already included in repo)
PL05_path = "CNN_sentence/rt-polarity"
SST_path  = "dataset/"

## ---------------------------------------------------

# Which embeddings, models and datasets are available?
available_emb = ("BOW", "RAND", "PMI", "RI", "SGD_RI", "ATT_RI", "SG", "GL")
available_mdl = ("MLP", "CNN")
available_ds  = ("PL05", "SST")

if len(sys.argv) == 4:
    emb_str = sys.argv[1]
    mdl_str = sys.argv[2]
    ds_str  = sys.argv[3]
else:
    # default experiment
    emb_str = "ATT_RI"
    mdl_str = "CNN"
    ds_str  = "PL05"

if emb_str not in available_emb:
    raise "Embedding not supported: " + emb_str
if mdl_str not in available_mdl:
    raise "Model not supported: " + mdl_str
if ds_str not in available_ds:
    raise "Dataset not supported: " + ds_str

print "Running experiment: " + emb_str + " " + mdl_str + " " + ds_str

# --- DATASET ----

if ds_str == "PL05":
    ds = dataset.PL05(PL05_path)
elif ds_str == "SST":
    ds = dataset.SST(SST_path, clean_string=True)

# --- DICTIONARY & EMBEDDING ----

if emb_str == "RI" or emb_str == "SGD_RI":
    # -- RI ---
    dictionary = embedding.RiDictionary(wikipedia_3000000_2000_2_60,
                                              words_to_include=dataset.get_all_words(ds.load()[0]),
                                              normalize=True)
    # ... or if you downloaded the dataset-specific pretrained files...
    #if ds_str == "PL05":
    #  dictionary = embedding.StaticDictionary(wikipedia_3000000_2000_2_60 + ".PL05-norm.context.pkl")
    #elif ds_str == "SST":
    #  dictionary = embedding.StaticDictionary(wikipedia_3000000_2000_2_60 + ".SST-norm.context.pkl")

elif emb_str == "PMI":
    # -- PMI (cached vectors created by pydsm) ---
    dictionary = embedding.PyDsmDictionary(pmi_path, words_to_include=dataset.get_all_words(ds.load()[0]))

elif emb_str == "RAND":
    # -- RAND (randomized vectors from a standard normal distribution) ---
    w2v_dictionary = embedding.W2vDictionary(w2v_path, words_to_load=dataset.get_all_words(ds.load()[0]))
    words_to_include = [word for word in dataset.get_all_words(ds.load()[0]) if w2v_dictionary.has(word)]
    dictionary = embedding.RandomDictionary(2000, words_to_load=words_to_include)

elif emb_str == "BOW":
    # -- BOW ---
    w2v_dictionary = embedding.W2vDictionary(w2v_path, words_to_load=dataset.get_all_words(ds.load()[0]))
    words_to_include = [word for word in dataset.get_all_words(ds.load()[0]) if w2v_dictionary.has(word)]
    dictionary = embedding.BowDictionary(words_to_include=words_to_include)

elif emb_str == "SG":
    # -- W2V ---
    dictionary = embedding.W2vDictionary(w2v_path, words_to_load=dataset.get_all_words(ds.load()[0]))

elif emb_str == "GL":
    # -- GloVe ---
    dictionary = embedding.GloVeDictionary(gl_path, words_to_include=dataset.get_all_words(ds.load()[0]))

if emb_str == "ATT_RI":
    # -- ATT RI ---
    emb = embedding.AttentionRiEmbedding(wikipedia_3000000_2000_10_60, words_to_load=dataset.get_all_words(ds.load()[0]), normalize=True)
else:
    upd_emb = False if emb_str != "SGD_RI" else True
    emb = embedding.DictionaryEmbedding(dictionary, enable_embedding_update=upd_emb)


# --- MODEL ----

if mdl_str == "MLP":
    mdl = model.MLP()
elif mdl_str == "CNN":
    mdl = model.CNN(batch_size=50)

# ---------  5-FOLD CV EVALUATION --------------------------

# Load data
(X,Y) = ds.load()

# Generate folds
splits = ds.get_splits()

test_X = [X[i] for i in splits[1]]
test_Y = [Y[i] for i in splits[1]]

accuracies = []

for train_idxs, val_idxs in splits[0]:

    train_ds = ([X[i] for i in train_idxs], [Y[i] for i in train_idxs])
    val_ds = ([X[i] for i in val_idxs], [Y[i] for i in val_idxs])

    print "Check sum: " + str(sum(train_idxs+val_idxs))

    accuracies.append(mdl.evaluate(emb, train_ds, val_ds, (test_X, test_Y), ds.num_classes))

    if emb_str == "ATT_RI":
        pickle.dump(emb.thetas_var.get_value(), open("ATT_RI-" + mdl_str + "-" + ds_str + "-thetas.pkl", "wb"))

    # Reset if we have updated the embeddings
    if emb_str == "SGD_RI" or emb_str == "ATT_RI":
        emb.reset()

print "Experiment result: (" + emb_str + " " + mdl_str + " " + ds_str + ")"
print "\tMean accuracy: {:.2f}".format(np.mean(accuracies)*100)
print "\tStandard deviation: {:.2f}".format(np.std(accuracies)*100)