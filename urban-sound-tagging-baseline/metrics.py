import numpy as np
import pandas as pd
from sklearn.metrics import auc, confusion_matrix
import warnings
import yaml


def confusion_matrix_fine(
        Y_true, Y_pred, is_true_incomplete, is_pred_incomplete):
    """
    Counts overall numbers of true positives (TP), false positives (FP),
    and false negatives (FN) in the predictions of a system, for a number K
    of fine-level classes within a given coarse category, in a dataset of N
    different samples. In addition to the K so-called "complete" tags (i.e.
    with a determinate fine-level category as well as a determinate
    coarse-level category), we consider the potential presence of an "incomplete"
    tag, i.e. denoting the presence of a class with a determinate coarse-level
    category yet no determinate fine-level category. This incomplete tag
    be present in either the prediction or the ground truth.

    Our method for evaluating a multilabel classifier on potentially incomplete
    knowledge of the ground truth consists of two parts, which are ultimately
    aggregated into a single count.

    For the samples with complete knowledge of both ground truth (Part I in the
    code below), we simply apply classwise Boolean logic to compute TP, FP, and
    FN independently for every fine-level tag, and finally aggregate across
    all tags.

    However, for the samples with incomplete knowledge of the ground truth
    (Part II in the code below), we perform a "coarsening" of the prediction by
    apply a disjunction on the fine-level complete tags as well as the
    coarse incomplete tag. If that coarsened prediction is positive, the sample
    produces a true positive; otherwise, it produces a false negative.

    Samples which contain the incomplete tag in the prediction but not the
    ground truth overlap Parts I and II. In this case, we sum the zero, one,
    or multiple false alarm(s) from Part I with the one false alarm from Part II
    to produce a final number of false positives FP.

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
    TP: int
        Number of true positives.

    FP: int
        Number of false positives.

    FN: int
        Number of false negatives.
    """

    ## PART I. SAMPLES WITH COMPLETE GROUND TRUTH AND COMPLETE PREDICTION
    # Negate the true_incomplete Boolean and replicate it K times, where
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


    ## PART II. SAMPLES WITH INCOMPLETE GROUND TRUTH OR INCOMPLETE PREDICTION.
    # Compute a vector of "coarsened predictions".
    # For each sample, the coarsened prediction is equal to 1 if any of the
    # complete fine tags is predicted as present, or if the incomplete fine
    # tag is predicted as present. Conversely, it is set equal to 1 if all
    # of the complete fine tags are predicted as absent, and if the incomplete
    # fine tags are predicted as absent.
    # The result is a (N,) vector.
    y_pred_coarsened_without_incomplete = np.logical_or.reduce(Y_pred, axis=1)
    y_pred_coarsened = np.logical_or(
        y_pred_coarsened_without_incomplete, is_pred_incomplete)

    # Compute true positives for samples with incomplete ground truth.
    # For each sample n, is_TP_incomplete is equal to 1
    # if and only if the following two conditions are met:
    # (i)   the ground truth contains the incomplete fine tag
    # (ii)  the coarsened prediction of sample n contains at least one tag
    # The result is a (N,) vector.
    is_TP_incomplete = np.logical_and(is_true_incomplete, y_pred_coarsened)

    # Compute false positives for samples with incomplete ground truth.
    # For each sample n, is_FP_incomplete is equal to 1
    # if and only if the following two conditions are met:
    # (i)   the incomplete fine tag is absent in the ground truth
    # (ii)  the prediction of sample n contains the incomplete fine tag
    # The result is a (N,) vector.
    is_FP_incomplete = np.logical_and(
        np.logical_not(is_true_incomplete), is_pred_incomplete)

    # Compute false negatives for samples with incomplete ground truth.
    # For each sample n, is_FN_incomplete is equal to 1
    # if and only if the following two conditions are met:
    # (i)   the incomplete fine tag is present in the ground truth
    # (ii)  the coarsened prediction of sample n does not contain any tag
    # The result is a (N,) vector.
    is_FN_incomplete = np.logical_and(
        is_true_incomplete, np.logical_not(y_pred_coarsened))


    ## PART III. AGGREGATE EVALUATION OF ALL SAMPLES
    # The following three sums are performed over NxK Booleans,
    # implicitly converted as integers 0 (False) and 1 (True).
    TP_complete = np.sum(is_TP_complete)
    FP_complete = np.sum(is_FP_complete)
    FN_complete = np.sum(is_FN_complete)

    # The following three sums are performed over N Booleans,
    # implicitly converted as integers 0 (False) and 1 (True).
    TP_incomplete = np.sum(is_TP_incomplete)
    FP_incomplete = np.sum(is_FP_incomplete)
    FN_incomplete = np.sum(is_FN_incomplete)

    # Sum FP, TP, and FN for samples that have complete ground truth
    # with FP, TP, and FN for samples that have incomplete ground truth.
    TP = TP_complete + TP_incomplete
    FP = FP_complete + FP_incomplete
    FN = FN_complete + FN_incomplete
    return TP, FP, FN


