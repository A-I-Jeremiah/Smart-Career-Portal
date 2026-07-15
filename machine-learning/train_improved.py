"""
Improved training script for Smart-Career-Portal
- Loads cleaned dataset (expects CSV with subject grade columns and 'career_label')
- Performs robust preprocessing, label encoding, stratified CV, grid search for XGBoost
- Saves trained model and label encoder to models/

Usage:
  python ml/train_improved.py --data path/to/dataset.csv --out models/

This script focuses on stronger feature engineering and class-balanced training to reduce wrong recommendations (e.g., science students mapped to arts).
"""

import argparse
import os
import joblib
import pandas as pd
import numpy as np

from sklearn.model_selection import train_test_split, StratifiedKFold, RandomizedSearchCV
from sklearn.pipeline import Pipeline
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OrdinalEncoder, OneHotEncoder
from sklearn.metrics import classification_report, accuracy_score
from xgboost import XGBClassifier


def load_data(path):
    df = pd.read_csv(path)
    return df


def simple_feature_engineering(df):
    # Expecting subject score columns like 'mathematics','physics',... convert to numeric and impute
    subject_cols = [c for c in df.columns if c.lower() not in ('career_label','career')]
    for c in subject_cols:
        df[c] = pd.to_numeric(df[c], errors='coerce').fillna(df[c].median())

    # Add aggregates
    df['subject_mean'] = df[subject_cols].mean(axis=1)
    df['subject_std'] = df[subject_cols].std(axis=1).fillna(0.0)
    df['strong_subjects'] = (df[subject_cols] >= 75).sum(axis=1)
    df['weak_subjects'] = (df[subject_cols] < 50).sum(axis=1)

    return df, subject_cols + ['subject_mean', 'subject_std', 'strong_subjects', 'weak_subjects']


def train(args):
    df = load_data(args.data)
    if 'career_label' not in df.columns and 'career' in df.columns:
        df['career_label'] = df['career']

    df, feature_cols = simple_feature_engineering(df)
    X = df[feature_cols]
    y = df['career_label']

    # Encode target labels
    from sklearn.preprocessing import LabelEncoder
    le = LabelEncoder()
    y_enc = le.fit_transform(y.astype(str))

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(X, y_enc, test_size=0.2, stratify=y_enc, random_state=42)

    # Use XGB with balanced class weight via scale_pos_weight estimation per class (approx)
    classes, counts = np.unique(y_train, return_counts=True)
    class_weights = {c: (len(y_train) / (len(classes) * counts[i])) for i, c in enumerate(classes)}

    # Sample model and hyperparams
    model = XGBClassifier(objective='multi:softprob', eval_metric='mlogloss', use_label_encoder=False, tree_method='hist', random_state=42, n_jobs=-1)

    param_dist = {
        'n_estimators': [100, 200, 300],
        'max_depth': [3, 5, 7],
        'learning_rate': [0.01, 0.05, 0.1],
        'subsample': [0.6, 0.8, 1.0],
        'colsample_bytree': [0.6, 0.8, 1.0],
    }

    cv = StratifiedKFold(n_splits=4, shuffle=True, random_state=42)
    search = RandomizedSearchCV(model, param_distributions=param_dist, n_iter=12, n_jobs=-1, cv=cv, scoring='accuracy', random_state=42, verbose=2)

    print('Starting hyperparameter search...')
    search.fit(X_train, y_train)

    print('Best params:', search.best_params_)
    best = search.best_estimator_

    # Evaluate
    y_pred = best.predict(X_test)
    print('Test accuracy:', accuracy_score(y_test, y_pred))
    print('Classification report:\n', classification_report(y_test, y_pred, target_names=le.classes_))

    # Save model and label encoder
    os.makedirs(args.out, exist_ok=True)
    joblib.dump(best, os.path.join(args.out, 'xgb_improved_model.pkl'))
    joblib.dump(le, os.path.join(args.out, 'label_encoder.pkl'))
    print('Saved model and label encoder to', args.out)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--data', required=True, help='Path to training CSV')
    parser.add_argument('--out', default='ml/models', help='Output directory for model artifacts')
    args = parser.parse_args()
    train(args)
