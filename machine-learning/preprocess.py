# preprocess.py
from typing import Dict, Any
import pandas as pd
import numpy as np
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OrdinalEncoder
import joblib
from pathlib import Path


class CareerDataPreprocessor:
    """
    Handles data preprocessing. Now with safer fitting and type handling.
    """
    
    def __init__(self):
        self.grade_map = {'A': 8, 'B': 6, 'C': 5, 'D': 3, 'E': 2, 'F': 1, 'Unknown': 5}
        
        self.categorical_columns = [
            'gender', 'school_type', 'department', 'academic_strength',
            'best_subject_category', 'confidence_level', 'career_influence'
        ] + [
            'mathematics', 'english', 'civic_education', 'physics', 'chemistry', 'biology',
            'further_mathematics', 'agricultural_science', 'geography', 'technical_drawing',
            'computer_studies', 'yoruba', 'igbo_hausa', 'data_processing',
            'literature_in_english', 'christian_religious_studies/islamic_studies',
            'creative_arts', 'economics', 'financial_accounting', 'commerce',
            'government', 'marketing'
        ]
        
        self.numerical_columns = [
            'waec_year', 'waec_credits', 'cgpa', 'course_alignment',
            'aptitude_score_10', 'cognitive_score_10', 'psychometric_avg_5', 
            'sentiment_avg_5', 'age'
        ]
        
        self.preprocessor = None
        self.is_fitted = False

    def clean_input_data(self, data: Dict[str, Any]) -> pd.DataFrame:
        """Clean single student input."""
        df = pd.DataFrame([data])
        df.columns = df.columns.str.strip().str.lower().str.replace(' ', '_', regex=False)
        
        # Drop unused columns
        drop_cols = ['french', 'history', 'age_group']
        for col in drop_cols:
            if col in df.columns:
                df = df.drop(columns=[col])
        
        # Generate age if missing
        if 'age' not in df.columns:
            df['age'] = np.random.randint(17, 25, size=len(df))
        
        # Fill missing columns
        all_expected = self.categorical_columns + self.numerical_columns
        for col in all_expected:
            if col not in df.columns:
                if col in self.numerical_columns:
                    df[col] = 0.0 if col != 'waec_credits' else 5.0
                else:
                    df[col] = 'Unknown'
        
        # Grade mapping (ensure string)
        grade_cols = [col for col in self.categorical_columns 
                     if col not in ['gender','school_type','department',
                                    'academic_strength','best_subject_category',
                                    'confidence_level','career_influence']]
        
        for col in grade_cols:
            if col in df.columns:
                df[col] = df[col].astype(str).str.upper().map(self.grade_map).fillna(5)
        
        # Convert numericals
        for col in self.numerical_columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0.0)
        
        return df

    def fit(self, df: pd.DataFrame):
        """Fit preprocessor safely."""
        if self.preprocessor is None:
            self.preprocessor = ColumnTransformer(transformers=[
                ('num', StandardScaler(), self.numerical_columns),
                ('cat', OrdinalEncoder(handle_unknown='use_encoded_value', unknown_value=-1), 
                 self.categorical_columns)
            ])
        
        feature_cols = self.categorical_columns + self.numerical_columns
        
        # Ensure categorical columns are strings
        for col in self.categorical_columns:
            if col in df.columns:
                df[col] = df[col].astype(str)
        
        self.preprocessor.fit(df[feature_cols])
        self.is_fitted = True
        print("✅ Preprocessor fitted successfully.")
        return self

    def transform(self, df: pd.DataFrame):
        """Transform data. Auto-fit if needed."""
        if not self.is_fitted:
            print("⚠️  Preprocessor not fitted. Fitting on safe dummy data...")
            dummy = self.clean_input_data({
                'Gender': 'Male', 'School_Type': 'Government School', 'Department': 'Science',
                'Mathematics': 'C', 'English': 'C', 'Civic Education': 'C',
                'Academic_Strength': 'Average', 'Best_Subject_Category': 'Science',
                'Confidence_Level': 'Somewhat confident', 'Career_Influence': 'Personal passion'
            })
            self.fit(dummy)
        
        feature_cols = self.categorical_columns + self.numerical_columns
        
        # Ensure categorical are strings before transform
        for col in self.categorical_columns:
            if col in df.columns:
                df[col] = df[col].astype(str)
        
        return self.preprocessor.transform(df[feature_cols])


# Global instance
preprocessor = CareerDataPreprocessor()