def confusion_matrix_coarse(y_true, y_pred):
    """
    Counts overall numbers of true positives (TP), false positives (FP),
    and false negatives (FN) in the predictions of a system, for a single
    Boolean attribute, in a dataset of N different samples.


    Parameters
    ----------
    y_true: array of bool, shape = [n_samples,]
        One-hot encoding of true presence for a given coarse tag.
        y_true[n] is equal to 1 if the tag is present in the sample.

    y_pred: array of bool, shape = [n_samples,]
        One-hot encoding of predicted presence for a given coarse tag.
        y_pred[n] is equal to 1 if the tag is present in the sample.


    Returns
    -------
    TP: int
        Number of true positives.

    FP: int
        Number of false positives.

    FN: int
        Number of false negatives.
    """
    cm = confusion_matrix(y_true, y_pred)
    FP = cm[0, 1]
    FN = cm[1, 0]
    TP = cm[1, 1]
    return TP, FP, FN


def evaluate(prediction_path, annotation_path, yaml_path, mode):
    # Set minimum threshold.
    min_threshold = 0.01

    # Create dictionary to parse tags
    with open(yaml_path, 'r') as stream:
        try:
            yaml_dict = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    # Parse ground truth.
    gf_df = parse_ground_truth(annotation_path, yaml_path)

    # Parse predictions.
    if mode == "fine":
        pred_df = parse_fine_prediction(prediction_path, yaml_path)
    elif mode == "coarse":
        pred_df = parse_coarse_prediction(prediction_path, yaml_path)

    # Initialize dictionary of DataFrames.
    df_dict = {}

    # Loop over coarse categories.
    for coarse_id in yaml_dict["coarse"]:
        # List columns corresponding to that category
        columns = [column for column in pred_df.columns
            if column.startswith(str(coarse_id)) and not column.endswith("X")]

        # Sort columns in alphanumeric order.
        columns.sort()

        # Restrict prediction to columns of interest.
        restricted_pred_df = pred_df[columns]

        # Restrict ground truth to columns of interest.
        restricted_gt_df = gt_df[columns]

        # Aggregate all prediction values into a "raveled" vector.
        thresholds = np.ravel(restricted_pred_df.values)

        # Sort in place.
        thresholds.sort()

        # Skip very low values of the threshold.
        # This is to speed up the computation of the precision-recall curve
        # in the low-precision regime.
        thresholds = thresholds[np.searchsorted(thresholds, min_threshold):]

        # Restrict to unique elements.
        thresholds = np.unique(thresholds)

        # Count number of thresholds.
        n_thresholds = len(thresholds)
        TPs, FPs, FNs = (np.zeros((n_thresholds,).astype('int')),) * 3

        # FINE MODE.
        if mode == "fine":
            incomplete_tag = str(coarse_id) + "-X"

            # Load ground truth as numpy array.
            Y_true = restricted_gt_df.values
            y_true_predicted = restricted_gt_df[incomplete_tag].values

            # Loop over thresholds in a decreasing order.
            for i, threshold in enumerate(reversed(thresholds)):
                # Threshold prediction for complete tag.
                Y_pred = restricted_pred_df.values > threshold

                # Threshold prediction for incomplete tag.
                y_pred_incomplete =\
                    restricted_pred_df[incomplete_tag].values > threshold

                # Evaluate.
                TPs[i], FPs[i], FNs[i] = confusion_matrix_fine(
                    Y_true, Y_pred, is_true_incomplete, is_pred_incomplete)

        # COARSE MODE.
        elif mode == "coarse":
            # Load ground truth as numpy array.
            Y_true = restricted_gt_df.values

            # Loop over thresholds in a decreasing order.
            for i, threshold in enumerate(reversed(thresholds)):
                # Threshold prediction.
                Y_pred = restricted_pred_df.values > threshold

                # Evaluate.
                TPs[i], FPs[i], FNs[i] = confusion_matrix_coarse(Y_true, Y_pred)

        # Build DataFrame from columns.
        eval_df = pd.DataFrame({
            "threshold": thresholds, "TP": TPs, "FP": FPs, "FN": FNs})

        # Add columns for precision, recall, and F1-score.
        # NB: we take the maximum between TPs+FPs and mu=0.5 in the
        # denominator in order to avoid division by zero.
        # This only ever happens if TP+FP < 1, which
        # implies TP = 0 (because TP and FP are nonnegative integers),
        # and therefore a numerator of exactly zero. Therefore, any additive
        # offset mu would do as long as 0 < mu < 1. Choosing mu = 0.5 is
        # purely arbitrary and has no effect on the outcome (i.e. zero).
        mu = 0.5
        eval_df["P"] = TPs / np.maximum(TPs + FPs, 0.5)

        # Likewise for recalls, although this numerical safeguard is probably
        # less necessary given that TP+FN=0 implies that there are zero
        # positives in the ground truth, which is unlikely but no unheard of.
        eval_df["R"] = TPs / np.maximum(TPs + FNs, mu)

        # Compute F1-scores.
        # NB: we use the harmonic mean formula (1/F = 1/P + 1/R) rather than
        # the more common F = (2*P*R)/(P+R) in order circumvent the edge case
        # where both P and R are equal to 0 (i.e. TP = 0).
        eval_df["F"] = 1 / (1/eval_df["P"] + 1/eval_df["R"])

        # Store DataFrame in the dictionary.
        df_dict[coarse_id] = eval_df

    # Return dictionary.
    return df_dict


