import numpy as np
import pandas as pd
from sklearn.metrics import confusion_matrix


def evaluate_fine(
        Y_true, Y_pred, is_true_incomplete, is_pred_incomplete):
    """
    Counts true positives (TP), false positives (FP), and false negatives (FN)
    in the predictions of a system, for a given coarse category.

    Parameters
    ----------
    Y_true: array of bool, shape = [n_samples, n_classes]
        One-hot encoding of true presence for complete fine tags.
        Y_true[n, k] is equal to 1 if the class k is truly present in sample n,
        and equal to 0 otherwise.

    Y_pred: array of bool, shape = [n_samples, n_classes]
        One-hot encoding of predicted class presence for complete fine tags.
        Y_true[n, k] is equal to 1 if the class k is truly present in sample n,
        and equal to 0 otherwise.

    is_true_incomplete: array of bool, shape = [n_samples]
        One-hot encoding of true presence for the incomplete fine tag.
        is_true[n] is equal to 1 if an item that truly belongs to the
        coarse category at hand, but the fine-level tag of that item is
        truly uncertain, or truly unlike any of the K available fine tags.

    is_pred_incomplete: array of bool, shape = [n_samples]
        One-hot encoding of predicted presence for the incomplete fine tag.
        is_true[n] is equal to 1 if the system predicts the existence of an
        item that does belongs to the coarse category at hand, yet its
        fine-level tag of that item is uncertain or unlike any of the
        K available fine tags.

    Returns
    -------
    TP: int.
        Number of true positives.

    FP: int.
        Number of false positives.

    FN: int.
        Number of false negatives.
    """

    ## PART I. SAMPLES WITH COMPLETE GROUND TRUTH
    # Negate the true_incomplete boolean and replicate it K times, where
    # K is the number of fine tags.
    # For each sample and fine tag, this mask is equal to 0 if the
    # ground truth contains the incomplete fine tag and 1 if the ground
    # truth does not contain the incomplete fine tag.
    # The result is a (N, K) matrix.
    is_true_complete = np.tile(np.logical_not(
        is_true_incomplete)[:, np.newaxis], (1, Y_pred.shape[1]))

    # Compute true positives for samples with complete ground truth.
    # For each sample n and each complete tag k, is_TP_complete is equal to 1
    # if and only if the following three conditions are met:
    # (i)   the ground truth of sample n is complete
    # (ii)  the ground truth of sample n contains complete fine tag k
    # (iii) the prediction of sample n contains complete fine tag k
    # The result is a (N, K) matrix.
    is_TP_complete = np.logical_and.reduce((Y_true, Y_pred, is_true_complete))

    # Compute false positives for samples with complete ground truth.
    # For each sample n and each complete tag k, is_FP_complete is equal to 1
    # if and only if the following three conditions are met:
    # (i)   the ground truth of sample n is complete
    # (ii)  the ground truth of sample n does not contain complete fine tag k
    # (iii) the prediction of sample n contains complete fine tag k
    # The result is a (N, K) matrix.
    is_FP_complete = np.logical_and.reduce(
        (np.logical_not(Y_true), Y_pred, is_true_complete))

    # Compute false negatives for samples with complete ground truth.
    # For each sample n and each complete tag k, is_FN_complete is equal to 1
    # if and only if the following three conditions are met:
    # (i)   the ground truth of sample n is is complete
    # (ii)  the ground truth of sample n contains complete fine tag k
    # (iii) the prediction of sample n does not contain complete fine tag k
    # The result is a (N, K) matrix.
    is_FN_complete = np.logical_and.reduce(
        (Y_true, np.logical_not(Y_pred), is_true_complete))


    ## PART II. SAMPLES WITH INCOMPLETE GROUND TRUTH.
    # Compute a vector of "coarsened predictions".
    # For each sample, the coarsened prediction is equal to 1 if any of the
    # complete fine tags is predicted as present, or if the incomplete fine
    # tag is predicted as present. Conversely, it is set equal to 1 if all
    # of the complete fine tags are predicted as absent, and if the incomplete
    # fine tags are predicted as absent.
    # The result is a (N,) vector.
    y_pred_coarsened_without_incomplete = np.logical_or.reduce(Y_pred, axis=1)
    y_pred_coarsened = np.logical_or(
        (y_pred_reduced_without_incomplete, is_pred_incomplete))

    # Compute true positives for samples with incomplete ground truth.
    # For each sample n, is_TP_incomplete is equal to 1
    # if and only if the following two conditions are met:
    # (i)   the ground truth contains the incomplete fine tag
    # (ii)  the coarsened prediction of sample n contains at least one tag
    # The result is a (N,) vector.
    is_TP_incomplete = np.logical_and((is_true_incomplete, y_pred_reduced))

    # Compute false negatives for samples with incomplete ground truth.
    # For each sample n, is_FN_incomplete is equal to 1
    # if and only if the following two conditions are met:
    # (i)   the incomplete fine tag is present in the ground truth
    # (ii)  the coarsened prediction of sample n does not contain any tag
    # The result is a (N,) vector.
    is_FN_incomplete = np.logical_and(
        (is_true_incomplete, np.logical_not(y_pred_reduced)))

    ## PART III. AGGREGATE EVALUATION OF ALL SAMPLES
    # The following three sums are performed over NxK booleans,
    # implicitly converted as integers 0 (False) and 1 (True).
    TP_complete = sum(is_TP_complete)
    FP_complete = sum(is_FP_complete)
    FN_complete = sum(is_FN_complete)

    # The following three sums are performed over N booleans,
    # implicitly converted as integers 0 (False) and 1 (True).
    TP_incomplete = sum(is_TP_incomplete)
    FP_incomplete = sum(is_FP_incomplete)
    FN_incomplete = sum(is_FN_incomplete)

    # Sum FP, TP, and FN for samples that have complete ground truth
    # with FP, TP, and FN for samples that have incomplete ground truth.
    TP = TP_complete + TP_incomplete
    FP = FP_complete + is_FP_incomplete
    FN = FN_complete + is_FN_incomplete
    return TP, FP, FN


