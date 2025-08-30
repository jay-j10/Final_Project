import pandas as pd

def predict_next_counts(df, gate, horizon=5):
    """
    Predict next crowd counts for given gate using EWMA.
    horizon = how many future steps to forecast (in minutes/steps).
    """
    if gate not in df.columns:
        return []

    # Smooth the data
    series = df[gate].ewm(span=5).mean()

    # Take last value as trend base
    last_val = series.iloc[-1]
    trend = series.diff().mean()  # avg change per step

    # Forecast next 'horizon' steps
    forecast = [max(0, last_val + (i+1) * trend) for i in range(horizon)]
    return forecast