def micro_averaged_auprc(df_dict, return_df=False):
    """
    Compute micro-averaged area under the precision-recall curve (AUPRC)
    from a dictionary of class-wise DataFrames obtained via `evaluate`.
    """
    # List all unique values of threshold.
    thresholds = np.unique(x["threshold"] for x in df_dict.values())

    # Count number of unique thresholds.
    n_thresholds = len(thresholds)

    # Initialize arrays for TP, FP, and FN
    TPs, FPs, FNs = (np.zeros((n_thresholds,)),) * 3

    # Loop over thresholds.
    for i, threshold in enumerate(thresholds):

        # Initialize counters of TP, FP, and FN across all categories.
        global_TP, global_FP, global_FN = 0, 0, 0

        # Loop over coarse categories.
        for coarse_id in df_dict.keys():

            # Find last row above threshold.
            row = df_dict[coarse_id][df_dict[coarse_id] > threshold].iloc[-1]

            # Increment TP, FP, and FN.
            global_TP += row["TP"]
            global_FP += row["FP"]
            global_FN += row["FN"]

        # Store micro-averaged values of TP, FP, and FN for the given threshold.
        TPs[i] = global_TP
        FPs[i] = global_FP
        FNs[i] = global_FN

    # Build DataFrame from columns.
    eval_df = pd.DataFrame({
        "threshold": thresholds, "TP": TPs, "FP": FPs, "FN": FNs})

    # Add columns for precision, recall, and F1-score.
    # NB: we take the maximum between TPs+FPs and mu = 0.5 in the
    # denominator in order to avoid division by zero.
    # This only ever happens if TP+FP < 1, which
    # implies TP = 0 (because TP and FP are nonnegative integers),
    # and therefore a numerator of exactly zero. Therefore, any additive
    # offset mu would do as long as 0 < mu < 1. Choosing mu = 0.5 is
    # purely arbitrary and has no effect on the outcome (i.e. zero).
    mu = 0.5
    eval_df["P"] = TPs / np.maximum(TPs + FPs, 0.5)

    # Likewise for recalls, although this numerical safeguard is probably
    # less necessary given that TP+FN=0 implies that there are zero
    # positives in the ground truth, which is unlikely but no unheard of.
    eval_df["R"] = TPs / np.maximum(TPs + FNs, mu)

    recalls = np.array([1.0] + list(eval_df["R"]) + [0.0])
    precisions = np.array([0.0] + list(eval_df["P"]) + [1.0])
    auprc = auc(recalls, precisions)

    # If the DataFrame containing the full P-R curve is requested.
    if not return_df:
        # Compute F1-scores.
        # NB: we use the harmonic mean formula (1/F = 1/P + 1/R) rather than
        # the more common F = (2*P*R)/(P+R) in order circumvent the edge case
        # where both P and R are equal to 0 (i.e. TP = 0).
        eval_df["F"] = 1 / (1/eval_df["P"] + 1/eval_df["R"])

        # Return
        return auprc, eval_df
    else:
        # Otherwise, return only the AUPRC as a scalar.
        return auprc



