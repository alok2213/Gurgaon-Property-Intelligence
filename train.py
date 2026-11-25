"""Retrain the price model and refresh artifacts/ (run after changing data/model_data.csv)."""
import services

if __name__ == "__main__":
    print(services.train_model())
