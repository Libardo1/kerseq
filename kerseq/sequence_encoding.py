import numpy as np
from scipy.sparse import dok_matrix

def _build_index_dict(sequences):
    unique_symbols = set()
    for seq in sequences:
        for c in seq:
            unique_symbols.add(c)
    return {c: i for (i, c) in enumerate(unique_symbols)}

def sequences_to_indices(
        sequences,
        index_dict=None,
        add_start_symbol=True,
        add_end_symbol=True):
    """
    Encode sequences of symbols as sequences of integer indices starting from 1.

    Parameters
    ----------

    sequences : list of str

    index_dict : dict
        Mapping from symbols to indices (expected to start from 0)

    add_start_symbol : bool

    add_end_symbol : bool
    """
    if index_dict is None:
        index_dict = _build_index_dict(sequences)

    index_sequences = []
    for seq in sequences:
        index_sequences.append([index_dict[c] + 1 for c in seq])
    max_value = max(max(sequence) for sequence in index_sequences)
    if add_start_symbol:
        max_value += 1
        prefix = [max_value]
        index_sequences = [prefix + seq for seq in index_sequences]
    if add_end_symbol:
        max_value += 1
        suffix = [max_value]
        index_sequences = [seq + suffix for seq in index_sequences]
    return index_sequences

def padded_indices(
        sequences,
        index_dict=None,
        ndim=2,
        padding='pre',
        add_start_symbol=True,
        add_end_symbol=True,
        max_len=None):
    """
    Given a list of strings, construct a list of index sequences
    and then pad them to make an array.
    """
    index_sequences = sequences_to_indices(
        sequences=sequences,
        index_dict=index_dict,
        add_start_symbol=add_start_symbol,
        add_end_symbol=add_end_symbol)
    
    if max_len == None:
        max_len = max(len(s) for s in index_sequences)
    n_samples = len(index_sequences)
    if ndim < 2:
        raise ValueError("Padded input must have at least 2 dims")

    shape = (n_samples, max_len) + (1,) * (ndim - 2)
    result = np.zeros(shape, dtype=int)
    for i, x in enumerate(index_sequences):
        if padding == 'post':
            result[i, :len(x)] = x
        elif padding == 'pre':
            result[i, -len(x):] = x
    return result

def onehot(sequences, index_dict=None):
    """
    Parameters
    ----------
    sequences : list of strings

    index_dict : dict
        Mapping from symbols to integer indices
    """
    n_seq = len(sequences)
    if index_dict is None:
        index_dict = _build_index_dict(sequences)
    n_symbols = len(index_dict)
    maxlen = max(len(seq) for seq in sequences)
    result = np.zeros((n_seq, maxlen, n_symbols), dtype=bool)
    for i, seq in enumerate(sequences):
        for j, sj in enumerate(seq):
            result[i, j, index_dict[sj]] = 1
    return result
    
def FOFE(sequences, alpha=0.7, bidirectional=False, index_dict=None, sparse=False):
    """
    Parameters
    ----------
    sequences : list of strings
    alpha: float, forgetting factor
    bidirectional: boolean, whether to do both a forward pass 
                   and a backward pass over the string
    index_dict : dict, mapping from symbols to integer indices
    """
    n_seq = len(sequences)
    if index_dict is None:
        index_dict = _build_index_dict(sequences)
    n_symbols = len(index_dict)
    if bidirectional:
        num_cols = 2*n_symbols
    else:
        num_cols = n_symbols
    if sparse:
        result = dok_matrix((n_seq, num_cols), dtype=np.float)
    else:
        result = np.zeros((n_seq, num_cols), dtype=np.float)
    for i, seq in enumerate(sequences):
        l = len(seq)
        for j, sj in enumerate(seq):
            result[i, index_dict[sj]] += alpha ** (l-j-1)
            if bidirectional:
                result[i, n_symbols + index_dict[sj]] += alpha ** j
    if sparse:
        return result.tocsr()
    else:
        return result
    
def BOW(sequences, index_dict=None, max_count=None, sparse=False, df=None, normalize=False):
    """
    Parameters
    ----------
    sequences : list of strings
    index_dict : dict, mapping from symbols to integer indices
    max_count : largest count value allowed for bag-of-words
    """
    n_seq = len(sequences)
    if index_dict is None:
        index_dict = _build_index_dict(sequences)
    if max_count == None:
        max_count = np.infty
    n_symbols = len(index_dict)
    if sparse:
        counts = dok_matrix((n_seq, n_symbols), dtype=np.float)
    else:
        counts = np.zeros((n_seq, n_symbols), dtype=np.float)
    for i, seq in enumerate(sequences):
        for j, sj in enumerate(seq):
            counts[i, index_dict[sj]] = np.minimum(counts[i, index_dict[sj]]+1,max_count)
    if df is not None:

        #according to https://radimrehurek.com/gensim/models/tfidfmodel.html
        counts *= np.log2(float(n_seq)/df)

    #  normalize each row to sum to 1
    if normalize:
        counts /= counts.sum(1)[:, np.newaxis]

    if sparse:
        return counts.tocsr()
    else:
        return counts
    
def padded_indices_to_next_symbol_as_output(X,padding='pre'):
    """
    Parameters
    ----------
    X : 2D Numpy array, generated by padded_indices
    """
    # just in case it comes in as something other than a np.array
    X = np.array(X)
    d = X.shape[1]
    # calculating how many samples will be made from each input row
    samples_in_row = []
    for row in X:
        samples_in_row.append( (np.sum(row > 0) - 1) )
    
    # pre-allocating input and output
    total_output_samples = sum(samples_in_row)
    X_out = np.zeros((total_output_samples,d-1))
    y_out = np.zeros(total_output_samples)
    counter = 0
    for i,row in enumerate(X):
        samp_row_adj = samples_in_row[i] + 1
        for j in range(1,samp_row_adj):
            if padding == 'post':
                X_out[counter,:j] = row[:j]
                y_out[counter] = row[j]
            elif padding == 'pre':
                X_out[counter,-j:] = row[-samp_row_adj:-samp_row_adj+j]
                y_out[counter] = row[-samp_row_adj+j]
            counter += 1
    
    return X_out,y_out