def macro_averaged_auprc(df_dict):
    """
    Compute macro-averaged area under the precision-recall curve (AUPRC)
    from a dictionary of class-wise DataFrames obtaines via `evaluate`.
    """
    # Initialize list of category-wise AUPRCs.
    auprcs = []

    # Loop over coarse categories.
    for coarse_id in df_dict.keys():
        # Load precisions and recalls.
        # NB: we prepend a (1,0) and append a (0,1) to the curve so that the
        # curve reaches the top-left and bottom-right quadrants of the
        # precision-recall square.
        recalls = np.array([1.0] + list(df_dict[coarse_id]["R"]) + [0.0])
        precisions = np.array([0.0] + list(df_dict[coarse_id]["P"]) + [1.0])
        auprcs.append(auc(recalls, precisions))

    # Average AUPRCs across coarse categories with uniform weighting.
    return np.mean(auprcs)


def parse_coarse_prediction(pred_csv_path, yaml_path):
    """
    Parse coarse-level predictions from a CSV file containing both fine-level
    and coarse-level predictions (and possibly additional metadata).
    Returns a Pandas DataFrame in which the column names are coarse
    IDs of the form 1, 2, 3 etc.


    Parameters
    ----------
    pred_csv_path: string
        Path to the CSV file containing predictions.

    yaml_path: string
        Path to the YAML file containing coarse taxonomy.


    Returns
    -------
    pred_coarse_df: DataFrame
        Coarse-level complete predictions.
    """

    # Create dictionary to parse tags
    with open(yaml_path, 'r') as stream:
        try:
            yaml_dict = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    # Collect tag names as strings and map them to coarse ID pairs.
    rev_coarse_dict = {"_".join([k, yaml_dict["coarse"][k]]): k
        for k in yaml_dict["coarse"]}

    # Read comma-separated values with the Pandas library
    pred_df = pd.read_csv(pred_csv_path)

    # Assign a predicted column to each coarse key, by using the tag as an
    # intermediate hashing step.
    pred_coarse_dict = {
        rev_coarse_dict[c]: pred_df[c] for c in rev_coarse_dict}

    # Copy over the audio filename strings corresponding to each sample.
    pred_coarse_dict["audio_filename"] = pred_df["audio_filename"]

    # Build a new Pandas DataFrame with coarse keys as column names.
    pred_coarse_df = pd.DataFrame.from_dict(pred_coarse_dict)

    # Return output in DataFrame format.
    # The column names are of the form 1, 2, 3, etc.
    pred_coarse_df = pred_coarse_df[coarse_columns]
    return pred_coarse_df