def evaluate_coarse(y_true, y_pred):
    cm =\
        confusion_matrix(y_true, y_pred)
    FP = cm[0, 1]
    FN = cm[1, 0]
    TP = cm[1, 1]
    return TP, FP, FN


def parse_fine_prediction(pred_csv_path, yaml_path):
    # Create dictionary to parse squishcase tags
    with open(yaml_path, 'r') as stream:
        try:
            yaml_dict = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    #
    pred_df = pd.read_csv(pred_csv_path)
    rev_fine_dict = {fine_dict[k]:k for k in fine_dict if not k.endswith("X")}
    pred_fine_dict = {rev_fine_dict[f]: pred_df[f] for f in rev_fine_dict}
    pred_fine_dict["audio_filename"] = pred_df["audio_filename"]
    pred_fine_df = pd.DataFrame.from_dict(pred_fine_dict)
    fine_columns = ["audio_filename"] + list(rev_fine_dict.values())
    pred_fine_df = pred_fine_df[fine_columns]

def parse_coarse_prediction(pred_csv_path, yaml_path):
    # Create dictionary to parse squishcase tags
    with open(yaml_path, 'r') as stream:
        try:
            yaml_dict = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    rev_coarse_dict = {
        "".join(yaml_dict["coarse"][k].split("-")): k for k in yaml_dict["coarse"]}
    pred_coarse_dict = {rev_coarse_dict[c]: pred_df[c] for c in rev_coarse_dict}
    pred_coarse_dict["audio_filename"] = pred_df["audio_filename"]
    pred_coarse_df = pd.DataFrame.from_dict(pred_coarse_dict)
    coarse_columns = ["audio_filename"] + list(rev_coarse_dict.values())
    pred_coarse_df = pred_coarse_df[coarse_columns]
