import pandas as pd


def parse_oam_excel(file_path):
    df = pd.read_excel(file_path)

    protocols = (
        df["Protocol"]
        .dropna()
        .astype(str)
        .str.strip()
        .str.lower()
        .tolist()
    )

    return protocols, df