def parse_fine_prediction(pred_csv_path, yaml_path):
    """
    Parse fine-level predictions from a CSV file containing both fine-level
    and coarse-level predictions (and possibly additional metadata).
    Returns a Pandas DataFrame in which the column names are mixed (coarse-fine)
    IDs of the form 1-1, 1-2, 1-3, ..., 1-X, 2-1, 2-2, 2-3, ... 2-X, 3-1, etc.


    Parameters
    ----------
    pred_csv_path: string
        Path to the CSV file containing predictions.

    yaml_path: string
        Path to the YAML file containing fine taxonomy.


    Returns
    -------
    pred_fine_df: DataFrame
        Fine-level complete predictions.
    """

    # Create dictionary to parse tags
    with open(yaml_path, 'r') as stream:
        try:
            yaml_dict = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    # Collect tag names as strings and map them to mixed (coarse-fine) ID pairs.
    # The "mixed key" is a hyphenation of the coarse ID and fine ID.
    fine_dict = {}
    for coarse_id in yaml_dict["fine"]:
        for fine_id in yaml_dict["fine"][coarse_id]:
            mixed_key = "-".join([str(coarse_id), str(fine_id)])
            fine_dict[mixed_key] = "_".join([
                mixed_key, yaml_dict["fine"][coarse_id][fine_id]])

    # Invert the key-value relationship between mixed key and tag.
    # Now, tags are the keys, and mixed keys (coarse-fine IDs) are the values.
    # This is possible because tags are unique.
    rev_fine_dict = {fine_dict[k]: k for k in fine_dict}

    # Read comma-separated values with the Pandas library
    pred_df = pd.read_csv(pred_csv_path)

    # Assign a predicted column to each mixed key, by using the tag as an
    # intermediate hashing step.
    pred_fine_dict = {}
    for f in sorted(rev_fine_dict.keys()):
        if f in pred_df:
            pred_fine_dict[rev_fine_dict[f]] = pred_df[f]
        else:
            pred_fine_dict[rev_fine_dict[f]] = np.zeros((len(pred_df),))
            warnings.warn("Column not found: " + f)

    # Loop over coarse tags.
    n_samples = len(pred_df)
    coarse_dict = yaml_dict["coarse"]
    for coarse_id in yaml_dict["coarse"]:
        # Construct incomplete fine tag by appending -X to the coarse tag.
        incomplete_tag = str(coarse_id) + "-X"

        # If the incomplete tag is not in the prediction, append a column of zeros.
        # This is the case e.g. for coarse ID 7 ("dogs") which has a single
        # fine-level tag ("7-1_dog-barking-whining") and thus no incomplete
        # tag 7-X.
        if incomplete_tag not in fine_dict.keys():
            pred_fine_dict[incomplete_tag] =\
                np.zeros((n_samples,)).astype('int')


    # Copy over the audio filename strings corresponding to each sample.
    pred_fine_dict["audio_filename"] = pred_df["audio_filename"]

    # Build a new Pandas DataFrame with mixed keys as column names.
    pred_fine_df = pd.DataFrame.from_dict(pred_fine_dict)

    # Return output in DataFrame format.
    # Column names are 1-1, 1-2, 1-3 ... 1-X, 2-1, 2-2, 2-3 ... 2-X, 3-1, etc.
    return pred_fine_df


def parse_ground_truth(annotation_path, yaml_path):
    """
    Parse ground truth annotations from a CSV file containing both fine-level
    and coarse-level predictions (and possibly additional metadata).
    Returns a Pandas DataFrame in which the column names are coarse
    IDs of the form 1, 2, 3 etc.


    Parameters
    ----------
    annotation_path: string
        Path to the CSV file containing predictions.

    yaml_path: string
        Path to the YAML file containing coarse taxonomy.


    Returns
    -------
    gt_df: DataFrame
        Ground truth.
    """
    # Create dictionary to parse tags
    with open(yaml_path, 'r') as stream:
        try:
            yaml_dict = yaml.load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    # Load CSV file into a Pandas DataFrame.
    ann_df = pd.read_csv(annotation_path)

    # Restrict to ground truth ("annotator zero").
    gt_df = ann_df[ann_df["annotator_id"]==0]

    # Rename coarse columns.
    coarse_dict = yaml_dict["coarse"]
    coarse_renaming = {
        "_".join(["high", "".join(coarse_dict[c].split("-")), "presence"]): str(c)
        for c in coarse_dict}
    gt_df = gt_df.rename(columns=coarse_renaming)

    # Collect tag names as strings and map them to mixed (coarse-fine) ID pairs.
    # The "mixed key" is a hyphenation of the coarse ID and fine ID.
    fine_dict = {}
    for coarse_id in yaml_dict["fine"]:
        for fine_id in yaml_dict["fine"][coarse_id]:
            mixed_key = "-".join([str(coarse_id), str(fine_id)])
            fine_dict[mixed_key] = yaml_dict["fine"][coarse_id][fine_id]

    # Rename fine columns.
    fine_renaming = {"_".join([k, fine_dict[k], "presence"]): k
        for k in fine_dict}
    gt_df = gt_df.rename(columns=fine_renaming)

    # Loop over coarse tags.
    n_samples = len(gt_df)
    coarse_dict = yaml_dict["coarse"]
    for coarse_id in yaml_dict["coarse"]:
        # Construct incomplete fine tag by appending -X to the coarse tag.
        incomplete_tag = str(coarse_id) + "-X"

        # If the incomplete tag is not in the prediction, append a column of zeros.
        # This is the case e.g. for coarse ID 7 ("dogs") which has a single
        # fine-level tag ("7-1_dog-barking-whining") and thus no incomplete
        # tag 7-X.
        if incomplete_tag not in gt_df.columns:
            gt_df[incomplete_tag] = np.zeros((n_samples,)).astype('int')
