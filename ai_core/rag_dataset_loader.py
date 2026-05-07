# rag_dataset_loader.py

import csv
from typing import List, Dict


def load_attractions_dataset(csv_path: str) -> List[Dict]:
    """
    Converts CSV rows into RAG-ready documents.
    """
    docs = []

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            text = (
                f"Place: {row['place']}\n"
                f"City: {row['city']}\n"
                f"Category: {row['category']}\n"
                f"Entrance Fee: INR {row['entrance_fee']}\n"
                f"Description: {row['description']}"
            )

            docs.append(
                {
                    "content": text,
                    "title": row["place"],
                    "city": row["city"],
                    "source": "dataset",
                }
            )

    return docs
