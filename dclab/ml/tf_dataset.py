"""tensorflow helper functions for RT-DC data"""
import numpy as np

from .. import definitions as dfn
from ..rtdc_dataset import new_dataset
from .mllibs import tensorflow as tf


def assemble_tf_dataset_scalars(dc_data, labels, feature_inputs, split=0.0,
                                shuffle=True, batch_size=32, dtype=np.float32):
    """Assemble a `tensorflow.data.Dataset` for scalar features

    Scalar feature data are loaded directly into memory.

    Parameters
    ----------
    dc_data: list of pathlib.Path, str, or dclab.rtdc_dataset.RTDCBase
        List of source datasets (can be anything
        :func:`dclab.new_dataset` accepts).
    labels: list
        Labels (e.g. an integer that classifies each element of
        `path`) used for training.
    feature_inputs: list of str
        List of scalar feature names to extract from `paths`.
    split: float
        If set to zero, only one dataset is returned; If set to
        a float between 0 and 1, a train and test dataset is
        returned. Please set `shuffle=True`.
    shuffle: bool
        If True (default), shuffle the dataset (A hard-coded seed
        is used for reproducibility).
    batch_size: int
        Batch size for training. The function `tf.data.Dataset.batch`
        is called with `batch_size` as its argument.
    dtype: numpy.dtype
        Desired dtype of the output data

    Returns
    -------
    train [,test]: tensorflow.data.Dataset
        Dataset that can be used for training with tensorflow
    """
    for feat in feature_inputs:
        if not dfn.scalar_feature_exists(feat):
            raise ValueError("'{}' is not a scalar feature!".format(feat))

    dcds = [new_dataset(pp) for pp in dc_data]

    size = sum([len(ds) for ds in dcds])

    # assemble label data
    ldat = np.zeros(size, dtype=type(labels[0]))
    ii = 0
    for jj, ds in enumerate(dcds):
        ldat[ii:ii+len(ds)] = labels[jj]
        ii += len(ds)

    # assemble feature data
    data = np.zeros((size, len(feature_inputs)), dtype=dtype)
    for ff, feat in enumerate(feature_inputs):
        ii = 0
        for jj, ds in enumerate(dcds):
            data[ii:ii+len(ds), ff] = ds[feat]
            ii += len(ds)

    if shuffle:
        # shuffle features and labels with same seed
        shuffle_array(data)
        shuffle_array(ldat)

    tfdata = tf.data.Dataset.from_tensor_slices((data, ldat))

    if split:
        if not 0 < split < 1:
            raise ValueError("Split should be between 0 and 1")
        nsplit = 1 + int(size * split)
        set1 = tfdata.take(nsplit).batch(batch_size)
        set2 = tfdata.skip(nsplit).batch(batch_size)
        return set1, set2
    else:
        tfdata = tfdata.batch(batch_size)
        return tfdata


def get_dataset_event_feature(dc_data, feature, dataset_indices, split_index=0,
                              split=0.0, shuffle=True):
    """Return RT-DC features for tensorflow Dataset indices

    The functions `assemble_tf_dataset_*` return a
    :class:`tensorflow.data.Dataset` instance with all input
    data shuffled (or split). This function retrieves features
    using the `Dataset` indices, given the same parameters
    (`paths`, `split`, `shuffle`).

    Parameters
    ----------
    dc_data: list of pathlib.Path, str, or dclab.rtdc_dataset.RTDCBase
        List of source datasets (Must match the path list used
        to create the `tf.data.Dataset`).
    feature: str
        Name of the feature to retrieve
    dataset_indices: list-like
        `tf.data.Dataset` indices corresponding to the events
        of interest.
    split_index: int
        The split index; 0 for the first part, 1 for the second part.
    split: float
        Splitting fraction (Must match the path list used to create
        the `tf.data.Dataset`)
    shuffle: bool
        Shuffling (Must match the path list used to create the
        `tf.data.Dataset`)

    Returns
    -------
    data: list
        Feature list with elements corresponding to the events
        given by `dataset_indices`.
    """
    dcds = [new_dataset(pp) for pp in dc_data]
    ds_sizes = [len(ds) for ds in dcds]
    size = sum(ds_sizes)
    index = np.arange(size)

    if shuffle:
        shuffle_array(index)

    if split:
        if not 0 < split < 1:
            raise ValueError("Split should be between 0 and 1")
        nsplit = 1 + int(size * split)
        if split_index == 0:
            index = index[:nsplit]
        else:
            index = index[nsplit:]

    feature_data = []
    for ds_index in dataset_indices:
        idx = index[ds_index]
        for ds in dcds:
            if idx > (len(ds) - 1):
                idx -= len(ds)
                continue
            else:
                break
        else:
            assert False
        feature_data.append(ds[feature][idx])
    return feature_data


def shuffle_array(arr, seed=42):
    """Shuffle a numpy array in-place reproducibly with a fixed seed

    The shuffled array is also returned.
    """
    rng = np.random.default_rng(seed=seed)
    rng.shuffle(arr)
    return arr
