import pandas as pd

def load_and_aggregate(csv_path="raw_data/data.csv", hours=72):

    df = pd.read_csv(csv_path, encoding="ISO-8859-1") 
    df = df.dropna(subset=["InvoiceDate", "InvoiceNo"])

    df["InvoiceDate"] = pd.to_datetime(df["InvoiceDate"])
    orders_per_hour = (
        df.drop_duplicates(subset="InvoiceNo")
          .set_index("InvoiceDate")
          .resample("h")
          .size()
    )
    orders_per_hour = orders_per_hour[orders_per_hour > 0].tail(hours)

    result = pd.DataFrame({
        "timestamp": orders_per_hour.index,
        "order_count": orders_per_hour.values,
    }).reset_index(drop=True)

    return result

if __name__ == "__main__":
    df = load_and_aggregate()
    print(df.describe())
    print(df.head(10))
    df.to_csv("data/real_orders_baseline.csv", index=False)
    print(f"\nSaved {len(df)} rows to data/real_orders_baseline.csv")