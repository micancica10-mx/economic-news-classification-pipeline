"""Train economic-news classifiers and label newly collected articles.

Private inputs (not distributed): labeled training data and a Spanish stopword list.
Run from any working directory; all paths are provided as arguments.
"""

from __future__ import annotations

import argparse
import re
import string
from pathlib import Path

import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.svm import SVC


def clean_text(text: object) -> str:
    """Apply the same basic normalization to training and prediction text."""
    if pd.isna(text):
        return ""
    text = str(text).lower()
    text = re.sub(r"http\S+", "", text)
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\d+", "", text)
    return " ".join(text.split())


def load_stopwords(path: Path) -> list[str]:
    """Read the user-supplied Spanish stopword list from its 'palabra' column."""
    frame = pd.read_excel(path)
    if "palabra" not in frame:
        raise ValueError("Stopword file must contain a 'palabra' column.")
    return frame["palabra"].dropna().astype(str).str.strip().str.lower().tolist()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--training", type=Path, required=True,
                        help="Private labeled Excel file with 'texto' and 'econ' columns")
    parser.add_argument("--stopwords", type=Path, required=True,
                        help="Spanish stopword Excel file with a 'palabra' column")
    parser.add_argument("--input", type=Path, required=True,
                        help="Consolidated news Excel file with a 'texto' column")
    parser.add_argument("--output", type=Path, default=Path("clasificacion_texto.xlsx"))
    args = parser.parse_args()

    training = pd.read_excel(args.training)
    incoming = pd.read_excel(args.input)
    if not {"texto", "econ"}.issubset(training.columns):
        raise ValueError("Training data must contain 'texto' and 'econ'.")
    if "texto" not in incoming.columns:
        raise ValueError("Input data must contain 'texto'.")

    training = training.dropna(subset=["texto", "econ"]).copy()
    if training["econ"].nunique() < 2:
        raise ValueError("Training data must contain at least two distinct classes.")

    training_texts = training["texto"].map(clean_text)
    training_labels = training["econ"]
    stopwords = load_stopwords(args.stopwords)

    # Fit TF-IDF on the training partition only to prevent test-set leakage.
    # A 20% holdout gives more informative diagnostics than the original 1% split.
    x_train_text, x_test_text, y_train, y_test = train_test_split(
        training_texts, training_labels, test_size=0.20, random_state=100,
        stratify=training_labels,
    )
    vectorizer = TfidfVectorizer(stop_words=stopwords)
    x_train = vectorizer.fit_transform(x_train_text)
    x_test = vectorizer.transform(x_test_text)

    # L1-regularized logistic regression (the original l1_ratio=1 specification).
    logit = LogisticRegression(penalty="l1", C=1, solver="saga", max_iter=2000,
                               random_state=100)
    # Linear-kernel support vector machine with balanced class weights.
    svm = SVC(C=1, gamma=0.1, kernel="linear", class_weight="balanced")

    for name, model in (("Logistic regression", logit), ("SVM", svm)):
        model.fit(x_train, y_train)
        predicted = model.predict(x_test)
        print(f"\n{name} — holdout evaluation")
        print(classification_report(y_test, predicted, zero_division=0))
        print(confusion_matrix(y_test, predicted))

    # Refit on all labeled observations before classifying new articles.
    vectorizer = TfidfVectorizer(stop_words=stopwords)
    full_features = vectorizer.fit_transform(training_texts)
    logit.fit(full_features, training_labels)
    svm.fit(full_features, training_labels)

    # Use identical preprocessing for training and newly collected articles.
    new_features = vectorizer.transform(incoming["texto"].map(clean_text))
    incoming["econ_logit"] = logit.predict(new_features)
    incoming["econ_svm"] = svm.predict(new_features)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    incoming.to_excel(args.output, index=False)
    print(f"Saved {len(incoming)} classified articles to {args.output}")


if __name__ == "__main__":
    main()
