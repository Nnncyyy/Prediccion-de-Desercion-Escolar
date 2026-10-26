"""Entrena sin data leakage; NO incorpora datos laborales ausentes en CSV."""
import argparse
from pathlib import Path
import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.impute import SimpleImputer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--csv',required=True)
    parser.add_argument('--out',required=True)
    args=parser.parse_args()
    df=pd.read_csv(args.csv)
    if 'Target' not in df.columns: raise ValueError('Falta Target')
    df=df.dropna(subset=['Target']).copy()
    X=df.drop(columns=['Target']);y=df['Target']
    numeric=X.select_dtypes(include='number').columns.tolist()
    categorical=[c for c in X.columns if c not in numeric]
    preprocess=ColumnTransformer([
        ('num',Pipeline([('fill',SimpleImputer(strategy='median')),('scale',StandardScaler())]),numeric),
        ('cat',Pipeline([('fill',SimpleImputer(strategy='most_frequent')),('encode',OneHotEncoder(handle_unknown='ignore'))]),categorical)
    ])
    model=Pipeline([('preprocess',preprocess),('classifier',LogisticRegression(max_iter=1500,class_weight='balanced',random_state=42))])
    X_train,X_test,y_train,y_test=train_test_split(X,y,test_size=.2,stratify=y,random_state=42)
    model.fit(X_train,y_train)
    pred=model.predict(X_test)
    print(classification_report(y_test,pred,zero_division=0))
    print('Clases:',list(model.classes_))
    print('Matriz de confusión:\n',confusion_matrix(y_test,pred,labels=model.classes_))
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    joblib.dump({'pipeline':model,'columns':list(X.columns),'numeric_columns':numeric,'model_name':'LogisticRegression-balanced-v0.1'},out)
    print('Modelo guardado en',out)

if __name__=='__main__':main()
