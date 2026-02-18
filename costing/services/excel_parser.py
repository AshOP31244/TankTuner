import pandas as pd
from .material_mapping import MATERIAL_MAPPING


def parse_excel(file_path):
    """
    Reads Excel and returns structured data:
    {
      product: {
        model_name: model_data
      }
    }
    """

    # ✅ Read Excel, skip first 4 rows (header rows)
    # Row 5 onwards contains actual tank model data
    df = pd.read_excel(file_path, skiprows=4, header=None)
    
    # ✅ Drop completely empty rows
    df = df.dropna(how='all')
    
    # ✅ Reset index
    df = df.reset_index(drop=True)
    
    print("🔍 First 3 data rows:")
    print(df.head(3).iloc[:, :10])  # Show first 10 columns only

    parsed_data = {}

    for idx, row in df.iterrows():
        
        # ✅ Model name is in column 0
        model_name = row[0]
        
        # ✅ Product type (hardcoded for RCT, can be extended later)
        product_type = "RCT"
        
        if pd.isna(model_name) or str(model_name).strip() == '':
            continue

        model_obj = {
            "product": product_type,
            "model": str(model_name).strip(),
            "materials": [],
            "final_cost": 0
        }

        total_cost = 0

        # ✅ Extract each material using column indices
        for material_name, config in MATERIAL_MAPPING.items():
            try:
                qty = row[config["qty_col_idx"]]
                rate = row[config["rate_col_idx"]]
                
                # Skip if qty or rate is missing
                if pd.isna(qty) or pd.isna(rate):
                    continue
                
                # Calculate material total
                material_total = float(qty) * float(rate)

                model_obj["materials"].append({
                    "name": material_name,
                    "quantity": float(qty),
                    "rate": float(rate),
                    "unit": config["unit"],
                    "total": material_total
                })

                total_cost += material_total
                
            except (IndexError, KeyError, ValueError) as e:
                # Skip materials that don't exist in this row
                continue

        model_obj["final_cost"] = total_cost

        parsed_data.setdefault(product_type, {})
        parsed_data[product_type][str(model_name).strip()] = model_obj

    print(f"\n✅ Parsed {sum(len(models) for models in parsed_data.values())} models")
    print(f"✅ Products: {list(parsed_data.keys())}")
    
    return parsed_data
