"""
model.py
---------
Trains a Random Forest classifier on the irrigation dataset.

Future Scope:
- Serialize model with joblib for persistent storage
- Add cross-validation and hyperparameter tuning
- Deploy model as a local REST API (Flask/FastAPI) for embedded systems
"""

from sklearn.ensemble import RandomForestClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, classification_report
import pandas as pd


def train_model(X, y, model_type="random_forest", test_size=0.2, random_state=42):
    """
    Trains a classifier on the given feature matrix and labels.

    Parameters:
        X (pd.DataFrame): Feature matrix
        y (pd.Series): Target labels
        model_type (str): "random_forest" or "decision_tree"
        test_size (float): Fraction of data for testing
        random_state (int): Seed for reproducibility

    Returns:
        model, X_test, y_test, accuracy
    """

    # Train/test split
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )

    # Select model
    if model_type == "decision_tree":
        model = DecisionTreeClassifier(max_depth=6, random_state=random_state)
        model_name = "Decision Tree"
    else:
        model = RandomForestClassifier(
            n_estimators=100,
            max_depth=8,
            random_state=random_state,
            n_jobs=-1
        )
        model_name = "Random Forest"

    # Train
    print(f"[..] Training {model_name} model...")
    model.fit(X_train, y_train)

    # Evaluate
    y_pred = model.predict(X_test)
    accuracy = accuracy_score(y_test, y_pred)

    print(f"\n{'='*50}")
    print(f"  Model      : {model_name}")
    print(f"  Train Size : {len(X_train)} samples")
    print(f"  Test Size  : {len(X_test)} samples")
    print(f"  Accuracy   : {accuracy * 100:.2f}%")
    print(f"{'='*50}")
    print("\n[Classification Report]")
    print(classification_report(y_test, y_pred, target_names=["No Irrigation", "Irrigation Needed"]))

    # Feature importances (Random Forest only)
    if model_type == "random_forest":
        features = X.columns.tolist()
        importances = model.feature_importances_
        fi_df = pd.DataFrame({"Feature": features, "Importance": importances})
        fi_df = fi_df.sort_values("Importance", ascending=False)
        print("[Feature Importances]")
        for _, row in fi_df.iterrows():
            bar = "#" * int(row["Importance"] * 40)
            print(f"  {row['Feature']:<18} {bar} {row['Importance']:.4f}")
        print()

    return model, X_test, y_test, accuracy


def predict_irrigation(model, encoded_input):
    """
    Runs a single prediction using the trained model.

    Parameters:
        model: Trained sklearn model
        encoded_input (list): Encoded feature row

    Returns:
        prediction (int): 0 = No irrigation, 1 = Yes
        confidence (float): Model confidence %
    """
    features = ["Temperature", "Humidity", "Rain_Enc", "Soil_Moisture", "Crop_Enc"]
    input_df = pd.DataFrame(encoded_input, columns=features)
    prediction = model.predict(input_df)[0]

    # Confidence score
    if hasattr(model, "predict_proba"):
        proba = model.predict_proba(input_df)[0]
        confidence = max(proba) * 100
    else:
        confidence = None

    return prediction, confidence
