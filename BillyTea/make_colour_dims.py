"""
make_colour_dims.py  --  colour-lock helper tables for Power BI
===============================================================
Writes dim_year.csv and dim_product.csv next to the Pax master. In Power BI,
use "Format by field value" on each visual's colours, pointing at [Hex], so a
given year/product ALWAYS renders in the same colour on every chart, regardless
of how many years a chart shows (the theme palette alone can't guarantee this
because it maps by series ORDER, not value).
"""
import os
import csv

DEST_DIR = r"C:\Users\penny\Down Under Cruise and Dive\Files - DUD-SHARED\Accounts\Month End\END OF MONTH\MONTH END - BILLY TEA\Billy Tea Month End"

# recent years vivid + colourblind-aware (Okabe-Ito); older years recede to grey
YEAR_HEX = {
    2026: "#000000", 2025: "#E69F00", 2024: "#D55E00", 2023: "#009E73",
    2022: "#56B4E9", 2021: "#CC79A7", 2020: "#9E9E9E",
}
OLD_GREY = "#D6D6D6"

def write_years():
    p = os.path.join(DEST_DIR, "dim_year.csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Year", "Hex"])
        for y in range(2010, 2027):
            w.writerow([y, YEAR_HEX.get(y, OLD_GREY)])
    print("wrote", p)

def write_products():
    p = os.path.join(DEST_DIR, "dim_product.csv")
    with open(p, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["Product", "Hex"])
        w.writerow(["Daintree Cape Tribulation", "#2E7D32"])  # rainforest green
        w.writerow(["Chillagoe Caves", "#B7791F"])            # outback ochre
    print("wrote", p)

if __name__ == "__main__":
    write_years()
    write_products()
