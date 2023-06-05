import json
import pandas as pd


def fetch_json_data(path: str) -> dict:
    """
    Get json file data
    """
    with open(path, "r") as json_file:
        data_dict = json.load(json_file)
        return data_dict


def fetch_prices(prices_path: str, hotel_name: str = None, worker=None) -> pd.DataFrame:
    hotel_name = hotel_name if hotel_name else "NO-HOTEL-NAME"
    message = f"{hotel_name} : Récupération du positionnement tarifaire"
    if worker is not None:
        worker.emit_signals(message, message)
    else:
        print(message)

    # Open and format the df containing prices
    df_prices = pd.read_excel(prices_path)
    df_prices.dropna(inplace=True)
    df_prices["Date"] = df_prices["Date"].dt.date
    df_prices = df_prices[["Date", "Price"]]

    return df_prices


# def try_to_open_file(path: str, mode: str):
#     """
#     Open a file with exception handling
#     """
#     try:
#         file = open(path, mode)
#     except FileNotFoundError:
#         print("file not found at", path)
#         return False
#     except Exception:
#         print("Error occured trying to open file at", path)
#         return False
#     else:
#         return file
